# 新對話交接：RF-01 與報告呈現

更新：2026-11-13。此文件為下一個對話的入口；先閱讀，再依使用者的新指示執行。建立本文件不代表批准尚待確認的設計或部署。

## 工作區與發布方式

- 工作區：D:/Codex/bmc_auto_test。
- 本機正式服務程式：BMCAgent；網址 http://127.0.0.1:5000。正式 DB：BMCAgent/web_ui/workspace/testcase_meta.db；執行腳本：BMCAgent/main_program。
- 本機 BMCAgent checkout 有其他工作留下的修改，禁止整批 stage、reset 或覆蓋。
- 乾淨發布 checkout：bmca-runtime/publish-handoff-20261111；分支 main；唯一正確 remote：https://github.com/baga0607-cpu/bmcauto.git。不要推送已退休的 Ulrox0880 remote。
- Git 執行檔：C:/Users/david.huang/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe。Shell PATH 未必可找到 git/rg。
- Python：BMCAgent/.venv/Scripts/python.exe。
- case 原始來源：testcases/redfish；Git 追蹤鏡像：BMCAgent/test_assets/redfish 及發布 checkout 的 test_assets/redfish。Repository 與 Plan 是獨立已安裝副本，修改鏡像不等於同步它們。
- 遵守 BMCAgent/AGENTS.md 與 .agents/skills/bmc_agent_v4_test_management/SKILL.md。測試使用隔離的 BMC_WEB_UI_WORKSPACE_DIR、BMC_MAIN_PROGRAM_DIR、TEMP/TMP；不可在正式 DB 跑變動測試。

## 已完成並推送

| Commit | 內容 | 生效狀態 |
|---|---|---|
| dbe4576 | 其餘 RF-01 Checkpoint 文案易讀化，保留判定條件、Result | 當時已同步 Repository/Plan，保留設定與歷史 |
| 1d67ddf | Spec Ref. 引用之間雙換行改單換行 | 已重啟服務 |
| d26c30d | 報告四項緊湊版面調整 | 已重啟服務 |
| c61cd6a | 整合另一對話的 Note 規則與 RF-01-011 schema 修正 | 已推送，部署與已安裝測項同步仍待處理 |

四項版面調整：Checkpoint Description 僅在呈現時移除空白列，不改原始 case.py/歷史定義/Result；欄寬 Step/Type/Description/Result/Judgement 為 6/13/39/30/12%；HTML cell 上下 padding 3px（原 4px），PDF/列印維持 2pt；收緊 Test Data/Test Information 標題與內容間距。共用 report_case.py 支援 HTML、預覽、PDF。

## 不可恢復的舊規則

- 報告完全不補列 Case-level note (no recorded step association)。Step/Checkpoint 自己的 Note 保留。原始 case_result.note、Log、附件與歷史結果不改。
- 另一對話先前的「Case Note 去重後保留 fallback」已被使用者後續決策取代，不可恢復。舊文件後段仍有歷史描述，以檔頭 superseding decision 及本文件為準。
- C-PASS（非 CP）只用於 Checkpoint 與 Case 最終判定，必須附 Note；Skip 附原因；Record 為 COMPLETED，記錄無標準的觀測結果，不作驗證中繼儲存。
- 表格維持 Step | Type | Description | Result | Judgement；Type 是 Command/Action/Checkpoint/Record，不使用 Step 作 Type。Command/Action 顯示步驟數，Checkpoint/Record 對應列的步驟欄留白。
- Case Name 是整個 Case 唯一既有收折入口。Test Data 包含 Description、Spec Ref.、Log、Test Steps & Results；Test Information 包含 Task Name、Tester、Execution Time、FW Package、Configuration。無獨立 Result Summary/Note 欄。
- Test Log section 的 [1]、[2] 已移除，不要把 HTTP 證據識別或步驟關聯一併移除。

## 跨對話整合內容與限制

RF-01-011：資源只允許同來源；schema 可由同來源或 allowlist 的 redfish.dmtf.org /schemas/ JSON 取得。公開 HTTP canonical identifier 轉 HTTPS 取得，逐跳檢查 redirect，獨立無 BMC 憑證 session 並驗證 TLS。依 BMC @odata.type 選精確 schema 版本；單次執行記憶體快取，沒有持久快取；未版本化 schema 首次 GET 帶 Cache-Control:no-cache。增加 schema URL/cache-hit/failure-stage 證據。

已同步外部來源與兩個 test_assets 鏡像。既有 Repository/Plan RF-01-011 尚未同步，也未實機測試。沒有在 c61cd6a 整合時重啟服務或修改正式 DB。RF-01-013 本身沒有在這次整合中修改，其重複 Note 問題由共用報告修正處理。

最後一次本對話實際執行服務重啟是在 d26c30d：備份 bmca-runtime/backups/restart-20261113-135659-288，當時無 active tasks，21 個 table fingerprints 完全不變，integrity ok、foreign-key errors 0。後續是否有別的對話/使用者重啟必須重新查證，不可假定執行中服務已載入 c61cd6a。

## 下一步：待使用者確認的 Checkpoint 摘要設計

使用者困擾：RF-01-003/009/010/011/012 因相同 Checkpoint 對多個成員或 URI 重複展開，使報告很長。使用者只批准了留白調整，尚未批准以下摘要方案。最後已用 RF-01-012 示範給使用者，示範中的 120 references/118 PASS/2 FAIL 等數字完全虛構，不能當作測試結果。

提案：每項 Checkpoint 一列摘要；異常明細直接顯示；完整明細可展開。

- 只彙整同一 Step 下同一 Checkpoint 的重複結果；不同接受條件不合併，完整規則只顯示一次。
- Result 顯示實際檢查筆數與各狀態計數，不把檢查筆數誤稱不重複 URI 數。
- FAIL/C-PASS/Skip 預設直接顯示來源、欄位、Actual、Reason/Note；PASS 明細預設收起。缺失來源欄位顯示未記錄，不能推測。
- View all details (N) 在所屬 Checkpoint 下方展開跨欄明細，保留已記錄的 Expected/Actual/Reason/Note。單筆短結果不用額外展開。
- 無適用項目、提前中斷與覆蓋不完整不能自動當 PASS；Case 最終判定維持已存結果，不由呈現重新判定。
- 預覽/HTML 可展開；PDF 主文摘要與異常、完整資料放附錄。此 PDF 附錄方案同樣尚未批准。
- 不新增 Record 中繼步驟，不改原始結果/Log；不恢復舊 S/C/R ID 設計。

RF-01-012 示範保留三個主要步驟、五項 Checkpoint：有效 origin；traversal 無讀取/連結/分頁錯誤；相對 URI 必須是 /path 或含有效 authority 的 //authority/path（也接受 absolute URI）；至少一個適用 relative reference；discovered scope 全部評估。僅 URI 規則的重複執行彙整，不刪接受條件。

## 驗證與可重用資料

- d26c30d：17 項 Python 報告測試通過；report_methods.test.cjs 瀏覽器檢查通過（無 overflow、附件、收折與列印狀態恢復）。另直接驗證 Description 空白列移除而 Result/input 不變。資料在 bmca-runtime/verification/report-spacing-20261113。
- c61cd6a：發布 checkout 跑 19 項 report tests 通過（test_report_note_association、test_report_case、test_report_method_table、test_conditional_pass.ConditionalCaseTest.test_policy_and_legacy_display），包含隔離 DB HTML/PDF 匯出；test_rf011_schema_retrieval 20 項離線測試通過。無 live DUT/browser 驗證。
- RF011 測試已從 runtime 腳本保存為 web_ui/tests/test_rf011_schema_retrieval.py，使用 test_assets 來源；將不具可攜性的檔案 birth-time 比較改為保留原始 created_at 日期比較。
- 整合驗證目錄 bmca-runtime/verification/cross-chat-20261113；PYTHONPATH 加發布 checkout 的 web_ui、web_ui/tests、main_program，TEMP/TMP 與 workspace/main 指向隔離目錄。

## 後續工作操作原則

先確認使用者下一項指示：批准摘要實作、部署 Note 修正、同步 RF011，或其他工作；不要因本交接自行啟動測試或同步。若要求同步 Repository/Plan，先查 active tasks、備份並比對獨立來源與設定，保留既有結果/Log，只更新授權來源欄位與必要重測標記。若要求部署，使用既有 bmca-runtime/launch.ps1 -Action Restart -Mode Local -NoBrowser，檢查備份、父子程序與 DB 一致性。

使用者慣例：完成實作後更新交接文件並 commit & push。未批准的提案先展示確認，不直接改程式。

## 相關文件

- [跨對話整合](2026-11-13-cross-chat-integration.md)
- [報告 Note 最終決策](2026-11-13-report-note-association.md)
- [四項留白調整](2026-11-13-report-spacing.md)
- [Spec Ref. 間距](2026-11-13-spec-ref-spacing.md)
- [RF011 實作與限制](../redfish-compliance/rf-01-011-implementation.md)
- [前次整合交接](2026-11-11-consolidated-handoff.md)
