# case.py 作者指南決策紀錄 · 2026-11-18

供團隊逐項確認作者介面。完整的 LAN／KCS 範例見[作者指南](../case-py-author-guide-draft.md)。以下「已確認」指設計共識；平台實作進度須另外核對。

## 新對話從第 1 項開始

請先討論「case.py 單檔骨架與入口」。目標是讓夥伴拿到一份可照著寫的範本：列出基本資料、各宣告的必填與選填欄位，以及平台如何呼叫入口。請對照草稿的 `run(ctx)` 與現行載入器的 `execute(client, context=..., preset=...)`，提出一個最小英文範例供確認。這一階段先討論設計。

使用者想重新設計 Log 寫法，待第 1 項確認後再進入第 2 項。目前 RF-01 的 Log 通常在每個動作後記下該步驟的 Checkpoint，最後寫入 `Final result`；這是現況參考，新版編排仍待討論。Execution 與 Connection 的 UI 設計暫緩正式導入，兩個原型只保留在本機。

## 已確認的作者規則

| 主題 | 作者可以依循的規則 |
|---|---|
| 語言與範圍 | 指南可用中文。整份 `case.py` 必須是英文，包括識別名稱、註解、docstring、字串、Log 和例外訊息。新格式可直接採用；既有調整範圍為 RF-01 的 13 個 Case。 |
| 環境與路徑 | `environments` 宣告從哪台機器取得哪個 shell；`command_routes` 宣告在哪個環境、經哪個介面送指令。Case 選擇驗證路徑。Console 路徑先 SSH 登入 Console Server，再從該機執行 `telnet 0 <Console Port>`。看到登入提示才登入；已在 DUT shell 就直接使用。 |
| 設定與生命週期 | 各 Case 獨立，先用 Task Connection 固定值，Case 依目的決定是否查詢動態值並重試。臨時值只用於當次 Case；只有測試者可更新 Task Connection。平台建立連線並回報失敗階段、路段、原因代碼與說明，最後負責關閉連線。 |
| Checkpoint 與續跑 | 固定項目事先宣告識別值、名稱、預期結果及使用的路徑。動態項目發現後先登記，再記結果。首次執行和同一次續跑都先確認全部必要連線；復檢通過後，已有最終判定的項目沿用原結果，尚未執行的項目才執行。新一輪執行重新驗證。 |
| 判定 | 已實測才判 PASS／FAIL；條件式通過 C-PASS 附 Note，不適用而 Skip 附原因。必要前置受阻而無法執行時，保留「未執行」及原因。LAN／KCS 範例中兩者皆通過才 PASS；有必要驗證 FAIL 時整體 FAIL；其餘必要驗證受阻時整體 Block。 |
| 暫停或繼續 | 所有必要前置連線確認後，只要仍有一條受阻，平台就依 Task 選項暫停或繼續。暫停後可由測試者排除問題並更新 Connection；選繼續時執行可完成的項目及後續 Case。 |
| Log 與報告 | 平台自動記錄透過平台執行的指令、位置、路徑、回應及失敗原因，遮蔽密碼並補上程式例外資訊。Case 提供有測試意義的觀察與判定。報告的 Judgement 與 Result 共用一欄；有 Judgement 時分行，沒有時直接顯示 Result。 |

## 分享給作者前，依序確認

1. **單檔骨架與入口**。列出 Case 基本資料、必填及選填欄位、各宣告與入口函式。草稿用 `run(ctx)`；正式載入器目前呼叫 `execute(client, context=..., preset=...)`。需定下新作者要交付的唯一範本。
2. **Log 與結果怎麼寫**。用同一筆測試對照 Command、Action、Record、Checkpoint 四種類型，定下作者需呼叫的方法、必填參數、平台自動補的欄位，以及例外時保留的證據。例如平台已記下 `mc info` 和回應，作者寫 Checkpoint 判定即可；從 Console 查出的新 DUT IP 則可用 Record 說明。
3. **平台工具與設定鍵名**。定稿 Redfish、SSH、Console、IPMI 的最小呼叫範例、`task.*` 欄位路徑、回傳與錯誤欄位、動態值傳入方式。納入 BMC／DUT 重啟時，Case 如何指定等待就緒及重連。
4. **Case 最終判定表**。補齊全部 Skip、C-PASS 與其他結果並存，以及程式例外時整個 Case 的結果。表內須保留已約定的 Block／FAIL 規則。
5. **動態 Checkpoint 與續跑細節**。用一個動態列舉例子定下登記呼叫與穩定識別值，並示範指令已送出但結果不明時，作者如何查證，避免重送重啟指令。

分享時應註明哪些呼叫僅屬設計，哪些已可在正式版使用。正式版的優先核對項為取消無條件 Redfish 前置依賴，以及能否保留「未執行」、Skip、Block 與 FAIL 的差別。

## UI 設計備忘 · 暫緩正式導入

原型存於本機工作區的 `bmca-runtime/prototypes/connection-20261117/`；以下檔名供回到同一工作區時查閱。

| Prototype | 已試作內容 | 狀態 |
|---|---|---|
| Connection（`current-layout.html`） | 沿用 Task Info 右側面板。BMC 帳密在前，預設一列；每列一組 BMC IP 與 IPMI channel，可新增或刪除，port 編號隨 channel 連動。規則為有 BMC IP 就必填 channel。Console Server 帳密在前，Server IP、SSH Port、Console Port 各一列；DUT OS 放帳密、DUT IP、SSH Port、Shell Prompt。SSH Port 預設 22，其餘以提示文字呈現；可雙擊空欄套用已定義的常用提示。 | 保留原型與欄位規則，正式頁面導入時程及 UI 驗收另議。 |
| Execution（`execution-disconnect.html`） | 已試作持續測試選項、暫停與繼續兩種情境、固定／動態失敗原因、由 Connection 面板更新設定、Resume 與後續 Case 結果。 | 頁面設計暫緩，後續另行檢討版面。連線判斷、續跑及結果規則仍保留於作者指南。 |
