from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import yaml
import os
import sys
import socket

# ---------------------------------------------------------
# 設定來源整合與環境配置
# ---------------------------------------------------------
sys.path.append(os.getcwd())

try:
    # 嘗試從 status_players.py 匯入 CONFIG_PATH
    from status_players import CONFIG_PATH
    print(f"成功載入設定檔路徑: {CONFIG_PATH}")
except ImportError:
    CONFIG_PATH = 'players.yml'
    print(f"警告: 找不到 status_players.py，使用預設路徑: {CONFIG_PATH}")

app = Flask(__name__)

def load_players_data():
    """讀取完整的 YAML 資料結構"""
    if not os.path.exists(CONFIG_PATH):
        return {'players': []}
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                if isinstance(data, list):
                    return {'players': data}
                return {'players': []}
            if 'players' not in data:
                data['players'] = []
            return data
    except Exception as e:
        print(f"讀取 YAML 失敗: {e}")
        return {'players': []}

def save_players_data(data):
    """儲存 YAML 資料，保持格式相容"""
    try:
        directory = os.path.dirname(CONFIG_PATH)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"寫入 YAML 失敗: {e}")

def check_status(ip_port):
    """簡單測試連線狀態 (Timeout 0.5s)"""
    try:
        if ':' not in ip_port: return 'Offline'
        ip, port = ip_port.split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5) 
        result = sock.connect_ex((ip, int(port)))
        sock.close()
        return 'Online' if result == 0 else 'Offline'
    except:
        return 'Offline'

# ---------------------------------------------------------
# 路由設定
# ---------------------------------------------------------

@app.route('/')
def root():
    return redirect(url_for('players_page'))

@app.route('/players', methods=['GET'])
def players_page():
    full_data = load_players_data()
    players = full_data.get('players', [])
    
    safe_players = []
    for player in players:
        if not isinstance(player, dict): continue
        if 'system' not in player: player['system'] = ''
        if 'name' not in player: player['name'] = 'Unknown'
        if 'ip_port' not in player: player['ip_port'] = '0.0.0.0:0'
        player['status'] = check_status(player['ip_port'])
        player['last_checked'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_players.append(player)

    return render_template('players.html', players=safe_players)

@app.route('/add', methods=['POST'])
def add_player():
    system = request.form.get('system', '').strip()
    name = request.form.get('name', '').strip()
    ip_port = request.form.get('ip_port', '').strip()
    
    if name and ip_port:
        full_data = load_players_data()
        full_data['players'].append({
            'system': system,
            'name': name, 
            'ip_port': ip_port
        })
        save_players_data(full_data)
    return redirect(url_for('players_page'))

@app.route('/edit_player', methods=['POST'])
def edit_player():
    original_name = request.form.get('original_name')
    new_system = request.form.get('system')
    new_name = request.form.get('name')
    new_ip_port = request.form.get('ip_port')
    
    full_data = load_players_data()
    players = full_data.get('players', [])
    
    found = False
    for player in players:
        if player.get('name') == original_name:
            player['system'] = new_system
            player['name'] = new_name
            player['ip_port'] = new_ip_port
            found = True
            break
    if found:
        save_players_data(full_data)
    return redirect(url_for('players_page'))

@app.route('/delete/<name>')
def delete_player(name):
    full_data = load_players_data()
    players = full_data.get('players', [])
    new_players = [p for p in players if p.get('name') != name]
    full_data['players'] = new_players
    save_players_data(full_data)
    return redirect(url_for('players_page'))

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:80/players")
    app.run(debug=True, host='0.0.0.0', port=80)