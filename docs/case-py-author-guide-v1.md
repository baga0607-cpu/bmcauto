# BMCAgent · case.py 作者指南 v1

2026-11-23｜適用於新版單檔 Case 設計

每個 Case 交付一份 Python 測試程式。除非另有指定，檔名使用「案例編號＋測試名稱」，以小寫英文字母、數字與底線組成，副檔名為 `.py`。例如，RF-01-001 的 Version Discovery Endpoint 使用 `rf_01_001_version_discovery_endpoint.py`。檔案開頭的 `TEST_CASE` 讓審閱者在執行前讀完整個測試流程；BMCAgent 從字典外的 `run(ctx)` 開始執行。整份 Python 使用英文，包括名稱、註解、docstring、測試字串、觀察、Note 與例外訊息。Case ID 由平台建立。

**先選對執行環境。** 下文的範本是 v1 作者介面設計。正式版目前仍檢查 `execute(client, context=None, preset=None)`。本機 RF-01-002 prototype 已能執行 `run(ctx)`，但工具方法與設定鍵仍有差異，詳見文末對照。[正式匯入器](../web_ui/single_case.py)

作者選擇測試路徑、執行步驟、設定判定條件並回報觀察。BMCAgent 管理連線、提供通訊事實，並把證據保存到對應的步驟或 Checkpoint。

## 1. 從一個步驟開始

以下是可複製的最小 Redfish Service Root HTTP 狀態檢查，只驗證 GET 的回應狀態。完整 RF-01-002 還有 JSON、資源型別、URI 及版本記錄等步驟。建立新檔時替換名稱、目的、日期、路徑與判定條件；有規格或設計文件依據時補上 `spec_ref`。

```python
TEST_CASE = {
    "name": "Read the Redfish service root",
    "automation": "automatic",
    "description": "Verify that a GET request to the service root returns HTTP 200.",
    "created_at": "2026-11-23T09:00:00+08:00",
    "modified_at": "2026-11-23T09:00:00+08:00",
    "command_routes": {
        "bmc_redfish": {
            "from": "bmcagent",
            "to": "bmc",
            "method": "redfish",
            "lan_port": "task.bmc.lan_ports.port1",
            "username": "task.bmc.username",
            "password": "task.bmc.password",
        },
    },
    "test_method": [
        {
            "step_number": 1,
            "step": "Send a GET request to /redfish/v1/.",
            "route": "bmc_redfish",
            "checkpoints": {
                "http_status": {"expected": "The response status is HTTP 200."},
            },
        },
    ],
}


def run(ctx):
    with ctx.step(1) as step:
        response = step.redfish.get("/redfish/v1/")
        actual = response.status_code
        step.checkpoint(
            "http_status",
            judgement="PASS" if actual == 200 else "FAIL",
            expected=200,
            actual=actual,
        )
```

## 2. 填寫 TEST_CASE

使用頂層字典與可靜態讀取的字面值。載入時，BMCAgent 讀取 `TEST_CASE`。執行時，作者在 `run(ctx)` 透過平台工具執行測試步驟，BMCAgent 依步驟指定的 `route` 管理連線。

| 欄位 | 何時填寫 | 內容 |
|---|---|---|
| `name` | 必填 | 英文顯示名稱。 |
| `automation` | 新建 Case 必填 | 依測試方法需要的人員參與程度，填 `automatic`、`semi_automatic` 或 `manual`。 |
| `description` | 必填 | 英文測試目的。報告會印出這段內容。 |
| `created_at`、`modified_at` | 兩者必填 | 作者填寫台北時間，以含 `+08:00` 的 ISO 8601 字串保存。新建來源檔時兩者相同。直接編輯來源檔時，保留 `created_at` 並更新 `modified_at`。透過 Plan 編輯器儲存時保留原建立時間，修改時間的處理見第 5 節。 |
| `spec_ref` | 有文件化設計來源時必填 | 英文字串清單。列出規範或設計文件名稱／編號，可取得時附版本與章節；每個引用章節各列一項。來源屬於整個 Case，無須逐一對應 Checkpoint。 |
| `environments` | 需要其他機器的 shell 時必填 | 宣告如何取得具名環境，例如從 BMCAgent 經 SSH 登入 Console Server。全程由本機發送時可省略。 |
| `command_routes` | 任一執行分支會發送命令或請求時必填 | 每條路徑有唯一字典鍵，必填 `from`、`to`、`method`，其餘依介面決定。只在錯誤復原分支使用的路徑也要宣告。 |
| `test_method` | 必填 | 有順序的清單，每項代表一個步驟，涵蓋驗證、操作和單純記錄資料的步驟。 |

### 時戳與台北時間

每次修改 Case 來源檔，都必須保留 `created_at` 所代表的原始建立時間，並在同一次修改中將 `modified_at` 更新為本次實際修訂的台北時間。即使只調整格式、註解或 metadata（例如換算時戳的時區），也適用這項規則。

Plan 以 Repository ID 識別來源測項，並以來源的 `modified_at` 比對版本。替換測項庫中的來源檔時，新檔的 `modified_at` 必須晚於原版本。匯入 Plan、複製測項或只修改 Plan 的參數值時，沿用來源的修改時間。

BMCAgent 所有頁面、歷程與報告的時戳一律換算為台北時間（Asia/Taipei，UTC+08:00），採 24 小時制，以 `YYYY-MM-DD HH:mm:ss` 顯示到秒。`created_at` 與 `modified_at` 同樣適用。例如來源值 `2026-11-27T02:42:12.574147+08:00` 和既有來源值 `2026-11-26T18:42:12.574147Z` 均顯示為 `2026-11-27 02:42:12`。

來源檔、API 與版本比對保留時區和原有小數秒精度。新測項的兩個欄位皆須明寫時區。排程起訖日是台北日曆日期，維持 `YYYY-MM-DD`。

### 如何選擇 automation

| 值 | 填寫條件 | 例子 |
|---|---|---|
| `automatic` | 共用 Task Connection 就緒後，程式可自行取得資料、執行及判定。 | RF-01-002 依已宣告的條件驗證 Service Root。測試者事先填 BMC IP 與帳密不影響此分類。 |
| `semi_automatic` | 程式執行部分或大部分測試，方法還需要人員提供 Case 專用參數或預期值，或在執行中操作、觀察、回答問題。 | RF-01-005 由測試者提供預期 RedfishVersion，即使預先填好 preset，仍為半自動。 |
| `manual` | 人員負責操作、觀察並判定。 | 人員操作實體面板、查看燈號並自行判定。現行平台接受此分類，專屬手動工作流程尚未定義。 |

自 2026-11-24 起，v1 作者規則正式啟用：每份新版 `TEST_CASE` 都必須明列上表三值之一。省略欄位、填空值或填 `unclassified` 均不符合 v1。現行匯入器對省略欄位仍會回退為 Unclassified，這是平台驗證與 v1 規則的差異。[現行分類定義](status/2026-10-29-case-floating-tools.md)

### 每一步怎麼寫

- **必填 `step_number`、`step`**。從 1 依清單順序編號，以英文說明動作。匿名、特殊等待、重新導向等會改變測試條件的設定，都寫進該步。
- **發送命令或請求才填 `route`**，值引用已宣告的路徑。進入 `ctx.step(n)` 後，工具沿用該路徑。
- **有固定檢查項目才填 `checkpoints`**。字典鍵是整個 Case 內唯一、穩定的識別值。每筆只填英文 `expected`；平台依鍵配對結果。
- **只有觀察值時，只寫動作**。例如步驟寫 `"Record the RedfishVersion value if present, or record 'Not present' if the property is absent."`，執行時用 `step.record(value)`。報告將值放進該步的 Result。宣告區省略 `type`、`records` 及 Checkpoint 的 `name`。

## 3. 選擇連線路徑

`from` 表示指令在哪個環境執行，`to` 表示目的地，`method` 指定介面。`bmcagent` 是內建起點。同一個 BMC 可以由本機經 Redfish 存取，也可以先進 DUT shell 再經 KCS 驗證；兩種測試目的選用各自的路徑。一般 Console Case 只需宣告如何到達 DUT shell，再指定要在其中執行的驗證。若登入本身就是受測行為，例如驗證錯誤密碼會被拒絕，作者在 `step` 說明並控制該次登入嘗試。環境與介面範例可參考[早期 LAN／KCS 草稿](case-py-author-guide-draft.md)，單檔欄位與報告規則以本版為準。

**一般 Redfish 路徑**明列 `lan_port`、`username`、`password`。即使只有一筆 BMC IP，也指定測試使用的 port；填入 Task Connection 欄位引用，憑證值留在 Task。若測試目的需要查得動態位址，作者將新值明確交給該次重連。臨時值只用於當次 Case，只有測試者可更新 Task Connection。

| 請求情境 | 作者要指定或判定的內容 |
|---|---|
| 匿名存取 | 在步驟說明匿名存取的條件，並於該次呼叫指定匿名模式，例如 `auth="none"`。 |
| 重新導向 | 若測試需要跟隨重新導向，在步驟說明並於呼叫指定，例如 `redirects="same_origin"`。 |
| 逾時 | 特殊等待須在該步說明並指定。測試本身有時限時，將門檻寫入 Checkpoint 的 `expected`。 |
| 收到 4xx／5xx | 依狀態碼與回應內容核對完整接受條件。例如 RF-01-008 要回報 C-PASS，還須確認錯誤內容符合選用端點的缺席規則。 |
| 沒有收到回應 | 依平台提供的失敗原因、送出狀態及測試目的決定後續動作。已送出但逾時，若違反測試時限才據此判 FAIL。重啟等會改變設備狀態的命令若結果不明，先查證再決定是否重送。 |

**逐跳檢查。** 若中間回應也是受測對象，在步驟中寫清起點、可跟隨的狀態碼、跳數上限與允許的目標。RF-01-012 Step 2 從 `/redfish/v1/` 開始，只跟隨同來源的 301、302、307、308，最多五跳，並排除 Action 端點。在逐跳檢查函式中，於下一個 GET 送出前讀取本跳的原始 `Location`、`Content-Location` 與各筆 `Link`。先回報已取得的 Link 語法觀察；若重新導向的 Location 違反受測的 URI 規則，停止跟隨該鏈，並記錄未讀原因。

**只驗證最終回應。** RF-01-002 Step 1 從 `/redfish/v1/` 發出 GET，只跟隨同來源的 301、302、307、308，最多五次。若先收到 302、跟隨後收到 200，就以最終 200 判定 `http_status`，並將該回應本文交給 Step 2。若最終收到 404，GET 已完成，`http_status` 判 FAIL。若 302 指向其他來源而受阻，回報操作失敗及受阻原因，`http_status` 保留「未執行」。

## 4. 回報判定、觀察與提早結束

作者先標明進入哪個步驟，再於該步驟內執行操作。每取得一筆足以判定的觀察就立即回報，即使遍歷仍在進行。v1 設計以 `ctx.step(n)` 標明邊界，現行呼叫見第 6 節。需要保存程式內的觀察值時，由 Case 明確回報，例如用 `step.record(value)` 記錄版本。驗證時，用 `step.checkpoint(checkpoint_id, judgement=..., ...)` 回報該步已宣告的檢查項目。宣告中的 `expected` 說明驗證條件；呼叫時的 `expected` 選填，用於保存這次實際比較的值。

**回報操作結果。** 使用現行介面時，先以 `report.begin_step(n)` 標明步驟。操作成功且有資料要呈現時，用 `report.operation_result(actual=...)`；操作失敗時，用 `report.operation_result(failure=reason)`。一次呼叫擇一填寫，之後仍可回報同一步的 Checkpoint。例如 RF-01-002 Step 2 解析成功時回報 `{"top_level_type": type(body).__name__}`；解析失敗時回報失敗原因，再對 `json_parseable` 回報 FAIL、Actual `"Parse failed"` 與原因，對 `top_level_object` 回報「未執行」與原因。

| 判定 | 作者必填 | 報告如何解讀 |
|---|---|---|
| PASS／FAIL | `actual` | 已執行驗證。FAIL 可另附 `reason` 解釋差異。 |
| C-PASS | `actual`、`note` | Note 說明實際符合哪項條件式接受規則。 |
| Skip | `reason` | 作者明確判定該項不適用；若已有相關觀察，可附 actual。 |
| 未執行（`Not executed`） | `reason` | 前置受阻，已有資訊不足以完成該項驗證。 |

**逐項說明失敗。** 有具體差異時，在該筆 `report.checkpoint(key, "FAIL", actual=value, reason=reason)` 寫明原因。RF-01-002 收到 `@odata.type = "#Wrong.Type"` 和 `@odata.id = "/wrong"` 時，分別對 `service_root_type_format` 說明型別格式不符，對 `service_root_uri_exact` 說明 URI 必須精確等於 `/redfish/v1/`。兩個欄位皆為字串，因此各步的字串檢查仍判 PASS。

### 選擇備註層級

整個 Case 的執行背景，例如「更新韌體後重新執行」，可放在 Case 層級的 `note`。備註的保存位置及現行正式介面見第 5 節。

Checkpoint 的 `note` 用於 C-PASS。核對全部條件式接受規則後，明確回報 `judgement="C-PASS"`，並以英文說明符合的條件。FAIL 的差異可寫在 `reason`。以下是選用端點符合缺席條件時的 v1 呼叫範例。

```python
step.checkpoint(
    "optional_endpoint",
    judgement="C-PASS",
    actual=response.status_code,
    note="The endpoint is optional for this model and meets the documented absence criteria.",
)
```

範例中的 `optional_endpoint` 應先宣告在該步的 `checkpoints`。

### 提早結束與多筆觀察

RF-01-008 的選用端點若符合專案明定的缺席條件，作者先回報端點 Checkpoint 的 C-PASS 與 Note，再明確指出哪些後續文件驗證已不適用，並提供 Skip 原因，例如 `"Optional endpoint is absent; no document is available for validation."`。若只是前置連線受阻，應依已知事實說明受阻原因。單純 `return` 不代表作者已判定後續項目應 Skip。若整個流程提早結束，回報已知觀察與受阻原因即可。RF-01-012 現行結束呼叫見第 6 節。

例如 RF-01-012 遍歷完整且所有回應都沒有 Link，Checkpoint A 判 Skip，理由是範圍內沒有可檢查的 Link。若部分資源未讀，已讀回應又都沒有 Link，A 回報「未執行」並說明遍歷受阻原因。此時 Checkpoint B 仍有足夠證據判定遍歷不完整，應回報 FAIL 與未讀原因。

**局部受阻。** RF-01-002 若缺少 `@odata.type`，Step 3 A 已確認欄位缺少，判 FAIL；Step 3 B 沒有可供格式比對的字串，回報 `Not executed` 與缺值原因。Step 4、5 仍可從同一個 JSON 物件讀取其他屬性，繼續執行。

**多筆觀察。** 對多個對象執行相同檢查時，使用同一個 Checkpoint 識別值逐筆回報判定，每筆 `actual` 帶足以辨認受測對象的資訊，例如 RF-01-012 檢查的資源 URI。只有執行中發現的對象需要獨立報告列且可個別續跑時，才先登記動態 Checkpoint，再記結果。現有 RF-01 的 13 個案例皆可使用固定 Checkpoint。

**HTTP 觀察的 actual。** RF-01-012 的 Checkpoint A 每個含 Link 的回應回報一筆，`actual` 帶 `uri`、`evidence_id` 與 `issues`。例如同一跳第二筆 Link 有問題，在該筆 issue 填 `header_index: 2`，即可用 evidence 編號與從 1 起算的標頭序號查回原值。Checkpoint B 的整體觀察則列已讀資源數、未讀項目與原因，以及排除的項目。兩者都只需回報判定所需的資料。

RF-01-002 Step 1 若同來源 302 後取得 200，操作的 `actual` 只填 `{"final_uri": response.uri, "status": response.status}`，`http_status` 的 `actual` 只填數字 `200`。若未取得最終回應，只回報受阻原因。每一跳的 HTTP evidence 由第 5 節說明。

**記錄選填值。** RF-01-002 Step 5 以 `"RedfishVersion" in body` 判斷欄位是否存在。讀取結果用 `operation_result()` 回報，觀察值用 `record()` 回報。

| 作者取得的資料 | 作者的回報 |
|---|---|
| JSON 物件含有欄位 | 回報 `actual={"present": True}`，再以 `report.record(value)` 記下原值。明確的 JSON `null`、`false`、`0` 與空字串都是已取得的值。 |
| 已讀到 JSON 物件，確認欄位缺少 | 回報 `actual={"present": False}`，再呼叫 `report.record("Not present")`。 |
| 前置受阻，例如 Step 2 無法解析 JSON | 在受阻處回報原因，以 `report.finish(observations, blocked=reason)` 結束；流程到此為止，沒有可供 Step 5 記錄的值。 |

## 5. BMCAgent 自動處理

以下是新版平台契約，實作進度見第 6 節。

**Plan 編輯器的修改時間。** 在現行 Plan 編輯器儲存已變更的 Python 來源時，平台更新 `modified_at`，並檢查 `created_at` 與原始值一致。

**連線生命週期。** BMCAgent 在建立或重建連線時解析路徑引用，從 Task Connection 取用設定與帳密。指定的 port 缺值時，平台回報該路徑的受阻原因。一般 Console 路徑由平台 SSH 登入 Console Server，執行 `telnet 0 <Console Port>` 並辨認畫面；已有 DUT shell 時直接使用，看到登入提示才登入。若步驟要驗證登入行為，平台將該次嘗試留給步驟控制。Case 結束或發生例外時，平台釋放其建立的連線。

**HTTP 請求與通訊事實。** 平台工具依該次呼叫處理認證、重新導向及 timeout。匿名請求省略路徑帳密、既有 token 和登入 cookie，後續一般請求仍使用路徑帳密。預設取第一次回應；指定跟隨重新導向時，平台記錄各跳 URI 與狀態。平台記錄實際 timeout，並將收到的 4xx／5xx 狀態與內容交回 Case。未收到回應時，平台保留失敗階段、路段、原因及可確認的送出狀態（未送出／已送出／不明），HTTP 狀態留白。

RF-01-012 使用的 Redfish 遍歷工具管理 HTTP Session、路徑帳密及後續 GET。每收到一跳回應，平台先將 HTTP evidence 保存於當前 Action 並給予 `evidence_id`，同名 Link 標頭保留原始順序。平台將該編號與本跳標頭交給 Case 檢查，檢查結束後才依跟隨條件處理下一跳。各 Checkpoint 可引用同一份 evidence。RF-01-002 的每跳 URI、狀態、標頭與本文均保存在平台的 HTTP 紀錄，Case 無須另建 `case_result["evidence"]`。

**保存進度與續跑。** 平台在首次執行及同一次 Resume 時確認全部必要連線。Resume 時重新讀取 Task Connection，複檢後依既有規則沿用已有最終判定的結果與觀察，識別尚待執行的項目。新一輪測試重新驗證。作者只需提供測試特有的恢復動作，例如查證 DUT 是否已完成重啟。

**證據與輸出。**

平台將事件綁定當次 Case 執行與宣告快照，核對 Checkpoint 識別值屬於當前步驟，並依步驟編號及識別值保存證據。平台工具自動記錄通訊時間、命令、路徑、請求與回應、例外及失敗原因，並遮蔽密碼等敏感資料。

**步驟邊界與中途停止。** 使用 `ReportedCase` 開始下一步或結束 Case 時，平台收束目前步驟、產生 Outcome，並在 test.log 與 HTML 依 Action、Outcome、各 Checkpoint 的宣告順序呈現。觀察在 Case 回報時即保存。即使遍歷中途停止，已回報的觀察仍可在該步驟查到。

**Skip 與前置受阻。** 平台依作者明確指出的適用範圍，把 Skip 原因配到受影響且尚未執行的項目。RF-01-012 提早結束時，平台為尚無回報的宣告項目保留「未執行」與受阻原因。

**最終狀態與相容輸出。** RF-01-012 使用的 `ReportedCase` 依已回報的事實彙整結果。明確回報程式錯誤時為 Error；有失敗判定時為 Fail；其餘情況若前置受阻、仍有未執行項目或無任何通過的驗證，為 Block。其餘可通過的結果中，有明確 C-PASS 才彙整為 C-PASS，否則為 Pass。全部 Checkpoint 通過並附 Case Note，最終仍是 Pass；同時有 C-PASS 與 FAIL，最終為 Fail。平台寫入最終紀錄，並產生 `case_result` 與 `_tc_status` 供既有呼叫端讀取。

**失敗摘要。** 未傳入自訂 `summary` 且有 Checkpoint 判 FAIL 時，平台產生預設的 Fail 摘要，依宣告順序列出失敗的 Checkpoint、當次顯示標籤與回報原因。同一個 Checkpoint 多筆 FAIL 計為一項；「未執行」的原因保留在該列。RF-01-002 的雙失敗摘要先列 Step 3 B，再列 Step 4 B，兩筆 Actual 留在各自的結果列。摘要同時寫入 `case_result["reason"]` 與 test log 的最終 Reason。

**備註保存與呈現。** 平台將 Case 層級的備註保存在當次 Task Case 執行結果（`task_testcases.result_json` 的 `note` 欄位）。平台也將 Case 備註寫入 test.log 的 `Final result`。使用 `ReportedCase` 時，若最終為 C-PASS 且未另給 Case Note，平台會彙集明確判為 C-PASS 的 Checkpoint Note，去除重複文字後作為 Case Note。HTML 省略 Case 層級備註；Checkpoint 自己的 Note 顯示在該列的 Result 欄，與判定及 Actual 一起閱讀。

### Case 共用的 test.log 與 HTML 報告格式（2026-11-26 定稿）

兩種輸出使用相同的英文定位標籤及步驟順序。讀者可以從報告複製整個標籤，例如 `Step 2 | Checkpoint B`，直接在 test.log 搜尋。作者在 `TEST_CASE` 撰寫操作與驗證條件，並在執行時回報結果。平台依下表產生顯示標籤。

| 定位標籤 | Description 來源 | 內容 |
|---|---|---|
| `Step n \| Action` | 步驟的 `step` 原文 | 開始執行操作。發送命令或 HTTP 請求時，平台將該次請求與回應證據放在此步。 |
| `Step n \| Outcome` | 留白 | 平台產生 Outcome 列，依操作結果呈現完成狀態與已回報的 Actual。`COMPLETED` 表示操作已完成；驗證的 PASS／FAIL 來自 Case 的 Checkpoint 判定。例如 JSON 解析完成時，Actual 為 `{"top_level_type": "dict"}`，Judgement 為 `COMPLETED`。 |
| `Step n \| Checkpoint A`、`Step n \| Checkpoint B` … | 該 Checkpoint 宣告的 `expected` 原文 | 每步從 A 起，依宣告順序固定分配字母。事件與證據仍以原有 Checkpoint 識別值配對。依第 4 節呈現判定與適用的 Expected、Actual、Reason、Note。 |
| `Step n \| Record` | 該筆觀察的記錄說明 | 呈現單純記錄的值，例如 RF-01-002 步驟 5 讀到的 RedfishVersion `1.18.0`。 |

**test.log。** 保留 Web UI Run Log、Platform connection、各步執行內容及最終結果的順序。步驟標題使用「定位標籤 | Description」，多行描述完整保留在標題下方，區塊內省略重複的 Description 欄位。Outcome 標題到 `Outcome` 為止，成功時列 Actual，再列 Judgement；操作失敗或前置受阻時列 Reason 與 Judgement，省略沒有取得的 Actual。以下為 RF-01-002 的完整 Outcome 區塊：

```text
Step 2 | Outcome
Actual: {"top_level_type": "dict"}
Judgement: COMPLETED
```

操作完成與驗證通過分別記錄。RF-01-002 步驟 2 依序顯示 Action、Outcome、Checkpoint A（可解析為 JSON）、Checkpoint B（最外層為物件）。平台按步驟保存操作與驗證的時間、請求、回應標頭與本文等證據。多筆觀察在易讀 log 顯示總數、各判定筆數及每種判定的第一筆，JSONL 保存完整逐筆事件。

**HTML。** 每個定位標籤獨占一列。由左至右對齊定位標籤、Description、Result 三欄，直接從第一個 Action 列開始，省略可見的欄名列。Checkpoint 列不縮排，定位標籤與描述分別和 Action、Outcome 列的同欄內容靠左對齊。Outcome 的第二欄留白，第三欄顯示操作狀態，以及適用的 Actual 或 Reason。Checkpoint 的第三欄顯示判定及比較資料。HTTP 證據可在對應 Action 列展開。同一個 Action 有多筆 HTTP 證據時，平台會將它們收進該列一個預設收合的 `Details`，展開後可逐筆查看請求與回應。[RF-01-012 定稿 test.log](../../report-previews/RF-01-012-replay-test.log) · [RF-01-012 定稿 HTML 報告](../../report-previews/RF-01-012-replay-report.html)

多筆觀察在同一列按判定分組，可展開逐筆閱讀，每筆顯示完整 Actual。已宣告而沒有資料的列保留，結果欄留白；已有 Skip 或受阻原因就顯示。保留 `0`、`false`、空字串等實際值。

**Record 的呈現。** RF-01-002 Step 5 已執行時，test log 與 HTML 依序呈現 Action、Outcome、Record。Outcome 以 `COMPLETED` 和 `present` 說明讀取結果；Record 同為 `COMPLETED`，顯示原值或 `"Not present"`。前置受阻時，Outcome 與 Record 均顯示 `Not executed` 和受阻原因，兩列皆省略 Actual。

本機工作區的 RF-01-002 定稿樣本供後續 Case 核對輸出。[完整 test.log](../../report-previews/RF-01-002-action-outcome-test.log) · [HTML 報告](../../report-previews/RF-01-002-action-outcome-report.html)

## 6. 可執行範例與實作界線

| 環境 | 作者目前可以依賴的行為 |
|---|---|
| 現行正式版 | 匯入器讀取字面值 `TEST_CASE` 並檢查 `execute(client, context=None, preset=None)`。RF-01-002 與 RF-01-012 均透過此入口使用 `ReportedCase` 與 `RedfishRoute`，現行寫法見下表。 |
| 本機 RF-01-002 prototype | 已用真實 Task Connection 驗證 `run(ctx)`、`ctx.step(n)`、`step.get(...)`、`step.check(key, passed, expected, actual)`、`step.record(value)`、JSONL、易讀 log 與三欄 HTML。該版路徑使用 `task.connection.host`，GET 工具內建 15 秒 timeout 與同來源重新導向處理。 |
| v1 作者介面 | 本指南採用具名 LAN port、每次請求的認證／重新導向／timeout 選項，以及明確的 Checkpoint 判定。示例方法名稱供新版實作對齊。 |

### RF-01-002 現行寫法對照

現行單檔 Case 從 `execute(client, context=None, preset=None)` 建立 `report = ReportedCase(context, TEST_CASE, CaseFailure)`。早期 prototype 從 `run(ctx)` 進入，使用 `ctx.step(n)`、`step.get(...)`、`step.check(key, passed, ...)` 與 `step.record(value)`。下表對照現行來源中的呼叫。[RF-01-002 現行可執行來源](../test_assets/redfish/rf_01_002_service_root_endpoint.py)

| 操作 | 現行 RF-01-002 的寫法 |
|---|---|
| 取得最終回應 | `report.begin_step(1)` 後以該步宣告的 route 建立 `RedfishRoute`。在 `route.traversal(...)` 中呼叫 `response = get(urljoin(route.host, ENDPOINT))`，從 `response.uri`、`response.status`、`response.text` 取得最終 URI、狀態碼與本文。 |
| 回報操作與驗證 | `report.operation_result(actual={"final_uri": response.uri, "status": response.status})` 回報 GET 結果。以 `report.checkpoint("http_status", "PASS", expected=200, actual=response.status)` 回報最終 200，其他最終狀態碼明確回報 FAIL 與原因。 |
| 留下純觀察值 | 現行 `test_method` 在 Step 5 宣告一個 Action 及一筆同一步號、`type="Record"` 的項目。`report.record(value)` 使用當前步驟唯一的 Record 宣告。第 2 節省略 `type` 的寫法屬於 v1 作者介面設計。 |
| 結束 Case | `report.finish(observations, blocked=reason)` 交付觀察與受阻原因，正常走完時 `reason` 為空字串。此 Case 省略自訂 `summary`；最終判定與預設摘要見第 5 節。 |

Step 3、4 的失敗原因與 Step 5 的 Record 可在同一份執行結果逐列核對。[雙失敗 test log](../../report-previews/rf-01-002-platform-summary/test.log) · [HTML 報告](../../report-previews/rf-01-002-platform-summary/report.html)

### RF-01-012 現行寫法對照

下表摘錄現行 Case 的呼叫。遍歷、解析與判定條件可在完整來源中逐步對照。[RF-01-012 可執行來源](../test_assets/redfish/rf_01_012_relative_uri_references.py)

| 作者要做的事 | RF-01-012 在 `execute(...)` 內的寫法 |
|---|---|
| 開始回報、標明步驟 | 先建立 `report = ReportedCase(context, TEST_CASE, CaseFailure)`，進入遍歷前呼叫 `report.begin_step(2)`。 |
| 使用宣告的路徑、逐跳檢查 | 以 `RedfishRoute(context, TEST_CASE["command_routes"][route_name])` 取得路徑。在 `with route.traversal(redirect_statuses=redirect_statuses, max_redirects=5, allow_target=allow_target, inspect_hop=inspect_hop) as get:` 內呼叫 `get(requested)`。 |
| 回報 Step 2 觀察 | 在 `inspect_hop(hop)` 內讀取 `hop.headers`，以 `report.checkpoint("link_header_syntax", ...)` 回報本跳的判定與 actual。遍歷的未讀原因及整體結果用 `"traversal_complete"` 回報。Step 1、2、3 的 Checkpoint 均以宣告的具名鍵回報。 |
| 結束並提供背景 | 正常走完時呼叫 `report.finish(observations, summary=summary)`。受阻可傳 `blocked=reason`，若當前操作也失敗，再傳 `operation_failure=reason`。程式錯誤用 `error=...`，整個 Case 的備註可用 `note=...`。這些呼叫只須給觀察與原因，最終狀態依第 5 節彙整。 |

使用已保存的實測回應重跑時，Step 2 的 Link 語法觀察有 997 筆 PASS、94 筆 FAIL，遍歷結果為 PASS，Case 最終為 Fail。[RF-01-012 實測重播 test.log](../../report-previews/rf-01-012-platform-verdict/test.log)

以下為早期 prototype 的執行產物；後續 Case 的輸出格式以第 5 節定稿樣本為準。[RF-01-002 早期 prototype 來源](../../bmca-runtime/prototypes/case-authoring-20261123/RF-01-002.py)、[易讀 log](../../bmca-runtime/prototypes/case-authoring-20261123/runs/20261123T071605978194Z/test.log) 與[三欄 HTML](../../bmca-runtime/prototypes/case-authoring-20261123/runs/20261123T071605978194Z/report.html) 可逐列對照；上述 prototype 位於 BMCAgent repository 外。

第 5 節的最終狀態規則適用於採用 `ReportedCase` 的 Case。其他執行路徑的混合判定，以及 v1 的完整暫停、續跑與動態登記介面，仍屬後續工作。
