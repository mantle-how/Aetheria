# 代理人模組

`domain/agent/` 定義代理人的內部狀態，以及決定下一步行動的邏輯。

## 檔案

- `agent_model.py`：`ABMAgent`，模擬中使用的主要代理人物件。
- `need.py`：`NeedState`，管理飢餓、精力與心情的變化。
- `relationship.py`：`Relationship` 與 `RelationshipLedger`，負責社交親和度追蹤。

## 決策優先序

`ABMAgent.decide_action()` 目前採用固定優先序：

1. 飢餓過高時先嘗試進食；若沒有食物，就移動到可取得食物的地點。
2. 精力過低時回家休息。
3. 心情過低時優先社交；若沒有目標，就前往社交地點。
4. 工作時段內前往工作地點並執行工作。
5. 在沒有緊急需求時，傾向進行社交行為。
6. 若沒有更合適的行動，則維持待機。

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

- `affinity` 會被限制在 `-100..100`。
- 正向社交互動會提升親和度。
- 社交時未被選中的附近代理人，可能會受到小幅衰減。
- `strongest_bond()` 可讓代理人優先選擇目前關係最好的社交對象。
