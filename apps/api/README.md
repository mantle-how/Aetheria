# Aetheria Demo Web API

## 簡介
`apps/api/main.py` 是 Web 傳輸層，負責提供頁面、WebSocket 推流與控制指令轉發：
- `GET /`：Web 前端頁面（Canvas Topdown + Dashboard）。
- `WS /ws/sim`：30 FPS 推送模擬 snapshot，並接收控制指令。

## 控制指令
WebSocket 支援下列 JSON 指令：
- `{"cmd":"play"}`
- `{"cmd":"pause"}`
- `{"cmd":"toggle"}`
- `{"cmd":"step"}`
- `{"cmd":"reset"}`

## Snapshot
目前 snapshot 除了世界與代理人資料外，還包含：
- `world_revision`：每次重置世界後自增，前端可用來清空舊動畫與歷史資料。

## 執行方式
1. `pip install -r requirements.txt`
2. `python view/demo.py`
