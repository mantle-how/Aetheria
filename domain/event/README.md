# 事件模組

`domain/event/` 定義模擬、日誌與視圖層共用的事件格式。

## 檔案

- `base.py`：定義 `SimulationEvent`。

## SimulationEvent

`SimulationEvent` 是目前唯一的事件型別，內容包含：

- `tick`：模擬步次。
- `minute_of_day`：世界內時間（以分鐘表示）。
- `actor_id`：執行動作的代理人編號；若無可為 `None`。
- `event_type`：事件類型，通常對應 `ActionType` 的字串值。
- `message`：給人閱讀的摘要訊息。
- `payload`：結構化補充資料，例如成功狀態、座標、需求值與物品數量。

## 日誌輸出

`SimulationEvent.to_log_line()` 會把事件轉成可直接顯示的日誌文字。

目前事件模組維持輕量設計，沒有再拆成 world event 或 agent event；所有行為都統一透過同一種事件結構表達。
