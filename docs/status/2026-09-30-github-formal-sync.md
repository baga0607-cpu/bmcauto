# 正式版與 GitHub 同步、備份紀錄

日期：2026-09-30。使用者明確要求 GitHub main 與現有本機正式版一致，包含程式、TC 資產、設計、計畫與 skill。

## 同步範圍

本次推送既有正式版實作提交，以及分開提交的正式 TC JSON、實際新增／移除的 TC 腳本、9 個步驟檔、文件和 runtime 排除規則。保留正式資產內容，包括原有空白格式；本次沒有修改測試邏輯。

GitHub main 管理可重建的程式與 TC 定義。執行中的資料庫、含連線資訊的 config.yaml、Log 與結果檔屬於 runtime 狀態，另行完整備份；Git checkout 本身不等於還原正式資料。原本追蹤的 import_tc_debug.txt 改為僅本機保留，實體檔案未刪除。

本次取代先前僅文件的 PR #2 交付方式。GitHub Issue #1 保留作為設計索引。

## 備份

本機備份目錄：`D:/Pytest/_redfish/release-backups/github-formal-sync-20260930-164242`。

- `files/`：301 個檔案，包含正式程式、TC、設定、資料庫、結果及 Log；排除 Git 內部資料、虛擬環境、快取和獨立驗證 Worktree。
- `manifest.json`：每個檔案的路徑、大小及 SHA-256；備份後逐一重新核對。
- SQLite 使用 backup API 製作一致性副本，完整性與外鍵檢查通過。
- `repository-before.bundle`：本次同步前的 Git 分支歷史。
- `repository-published.bundle` 與 `published-source-manifest.json`：同步完成時的 Git 歷史及正式 checkout 原始檔雜湊；最後保存 `published-commit.txt` 對應遠端版本。
- `validation/`：本次測試輸出及正式 API／DB 核對紀錄。

這是本機備份，不是異地備份；GitHub 上沒有正式資料庫與含連線資訊的設定副本。若主機磁碟故障，仍需要將此備份目錄另存至組織指定的安全備份位置。

## 還原順序

1. 先另存目前正式資料，停止使用 5000 的正式服務；確認目標路徑，避免覆寫其他專案。
2. 從 GitHub 或 published bundle 取回 published-commit.txt 對應版本。
3. 從 files/ 還原 main_program/config.yaml、web_ui/workspace/ 及需要的執行 Log。其他程式與 TC 資產以同版 Git checkout 為準。
4. 驗證備份 manifest、SQLite integrity_check / foreign_key_check，確認 DB 指向的 TC 腳本存在。
5. 依既有正式服務啟動方式綁定 127.0.0.1:5000，核對 UI 與 API。備份含連線資訊，應保存於受控位置。

## 本次驗證

- Python unittest：138 項通過，使用備份衍生的獨立 workspace / main_program 副本。
- Node：68 項通過。
- 新增與修改的 TC / step 資產完成 Python AST／JSON 解析。
- 正式 5000 API 可連線，17 筆 TC ID 與正式 SQLite 相同，所有 DB script_path 都有對應檔案。
- 本次未對實體 BMC 執行測試。既有 Chrome 驗證見正式版整合紀錄。
