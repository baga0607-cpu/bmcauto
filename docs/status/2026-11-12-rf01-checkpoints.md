# 其餘 RF-01 Checkpoint 整理 — 2026-11-12

依使用者逐項確認的版本，將過長或含多個條件的 Checkpoint 改為分行條列。共 11 支測項、26 個 Checkpoint。RF-01-001 與先前完成的 008 不變。

| 測項 | 修改 Checkpoint 數 |
| --- | ---: |
| RF-01-001 | 0 |
| RF-01-002 | 1 |
| RF-01-003 | 1 |
| RF-01-004 | 2 |
| RF-01-005 | 2 |
| RF-01-006 | 2 |
| RF-01-007 | 1 |
| RF-01-008 | 0 |
| RF-01-009 | 3 |
| RF-01-010 | 2 |
| RF-01-011 | 4 |
| RF-01-012 | 4 |
| RF-01-013 | 4 |

## 變更界線

只修改 TEST_CASE.test_method 中已確認的 Checkpoint.step 與 modified_at。沒有增加／拆分 Checkpoint、更動 Step number／method_index、修改 Spec Ref. 或其他參數。AST 比對排除 TEST_CASE 後完全相同，metadata 比對也確認只變更指定文字與修改時間。

Result、Expected／Actual、Note 的產生方式與內容，以及 PASS／FAIL／C-PASS／Skip／Block 判定邏輯全部維持原樣。013 的 Block 文字明確指 Case outcome，不讓 Checkpoint 使用 Block。來源使用真正換行與一般文字條列，不依賴 Markdown renderer。

## 驗證

- 27 項既有離線回歸通過：test_rf01_method_items、test_rf01_series_audit、test_conditional_pass.ConditionalCaseTest。
- 每支已修改來源與本機／發布 test_assets 鏡像相同；metadata 與 runtime AST 查核記錄於 audit.json。
- 正式 DB／來源副本更新演練通過，第二次執行零變動。
- 正式更新 Repository 11 筆；既有 Plan 只有 001／002／008，其中僅 002 需要更新。未自動加入其他測項或變更 Task scope。
- 保留 ID、名稱、位置、資料夾、settings_json、Task Connection、人工判定、原狀態、執行時間、result_json／report_definition／result_note／log_text／api_log_text。僅來源、來源世代、Plan revision 與 needs_retest 依更新流程變動。
- 173 個既有 Log／報告證據檔雜湊一致；SQLite integrity=ok、foreign_key_errors=0。既有 002 結果標記需要重測，不重新判定。
- 正式唯讀 API 核對 13 筆 Repository、3 筆 Plan 原設定與來源、3 份歷史報告預覽通過。未執行 DUT。

備份：bmca-runtime/backups/rf01-checkpoints-20261112/，含 before.db、更新前 Plan source、全部 logs/results、雜湊及 verification.json。驗證：bmca-runtime/verification/rf01-checkpoints-20261112/，含 before、replacements.json、audit.json、tests.txt 與資料副本。正式資料及設定不提交 Git。

重新整理後即可使用更新來源，不需要重啟服務。歷史結果的 captured description／report_definition／Log 保持原樣；重跑才產生新描述，Result 格式仍不變。

前次交接：[RF-01-008 Checkpoint](2026-11-12-rf008-checkpoint.md)、[Spec Ref. 與政策分離](2026-11-12-rf01-spec-ref.md)。
