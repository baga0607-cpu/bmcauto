# Plan / Task 九項操作改善與驗證紀錄（2026-09-29）

測試網站：http://127.0.0.1:5127/

此網址執行隔離分支 `codex/plan-folder-current-state-20260917`，工作目錄為 `D:\Pytest\_redfish\plan-folder-current-state`。本次未合併、未推送、未部署；5127 是本次測試預覽，不能單憑 5000／5001 的埠號判定正式環境。

## 中文操作與驗收

| 項目 | 如何操作 | 預期結果 |
| --- | --- | --- |
| TC 與資料夾排序 | 拖曳把手至目標列上半部或下半部，看插入線後放開 | 上半部插入之前、下半部插入之後；第一筆可直接移到第二筆之後。跨資料夾／父資料夾同樣依插入位置儲存。 |
| 淺色／深色主題 | 點頁首太陽／月亮圖示 | Portal 與 Test Case Builder 切換白底／深色；重新整理保留偏好。 |
| 資料夾持久化 | 新增、改名、移動或排序資料夾後重新整理 | API 成功後已提交資料庫；結構和順序保留。執行中的 Plan 禁止結構修改。 |
| 全選範圍 | 點 Plan 表頭框、或某一資料夾旁的框；再點一次 | Plan 框控制整個 Plan。資料夾框只控制該資料夾直接所屬 TC，未包含子資料夾；再次點擊取消。部分選取顯示半選狀態。 |
| 父子收折 | 點父資料夾旁展開／收折箭頭 | 同時隱藏其子資料夾；再展開時保留子資料夾原本的收折狀態。 |
| TC 匯入 | 選擇 JSON 檔案，檢視名稱、目的資料夾與錯誤提示 | 以欄位表格顯示；不直接攤開程式碼。成功項目移除，失敗項目保留供修改重試；檔名僅作來源參考。 |
| 手動結果 | 在 Task Detail／Execution Detail 點結果旁的鉛筆，選 TBD／Passed／Failed，填寫可選原因 | 顯示 `✎ Manual` 標記，提示人工修改時間和原因；不允許手動設定 Running。 |
| 當前 Log | 點 Task testcase 的 Log | 以 Task 和 testcase ID 讀取已儲存的當前執行／API Log；讀取失敗有錯誤訊息。 |
| Tasks 分組 | 進入專案的 Tasks 清單 | 按 Plan 名称與數量分組，可展開／收折，重名 Task 仍能辨別所属 Plan。 |

## 人工修改的明確規則

- **從未執行的 TC 可以人工改結果。** 顯示人工修改標記；執行時間與 Log 保持空白，Log 對話框說明尚無執行紀錄、結果由人工設定。
- 已執行的 TC 人工改結果時，保留原始執行結果資料、執行時間、一般 Log、API Log。人工判定與執行證據分開記錄。
- 目前保存最新一次人工修改的結果、原因與時間，並非完整歷次人工修改稽核紀錄。
- 重新執行被選取的 TC 時，清除該 TC 的人工標記；未選取的 TC 保留。
- 同一 Plan 有執行中的 Task 時，人工修改與結構操作都被鎖定；仍可讀取 Log。
- PDF 報告包含人工修改標記、時間與原因。

## 驗證結果

- Python 完整測試：**131 / 131 通過**，`python -m unittest discover -s web_ui/tests -p 'test_*.py'`。
- JavaScript 完整測試：**61 / 61 通過**，`node --test web_ui/tests/*.test.js`。
- 瀏覽器使用真實 Chrome / Playwright，在 **5128 的另一份 SQLite 副本**執行九項功能測試；未使用使用者的 5127 資料做破壞性測試，也未對真實 BMC 執行測試。
- 實測包含同資料夾上下拖曳、跨資料夾之前／之後插入、跨父資料夾插入、父子收折、全選／取消／半選、匯入部分成功與修正重試、主題持久化、未執行人工判定、保留既有 Log、重跑清標記、執行鎖、搜尋後鎖定、Plan 分組、PDF 下載。
- 瀏覽器腳本未捕捉到 JavaScript pageerror。人工修改 PDF 文字驗證通過；白底 Portal／Builder／匯入對話框已檢視截圖，修正了 Builder 主題按鈕遮住名稱欄位的問題。
- 獨立程式審查提出的三個問題均修正：跨父資料夾插入、跨資料夾 TC 插入、專案重新載入時遺失畫面上的人工標記。複審無待解決阻擋項。

## 預覽重啟與資料保留

5127 已重啟，首頁、projects API、主題資源皆回應 HTTP 200。既有使用者資料庫在重啟前另外備份到 `verification/2026-09-29/before-final-restart.db`；沒有把自動測試資料庫覆蓋回去。

比對重啟前後八張資料表：原有資料列、結果與 Log 均保留；啟動只將一個 Plan 的既有 `folders_migrated` 標記由 0 改為 1，並新增人工修改欄位。另比對 main 的 112 個既有修改／未追蹤檔案雜湊，重啟前後相同。

本機驗證檔案位於 `verification/2026-09-29/`：`python-final.txt`、`node-final.txt`、`browser-results.json`、`browser-extra.json`、`browser-review-fixes.json`、`restart-result.json`、截圖及 PDF。資料庫／Log／截圖未加入 Git。程式審查紀錄位於 `verification/2026-09-29-review.md`。
