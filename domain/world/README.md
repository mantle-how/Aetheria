# 世界模組

`domain/world/` 定義模擬地圖、全域規則，以及各種動作對世界狀態造成的實際影響。

## 檔案

- `place.py`：`Place`，地點資料模型。
- `rule.py`：`WorldRules`，以設定為基礎的規則介面。
- `world_model.py`：`SimulationWorld`，世界狀態容器與動作執行器。

## Place

`Place` 代表一個場景地點，例如住家、工作場所、市場或廣場。

它提供：

- 識別欄位：`place_id`、`name`、`kind`
- 座標：`x`、`y`
- 資源：`food_stock`
- 額外標記：`tags`
- 輔助方法：`distance_to()`、`has_food()`、`consume_food()`、`restock_food()`

## WorldRules

`WorldRules` 是 `SimulationConfig` 的唯讀包裝，用來讓世界行為邏輯集中管理。

目前提供：

- `world`、`needs`、`population` 設定存取
- `arrival_radius` 到達判定半徑
- `is_work_time()` 工作時段判斷
- `clamp_position()` 世界邊界限制

## SimulationWorld

`SimulationWorld` 的主要責任包括：

- 保存 `places`、`agents`、`tick_count`、`minute_of_day`
- 驗證代理人引用的住家、工作與社交地點是否存在
- 找出代理人目前所在位置
- 搜尋附近代理人與最近食物來源
- 透過 `execute_action()` 分派各種動作執行
- 建立 `ActionOutcome` 與 `SimulationEvent`

## 動作效果

- `MOVE`：朝目標移動，並套用移動消耗。
- `EAT`：優先消耗身上食物，沒有時再嘗試使用地點食物。
- `REST`：在家可完整回復，不在家則僅部分回復。
- `WORK`：只有在工作地點才會成功，成功後可獲得食物。
- `SOCIALIZE`：需要附近有目標，並會更新心情與關係值。
- `IDLE`：不做主要狀態變更，只留下待機事件。
