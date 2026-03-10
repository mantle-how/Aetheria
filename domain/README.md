# 領域層說明

`domain/` 是 Aetheria Demo 的核心領域層，負責定義世界規則、代理人行為、事件資料，以及以 tick 為單位推進的模擬流程。

目前的領域層分成四個子模組：
- `agent/`：代理人的狀態、需求、關係與決策邏輯。
- `event/`：模擬事件的共用資料格式與日誌輸出格式。
- `simulation/`：動作契約、設定模型、感知建構、步進流程協調與事件記錄。
- `world/`：世界狀態、地點資料、全域規則與動作執行。

## 主要責任
- 不負責畫面呈現；UI 由 `view/` 處理。
- 專注在領域邏輯，也就是代理人如何決定行動，以及世界如何回應行動。
- `apps/engine/` 會使用這裡的契約與模型來組裝可執行的 demo simulation。

## 執行流程
目前一次模擬步驟（`ABMSimulation.step()`）的流程如下：
1. 先對所有代理人套用被動需求衰減。
2. 為每個代理人建立 `AgentPerception` 感知快照。
3. 呼叫 `ABMAgent.decide_action()` 產生 `ActionIntent`。
4. 將意圖交給 `SimulationWorld.execute_action()` 執行。
5. 產生 `SimulationEvent`，並交由 `SimulationLogger` 記錄。
6. 推進 `tick_count` 與 `minute_of_day`。

## 模組對照
- `agent/agent_model.py`：`ABMAgent`，包含行動優先序與目的地選擇。
- `agent/need.py`：`NeedState`，負責飢餓、精力、心情的更新。
- `agent/relationship.py`：`Relationship` 與 `RelationshipLedger`，負責社交親和度追蹤。
- `event/base.py`：`SimulationEvent`，目前模擬使用的單一事件結構。
- `simulation/action.py`：`ActionType`、`ActionIntent`、`ActionOutcome`。
- `simulation/config.py`：`SimulationConfig` 與相關子設定。
- `simulation/perception.py`：`AgentPerception`、`SimulationLogger`、`ABMSimulation`。
- `world/place.py`：`Place`，可互動地點的資料模型。
- `world/rule.py`：`WorldRules`，基於設定的唯讀規則介面。
- `world/world_model.py`：`SimulationWorld`，世界狀態容器與動作執行器。

## 設計備註
- 目前模擬為單執行緒，並依序更新每一位代理人。
- 事件模型刻意保持精簡，讓日誌與視圖層都能直接使用。
- 若要新增新動作，通常會一起調整：
  `domain/simulation/action.py`、`domain/agent/agent_model.py`、`domain/world/world_model.py`。
