# RF-01-008 Checkpoint 分行整理 — 2026-11-12

依使用者確認版本，僅將第一個 Checkpoint 改為分行條列：HTTP 200 為該 Checkpoint PASS；404 的精確缺 URI 訊息，或 400 同一 ExtendedInfo entry 同時具有指定 MessageId 與精確 Message，為專案政策允許的 C-PASS；其他回應 FAIL。保留 C-PASS 需 Note 且跳過文件檢查的說明。文字如下：

> Verify the response using these acceptance rules:
> 
> - PASS: HTTP 200.
> - C-PASS - HTTP 404: The message exactly matches "The URI /redfish/v1/openapi.yaml was not found."
> - C-PASS - HTTP 400: A single @Message.ExtendedInfo entry contains both:
>   - MessageId: Base.1.16.InvalidURI
>   - Message: "The URI /redfish/v1/openapi.yaml was not found." (exact match)
> - FAIL: Any other response.
> 
> C-PASS is a project acceptance policy. Include the actual response and acceptance reason in Note, and skip the remaining document checks.

此處 PASS 只表示該 Checkpoint 通過，HTTP 200 後仍執行文件檢查。既有 redirect／環境錯誤處理不變。

## Result 與歷史證據

只改 TEST_CASE.test_method[1].step 與 modified_at。AST 比對確認所有執行程式相同；Result、Expected／Actual、Note 產生方式、判定及其他 metadata 均未修改。原有歷史 result_json、report_definition、Log、人工結果、執行時間完整保留；舊報告不回寫為新描述。

## 正式同步與驗證

- 工作來源及兩份 test_assets 鏡像一致。
- 5 項既有 RF-01-008 conditional case 回歸通過。
- 在正式 DB／來源副本演練更新，第二次執行零變動。
- 正式 Repository 1 筆、Plan 1 筆 RF-01-008 已更新。其餘 RF-01 不修改；原 ID、資料夾、設定、Task 連線與歷史結果保留。更新來源世代／Plan revision，舊結果標記需要重測。
- 更新交易先檢查無 active Task／Running case。逐表逐欄比對只變動允許的 source、version、revision、needs_retest；172 個 Log／報告證據檔雜湊不變；integrity=ok、foreign_key_errors=0。
- 正式唯讀 API 核對 13 筆 Repository、3 筆 Plan 與 3 份歷史預覽通過；未執行 DUT，不需重啟服務。

備份：bmca-runtime/backups/rf008-checkpoint-20261112/，包含 before.db、舊 Plan source、全部 logs/results 及雜湊驗證。驗證：bmca-runtime/verification/rf008-checkpoint-20261112/。Git 不包含正式 DB、設定或歷史 Log。

重新整理頁面可讀到新的來源描述；新執行使用新 Checkpoint，Result 格式維持原樣。前次 [Spec Ref. 交接](2026-11-12-rf01-spec-ref.md) 的分工規則持續適用。
