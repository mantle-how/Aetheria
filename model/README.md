# 模型層說明

`model/` 放的是專案各層共用的資料契約、設定物件，以及組裝示範場景的輔助函式。

需要注意的是，`model/test.py` 目前實際上不是單元測試，而是示範場景的組裝入口。

## 檔案

- `action.py`：動作列舉，以及動作輸入與輸出的資料結構。
- `config.py`：模擬設定模型與數值驗證。
- `test.py`：示範世界建立器與提供給視圖層的轉接函式。

## action.py

這個模組定義了：

- `ActionType`：支援的動作列舉。
- `ActionIntent`：代理人下一步想執行的動作意圖。
- `ActionOutcome`：世界執行動作後的結果。

目前支援的動作有：

- `MOVE`
- `EAT`
- `REST`
- `WORK`
- `SOCIALIZE`
- `IDLE`

## config.py

`SimulationConfig` 由四段設定組成：

- `LoggingConfig`
- `NeedConfig`
- `WorldConfig`
- `PopulationConfig`

每個設定類別都會在 `__post_init__()` 進行自己的數值檢查，讓不合理設定在模擬開始前就直接失敗。

## test.py

這個模組目前提供示範場景的組裝工具：

- `Agent`：以 `ABMAgent` 為基底、方便展示的子類別
- `build_demo_simulation()`：建立預設世界、地點與代理人
- `simulation_to_entities()`：把世界資料轉成可直接繪製的實體清單
- `generate_demo_entities()`：建立模擬、先跑幾步，再回傳可繪製資料

若專案後續擴大，這個檔案很適合再拆成獨立的 demo 或 fixture 模組。
