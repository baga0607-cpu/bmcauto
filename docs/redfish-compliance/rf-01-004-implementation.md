# RF-01-004 Metadata Document Endpoint

2026-10-19（Asia/Taipei）。已建立獨立 `testcases/redfish/rf_01_004_metadata_document_endpoint.py`；未匯入正式 Repository／Plan，未執行實體 BMC。

## 行為

- 全自動、parameters={}，固定15秒HTTP timeout；使用 Task context.redfish 的連線資訊。
- GET /redfish/v1/$metadata，Accept: application/xml；不帶 query、條件式 headers 或 body。
- 沿用001～003的暫定同origin redirect防護（301/302/307/308，最多5次，防循環，不跨origin轉送帳密）；詳細規範仍由RF-02定義。
- 最終HTTP200，原始response.content依XML宣告編碼解析。根元素local name=Edmx、namespace=http://docs.oasis-open.org/odata/ns/edmx、未加namespace的Version屬性精確等於4.0才Pass。prefix任意，允許額外屬性與子元素。
- 不讀取Schema引用，不檢查EntityContainer／定義完整性；留RF-03。HTTP Content-Type符合性留RF-02。
- 標準庫ElementTree搭配拒絕DTD的TreeBuilder，避免處理DTD實體。DTD宣告會以明確parser safeguard理由Fail，不宣稱已證明DMTF違規。非法XML／不支援的文件編碼屬無法完成解析的Fail；未預期程式問題屬Error。
- 使用統一context['log'].section/http/check/finish；保存URI、HTTP status、過濾敏感headers後的headers與body文字證據，以及根元素觀察。獨立執行可fallback stdout，不import平台。HTTP原始位元組用於解析，Log body沿用response.text呈現。
- 檔名與歷史磁碟檔保存由平台負責，004不自行開Log檔。

## 驗證

命令：`BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_004_check.py`

7組unittest全部通過（含多組subTest）：literal metadata與step_x/criteria；prefix與預設namespace；UTF-16/ISO-8859-1；根名稱/namespace/Version錯誤或缺失；非法XML、DTD與未知編碼；非200；redirect各狀態／循環／跨origin／缺Location／上限；連線Fail、程式Error、缺requests及無效設定；敏感header過濾；實際CaseLog介面含HTTP證據與單一Final result。socket禁止連網、requests模擬，不載入app或正式DB。

目前平台仍有SDK前置登入與Error存成Failed的既有限制；本輪只建立測項及驗證文件，沒有修改平台產品程式或重啟服務。
