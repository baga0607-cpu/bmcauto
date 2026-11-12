# 既有 RF-01 Repository／Plan 更新 — 2026-11-12

依使用者明確要求，將正式環境既有 RF-01 測項更新為 8afe30a 的最新來源，同時保留設定與歷史測試證據。此紀錄取代上一份全系列交接中「既有副本尚未更新」的待辦。

## 更新範圍

- 實際既有 RF-01 只有 001、002、008：Repository 3 筆、1 個 Plan 內 3 筆，皆已更新。其餘 10 支沒有既有記錄，本次沒有新增測項或更動 Task scope。
- Repository 原 ID、名稱、資料夾關係保留；更新 source_text 及 source_version。Plan 的 case.py 更新為相同來源，source_version 對齊原 repository_id 的新來源世代，settings_revision 遞增以防舊畫面覆寫。
- 完整保留 Plan settings_json、Task Connection／其他設定、ID、位置、資料夾、選取狀態、人工判定、Bug ID、原判定、執行時間、result_json、result_note、log_text 與 api_log_text。
- 3 筆已有結果的 Task membership 標記 needs_retest=true。原結果不重判、不改為 NR，也沒有執行 DUT。

## 備份與驗證

本機備份：bmca-runtime/backups/rf01-installed-update-20261112/。

- before.db：一致性 SQLite 完整備份。
- main_program/：3 支更新前 Plan case.py。
- evidence/logs、evidence/results：168 個歷史 Log／報告證據檔完整備份。
- before-file-hashes.json、verification.json：檔案雜湊及正式更新驗證。

更新使用 BEGIN IMMEDIATE 序列化，檢查無 active Task／Running case 後才寫入。先在 DB／來源副本演練成功、人工注入中途錯誤後完整回復、再次更新零變動，再套用正式資料。

逐表逐欄比對確認，僅 repository_cases 的 source_text／source_version、testcases 的 source_version／settings_revision、task_testcases 的 needs_retest 可變動。其餘所有表／欄一致；來源檔以外的 main_program 檔案、168 個證據檔雜湊一致。integrity_check=ok、foreign_key_check=0。

正式服務唯讀 API 確認 Repository 3 筆來源、Plan 3 筆來源／原設定一致且未鎖定；3 份舊報告預覽可讀；API 驗證前後 DB 資料一致。服務每次執行重新讀取 Plan source，這次無需重啟。驗證腳本與副本在 bmca-runtime/verification/rf01-installed-update-20261112/，不提交正式 DB、備份、Log 或含設定的 runtime 檔案。

## 使用與接手

重新整理 Execution 後可直接選取原測項重新執行，使用 Command／Action／Checkpoint／Record、C-PASS／Skip 與無 [n] section 前綴的新格式。舊 Log 保留原格式。平台仍是每個 Task membership 保存最近一次結果，重跑後更新目前結果；重跑前的完整資料已另存上述備份，原磁碟 Log 不會因此被覆寫。

本次只更新正式實例資料與交接文件，不另改平台程式或測試判定邏輯。Git 僅提交交接紀錄至 baga0607-cpu/bmcauto main。
