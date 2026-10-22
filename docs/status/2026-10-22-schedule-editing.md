# Schedule 改期與日期對話框 — 2026-10-22

已部署本機 http://127.0.0.1:5000/#/tasks 。

## 行為
- 日期標籤列下方以覆蓋在儲存格上方的 1px 分隔線持續顯示，避免儲存格背景遮住框線。
- 隱藏水平捲動軸（overflow-x:hidden），空白區域保留滑鼠左鍵拖曳；垂直捲動軸仍可用，Today 仍可定位。
- 任務條改為編輯按鈕，名稱連結仍可進工作區。點任務條可編輯 Start/End Date，Note 必填且須包含非空白原因（最多 4000 字）。
- PATCH /api/tasks/<task_id>/schedule 同時支援 PlanningTask 與 Test Task，驗證日期順序、必填原因及原日期是否仍相同；沒有日期改動時拒絕送出。保留既有執行鎖、關聯、連線、測試結果／Log。
- 原 Notes 不覆蓋，在後方附加 UTC 時間、改動前後起訖與原因。只在此改期流程強制新的原因；原有一般 Task 資訊編輯功能維持原規則。
- 點標籤列日期直接開啟原生 dialog，僅顯示日期、工作日／非工作日兩個互斥單選、取消（左）／儲存（右）。取消或 Escape 不寫入；儲存沿用共用工作日曆的過期狀態防護。依使用者新規格，對話框不再顯示還原預設選項，後端原能力保留。

## 驗證
62 項 Python 測試通過：新增 7 項改期測試，包含兩種任務、必填 Note、過期時程衝突、非法日期／未變動拒絕、執行鎖、結果／連線保留；加上先前 55 項 Task/日曆測試。JS 語法檢查通過。

隔離 5002 瀏覽器：Note 空白時原生 required 阻擋儲存；Plan Task 延到 10/30（3→5 工作天），Test Task 改為 10/22–10/29（3→5 工作天），Notes 原因已持久寫入。日期對話框預選現有狀態；修改後取消保持原狀，再選工作日儲存才更新日曆與工時。水平 overflow hidden、垂直 auto、表頭下框線 1px 已確認。

正式服務備份前無執行中 Task，副本啟動所有原列完全一致；重啟後正式原列、完整性與外鍵檢查通過。正式瀏覽器只開啟並取消兩種編輯，沒有儲存改期或日曆。

備份（私有本機）：<LOCAL_PATH> 。
測試：<LOCAL_PATH> 。
正式畫面：<LOCAL_PATH> 、schedule-day-dialog-formal.png 。

2026-10-22 refinement: date-header bottom rule now uses var(--line), matching the other table borders in both themes; thickness remains 1px. CSS-only, no backend restart or data changes.
