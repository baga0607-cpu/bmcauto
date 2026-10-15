# Repository / Plan 單檔測項設計

2026-10-07 使用者定案，取代測項必須由多個 steps 組成的限制。舊 steps 測項保留相容性；新匯入測項採一個 Test Case 一個 `.py`。

## 工作流程與所有權

Project 擁有多本 Test Plan（例如不同 SKU）。Repository 保存標準 Python 原始碼；每次匯入由平台產生 UTC 微秒時戳，作為來源版本與測試手法世代。載入 Plan 時複製程式並獨立保存參數，不共用可變程式，也不自動追蹤 Repository 更新。從其他 Plan 複製及 JSON 匯出／匯入保留來源版本。

Task 參照其 Plan 的現存測項，只選 scope 和執行，不修改測項設定。執行 API 依 Task / TC ID 從 Plan 解析最新程式及參數，忽略瀏覽器提交的替代程式或 preset。Task 的標題、韌體資訊與既有人工結果功能維持目前行為。

Plan 的程式適配及参数修改不改來源版本。內部 settings_revision 僅防止覆寫別人的修改及記錄結果條件，並非公開的測試手法版本。修改後所有 Task 下次執行使用新條件；有結果／人工結果的 membership 標記 needs_retest，保留原狀態、結果與 Log。尚未執行的 membership 不產生虛構結果。Task 顯示重測提示；實際完成重跑後移除標記，中止則保留標記。

執行中的 TC（Running）禁止修改 `.py` 與參數；其他 TC 可編輯。Plan 的結構與 Task scope 異動仍沿用既有執行鎖。編輯及執行 admission 在同一 SQLite BEGIN IMMEDIATE 規則下序列化。

## 測項作者介面

`.py` 宣告 literal `TEST_CASE` 字典，含 `name`、選填 `description`，及 `parameters`。各參數宣告 `type`（string / integer / number / boolean）、`default` 與選填 `label`。平台使用 AST 讀取宣告，不為預覽或匯入執行 Python。

```python
TEST_CASE = {
    'name': 'Example service entry',
    'parameters': {
        'preset': {'type': 'string', 'label': 'Resource path', 'default': '/redfish/v1/'},
        'expected_status': {'type': 'integer', 'label': 'Expected HTTP status', 'default': 200},
    },
}

def execute(client, context=None, preset=None):
    settings = context['case_settings']
    response = client.get(preset)
    if response.status != settings['expected_status']:
        raise AssertionError('Unexpected HTTP status')
```

這是可編輯欄位與單檔載入的初始契約；各測項可調整參數仍依後續 case-by-case 討論。preset 若有宣告則額外傳入 execute；所有參數均由 context['case_settings'] 取得。程式每次執行重新讀取，不沿用 import 快取。

Repository 原始碼保存於 repository_cases 表；Plan 原始碼保存於 main_program/testcase_database/scripts/<TC-ID>/case.py。資料庫新增 source_version、repository_id、settings_json、settings_revision 等欄位。來源版本不會隨 Plan 設定變更更新。

## 介面

- 頂部 Test Case Repository：匯入 `.py`、查看標準測項與來源時戳、下載作者範例。
- Plan 的 Add from Repository：將選取的標準測項複製至該 Plan。
- Plan TC 預覽 / Edit：編輯宣告參數及專案 Python 適配。修改宣告後按 Read editable fields 重讀欄位，再儲存。
- Task：保留舊結果，顯示需重測及舊結果對應先前條件的提示。
- 舊積木編輯器標記為 Legacy step builder，既有測項仍可用。

## 本輪界線

本輪處理載入與設定所有權。全自動／半自動標記、not run / Pass / Fail / Error / block 結果契約、完整 config 注入、Test Plan 文件及跨 Task Final Report，仍依後續面向逐一定案，尚未宣稱本輪完成。現有結果執行契約保留：正常返回並且 context 狀態通過才 Passed；例外依原框架 Failed。
