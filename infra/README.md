# 地基

## DB:

* **models.py:** ORM models(映射資料表)
* **repository/** :資料庫存取(查詢)
* **unit_of_work.py:** 交易一致性(一次tick內寫入事件 + 狀態)
* **migration/** :資料庫版控

## MQ(選擇性):
* **任務佇列**
## observability可觀測性:
* **logging:** 日誌紀錄
* **metrics:** 蒐集系統狀態的log
* **tracing:** 追蹤請求流程