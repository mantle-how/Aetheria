# api接收
## 簡介
 負責接收api，區分用戶角色，並同意、拒絕對應操作
 * **admin:** 管理者，可以使用所有功能
 * **guest:** 訪客，只能操作自己的角色

## api列表

## 資料夾分層
* **router:** 路由分組(world,agent,event,admin,replay)
* **schemes:** api request/ response dto
* **deps.py:** di dbsession auth rate_limit
* **main.py:** 入口