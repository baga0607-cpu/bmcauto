# RF-01-001 本機整合現況與隔離驗證

日期：2026-10-15（Asia/Taipei）。本輪依根目錄 HANDOFF.md 接續，先核對現況及實際整合缺口。沒有修改平台產品程式、正式資料或 RF-01-001 原始碼，沒有連線實體 BMC。

## 本機現況

- 工作根目錄：`D:/Codex/bmc_auto_test`；平台：`BMCAgent/`。讀取平台 AGENTS.md、repository skill、CONTEXT.md、最新交接及相關契約。
- `.git/HEAD` 指向 main，ref 為 `76eee23b1c0926a76002e7f89cb7e6047e091636`。Git CLI 在目前環境不可用，因此未取得完整 staged/unstaged/untracked 清單，不能聲稱 checkout 乾淨；保留現有所有平台檔案。
- 正式服務 `http://127.0.0.1:5000` 可回應 `/api/run/active`，active_runs 與 locked_project_ids 均為空。查詢時 listener PID 為 24100；此 PID 不是固定設定。未重啟服務。
- sandbox 中 localhost 請求遭 WinError 10013 拒絕；其後經工具允許的 sandbox 外唯讀查詢確認服務正常。隔離測試 JSON 的 live_service 欄保留原始 sandbox 限制，不能解讀為服務離線。
- 正式資料庫：`BMCAgent/web_ui/workspace/testcase_meta.db`。6 Project、1 Plan、1 Plan Test Case、0 Task、1 Repository Test Case。SQLite integrity_check 為 ok，foreign_key_check 無錯誤。
- **RF-01-001 已存在於 Repository，亦已有獨立 Plan 副本**；兩者原始碼皆與 `testcases/redfish/rf_01_001_version_discovery_endpoint.py` 完全相同，Plan settings 為空。與根目錄交接所記「前一對話未匯入」不衝突，但接續時不應重複匯入。
- Plan 副本：`BMCAgent/main_program/testcase_database/scripts/badbe85c-f3d1-41d4-bc4e-7c98e092ccb2/case.py`。

## 本輪驗證

可重跑腳本：`bmca-runtime/verification/rf01_integration_check.py`（相對工作根目錄）。使用平台既有 `.venv`；單獨的 bmca-runtime/python 缺少 SQLAlchemy，不能直接代替平台環境。

```powershell
$env:PYTHONIOENCODING='utf-8'
& .\BMCAgent\.venv\Scripts\python.exe .\bmca-runtime\verification\rf01_integration_check.py
```

最終執行：3 tests passed，runner 測試內包含 10 個子情境。這是本輪新證據，並非之前 101 tests 的歷史數字。測試以 Flask test client 走真正 Repository → Plan → Task API 與背景 runner；HTTP Session、Redfish SDK 使用替身，另阻擋 socket.connect，避免真實連線。匯入 app 前已設定獨立 BMC_WEB_UI_WORKSPACE_DIR 與 BMC_MAIN_PROGRAM_DIR；測試資料庫、Plan 腳本及 log 都在暫存區。未進行瀏覽器視覺驗證。

確認項目：AST/JSON metadata、description 與三筆 step_x/criteria 保存、automatic 宣告、空參數、獨立 Plan 原始碼、Task host/verify_ssl 注入、固定15秒、不自動 redirect、不使用主機 proxy、跨 origin 不送出請求，以及敏感回應標頭不寫入 log。

| 情境 | 測項結果 | 平台保存 |
|---|---|---|
| 成功／同 origin redirect | Pass | Passed |
| 錯誤映射／非 JSON／404／跨 origin／連線失敗／非 object JSON | Fail | Failed |
| 程式故障 | Error | **Failed（現存缺口）** |
| SDK 前置登入失敗 | 測項未被呼叫、0 次測項 HTTP 請求 | Failed |

另外刻意提交錯誤的 test_method 欄位名稱，inspect 仍回 200，證明目前只有保存、沒有該欄位結構驗證。此斷言記錄現況，未來修復時應調整，不能把此通過視為目標功能已完成。

正式 DB 邏輯內容 SHA-256 在驗證前後一致：`71c70cc8ec610bff7bc28947e497fdb284ad49d33b337fa4101635ea72d73e69`。結果檔：`bmca-runtime/verification/rf01-isolated/report.json`。

## 具體缺口與下一個修改範圍

1. `web_ui/single_case.py:metadata` 保留未知 metadata，但沒有驗證 test_method。建議保留既有未宣告測項的相容性；有宣告時驗證清單、每筆依序 step_1/step_2/... 與非空 criteria 字串，維持純文件用途。
2. `web_ui/static/workbench.js` 的 Plan 編輯畫面已有 description；Repository 維持使用者已定案的原始碼／參數預覽。尚無逐步方法／Criteria 專用顯示。建議第一個整合增量先在 Plan 測項詳情加入唯讀方法表，保留 description、空參數與全自動分類，不恢復 step 執行器。Repository 顯示位置依使用者既定面板設計另行確認。
3. runner 只將事件、errors、來源版本及 settings 等存入 result_json，沒有結構化保存 context.case_result；Error 在 DB/UI 仍為 Failed。應另外處理結果契約、儲存及呈現，不能靠字串替換假裝完整支援。
4. runner 在呼叫 case 前強制建立並登入 SDK，登入失敗使 discovery 無法執行。需要明確的 client/HTTP 能力契約，不宜針對 RF-01-001 名稱加例外。
5. 測項直接 requests 的回應證據目前位於一般 log，沒有接平台 API Log。後續應提供公開 HTTP/證據介面。
6. 自動化圖示已讀取 automatic 宣告，但平台並未驗證「有 Plan 參數或互動必須半自動」的能力規則。
7. Test Plan HTML/PDF、手動 block、停止後結果及 Final Report 仍按原約定分開設計；本輪不變更。

下一步先討論並落實第1、2項的最小增量，再處理結果與 HTTP 契約。無需再次匯入現有 RF-01-001，也不以目前隔離驗證聲稱真機或完整平台整合完成。
