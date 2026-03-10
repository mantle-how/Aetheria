# 視圖層說明

`view/` 是展示層，負責把模擬資料畫出來，不應承載領域決策邏輯。

目前預設路徑已切換為 Web 視覺化：
- `view/demo.py` 啟動 Uvicorn，對外提供 `apps.api.main`
- 前端以 WebSocket 接收即時 snapshot，並在 Canvas 繪製 Topdown + Dashboard

## 檔案
- `demo.py`：可直接執行的 Web 入口（FastAPI/Uvicorn）。
- `legacy_entities.py`：提供舊版 Tk 視覺化可直接繪製的 entity helper。
- `topdown.py`：舊版 `tkinter` 視覺化（legacy/deprecated）。

## demo.py
`view/demo.py` 會直接啟動 Web 服務，預設：
1. 後端模擬以 30 tick/s 推進。
2. WebSocket `/ws/sim` 以 30 FPS 推送狀態。
3. 前端在瀏覽器繪製俯視圖與代理人儀表板。

常用啟動方式：
```bash
python view/demo.py
```

## legacy_entities.py
這個模組提供給舊版 Tk 視圖使用的 helper：
- `Entity`
- `InteractiveEntity`
- `simulation_to_entities()`
- `generate_demo_entities()`

## topdown.py
`TopDownVisualizer`（舊版）支援：
- `show(entities)`：顯示靜態畫面
- `show_live(...)`：依時間間隔持續更新畫面，並同步更新代理人儀表板

## 分層邊界
若未來更換 UI 技術，這個資料夾應是主要替換點。領域邏輯應留在 `domain/`，runtime orchestration 應留在 `apps/engine/`。

