2026-11-12 deployment update: Formal service restarted at 15:40; CP schema enabled. Desktop restart and quoted-table migration fix: [handoff](2026-11-12-desktop-restart-cp.md). The pending deployment notes below describe the earlier state.

# RF-01-008：CP、Skip、Record 與報告 Note — 2026-11-12

## 已確認並實作的規則

- 表格維持 Step | Type | Description | Result | Judgement。只有 Command / Action 顯示主步驟號碼。
- Checkpoint 可為 PASS / FAIL / CP / Skip。CP（Conditional Pass）必須附非空 Note；Command、Action、Record 不接受 CP。
- Command / Action 完成為 COMPLETED，執行失敗為 FAILED / ERROR；Record 成功為 COMPLETED，不賦予 PASS / FAIL。
- 未執行動作、未評估 Checkpoint、未取得 Record 統一顯示 Skip，必須附 Reason。整個未執行 Case 仍為 NR（資料庫 TBD）。
- Note 是條件接受的理由；一般資訊用 Actual，失敗與跳過原因用 Reason。新 numbered method API 拒絕非 CP 的 Note。
- Case CP 必須附 Note，不能覆蓋已記錄的 FAIL / FAILED / ERROR 或 execution errors。RF-01-008 的接受分支明確產生 Checkpoint CP 與 Case CP。
- 人工 Case CP 的 Reason 欄作為必要 Note。保留原執行 Log；報告表格另以「Manual case judgement」列明人工判定，與原執行檢查分開。

## RF-01-008

1. Command：GET /redfish/v1/openapi.yaml，保留同源重新導向、迴圈與五次上限保護。
   - Checkpoint：HTTP 200 進入內容驗證。
   - HTTP 404 必須精確符合缺少該 URI 的 JSON message。
   - HTTP 400 必須在同一 ExtendedInfo entry 同時符合 Base.1.16.InvalidURI 與精確 message。
   - 上述接受缺少端點時：Command COMPLETED、Checkpoint CP + Note、其餘七列 Skip + Reason，Case CP。
2. Action：解析單一 YAML；兩個 Checkpoint 分別確認可解析與頂層 object。
3. Action：讀取 openapi / info / paths；三個 Checkpoint 分別檢查存在與型別。
4. 不符合接受條件的 400/404、其他 HTTP 錯誤、錯誤 YAML / property 仍失敗；不以 CP 放寬已有文件的驗證。

僅轉換 RF-01-008 原始測項及 test_assets 鏡像；未批次修改其他 case.py、已匯入 Repository 版本或獨立 Plan 副本。RF-01-001/002 的舊 RECORDED / NOT_* 由共用 Log 正規化為 COMPLETED / Skip，新輸出採新規則。

## 共用整合

- result_policy.py 集中狀態別名與必要 Note / Reason 驗證；case_log.py 使用同一規則。
- 執行器傳遞 CP，TaskTestCase 的 SQLite CHECK 新增 CP；舊 Block schema 與更早 schema 均可冪等遷移。
- Execution badge、人工判定、Task count、Plan Matrix 與正式報告選取均認得 CP。CP 為完成結果，單獨計數；最新合格結果與同時間後欄優先規則不變。
- HTML 正式報告與單項預覽共用表格；PDF 同步 CP、Skip、COMPLETED 與 Note。
- 移除獨立 Note 欄位。Note 放入對應 Checkpoint 的 Result；不額外建立 Record。
- 歷史 step 的 nested checks 仍可讀。未具步驟關聯的舊 Case Note 以表格內「Case-level note (no recorded step association)」保留，Type / Judgement 為 —；不猜測關聯，也不把舊 PASS 改成 CP。
- 舊 log.check / log.step / finish 的 Note 相容入口保留，避免破壞獨立舊 Plan 程式。舊磁碟 Log 不改寫。

## 驗證

環境：D:/Codex/bmc_auto_test/bmca-runtime/verification/cp-rf008-20261112；隔離 workspace / main / TEMP，全部以模擬回應執行，未連實體 DUT。

- 本機 Python：57 項 CP / 報告 / 預覽 / RF-01-001/002 / 遷移 / Note 回歸，以及 18 項 CaseLog / 執行整合，均通過。
- 發佈 checkout：對應 51 項與 17 項，均通過。差異源自本機既有額外測試，不是刪除測試。
- 400 同 entry 限制、404 精確訊息、無效 YAML / property、CP 無 Note 拒絕、人工 CP 無 Note 拒絕、FAIL 優先於 CP、遷移保留資料與索引 / integrity / foreign keys 均驗證。
- Node CP Matrix：CP 計數、完成數、最新結果與讀取不修改來源通過。
- Chromium：本機新 Execution 與發佈舊 Execution 兩版預覽通過；CP badge、9 列判定、無獨立 Note、深淺主題、無水平溢出、refresh/retry、Escape / 焦點、切 Task / 關閉晚回應、無寫入 API。
- 正式 HTML：Record COMPLETED、完整 Log 附件、列印與收折還原通過。
- PDF 產物 cp-report.pdf 第 4/5 頁已渲染檢視：CP / Note / Skip 可讀，跨頁重複表頭，無遮擋。
- JavaScript syntax、git diff --check、RF-01-008 原始檔/兩份鏡像一致性，以及本機整合 patch reverse-check 通過。

## 交付與正式服務

發佈目的地：baga0607-cpu/bmcauto 的 main，使用 bmca-runtime/publish-handoff-20261111 獨立 checkout。未提交整份本機預存改動，也未推送舊 Ulrox0880 origin。

本機使用獨立 case_worker.py，發佈基線仍使用 app.py 的執行器；兩版均已接 CP。保留精確本機差異於 docs/patches/2026-11-12-cp-local-integration.patch（app / worker / plan_state / models / workbench）。共用模組以本次正常提交為準；不可將整個發佈 checkout 覆蓋本機較新的工作區。

本次未重啟正式 5000，也未對正式資料庫執行遷移。正式服務仍是上次 report-preview restart 的程序；新靜態檔可被讀到，不代表後端已更新。正式啟用需先確認無 active execution、備份正式 SQLite，再重啟以載入 CP schema；驗證 integrity_check / foreign_key_check 與原始結果保留。現有 Plan 為獨立副本，需明確匯入 / 更新 RF-01-008 後再執行，不能只重啟便宣稱已換新版。
