# 不可刪改的 Task History — 2026-10-22

已部署本機 http://127.0.0.1:5000 。本需求 supersedes 先前把改期原因追加至 Notes 的做法。

## 行為與資料
- Schedule 任務條的改期對話視窗改為必填 History（1–4000 字、不可全空白），不再接受 Note 取代。改期成功時同一交易更新日期並插入一筆 task_schedule_history。
- 每筆包含獨立 UUID、Task UUID／類型／當時名稱、UTC 微秒時間、原起訖、新起訖與原因。最新紀錄排前面，介面以 Asia/Taipei 顯示時間。
- Plan Task Info 與 Test Task Info 的任務資訊頁均顯示 History List（時間、原日期、新日期、History）；沒有編輯或刪除控制項。唯一 History API 為 GET /api/tasks/<id>/history。
- SQLite BEFORE UPDATE / BEFORE DELETE trigger 阻擋更新及刪除，包含批次 SQL；一般 metadata 儲存拒絕 history/history_list/schedule_history。改期插入失敗會連同日期一起回復。
- History 與 Notes 獨立。既有 Notes 原文保留，沒有將既有自由文字猜測轉成 History，也未補造過去紀錄；新改期不改寫 Notes。
- History 不使用對 Tasks 的 cascade FK，刪除 Task 仍保留紀錄與名稱快照；已刪除 Task 的 History 可由原 Task ID 的唯讀 API 查詢。這是使用者明確新增的排程變更紀錄，並非恢復已退休的測試執行歷史模型。
- 改期 API 保留原有 Plan 執行鎖、舊日期比對與日期驗證。一般 Task 資訊編輯維持原流程；新增不可變更紀錄適用原先要求原因的 Schedule 改期操作。

## 驗證
73 項相關 Python 測試通過，包含兩種 Task 的 History、Notes 保留、缺漏／非法原因與日期拒絕、過期衝突、SQL 及 API 不可修改／刪除、Task 刪除後保留、讀取範圍及排序、History 寫入失敗時日期原子回復。三份 JS 語法與 History HTML escaping、唯讀呈現、台灣時間檢查通過。

隔離 5002：Plan 與 Test 均由任務條輸入 History 改期成功，Task Info 顯示各自前後日期與原因，Notes 完全保留。空白 History 阻擋儲存。正式僅讀取兩種畫面並開啟後取消改期，未產生正式 History 測試資料。

正式備份前無執行中 Task；副本啟動只新增空 History 表與兩個不可修改／刪除 trigger，其餘列完全一致。重啟後正式原列完全一致，integrity / foreign keys 通過，兩個 trigger 存在。

備份（私有本機）：<LOCAL_PATH> 。
測試：<LOCAL_PATH> 。
畫面：<LOCAL_PATH> 、task-history-dialog-formal.png 。

Update: [Edit Task History](2026-10-22-edit-task-history.md) extends mandatory immutable reasons to ordinary Edit Task date changes, superseding the Schedule-only limitation above.
