# 模擬引擎層

`apps/engine/` 放的是模擬的組裝與執行協調，不直接處理 HTTP/UI。

## 檔案
- `config.py`：runtime 預設常數，例如 host、port、TPS、FPS、預設人口數。
- `bootstrap.py`：建立 demo world、places、agents，回傳 `ABMSimulation`。
- `engine.py`：`SimulationRuntime`，封裝背景執行緒、play/pause/step/reset、snapshot。

## Reset 世界
`SimulationRuntime.reset()` 會：
1. 沿用目前 runtime 的設定與 agent 數。
2. 在 lock 內重建新的 demo simulation。
3. 將 `world_revision` 加一。
4. 重置完成後自動恢復播放。

## 分層原則
- 世界規則與 agent 決策留在 `domain/`。
- Web/API 指令收發留在 `apps/api/`。
- 這裡只負責 runtime orchestration 與 bootstrap。
