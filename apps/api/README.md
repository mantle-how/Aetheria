# Aetheria Demo Web API

## 簡介
`apps/api/main.py` 提供 Web 視覺化所需的 API 與即時推流：
- `GET /`：Web 前端頁面（Canvas Topdown + Dashboard）。
- `WS /ws/sim`：30 FPS 推送模擬 snapshot，並接收控制指令。

## 控制指令
WebSocket 支援下列 JSON 指令：
- `{"cmd":"play"}`
- `{"cmd":"pause"}`
- `{"cmd":"toggle"}`
- `{"cmd":"step"}`

## 執行方式
1. `pip install -r requirements.txt`
2. `python view/demo.py`
