# Edit Task 改期必填 History — 2026-10-22

已部署本機 http://127.0.0.1:5000 。本需求將不可變更 History 規則擴及 Edit Task，取代之前僅 Schedule 改期操作要求原因的限制。

- Edit Task 起訖日期與載入時不同時，顯示必填 History；日期還原時隱藏／停用該欄，純 Owner/Notes 更新無需原因。New Task 初次設定日期仍不要求變更紀錄。
- PATCH /api/tasks/<id> 伺服器判斷真正的日期變動，要求新的 History 及 expected_start_date / expected_end_date；不能略過前端驗證直接無原因改期。
- Edit Task 與 Schedule 共用 append_schedule_history，同一交易更新日期、其他表單資訊並追加不可變更列。新增或清空排程日期也產生紀錄；同日期更新不產生空白或重複 History。
- 保留舊日期比對、執行鎖、Notes／Owner／其他 metadata 合併與所有執行證據。History 原有資料庫 UPDATE/DELETE 觸發器持續生效。

## 驗證
79 項相關 Python 測試通過（原有 73 加 6 項 Edit Task 規則測試），涵蓋兩種 Task、必填原因、日期不變、清空／重新設定、過期日期拒絕、History 寫入失敗時整筆回復、資料庫不可更新／刪除。既有日期編輯測試依新契約加入原因與原日期。
兩份 JS 語法、Edit-only 欄位／日期快照渲染檢查通過。

隔離瀏覽器：Plan Task 修改結束日期出現 required History，空白時阻擋、還原日期後不要求；填原因後在 Task Info 新增一筆 History，原 Notes 與原 History 保留。Test Task 從 Task List 的 Edit 修改開始日期，同樣新增至自己的 History List。
正式僅開啟並取消 Edit Task，確認原日期快照與條件顯示；未儲存任何正式日期或 History。重啟前無執行中 Task，備份、副本啟動及正式重啟後原列逐列一致，integrity / foreign keys 通過。

本機私有備份：<LOCAL_PATH> 。
驗證：<LOCAL_PATH> 、edit-task-history-preview.png（隔離測試資料）。
