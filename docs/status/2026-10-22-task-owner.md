# Task Owner — 2026-10-22

已部署本機 http://127.0.0.1:5000 。

- New Task / Edit Task 新增 Owner 下拉選單，預設 TBD。初始選項依使用者範例先設 TBD、David；其他人員名單尚待使用者補充。
- 同時支援 Plan / Test，Owner 儲存於各 Task 的 task_metadata.owner，改期與其他資訊編輯會保留。
- Schedule 在名稱下顯示 Owner: <名稱>，未設定的舊 Task 顯示 Owner: TBD；不寫入或遷移舊資料。文字保持 Owner 英文前綴。
- 名單設定：web_ui/task_owners.json；/api/tasks/options 回傳 owners。後端拒絕非選單值；若既有 Owner 日後移出名單，原 Task 仍可保留該值，新 Task 不能選該舊值。

## 驗證
67 項相關 Python 測試通過（5 項新增 Owner 測試 + 62 項既有 Task/日曆/改期測試），包含兩種 Task 預設、選擇與修改、保留既有資料、非法值拒絕與人員移出名單。三份 JS 語法檢查與隔離渲染檢查通過。

隔離瀏覽器確認 New Task 預設 TBD、選擇 David 建立成功後 Schedule 顯示 Owner: David；舊 Task 顯示 Owner: TBD。正式瀏覽器只開啟並取消 New Task，確認 TBD/David 選項與預設；正式 Schedule 僅讀取與 Today 定位，沒有建立或修改正式 Task。

重啟前無執行中 Task，SQLite backup 與副本啟動檢查通過，重啟後所有原列完全一致、完整性與外鍵通過。
備份（私有本機）：<LOCAL_PATH> 。
測試：<LOCAL_PATH> 。
正式畫面：<LOCAL_PATH> 。
