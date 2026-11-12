# RF-01 全系列格式轉換與 C-PASS — 2026-11-12

本次規則優先於前面文件中 CP、S/C/R ID、Step Type、Criteria 綁定及帶編號 section 的歷史設計。

## 完成內容

- RF-01-003～007、009～013 共 10 支改為 Command／Action／Checkpoint／Record；001／002／008 一併查核與狀態名稱更新。13 支來源均可獨立匯入，保留 created_at，更新 modified_at。
- 報告統一 Step | Type | Description | Result | Judgement。只有 Command／Action 顯示主 Step 號；Checkpoint／Record 透過 step_number 與 method_index 對應。沒有 S/C/R ID，也沒有名為 Step 的 Type。
- C-PASS 取代 CP，僅 Checkpoint 與 Case 最終判定使用，必須有 Note。Record 正常完成為 COMPLETED；未執行／不適用使用 Skip 與 Reason。必要 FAIL／ERROR 不會轉成 C-PASS。
- RF-01-008 保留既有可接受缺端點條件。RF-01-013 已辨識但非建議 dialect、沒有驗證到建議 /Schemas/ entry 時使用 C-PASS＋Note；必要檔案失敗仍 FAIL，不支援 archive 且無其他失敗仍 Block。沒有適用 fragment／relative URI 時，011／012 保持既有 FAIL 規則。
- Record 僅紀錄資訊：002／006 的 RedfishVersion、009 的觀測資源與 identity 數量；不將回應儲存拆成額外 Record。
- 多 URI／檔案每筆保留 source、URI／member 與結果；報告依擷取時的 method_index 對應全部觀測，修正只對上首筆後將其餘排到表尾的問題。完整 HTTP 內容仍在 Log。
- 新 Log 的 section 標題移除 [1]、[2] 等前綴。保留標題、Step 關聯、HTTP evidence 號碼及 URI；歷史 Log 檔不重寫。
- Execution、Plan matrix、人工判定、報告預覽、正式 HTML／PDF 均使用 C-PASS。歷史 CP 以相容別名讀取並顯示 C-PASS；DB 保留舊 CP 值，不重判歷史結果。
- 維持已確認的報告階層：Case Name 唯一收折控制；Test Data 包含 Description／Spec Ref.／Log／Test Steps & Results；Test Information 包含 Task Name／Tester／Execution Time／FW Package／Configuration。沒有 Result Summary 或獨立 Note 欄。

## RF-01 最終逐項查核

| 測項 | 主步驟數 | 宣告表格列數 | 格式／對應查核 |
| --- | ---: | ---: | --- |
| RF-01-001 | 3 | 9 | 通過 |
| RF-01-002 | 5 | 13 | 通過 |
| RF-01-003 | 4 | 13 | 通過 |
| RF-01-004 | 3 | 9 | 通過 |
| RF-01-005 | 5 | 12 | 通過 |
| RF-01-006 | 3 | 10 | 通過 |
| RF-01-007 | 3 | 10 | 通過 |
| RF-01-008 | 3 | 9 | 通過 |
| RF-01-009 | 3 | 11 | 通過 |
| RF-01-010 | 3 | 7 | 通過 |
| RF-01-011 | 3 | 8 | 通過 |
| RF-01-012 | 3 | 8 | 通過 |
| RF-01-013 | 5 | 14 | 通過 |

查核包括 literal metadata、Type 白名單、連續主 Step、Checkpoint／Record 對應、舊 ID／Criteria 移除、Skip Reason、C-PASS Note、Record 不做 PASS／FAIL 判斷、來源 created_at 保留及三份檔案 byte compare。執行迴圈可產生多於宣告列數的實際結果，每筆保留。

## 驗證

- 發布 checkout：80 項 Python 測試全部通過；本機 checkout：87 項全部通過。
- 覆蓋 001／002／008 既有離線案例，加上其餘 10 支的成功、無設定、HTTP／解析失敗、多 URI、fragment 缺目標、多 schema 檔、替代 dialect、必要失敗優先、archive Block、舊 CP 相容與重複結果表格關聯。
- 兩版 Execution 報告預覽瀏覽器測試通過；檢查按鈕、五欄、C-PASS／Skip、Note、Refresh／失敗重試、Escape／焦點、Task 切換、淺深主題與唯讀請求。正式 HTML 緊湊表格、離線附件、列印展開／還原通過。workbench.js 語法與 Plan matrix 相容測試通過。
- PDF 已渲染檢視 C-PASS 與 Note／Skip 表格；沒有裁切或重疊。未執行實體 DUT，離線通過不代表硬體測試 PASS。
- 正式資料副本升級兩次：21 張表所有資料指紋一致、integrity_check=ok、foreign_key_check=0。
- 本機證據：bmca-runtime/verification/rf01-conversion-20261112/，含 series-audit.json、published-tests-final.txt、local-tests-final.txt、migration-copy-result.json、HTML／PDF／截圖。

## 正式服務與資料

2026-11-12 16:48（Asia/Taipei）透過桌面 launch.ps1 -Action Restart -Mode Local -NoBrowser 重啟，launcher PID 14808，http://127.0.0.1:5000 可用。重啟前 active Tasks=0；備份 bmca-runtime/backups/restart-20261112-164809-472。重啟後 changed_tables=[]、21 張表保留、integrity=ok、foreign_key_errors=0、conditional_pass_schema=true。

**來源完成不代表既有 Plan 副本已更新。** 本次不覆寫 Repository／Plan 的獨立 Python／設定，也不重判既有 FAIL、不修改舊 Log。要用完整新流程，需匯入新來源並依既有 UI 更新欲執行的 Plan 測項，再重新執行。

## 發布與接手

發布至 baga0607-cpu/bmcauto main，使用 bmca-runtime/publish-handoff-20261111；沒有向退役 origin 推送。本機 BMCAgent 其他未提交功能保持原狀。來源位置為外層 testcases/redfish，兩份 Git checkout 的 test_assets/redfish 均相同。

遠端 runner 在 app.py，本機使用 case_worker.py 子程序；兩者皆更新 C-PASS 映射。本機父／子程序的精確差異保存於 [local-worker patch](../patches/2026-11-12-local-worker-c-pass.patch)，不可直接對不含 case_worker.py 的舊遠端結構套用。既有本機 UI 整合仍延續前幾次 handoff 的差異，不整批覆蓋 app.py、workbench.js 或 plan_state.py。
