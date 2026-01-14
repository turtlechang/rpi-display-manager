# 電視輪播後台管理系統 (TV Carousel Manager)

這是一個基於 Flask 的網頁後台管理系統，用於管理和監控電視輪播播放器（Players）的狀態。

## 功能特色

- **主機列表監控**：即時顯示所有播放器的連線狀態（Online/Offline）。
- **新增/編輯/刪除**：透過網頁介面輕鬆管理播放器資料（體系、名稱、IP:Port）。
- **快速篩選**：可依照「體系」篩選顯示的主機。
- **連線測試**：系統會自動測試 TCP 連線以確認主機是否存活。

## 環境需求

- Python 3.x
- Flask
- PyYAML

## 安裝與執行

1. **安裝依賴套件**
   ```bash
   pip install flask pyyaml
   ```

2. **啟動伺服器**
   ```bash
   python app.py
   ```
   或是若需要後台檢查功能：
   ```bash
   python status_players.py
   ```
   *(註：具體啟動方式視您的部署架構而定，`app.py` 為主要網頁入口)*

3. **使用系統**
   開啟瀏覽器訪問：`http://localhost:80/players` (預設埠號為 80)

## 設定檔

資料儲存於 `players.yml`，格式如下：

```yaml
players:
  - system: "體系名稱"
    name: "主機名稱"
    ip_port: "192.168.1.100:5000"
```

## 檔案結構

- `app.py`: 主要 Flask 應用程式邏輯。
- `templates/players.html`: 前端網頁樣板 (Bootstrap 5)。
- `players.yml`: 播放器資料儲存檔。
- `status_players.py`: 包含後端檢查邏輯與 API (若有使用 Blueprint 架構)。
