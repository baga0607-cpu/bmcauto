# 正式版整合紀錄 — 2026-09-30

正式網址：**http://127.0.0.1:5000/**

正式工作目錄：`D:\Pytest_redfish\v4.0`，分支 `main`。依使用者核准，main 從 `91d5f5f` 快轉至已驗證的 `28fd8ad`；包含 Plan Folder／Task current-state、人工結果與 Log、深淺主題、Plan 導覽與步驟預覽、Tasks／Test Executions 分組、精簡操作選單及可讀性改善。這次完成本機正式服務更新，未推送遠端。

## 正式資料與原有變更

正式服務使用原本的 `web_ui/workspace/testcase_meta.db` 和 `main_program`，未使用 5127 的測試資料覆蓋。升級前完整備份了工作目錄（包含既有修改、設定、執行資產與 Log）、SQLite 資料庫和 Git bundle。

備份目錄：`D:\Pytest\_redfish\release-backups\2026-09-30-formal-release`

- 正式資料保留：2 個 Project、2 個 Plan、2 個 Task、17 個 TC、10 筆 Task testcase 關聯；建立 14 個持久化資料夾。
- 名称、身分、Plan／Task 關聯、執行時間、bug ID、選取欄位、環境及 Task 設定比對一致；舊 `pending` 狀態按核准模型轉成 `TBD`。
- 舊 results／logs 檔案原封保留。現存舊結果 JSON 的 TC ID 已不屬於目前 Task 範圍，因此未將歷史結果重新綁定到其他 TC；新版畫面維持核准的當前狀態模型。
- SQLite `integrity_check` 為 ok，`foreign_key_check` 無違反。
- 114 個不需變動的原有修改／未追蹤路徑（包含既有刪除）逐一比對保留；資料庫屬於已驗證升級項目。
- 兩份重疊未追蹤文件已先保存於 `overlapping-originals/`：原 `CONTEXT.md` 的過時 Snapshot 語意依核准設計更新；SPEC 與分支版本相同。
- 舊 main 另保留分支 `codex/pre-release-main-20260930`。測試 Worktree、其測試資料及 5127 預覽保留。

## 驗證

正式資料副本啟動兩次，TC 數量、關聯與資料夾 ID／排序一致。整合前完整測試通過；合併後第一次驗證缺少 Worktree 專用的 baseline fixture，補齊隔離副本後，**Python 138 / 138、JavaScript 68 / 68 通過**。

正式 5000 Chrome 驗證通過：Plan 樹狀清單、單條 TC 全步驟預覽、資料夾選單、白色主題、14px 名稱字體、Tasks 按 Plan 分組及 Test Executions 按 Plan 分組。無 JavaScript pageerror，未對實體 BMC 下達測試。

證據位於備份目錄：`formal-verification.json`、`formal-browser.json`、`formal-plan.png`、`formal-executions.png`、`merged-python-final.txt`、`merged-node.txt`。

## 啟動與還原參考

服務固定綁定 `127.0.0.1:5000`，debug 與 reloader 關閉，沿用原本的本機部署方式。可重啟入口：

```powershell
python D:/Pytest/_redfish/release-backups/2026-09-30-formal-release/formal_server.py
```

启动前應確認 5000 無其他服務；本次程序識別記於備份目錄 `formal.pid`，stdout／stderr 也保存在同目錄。未新增系統開機自動啟動設定。

如需回復，先停止這個正式服務並另存上線後資料，再同步還原程式與資料庫；僅回退 Git 不會回復資料庫 schema。升級前完整原件位於 `main-before/`，一致性 SQLite 備份為 `formal-before.db`，Git 備份為 `repository-before.bundle`。
