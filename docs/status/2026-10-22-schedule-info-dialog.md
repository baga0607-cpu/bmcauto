# Schedule Task Info / 改期對話視窗 — 2026-10-22

已更新本機服務，僅修改前端，不需重啟後端或遷移資料。

- Schedule Task 名稱：Plan Task 連到 #/tasks/info/<task-id>，顯示該 Task 的 Project、SKU、Owner、日期、工作天數與 Notes，選中 Task Info；可用原 Edit Task 表單修改。Test Task 連到原 Task workspace 的 /info 子路徑，選中 Task Info 與任務資訊。使用穩定 UUID，名稱更改不影響關聯。
- 任務條：開啟原生 dialog 編輯起訖日期與必填新 Note，保留原 API 的執行鎖、過期日期檢查與原因附加。取消／Escape 不寫入；儲存成功後關閉對話視窗，保留 Schedule 捲動位置。
- 原 Task List 名稱連結與其他原有 workspace 預設頁不變；只有 Schedule 的名稱改用 infoLink。

## 驗證
兩份 JS 語法與純渲染／路由檢查通過。隔離瀏覽器確認兩種 Task 名稱開啟正確 Task Info，Test 直接選中任務資訊。Plan Task 對話視窗空白 Note 時 required 阻擋，填入原因後改期成功（結束日 10/30→11/02，7→8 工作天）並關閉視窗。正式只讀確認 Plan Task Info 與 Test Task /info 頁、開啟後取消改期對話視窗，沒有正式資料寫入。後端未變，本次未重跑歷史的 67 項 Python 測試。

私有本機驗證畫面：<LOCAL_PATH> 、task-schedule-dialog-formal.png 。
