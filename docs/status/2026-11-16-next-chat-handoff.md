# 下一個對話交接：正式報告現況與待決策事項

更新日期：2026-11-16。本文件為最新入口；若與早期提案或 Prototype 記錄衝突，以本文件及使用者後續指示為準。

## 最重要的界線

**Prototype 已捨棄。報告摘要與分組方案尚未批准正式導入。**

Checkpoint 彙整、原因分組、巢狀 reason、陣列原因集合、Case 層級 Result Summary、取消 Result 字數限制，都只曾試作或討論。不要因交接、先前試作授權或 commit/push 授權，自動將這些功能導入正式版。沒有已批准但尚未完成的報告實作。

「捨棄」指不再沿用或發布這版試作；本次沒有刪除本機 Prototype 檔案。不要將其當作正式依賴，也不要提交其資料庫副本或測試 Log。

## 已完成

| 項目 | 狀態／證據 |
|---|---|
| Nessus 風格報告 | 已正式導入、重啟並驗證；提交 d64386b。緊湊留白、圓角 Case 列、Judgement 不加框、FAIL/Note/C-PASS 顏色與粗體。 |
| Case 收折 | 正式版維持由 Case Name + Judgement 收起整個 Case。 |
| RF-01-011 與 Note | 使用者已手動同步 RF-01-011，Note 修正已生效，不重複同步。 |
| RF-01-012 | 「檢查測試錯誤」對話已 commit/push 0e7b2b3，回報 19 組離線測試通過；不要覆蓋其修正或重複同步使用者已更新的 Repository/Plan。 |
| 共用流程靜態檢查 | 本對話未發現依特定 Case 編號、名稱、Link/Traversal 錯誤內容改寫結果的單一 Case 特判。未發現正式程式引用 Prototype 分組模組。 |
| 提交協調 | 已等另一對話完成後推送 71b9a05，記錄 Prototype 捨棄與檢查結論。d64386b 已包含在 main 歷史中，沒有待重推的該提交。 |

## 尚未完成／待使用者決策

1. **長報告問題尚未解決**：大量重複 Checkpoint 仍會產生很長的 HTML/PDF。摘要、分組或其他縮短方式需重新確認；先不要實作。
2. **Result Summary 尚未恢復**：Case 層級結論只在 Prototype 展示，正式版未新增。
3. **Result 字數限制仍存在**：正式 report_case.py 超過 1200 字元時保留約 1100 字元並加提示。取消限制不是正式版已批准需求。
4. **通用性檢查可再擴充，但尚未授權實作**：執行器預設建立 Redfish 連線是平台技術依賴；PDF 模組的 _determine_test_type 依路徑推測類型，本次只找到定義，未找到呼叫。可由使用者決定是否進一步檢討。

目前靜態檢查涵蓋 Case 載入/執行、結果保存、判定契約、Log、HTML/PDF 與前端結果呈現；不是所有 Case 腳本的完整稽核，也不保證執行中程序與磁碟完全一致。Case 內專屬驗證邏輯屬測試職責，與平台共用流程特判分開判斷。

## 試作歷史（僅供理解，不代表核准）

曾比較同一 Checkpoint/Expected 彙整、完整原文分組、巢狀 reason 精確比對，以及陣列索引轉 [*] 後以原因集合分組。最終試作以通用規則將 RF-01-012 的 94 筆 FAIL 紀錄合併為一組，計得 206 次 reason 出現；取消 Result 截斷後，完整回應清單仍造成長篇幅。之後使用者明確捨棄 Prototype，轉為檢查正式版通用性。

當時資料來自 Test-FWA6084BMC-004：RF-01-002 PASS（11/16 10:32:10 台灣時間）、008 C-PASS（10:32:17）、012 FAIL（11:58:29）。012 保存結論為 Relative URI violations: 0; Link syntax issues: 206; traversal issues: 0。這是當時保存資料，不代表後續最新結果；需要資料時重新唯讀查詢，勿沿用舊 UUID 或備份。

本機試作位置：bmca-runtime/prototypes/report-summary-20261116；資料副本位於 bmca-runtime/prototype-data。localhost:5139 是試作入口，不是正式服務，下一對話不要假定它仍在執行。

## 工作區與安全操作

- 工作區：D:/Codex/bmc_auto_test；正式程式：BMCAgent；正式服務：http://127.0.0.1:5000。
- 正式資料庫：BMCAgent/web_ui/workspace/testcase_meta.db。檢視使用唯讀連線；變動測試必須使用隔離副本。
- 乾淨發布 checkout：bmca-runtime/publish-handoff-20261111；分支 main；唯一正確 origin：https://github.com/baga0607-cpu/bmcauto.git。
- BMCAgent 工作目錄有大量其他既存修改與未追蹤檔案，不可整批 stage、reset、覆蓋或推送。提交前核對最新 HEAD 與其他對話進度，只納入本次授權內容。
- Python：BMCAgent/.venv/Scripts/python.exe。
- Git：C:/Users/david.huang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe。PATH 可能沒有 git/rg。
- 遵守 BMCAgent/AGENTS.md 與 BMCAgent/.agents/skills/bmc_agent_v4_test_management/SKILL.md。
- Repository、Plan、來源腳本與 test_assets 是不同副本；修改來源不等於同步，勿自行覆蓋使用者已手動更新的測項。
- 若再使用 Nessus 參考檔，只能參考 UI/CSS/結構；使用者要求不要閱讀其報告內容文字。

## 下一對話如何開始

先閱讀本文件，確認使用者要延續「正式版通用性檢討」或重新討論長報告方案。若沒有新指示，先報告現況，不自行恢復 Prototype、變更 case.py、同步測項、部署或重啟。

相關紀錄：
- [正式報告部署](2026-11-16-nessus-report.md)
- [Prototype 結案與共用流程檢查](2026-11-16-report-prototype-retired.md)
- [較早交接與歷史提案](2026-11-13-next-chat-handoff.md)
