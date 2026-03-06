# 代理人模組

`domain/agent/` 定義代理人的內部狀態，以及決定下一步行動的邏輯。

## 檔案

- `agent_model.py`：`ABMAgent`，模擬中使用的主要代理人物件。
- `need.py`：`NeedState`，管理飢餓、精力與心情的變化。
- `relationship.py`：`Relationship` 與 `RelationshipLedger`，負責社交親和度追蹤。

## 決策優先序

`ABMAgent.decide_action()` 目前採用固定優先序：

1. `hunger < eat_threshold`：先嘗試進食；無食物則移動到最近食物來源。
2. `energy < rest_threshold`：進入休息恢復狀態，回住家休息（自己住家優先，否則父母住家 fallback），直到 `energy > rest_stop_threshold` 才退出。休息當下 tick 不會扣減飢餓與心情。
3. `food_inventory < food_restock_threshold`：前往工作站補糧，直到達標。
4. `mood < social_start_threshold`（或恢復中）：尋找最低心情且目前閒置的存活代理人社交，直到 `mood > social_stop_threshold`。
5. 若沒有更高優先行為，則維持 `IDLE`。

## NeedState

`NeedState` 提供世界邏輯會用到的主要狀態變化方法：

- `apply_passive_decay()`
- `apply_work_cost()`
- `apply_move_cost()`
- `recover_from_eating()`
- `recover_from_rest()`
- `recover_from_social()`

所有數值都會依 `NeedConfig` 的範圍做正規化處理。

## 關係模型

- `affinity` 會被限制在 `0..100`。
- 正向社交互動會提升親和度。
- 社交時未被選中的附近代理人，可能會受到小幅衰減。
- `strongest_bond()` 可讓代理人優先選擇目前關係最好的社交對象。
