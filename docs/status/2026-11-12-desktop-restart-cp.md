# 桌面重啟工具與 CP 正式啟用 — 2026-11-12

## 問題與原因

使用者看到 RF-01-008 為 FAIL，但 2026-11-12 15:25:52（UTC+08）執行的 Checkpoint、finish 與 case_done 都為 CP。無 manual override，也沒有 execution errors。
正式服務自 12:13 啟動，仍使用更新前主程序的 CP -> 預設 Failed 映射；新子程序已能產生 CP。正式 SQLite CHECK 當時也未加入 CP。

桌面 BMCAgent.lnk 指向 D:/Codex/bmc_auto_test/bmca-runtime/launch.ps1。原工具相同連線模式只開網頁，只有切換 Local/LAN 才嘗試重啟；重啟要求 PID 檔等於監聽 PID，無法辨識 Windows venv 的父子程序。

## 完成修改

- 桌面入口新增 Open BMCAgent / Restart service / Cancel，保留 Local / LAN 選擇並預設目前模式。原捷徑不需更換。
- Restart service 即使模式相同也重啟；Open 在相同模式沿用服務，改模式仍詢問重啟。
- service-control.ps1 從實際監聽 PID 辨識本工作區的 Python + 精確 server.py 路徑，再追溯經驗證的 Python 父程序。停止前重新核對 creation time / executable / command line。
- 不依 PID 檔強制終止程序，不停止其他 Python、其他 server.py、PID 重用者或不明監聽者。
- 查詢執行狀態失敗或有 active runs 時拒絕重啟；備份後、停止前再檢查。此工具沒有全域 maintenance lock，重啟期間勿另啟動新測試。
- restart-backup.py 使用 SQLite backup API 自動建立備份，啟動後比對所有資料表指紋、integrity / foreign keys，並記錄 CP schema。
- NoBrowser 模式錯誤輸出 stderr，不彈出隱藏的阻塞對話框。
- 在正式資料庫副本預演時發現 CP migration 不接受 SQLite rename 後的 CREATE TABLE "task_testcases"。已修正 quoted / unquoted table name 相容性並新增回歸測試。

## 正式部署結果

使用新版工具相同流程執行：

powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/Codex/bmc_auto_test/bmca-runtime/launch.ps1 -Action Restart -Mode Local -NoBrowser

- 2026-11-12 15:40:30（UTC+08）新服務啟動。
- 舊 launcher/listener PID 18928 / 26100 已結束；新 launcher/listener PID 25332 / 23152。
- 首頁 HTTP 200；active_runs=0；Local 模式保留。
- 備份：D:/Codex/bmc_auto_test/bmca-runtime/backups/restart-20261112-154027-284/testcase_meta-before.db。
- after-verification.json：21 tables、changed_tables=[]、integrity=ok、foreign_key_errors=0、cp_schema=true。
- 正式服務已載入 CP 更新；新執行可保存 CP，不再由舊主程序降成 Failed。
- 未執行實體 DUT 測試，未更改已保存結果。RF-01-008 的既有 FAIL 仍為原紀錄；需重跑才產生新的 CP 結果。
- 此紀錄取代前一份 CP 交接的「正式服務尚未重啟」狀態。15:25 的執行已確認實際 Plan 副本為新版 RF-01-008。

## 驗證與交付

- 12 個 PowerShell 程序辨識 / active-run 測試通過：直接 listener、父子鏈、孤立 child、不同 executable / script、同名不同目錄、PID 重用、多 listener、active / unavailable API。
- 3 個 SQLite 備份測試通過：完整備份 / 指紋、既有備份不覆寫、active execution 拒絕、資料改動偵測。
- 原生 WinForms Open / Restart / Cancel 點擊與 LAN 預設值測試通過；離螢幕繪製 launcher.png 已目視檢查。未透過 UI 測試停止服務。
- 本機與發佈版本 CP / migration Python 各 22 項通過。正式資料庫副本完整 migration 連跑兩次，21 個資料表內容保留，CP schema 與完整性驗證通過。
- 實際唯讀辨識舊父子 PID 成功；Open -NoBrowser 未重啟服務；正式 Restart 完整流程成功。
- 驗證目錄：D:/Codex/bmc_auto_test/bmca-runtime/verification/desktop-restart-20261112。
- 發佈原始碼：tools/windows-launcher/，包含部署方式與測試。執行檔仍部署在 sibling bmca-runtime/，不直接在 tools 原始碼目錄執行。
- Windows firewall helper 與 LAN 規則沿用既有行為；本次正式重啟為 Local，未測試遠端 LAN 連線。
- 發佈目標 baga0607-cpu/bmcauto main；獨立 publication checkout，未提交既有本機無關改動。
