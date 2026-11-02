# RF-01-005 Redfish Protocol Version

2026-10-19（Asia/Taipei）：已建立獨立 `testcases/redfish/rf_01_005_redfish_protocol_version.py`。未匯入正式Repository／Plan，未執行實體BMC；未修改平台程式或重啟服務。

## 執行契約

- 固定semi_automatic；唯一Plan參數preset（string，預設空白，label為Expected RedfishVersion）。即使填好preset仍為半自動。
- 使用execute傳入的preset；為None時讀context.case_settings.preset。平台已從Plan載入設定並傳入preset，不讀全域設定。
- 空字串／純空白／None時使用現有input介面詢問，沒有回答timer。空白提交或獨立執行EOF視為未提供版本，Fail理由精確為「Tester未提供版本號碼」，不發HTTP請求。平台Stop例外向外傳遞，由runner處理，不轉成Error或缺少版本Fail。
- 非空預期字串不trim、不做數字轉換。實際RedfishVersion存在且為三段ASCII十進位整數字串，並與預期完全相同才Pass。前導零不額外禁止，但不得與無前導零版本視為相等。較新版本仍須精確相等。
- 缺少屬性Fail：「ServiceRoot未提供RedfishVersion」；型別／格式錯誤Fail：「RedfishVersion格式不符合要求」；不相等Fail列出expected與actual。
- GET /redfish/v1/，Accept application/json，固定HTTP timeout15秒；沿用同origin、最多5次及防循環redirect暫定防護。RF-02保留完整redirect規則。JSON需為object，HTTP需為200。002的ServiceRoot型別／URI判定不重複加入005。
- 統一Log記錄輸入、Task設定、HTTP證據、JSON解析、版本格式與精確比對、最終結果。原始HTTP文字證據保存在case_result；觀察記錄expected_RedfishVersion、expected_version_source、RedfishVersion。支援無平台的stdout fallback。
- 平台目前CaseLog建構方式為(result_file, emit)，測項僅使用section/http/check/finish公開方法，相容單一test.log；檔名由平台負責。

## 驗證

`BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_005_check.py`：8組測試全通過，含多組版本與錯誤情境。覆蓋literal metadata、preset優先／context fallback／互動輸入、未回答期間尚無結果、空白與EOF、Stop例外傳遞、完全相等／較新較舊版本／前導零／空白／格式型別、HTTP／JSON／redirect、環境Fail與程式Error、敏感header過濾，以及目前平台CaseLog的Pass／Fail與單一finish。

requests及input模擬、socket禁止連網，未載入app／正式DB。平台SDK仍先登入才執行.py；Error仍存成Failed的既有限制未在本輪處理。

2026-10-19 English-only Python rule: all test-case .py source, metadata, comments, prompts and result messages must use English. This supersedes earlier exact Chinese failure-message requirements. RF-01-005 now reports "Tester did not provide a version number", "ServiceRoot did not provide RedfishVersion", and "RedfishVersion format does not meet requirements". Test behavior is unchanged.
