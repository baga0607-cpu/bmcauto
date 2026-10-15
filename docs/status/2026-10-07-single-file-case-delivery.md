# 單檔測項本機交付

日期：2026-10-07（Asia/Taipei）。本機 checkout：D:\bmc_auto_test\BMCAgent，來源 commit 76eee23。修改未 commit / push。

核准依據：[單檔測項設計](../superpowers/specs/2026-10-07-single-file-case-design.md)。完成 Repository 匯入與時戳、Plan 獨立 Python / 參數、Task 使用 Plan 最新定義、保留結果並標記需重測、執行中單一 TC 編輯鎖。支援單檔 TC 的 Plan 間複製與既有 JSON 匯出／匯入；保留舊 steps 資料。

## 驗證

- 使用 D:\bmc_auto_test\bmca-runtime\verification 內的獨立 workspace、main_program 副本及 TEMP。未執行實體 BMC 測試。
- 完整 Python 回歸：149 tests，148 pass、1 skip。歷史 17-TC production fixture 未隨 checkout 提供，明確略過該歷史備份啟動測試；未捏造 fixture。
- 最後單檔整合驗證：12 / 12 pass，包含 Plan 隔離、來源版本不變、所有 Task 的提示、Running TC 鎖、其他 TC 可編輯、舊結果保留、提交失敗回復程式與設定、伺服器使用 Plan 設定而忽略 Task 送入的替代步驟。
- JavaScript：68 / 68 pass。index.html 的兩個 inline scripts 及 single_case.js 語法解析通過。
- Browser：獨立 5127，Repository、Plan 參數儲存與時戳、Task 提示、640px 及 1440px 畫面確認；無 pageerror。CUA kernel 無法啟動後使用 bundled Playwright + headless Chrome 驗證。
- Impeccable detector：新增 CSS / JS 未檢出項目。
- 證據：python-tests-final.log、single-tests-final.log、node-tests-final.log、browser.json，以及 repository / plan-editor / task-retest screenshots，保存於上述 verification 目錄。

## 部署與資料保存

正式服務 http://127.0.0.1:5000，debug / reloader 關閉。重啟前確認沒有 active runs，確認 listener 是本專案 server.py。啟動入口 D:\bmc_auto_test\bmca-runtime\start.ps1。

升級前使用 SQLite backup 保存一致性資料庫，並保存原始 Git source ZIP。位置 D:\bmc_auto_test\bmca-runtime\backups\single-case-20261007。

重啟後首頁與 Repository API HTTP 200。SQLite integrity_check = ok，foreign_key_check 無違反。比對舊欄位所有 row 及數量一致：1 Project / 1 Plan / 0 TC / 0 Task / 0 Task membership。正式環境沒有放入 preview 示例。

若需回復，先停止此服務並另存上線後資料，再協調還原 source-before.zip 與 testcase_meta-before.db；不要單獨還原程式或直接覆蓋新輸入的 Repository / Plan 資料。

## 尚待逐一定案

全自動／半自動分類、完整環境注入及 Pass / Fail / Error / block 契約尚未在本輪變更。Report / Test Plan 文件及 Final Report 規則依使用者安排後續討論。本輪單檔 runner 沿用目前結果契約，不能將 return False 當成正式 Fail 回傳。
