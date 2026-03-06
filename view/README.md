# 視圖層說明

`view/` 是展示層，負責把模擬資料畫出來，不應承載領域決策邏輯。

目前預設路徑已切換為 Web 視覺化：

- `view/demo.py` 啟動 Uvicorn，對外提供 `apps/api/main.py`
- 前端以 WebSocket 接收即時 snapshot，並在 Canvas 繪製 Topdown + Dashboard

## 檔案

- `demo.py`：可直接執行的 Web 入口（FastAPI/Uvicorn）。
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

## topdown.py

`TopDownVisualizer`（舊版）支援：

- `show(entities)`：顯示靜態畫面
- `show_live(...)`：依時間間隔持續更新畫面，並同步更新代理人儀表板

主要責任包括：

- 計算世界邊界與縮放比例
- 將世界座標轉成畫布座標
- 依實體類別套用顏色
- 在俯視圖中顯示 agent 的名字與目前動作
- 繪製圖例與狀態列
- 在儀表板中為每位 agent 顯示：
  需求折線圖（飢餓、精力、心情）
  生命值（HP）
  目前動作與即時數值
- 儀表板卡片會依視窗寬度自動換列排列

## 鍵盤操作

- `Space`：播放或暫停
- `+`：放大
- `-`：縮小
- `Esc`：關閉視窗

補充：

- 儀表板有垂直捲軸，可在 agent 較多時往下查看
- 關閉儀表板後，主視窗仍可繼續播放

## 分層邊界

若未來更換 UI 技術，這個資料夾應是主要替換點。領域邏輯應留在 `domain/`，不要回寫到視覺層。
