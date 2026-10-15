# Plan / Task 工作區最新設計（整合版）

日期：2026-09-30。狀態：使用者已核准、完成本機正式版整合。本文件整理既有核准內容，不新增需求。

基礎規格：[Plan Folder / Task current-state](2026-08-24-plan-folder-and-task-current-state-design.md)。詞彙以 [CONTEXT.md](../../../CONTEXT.md) 為準。

## 資料夾與 TC

- Golden Plan 與自建 Plan 都能新增、重新命名、移動、刪除資料夾及 TC。資料夾持久化於資料庫，支援父層與一層子資料夾，空資料夾仍存在。
- TC 與同層資料夾可向上、向下排序。父資料夾收折時連同子資料夾隱藏。
- 資料夾勾選只操作直接隸屬該資料夾的 TC，可再次點擊取消；Plan 全選獨立提供。
- 刪除前顯示影響範圍。Golden 刪除及一般非空資料夾／含子資料夾刪除，需要额外勾選確認。
- 匯出選取 TC 時保留 FOLDER_PATH 與完整 STEPS。匯入在目標 Plan 解析完整路徑，缺少的資料夾自動建立；同名 TC 提示重複，不直接覆蓋。空資料夾不包含在 TC 匯出檔。
- 匯入介面呈現可理解的檔案、成功／錯誤資訊與修正方式，成功項目移除後可重試失敗項目。

## Task 當前狀態

- Task 直接參照同一 Plan 仍存在的 TC，只保存最新結果。Plan TC 刪除後，相關 Task membership、目前狀態、人工標記與目前執行證據同步移除；Task 本身保留。
- 網站不保留 Snapshot、Run History 或 execution attempts。已下載報告、外部備份和既有磁碟 Log 不因刪除 TC 而自動清除。
- 未執行的 TC 也可人工改成 TBD / Passed / Failed，標示人工修改與原因／時間；已有執行 Log 保留，未執行者不產生虛構 Log。
- Task Detail 依穩定 Task / TC ID 取得目前 Log 與 API Log。Tasks 與 Test Executions 皆按 Plan 分組。
- 執行中的 Plan 限制結構、範圍與人工結果異動。部分重跑只更新選取項目。

## 導覽與視覺

- 左側為可調整寬度的資料夾與 TC 樹；右側顯示點選 TC 的組成和依序排列的全部步驟。點選預覽與勾選操作互不影響。
- 資料夾保留 TC 數、加子資料夾、展開控制；Rename / Move / Delete 收進直立 ⋮。
- TC 名稱、Add to golden plan / In Golden plan 與 ⋮ 同列、不換行。
- 支援深淺主題。主要名稱 14px、次要資訊 12px、區塊標題 16px、TC 預覽標題 22px；圖示操作區至少 32px。
- 白色主題以明確邊框、淡灰標頭、白色內容卡與淡藍選取區區分功能區塊。

## 環境與驗證界線

正式版 5000 與測試版 5127 各用獨立資料庫，不互相複製即時變更。API 成功的異動會提交到所屬資料庫；其他已開啟的分頁可能需重新整理。

2026-09-30 唯讀核對：正式版 2 Plan / 17 TC / 2 Task，測試版 12 Plan / 45 TC / 9 Task。兩套 SQLite 完整性與外鍵檢查通過；資料庫/API 的資料夾、TC 歸屬、Task 狀態與 Log 一致，14 個 Plan 的畫面 TC ID 清單吻合。實際下載驗證包含正式版 1 個、測試版 5 個 Plan 的子資料夾匯出路徑與步驟。此為當時檢查結果，不代表所有情境均無缺陷。

相關紀錄：[九項改善](../../status/2026-09-29-plan-task-ux-verification.md)、[導覽與可讀性](../../status/2026-09-30-plan-navigator-verification.md)、[正式整合](../../status/2026-09-30-formal-release.md)。
