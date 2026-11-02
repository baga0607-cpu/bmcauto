# Compliance 測項執行與結果政策

> RF-01-008 current acceptance rule: HTTP 400 is PASS with Note only when one Redfish @Message.ExtendedInfo entry contains both MessageId Base.1.16.InvalidURI and the exact Message “The URI /redfish/v1/openapi.yaml was not found.” Other 400 responses fail. The existing explicit-message HTTP 404 rule still applies.

2026-10-06 使用者定案（RF-01-008／013 建議入口的結果規則已由下方 2026-11-02 決議取代）。本文件優先於先前文件的 N/A、未驗證、待確認、未符合建議等獨立狀態及建議入口不判 Fail 的安排。尚未修改 BMCAgent 程式。

## 自動化分類

2026-10-15 補充定義：只要 .py 提供可在 Test Plan 改動的 Parameters／Preset，即為半自動，即使執行時不需詢問或使用預設值亦同。既有「有互動分支即為半自動」規則繼續適用。全自動必須同時沒有 Plan 可編輯參數且所有分支全程自動。Task 連線環境設定不屬於此處測項宣告的 Parameters／Preset。

RF-01-001 最初可編輯 request_timeout 時屬半自動；目前 parameters={}、逾時固定15秒且無互動分支，屬全自動。這是分類政策，不代表 BMCAgent UI 已實作自動識別。

- 全自動：齒輪標記；沒有 Test Plan 可編輯 Parameters／Preset，且所有執行分支均全程自動，才能分類為全自動，可由使用者安排先執行。
- 半自動：板手標記；有 Test Plan 可編輯 Parameters／Preset，或有需要測試者互動的能力或分支，任一成立即為半自動。分類依測項能力固定，不隨當次 preset 是否填寫而改變。
- 互動詢問未回答則持續等待，不設 timer／timeout。RF-01-005 預期版本 preset 未填時詢問；空白提交代表仍未提供版本，Fail 理由為「Tester未提供版本號碼」。尚在等待不視為已完成或自動判 Fail。
- RF-01-005 固定為半自動；preset 已填雖可免除當次互動，仍顯示板手。其餘獨立測項以全自動為設計目標，實作若加入任何互動分支，必須標為半自動。

## 狀態

| 情況 | 狀態 |
|---|---|
| 未執行 | not run |
| 執行後滿足案例條件 | Pass |
| 程式本身執行有問題 | Error |
| 其他非程式問題，未滿足條件或無法完成判定 | Fail，必須提供理由 |

N/A、未驗證、待確認、執行不完整等不再作為程式獨立結果。測项實際執行後若發生上述情況且不是程式問題，判 Fail，理由保留原本的適用性／證據／環境／建議項語意。例如「未發現 fragment 屬性引用」、「未取得 TaskMonitor 證據」。尚未啟動的測項仍是 not run，不因欠缺證據提前改成 Fail。

所有 Fail 必須提供可判讀的理由與已取得證據，協助測試者決定維持 Fail 或手動改為 block。block 是測試者手動決策，不由測項自動設定。建議項 Fail 不等同已證明 DMTF 強制要求違規。

不要把所有例外一律當作 Error：程式缺陷／執行框架問題是 Error；DUT 回應不符合、缺少測試者輸入或其他非程式問題是 Fail。底層錯誤需依原因判讀。

現有固定 commit 的 BMCAgent 尚以 Passed／Failed／TBD 運作，所有步驟例外傾向 Failed，沒有完整 Error／block 契約。這是目標政策，後續介面需配合，不宣稱已支援。執行中顯示與手動停止後結果未在本次指定，不自行定義。

## RF-01 共用遍歷與衝突判準

2026-10-06 使用者確認：從 ServiceRoot 沿可發現連結探索本服務的標準與 OEM 資源，包含集合分頁。不自動遍歷外部服務，不呼叫 Actions；保存未讀取項目及原因。每個資源只探索一次，讀完可發現連結及分頁後結束；循環引用不重複讀取。實作須區分資源已探索與分頁尚未讀取，避免漏掉後續頁面。

相同 URI 被多處引用不是衝突。不同實例共用 resource path 須有明確證據；例如不同請求路徑提供不同資源卻宣告相同 @odata.id，且排除 alias／redirect 等合法等同情況。不可只以 path 不同或 payload 的動態值差異判斷不同實例。

無法完成應探索範圍或無法確認疑似衝突：Fail，提供具體原因與範圍；程式本身故障：Error。政策明定排除的外部服務／Action 呼叫不因未讀取本身判 Fail。HTTP redirect 詳細條件留到 RF-02；不得宣稱目前已完成該共用規則。

2026-10-19 English-only Python rule: all test-case .py source, metadata, comments, prompts and result messages must use English. This supersedes earlier exact Chinese failure-message requirements. RF-01-005 now reports "Tester did not provide a version number", "ServiceRoot did not provide RedfishVersion", and "RedfishVersion format does not meet requirements". Test behavior is unchanged.


## DUT 設定還原（2026-10-20 使用者定案）

凡測項會改動 DUT 設定，必須在測試步驟結束後還原至該測項執行前的初始狀態，避免影響後續測項。還原是測項完成條件的一部分。

1. **先保存初始狀態**：在第一次設定變更之前，讀取並保存所有將修改的設定及必要的相依狀態。還原目標是執行前的實際值，不是預設值或硬編碼值。無法取得必要初始值或無可靠還原方法時，不得進行該設定變更，依既有結果政策記錄原因。
2. **明列還原步驟與 Criteria**：TEST_CASE.test_method 必須包含設定還原及驗證；判定條件要求修改過的設定與初始值一致。新增的暫存設定／測試資源亦須清除，使其恢復原先不存在的狀態。
3. **所有結束路徑都執行清理**：以 try/finally 或等效機制安排還原，涵蓋正常完成、驗證失敗、程式例外與可正常處理的使用者停止。變更請求逾時也可能已生效，不能只依成功回應決定是否需要還原；須查證實際狀態。相依設定通常依變更的反向順序還原，單一還原失敗不應阻止其他仍可安全執行的還原。
4. **還原後讀回驗證**：不能僅以還原請求成功當作完成；須讀回並比對初始值，必要時等待設定實際生效。完成還原檢查後才輸出最終結果，不得先記 Pass 再清理。
5. **Log 與結果**：使用統一 Log 介面記錄獨立的 Restoration 階段、還原操作證據及每個比對結果。Log 不可洩漏密碼／token等敏感初始值。還原失敗或無法確認時不得 Pass；依原因區分 Fail（DUT／環境問題）或 Error（程式問題），同時保留原測試失敗與還原失敗原因，不可互相覆蓋，也不自動設定 block。明確列出未還原項目與人工恢復資訊，恢復確認前不應執行依賴該狀態的後續測項。
6. **驗證覆蓋**：有設定改動的測項，離線測試須覆蓋成功、途中失敗／例外、部分修改、請求逾時及還原失敗，確認初始值保留、清理確實執行、失敗不誤判 Pass。

程序被強制終止、主機斷電或 DUT 無法連線時，finally 無法保證完成還原；不得宣稱已恢復。此類案例設計需保留可用的恢復指引及必要且受保護的恢復資料。平台停止／排程控制的落實另由平台工作處理；本條規範不代表平台已新增自動攔截功能。

目前 RF-01-001～006 的測項操作為讀取 HTTP GET，沒有 DUT 設定寫入，因此不加入虛構的設定還原步驟。日後若擴充為修改設定，亦必須遵守上述規範。所有 .py 內容及 Log 文字仍須使用英文。


## 測項建立規則：Spec Ref. 與 Note（2026-11-02）

本節適用於新增或修訂的 Redfish compliance 測項。下列兩例的驗收條件優先於歷史文件中「缺少建議入口一律 Fail」的說明。

- **Spec Ref. 是設計依據。** 在英文 Python 原始碼的靜態 `TEST_CASE` metadata 宣告 `test_type: "compliance"` 及 `spec_ref`。使用字串或字串清單，寫出規範編號、版本、章節，適用時加表號。多個步驟有不同依據時，可在對應的 `test_method` 項目加 `spec_ref`。分開寫規範要求與 BMCAgent 自訂驗收條件，Criteria 要說明必要條件、建議或允許的替代做法。舊來源的欄位在平台上是選填；本規則要求新建／修訂的 compliance 測項明列依據。
- **Note 是執行結果的補充。** 當已定義的可選分支或建議偏差成立，以英文記錄實際證據、允許接受的規範理由、未執行的驗證範圍。有說明才填 Note，一般成功可留空。Note 不改變其他必要檢查的判定，也可與失敗結果並存。
- **保留在統一 Log 與報告中。** 將 Note 隨對應的 `log.check(..., note=...)` 和 `log.step(..., note=...)` 輸出，彙整到 `context["case_result"]["note"]` 與 `log.finish(..., note=...)`。沿用 Step／Criteria／Result；未執行的步驟以 `Result=None` 表示。報告從該次執行的 `result_json.note` 取 Note，從 `report_definition` 取 Spec Ref.。歷史結果不回填；重測只使用當次 Note。
- **建立時核對分支。** 用離線案例覆蓋正常提供、可接受偏差、證據不足及必要條件失敗。確認接受分支的 Note 可在步驟和最終結果找到，並核對未執行步驟及 Spec Ref.。只有個案明列、且實際證據符合的分支可採 PASS＋Note。

| 測項 | 目前的驗收例子 |
|---|---|
| RF-01-008 | 404 須在 JSON 的 `error.message` 精確符合 `The URI /redfish/v1/openapi.yaml was not found.`；400 須在同一筆 `error.@Message.ExtendedInfo` 同時符合 `MessageId=Base.1.16.InvalidURI` 及相同的 `Message`。以上才接受 PASS＋Note，保留原始狀態並註明未驗證文件。HTTP 200 仍驗證 YAML 與欄位，其他錯誤依原因判定。|
| RF-01-013 | 接受宣告且成功取得、辨識的本機檔案，包括目前支援的 `ArchiveUri`＋`ArchiveFile`。未取得建議 `/Schemas/` 路徑證據時，該項檢查 PASS＋Note，不能據此推論入口不存在。已辨識 JSON 的 dialect 與建議值不同亦以 Note 記錄。整體 Pass 仍要求完整探索且至少一個檔案、所有必要檔案驗證成功。依目前程式，僅受封裝格式支援限制且沒有其他探索／檔案失敗時為 Block；此例不推廣為其他測項的自動 Block 規則。|

平台欄位與相容性詳見 [報告輸出契約](../agents/report-step-output.md) 與 [Spec Ref. 宣告及報告資料來源](../status/2026-11-02-approved-report-layout.md)。兩支測項的實際條文與版本以各自的 `TEST_CASE.spec_ref` 為準。

## 2026-11-02 Expected／Received 訊息格式

結果原因若包含預期／實際值比對，統一使用 `Expected A = X; Received A = Y`，分號分隔、Received 首字大寫，兩側重複同一欄位名稱。例：`Expected HTTP status = 200; Received HTTP status = 404`。僅調整文字，不改判定、Note 或既有 Log。
