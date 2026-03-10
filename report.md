# 2026-03-06 工作日誌

## 今日完成

- 完成 Aetheria Demo 行為規則調整：
  - 社交目標改為優先尋找「其他存活且目前閒置、心情最低的 agent」。
  - 社交心情恢復量調整為 `0.5 / tick`。
  - 休息機制改為進入後持續到精力 `> 90` 才退出。
  - 休息中的 agent 當 tick 不會扣減飢餓與心情。
  - 休息精力恢復量調整為 `0.2 / tick`。

- 完成 Web 視覺化驗證與除錯：
  - 使用 Playwright 建立 smoke test 與 e2e 測試。
  - 修正 WebSocket 連線失敗問題，補上 `websockets` 依賴。
  - 確認 Topdown 畫布、儀表板、即時狀態列都能正常顯示。

## 今日產出

- 新增 Web 端測試與設定：
  - `playwright.config.js`
  - `e2e/playwright_smoke.cjs`
  - `e2e/web.spec.js`
  - `package.json` 測試 script

- 更新模擬與設定相關檔案：
  - `model/config.py`
  - `domain/agent/agent_model.py`
  - `domain/simulation/perception.py`
  - `domain/world/world_model.py`
  - `domain/agent/README.md`

## 驗證結果

- `python -m compileall -q domain model view apps` 通過。
- Playwright smoke test 通過。
- Playwright e2e test 通過。

## 備註

- 目前專案已有 `node_modules`、`package-lock.json` 與 Playwright 測試基礎，可直接繼續擴充前端測試案例。
