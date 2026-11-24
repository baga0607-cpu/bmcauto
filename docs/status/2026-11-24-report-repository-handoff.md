# 2026-11-24 交接｜單一 Case HTML 報告與測項庫

## 新對話從這裡開始

使用者決定先逐頁調整功能，最後一起確認全站介面設計規範。下一個功能頁由使用者指定。跨頁彈窗目前只完成影響評估，本輪未修改 DESIGN.md。

正式服務在本機 http://127.0.0.1:5000 ，工作目錄為 D:/Codex/bmc_auto_test/BMCAgent。GitHub 發布使用同工作區的 bmca-runtime/publish-handoff-20261111。正式工作目錄有其他對話留下的未發布差異，發布時請逐項核對。正式資料庫、測試設備連線、歷史執行證據與產生的預覽保留在本機。

## 已上線功能

- 單一 Case HTML 預覽與匯出共用 Step、Description、Result 三欄。主步驟用全寬橫線分組，Checkpoint 縮排，組內短線從子項編號延伸進 Result。缺少結果時保留空白。
- Result 先顯示粗體判定，再呈現已保存的 Expected、Actual、Reason、Note。超過 240 字元的單筆 Actual 用 Detail 展開。多筆觀察在同列依判定分組，例如 RF-01-012 的 2b 顯示 PASS 995、FAIL 94，各組在下一行展開完整內容。FAIL 分組用紅字。步驟記錄值回到所屬步驟。
- HTML 可讀取新版執行快照與事件，並相容舊資料。正式 runner 仍使用既有入口。新版作者介面、Resume 與動態 Checkpoint 的實作狀態見[作者指南](../case-py-author-guide-v1.md)與[11 月 23 日交接](2026-11-23-case-authoring-handoff.md)。這次的三欄變更限於 HTML。
- 測項庫取消列表右鍵選單與勾選框。點選反白整列，Shift 範圍選取，Ctrl 跳選。搜尋列提供新增資料夾、匯入、替換、刪除、全選、重新命名、排序及最右側 History。測項列先 View，再顯示適用的參數按鈕。圖示按鈕沿用 Execution 視覺，大小 34 × 34 px、圖示 18 px、間距 8 px。
- 刪除資料夾可選擇將子樹內測項搬到母資料夾或一併刪除。替換時預覽新舊名稱與時戳，保留測項 ID、資料夾與既有 Plan 副本。相同原始碼或來源版本已變更會被拒絕。
- History 唯讀，只記錄透過測項庫 API 成功提交的實際資料變更，操作者欄留待登入系統。選取、查閱、取消、失敗、無變更儲存皆不新增紀錄。直接 SQL、還原備份及 Plan 副本的變更不在此歷程範圍。舊的 203 筆操作歷程已於 11 月 24 日一次清除，無須再清除。
- 測項庫新增資料夾、改名、替換與刪除均為左上標題、右下主要操作與取消，桌面最大寬度 520 px。Source、唯讀 Parameters、History 固定頂部標題與關閉，僅內容捲動；檢視不額外改動選取狀態。

## 延後確認的設計議題

操作型與檢視型彈窗已有測項庫範例。未來再逐頁確認 Execution 可編輯表單與唯讀 Log、Task 排程、批次匯入結果、報告預覽等。Plan 拖放匯入可能逐次生效、報告可多次下載、離開未儲存畫面可能有三個選項，需分別決定行為。瀏覽器原生確認若改為應用內視窗，須另驗證非同步取消與資料保護。

## 驗證與已知限制

發布 checkout 已通過 66 項測項庫與報告 Python 測試，以及使用模擬 API 的 Chrome 測項庫操作測試。此前已在本機正式服務核對 RF-01-012 報告、資料夾選取、工具列、按鈕尺寸及各彈窗。正式資料庫未用於破壞性測試。

本機正式工作目錄另有既有的 Case 層級長 Note 測試，期待 HTML 匯出包含 END_OF_NOTE，先前未通過；該測試不在發布 checkout 的 66 項內。本次未更動 Case 層級 Note 政策。新版 RF-01-002 的執行證據來自本機 prototype；RF-01-008、012 的展示使用歷史執行資料。最新正式服務的重啟備份位於 bmca-runtime/backups/restart-20261124-144128-795。

## 可貼到新對話

> 請先讀 BMCAgent/docs/status/2026-11-24-report-repository-handoff.md。沿用已部署的報告與測項庫行為，先處理我指定的功能頁。全站彈窗設計規範等各頁功能定案後再一起確認。這次要調整的頁面是＿＿＿＿。

## Plan 測項列的 View 與 Parameters

兩個入口共用測項庫的原生彈窗版面。Plan 測項列與右鍵選單開啟同一個彈窗，儲存使用既有 Plan definition API 與 settings_revision。Chrome headless 以模擬 API 驗證原始碼、參數儲存、執行鎖定、三個關閉入口的未儲存確認及焦點還原。本機 5000 埠已供應新版 workbench.js。下一步可重新整理 Plan 頁面，以實際測項驗收列表位置與右鍵入口。

## Plan 改動歷程

排序右側的 History 顯示目前 Plan 的變更。每次成功提交才一起寫入 plan_history。既有 Plan 從啟用後開始記錄，登入身分由 REMOTE_USER 提供。多檔 Python 匯入保留逐檔結果，歷程以同一批次顯示成功項目。

隔離工作目錄執行 python -m unittest test_plan_history test_mixed_case_selection test_single_case_repository，共 31 項通過。Chrome headless 在獨立 Flask 服務從 Plan 工具列開啟歷程，確認排序右側入口與兩筆操作的顯示。正式服務的歷程 API 仍回應 404，重啟後才會建立新表並載入路由。

## Plan 選單與設定

Plan 清單與單一 Plan 連結共用下拉選單、Add Plan 與 Edit Plan，選單沿用瀏覽器原有的 Plan 排序。新增與編輯共用彈窗，編輯時帶入目前名稱與 SKU。改名沿用原有 PATCH，修改 SKU 由新版 settings 路由與名稱一起儲存。

Chrome 在隔離的 Flask 服務驗證兩個頁面入口、SKU 回填與修改、新增後選取及下拉切換。test_plan_history、test_mixed_case_selection、test_single_case_repository 共 31 項通過。目前 5000 埠服務需要重啟才能接受 settings 路由的 PATCH。
