# 模擬流程模組

`domain/simulation/` 負責把代理人、世界狀態與事件記錄串成可執行的 tick 式模擬流程。

## 檔案

- `perception.py`：定義 `AgentPerception`、`SimulationLogger`、`ABMSimulation`。

## 核心型別

- `AgentPerception`：單一代理人在單一 tick 內可見的資訊快照。
- `SimulationLogger`：儲存由 `SimulationEvent` 轉換而來的日誌文字。
- `ABMSimulation`：負責 `step()` 與 `run()` 的高階協調器。

## 執行模型

`ABMSimulation.step()` 目前會執行以下流程：

1. 對所有代理人套用被動衰減。
2. 為每位代理人建立感知資料。
3. 要求每位代理人產生動作意圖。
4. 透過 `SimulationWorld` 執行實際動作。
5. 記錄產生的事件。
6. 推進模擬時間。

`ABMSimulation.run(steps)` 則是重複呼叫 `step()`，並回傳累積的事件列表。

## 日誌行為

- `LoggingConfig.enabled=False` 時，完全不記錄。
- `LoggingConfig.max_events` 用來限制記憶體中的日誌上限。
- `LoggingConfig.print_to_stdout=True` 時，每個事件會即時印到主控台。
