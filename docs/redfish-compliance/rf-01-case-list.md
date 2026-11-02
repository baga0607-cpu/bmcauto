# RF-01 定案測項清單

> 2026-11-02 更新：RF-01-008 的明確 HTTP 404，以及 RF-01-013 缺少 /Schemas/ 建議入口證據，依 DSP0266 1.25.0 Required=No 改為 PASS＋Note；本機檔案依宣告位置驗證，不採兩種前綴白名單。必要檢查失敗仍 Fail。此規則取代本文較早的建議項 Fail 描述，詳見 execution-policy.md 與兩份 implementation 文件。報告格式另議。

最新執行分類與結果政策見 execution-policy.md，優先於本文件及舊案例文件的其他狀態安排。互動無 timer；結果採 not run／Pass／Fail／Error；其他非程式問題於執行後為 Fail 並附理由，block 由測試者手動決定。

2026-10-06：本對話已逐項確認驗證目的、動作與結果原則。尚未產生 Python、執行 DUT 或完成 RF-02 共用 redirect 規則。細節見 rf-01-standard-endpoints.md 與 rf-01-validator-report-review.md；報告複核及其後最新決策優先於早期口頭涵蓋記錄。

階層：Compliance Test → Redfish Test Suite → TestCaseName。

| ID | TestCaseName | 交付方式 |
|---|---|---|
| RF-01-001 | Version Discovery Endpoint | 獨立 .py |
| RF-01-002 | Service Root Endpoint | 獨立 .py |
| RF-01-003 | OData Service Document Endpoint | 獨立 .py |
| RF-01-004 | Metadata Document Endpoint | 獨立 .py |
| RF-01-005 | Redfish Protocol Version | 獨立 .py；preset 優先，未填執行中詢問，仍未提供 Fail：Tester未提供版本號碼 |
| RF-01-006 | Service Root URI Alias | 獨立 .py |
| RF-01-007 | Version Discovery URI Alias | 獨立 .py |
| RF-01-008 | OpenAPI Document Endpoint | 獨立 .py；建議入口 |
| RF-01-009 | Resource URI Uniqueness | 獨立 .py；遍歷證據及不同實例判準須實作前細化 |
| RF-01-010 | URI Character and Encoding Rules | 獨立 .py |
| RF-01-011 | URI Fragment References | 獨立 .py；條件適用 |
| RF-01-012 | Relative URI References | 獨立 .py；GET 所見 Body／headers 範圍 |
| RF-01-013 | Local Schema File Endpoint | 獨立 .py；建議入口與宣告檔案可取得性分開判定 |
| RF-01-014 | Task Monitor URI | 保留追蹤編號；檢查邏輯規劃合併至適當的 RF-14 .py，以獨立子結果記錄；不另建獨立 .py。狀態：待實作／未執行。 |

13 個規劃獨立 Python 測項，1 個跨章證據檢查項；不是已完成 13 個程式。

不另建自訂測項：Schema URI patterns 與已測本地 Registry 檔案取得／內容引用 RSV；資源識別有部分 RSV 證據，未證明的識別缺口仍保留；OEM 專屬 URI 規則由 RF-10；所有發現資源符合相同 protocol version 為跨章彙整要求。

## 實作前待定介面

- 預期版本 preset 欄位名稱、測試者互動詢問 API 與等待結束方式；不能自行假設逾時時間。
- Pass／Fail／N/A／未驗證／待確認／執行不完整／未符合建議的結果表示與 suite 彙整。缺測試者版本按特別規則 Fail，不等同 DUT 違規。
- RF-02 redirect 共用細節，以及平台取得原始 status／headers 的方式。
- 遍歷與衝突判準已確認於 execution-policy.md：本服務標準／OEM、分頁、外部服務排除、不呼叫 Actions、每資源探索一次；不同實例須排除 alias／redirect 與動態值差異後有明確證據。
- 依固定 Schema／產品文件確認本地檔案種類與最低辨識例外，避免排除合法文件形態。

下一步先確認上述執行契約再產生 .py。此清單完成規劃定案，不宣稱規範或 DUT 驗證已完成。

## 2026-10-19 實作狀態補充

RF-01-001～003已建立並整合統一Log；RF-01-004已建立獨立.py，7組離線測試通過，沿用統一Log，尚未匯入正式Repository／Plan或測試實體BMC。005～013仍為規劃；014引用RF-14證據。004詳見[實作紀錄](rf-01-004-implementation.md)。

2026-10-19後續：RF-01-005已建立，固定半自動、preset／無逾時互動及精確版本比對，8組離線測試通過；尚未正式匯入或真機測試。006～013仍規劃，014引用RF-14證據。見[005實作紀錄](rf-01-005-implementation.md)。

2026-10-19: RF-01-006 implemented; six offline test groups passed. Not imported into formal Repository/Plan or run on physical BMC. RF-01-007–013 remain planned;014 uses RF-14 evidence. See [006 implementation](rf-01-006-implementation.md).

2026-10-30: RF-01-007 implemented with unified Log, Step/Criteria/Result and source creation time; seven offline test groups passed. No formal import or physical BMC execution. RF-01-001 through RF-01-007 now have sources; RF-01-008 through RF-01-013 remain planned, and RF-01-014 uses RF-14 evidence. See [007 implementation](rf-01-007-implementation.md).

2026-10-30: RF-01-008 implemented with unified Log, Step/Criteria/Result and actual source creation time; eight offline test groups passed. HTTP 404 follows the latest execution policy: Fail with a missing recommended endpoint reason. No formal import or physical BMC execution. RF-01-001 through RF-01-008 now have sources; RF-01-009 through RF-01-013 remain planned, and RF-01-014 uses RF-14 evidence. See [008 implementation](rf-01-008-implementation.md).

2026-10-30: RF-01-009 implemented with structured-link traversal, pagination, scope evidence and conservative identity-path assessment. Unified Log, Step/Criteria/Result and actual source creation time; fourteen offline test groups passed. No formal import or physical BMC execution. RF-01-001 through RF-01-009 now have sources; RF-01-010 through RF-01-013 remain planned, and RF-01-014 uses RF-14 evidence. See [009 implementation](rf-01-009-implementation.md).

2026-10-30: RF-01-010 implemented with raw URI character/encoding checks, structured-link traversal, unified Log, Step/Criteria/Result and actual source creation time. Thirteen offline test groups passed. No formal import or physical BMC execution. RF-01-001 through RF-01-010 now have sources; RF-01-011 through RF-01-013 remain planned, and RF-01-014 uses RF-14 evidence. See [010 implementation](rf-01-010-implementation.md).

2026-10-30: RF-01-011 implemented with RFC6901 pointer resolution, conservative schema-based reference classification, unified Log, Step/Criteria/Result and actual source birth time. Fifteen offline test groups passed. No formal import or physical BMC execution. RF-01-001 through RF-01-011 now have sources; RF-01-012 and RF-01-013 remain planned; RF-01-014 uses RF-14 evidence. See [011 implementation](rf-01-011-implementation.md) for schema/scope limitations.

2026-10-30: RF-01-012 implemented with Body/GET-header relative URI checks, scope/header counts, unified Log, Step/Criteria/Result and actual source birth time. Fourteen offline test groups passed. No formal import or physical BMC execution. RF-01-001 through RF-01-012 now have sources; RF-01-013 remains planned; RF-01-014 uses RF-14 evidence. See [012 implementation](rf-01-012-implementation.md).

2026-10-30: RF-01-013 implemented with declared local schema-file discovery, separate acquisition/recognition and recommended-path results, unified Log, four Step/Criteria/Result rows and actual source birth time. Thirteen offline groups passed. No formal import or physical BMC execution. All RF-01-001 through RF-01-013 standalone sources now exist; this does not imply all cases were imported or passed on a physical DUT. RF-01-014 remains an RF-14 evidence check. See [013 implementation](rf-01-013-implementation.md).

Historical proposal, superseded by the merged RF-14 decision below — 2026-10-30: RF-01-014 evidence-reference design documented in [RF-14 evidence contract](rf-01-014-evidence-contract.md). Local RF-14 producer and cross-case/offline evidence adapter are not yet implemented. Three Step/Criteria/Result rows are specified using the current Log API. No real evidence evaluation, platform modification or additional standalone DUT-operation script; execution status remains not run.


## 2026-10-30 RF-01-014 最新決議（優先於先前引用介面提案）

保留 RF-01-014 作為需求與報告追蹤編號；檢查邏輯規劃合併至適當的 RF-14 .py，使用同次非同步操作的初始 HTTP 202／Location 證據，不另建 RF-01-014 獨立 .py 或重複執行 DUT 操作。沿用統一 Log 與 Step／Criteria／Result，明確標示 RF-01-014 子結果，與 RF-14 生命週期／還原結果分開記錄。

目前為規劃完成、待 RF-14 實作、未執行。跨測項證據傳遞與獨立離線 evaluator 不再是此方案前置需求；若日後需要獨立 Plan／報告結果列，再由平台加入映射支援。詳見 [RF-01-014 合併規劃](rf-01-014-evidence-contract.md)。
