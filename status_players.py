# -*- coding: utf-8 -*-
import os
import time
import socket
import threading
import logging
from typing import List, Dict, Any

import yaml
import tempfile
import json
from flask import Blueprint, jsonify, render_template, request
from urllib.parse import unquote

players_bp = Blueprint("players", __name__)

# 可調參數（亦可用環境變數覆寫）
CONFIG_PATH = os.environ.get("PLAYER_CONFIG_PATH", "/opt/status-monitor/config/players.yml")
CHECK_INTERVAL = int(os.environ.get("PLAYER_CHECK_INTERVAL", "5"))       # 每幾秒檢查一次
CONNECT_TIMEOUT = float(os.environ.get("PLAYER_CONNECT_TIMEOUT", "1.0")) # 單次 TCP 連線逾時秒數

log = logging.getLogger("players")
log.setLevel(logging.INFO)

_state_lock = threading.Lock()
_state: Dict[str, Any] = {
    "players": [],          # 例：[{name, ip_port, status, latency_ms, last_checked}]
    "updated_at": None,
}
_cfg_mtime: float = 0.0
_cfg_players: List[Dict[str, str]] = []
_checker_started = False


# 讀取現有 YAML（維持 players: [...] 結構）
def _read_cfg_dict() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    if "players" not in data or not isinstance(data["players"], list):
        data["players"] = []
    return data

# 安全原子寫入，避免半寫入破檔
def _write_cfg_dict(cfg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    dirpath = os.path.dirname(CONFIG_PATH) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dirpath, encoding="utf-8") as tf:
        yaml.safe_dump(cfg, tf, allow_unicode=True, sort_keys=False)
        tmpname = tf.name
    os.replace(tmpname, CONFIG_PATH)
    # 讓 checker 下輪強制重載
    global _cfg_mtime
    _cfg_mtime = 0.0

@players_bp.route("/api/players", methods=["POST"])
def api_players_add():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    ip_port = str(payload.get("ip_port", "")).strip()
    if not ip_port or ":" not in ip_port:
        return ("ip_port 格式不正確，應為 host:port", 400)
    if not name:
        name = ip_port.split(":", 1)[0]

    cfg = _read_cfg_dict()
    if any(p.get("ip_port") == ip_port for p in cfg["players"]):
        return ("該主機已存在", 409)

    cfg["players"].append({"name": name, "ip_port": ip_port})
    _write_cfg_dict(cfg)
    return jsonify({"status": "ok"}), 201

# 用 <path:ip_port> 才能包含冒號
@players_bp.route("/api/players/<path:ip_port>", methods=["DELETE"])
def api_players_delete(ip_port):
    ip_port = unquote(ip_port)
    cfg = _read_cfg_dict()
    new_list = [p for p in cfg["players"] if p.get("ip_port") != ip_port]
    if len(new_list) == len(cfg["players"]):
        return ("找不到該主機", 404)
    cfg["players"] = new_list
    _write_cfg_dict(cfg)
    return jsonify({"status": "deleted"})


def _load_config() -> List[Dict[str, str]]:
    global _cfg_mtime
    try:
        st = os.stat(CONFIG_PATH)
    except FileNotFoundError:
        log.warning("Config not found: %s", CONFIG_PATH)
        return []

    # 檔案未變更則沿用
    if _cfg_mtime == st.st_mtime:
        return _cfg_players

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    players = data.get("players", []) or []
    # 基本正規化
    norm = []
    for p in players:
        name = str(p.get("name", "")).strip()
        ip_port = str(p.get("ip_port", "")).strip()
        if not name or not ip_port or ":" not in ip_port:
            log.warning("Skip invalid player entry: %s", p)
            continue
        norm.append({"name": name, "ip_port": ip_port})
    _cfg_mtime = st.st_mtime
    log.info("Loaded %d players from %s", len(norm), CONFIG_PATH)
    return norm


def _probe(ip_port: str) -> Dict[str, Any]:
    host, port_str = ip_port.rsplit(":", 1)
    port = int(port_str)
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), CONNECT_TIMEOUT):
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {"status": "online", "latency_ms": latency_ms}
    except Exception:
        return {"status": "offline", "latency_ms": None}


def _checker_loop():
    global _cfg_players
    while True:
        try:
            _cfg_players = _load_config()
            results = []
            ts = int(time.time())
            for p in _cfg_players:
                res = _probe(p["ip_port"])
                results.append({
                    "name": p["name"],
                    "ip_port": p["ip_port"],
                    "status": res["status"],
                    "latency_ms": res["latency_ms"],
                    "last_checked": ts
                })
            with _state_lock:
                _state["players"] = results
                _state["updated_at"] = ts
        except Exception as e:
            log.exception("Checker loop error: %s", e)
        time.sleep(CHECK_INTERVAL)


def start_checker_once():
    global _checker_started
    if _checker_started:
        return
    t = threading.Thread(target=_checker_loop, name="players-checker", daemon=True)
    t.start()
    _checker_started = True


@players_bp.route("/players")
def page_players():
    # 簡單 HTML，資料由前端 JS 打 /api/players 取得
    return render_template("players.html")


@players_bp.route("/api/players")
def api_players():
    with _state_lock:
        return jsonify({
            "players": _state["players"],
            "updated_at": _state["updated_at"],
            "interval_sec": CHECK_INTERVAL,
            "timeout_sec": CONNECT_TIMEOUT
        })
