# 主功能啟動

* **config.py:** 引擎設定(參數、預設值、環境變數)
* **tick_loop.py:** 主迴圈 (tick推進、固定排序、commit)
* **schedular.py:** 排程(自動/手動ticket、加速)
* **command_bus.py:** 指令匯流(start/stop/pause/step/rewind)
* **services/:** 用例服務(ex. boostrapWorld, runTicks, takeSnapshot)