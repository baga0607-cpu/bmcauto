# BMCAgent 交接｜Plan、Task Execution 與 Connection

2026-11-25（台北）。本輪功能已推送至 GitHub。新對話可從下列定案繼續；下一項功能由使用者指定。

## 開發與發佈位置

| 用途 | 位置或版本 |
|---|---|
| 本機日常開發 | `D:\Codex\bmc_auto_test\BMCAgent`，介面程式在 `web_ui` |
| 本輪發佈用工作目錄 | `D:\Codex\bmc_auto_test\bmca-runtime\publish-20261125-ui`，本機提交 `7ead010ae3720095930efd8636139597b77a8e34` |
| GitHub 發佈基準 | [baga0607-cpu/bmcauto 的提交 f6dcbff](https://github.com/baga0607-cpu/bmcauto/commit/f6dcbff411c63f879cb726eb8d1a6257741b0d17)，推送後已核對 main |
| 版本核對 | 兩筆提交的父版本均為 `4437cad`，完整檔案樹均為 `692770543382d23c127222059b1b55c05941207b`。本機 Git 當時無法解析 github.com，改由 GitHub 連線工具建立遠端提交。 |

日常開發目錄另有其他工作的差異，且其 `origin` 指向另一個儲存庫。下次發佈應先核對目的地、遠端最新提交與本次修改範圍。此輪確認的是 GitHub 發佈，本機服務是否已重新啟動並載入新版仍待確認。

## 已定案的畫面與操作

| 位置 | 目前設計 |
|---|---|
| Plan 左側 | 左右欄各 50%。搜尋欄較短，右側工具按鈕靠齊搜尋框。清單左側留白 6 px、每層縮排 9 px。`Feature_ID` 固定顯示，舊 Case 缺值時留白。 |
| Plan 右側 | Case 標題與左側工具列對齊。Step 欄寬 48 px，步驟內容使用一般字重、移除列間橫線，上下留白各 3 px。Checkpoint 保留縮排與次要色編號。Parameters 使用滑桿圖示，有參數時才顯示。 |
| 平台色彩與選取 | 淺色模式使用藍灰導覽、霧灰工作區與白色表格。Plan 與 Repository 以淡藍底表示選取、藍色細線標示目前預覽的 Case。 |
| 共用圖示 | 全選用雙勾，清除全選最終採用「雙勾加反向斜線」，確認用單勾，關閉用 X。展開／收合使用線條箭頭，展開向下、收合向右。 |
| Task Execution → Connection | 工具列按鈕開啟置中彈窗，直接編輯該 Task 的連線設定。支援儲存、X、Esc、未儲存提示與執行中鎖定。 |

Plan 與 Execution 的入口在 `web_ui/static/workbench.js`，共用樣式在 `workbench.css`，圖示在 `action-icons.svg`。Connection 表單與彈窗在同目錄的 `task_info_drawer.js`、`task_info_drawer.css`。Plan 步驟表和匯出的 HTML Report 各有自己的樣式。

## Rerun needed 的判定與顯示

原因記錄在各 Task 的 Case 上。同一筆可累積多種原因並去重。Execution 清單使用固定寬度的 ↻ 圖示，滑鼠停留或鍵盤聚焦時顯示原因，結果明細顯示完整文字。

| 原因 | 觸發條件 |
|---|---|
| Parameter Modified | Plan Case 的參數值改變。 |
| Case Modified | Plan Case 的 Python 原始碼改變。 |
| Connection Modified | 該 Task 的連線設定改變，且該 Case 已有結果資料或執行時間。 |
| Case Overwritten | 匯入時選擇覆寫，來源與參數均相同，但原有結果仍依覆寫規則標記。 |

舊資料只有重跑旗標時顯示 `Reason unavailable`。重新執行並寫入 PASS、FAIL 或 C-PASS 後，旗標與原因一起清除；Block 會保留提示。資料模型與遷移在 `web_ui/models.py`、`plan_state.py`，原因寫入在 `single_case.py`、`task_environment.py`。

## 測試紀錄與後續驗證

- 發佈前執行 91 項回歸測試，90 項通過、1 項略過。Connection 相關測試另跑 6 項，全部通過。
- 另一次執行 `test_workbench_contract` 有 1 項錯誤：`test_legacy_records_are_readable_without_importing_their_code` 預期 Task summary 含 `log_text`，實際缺少該欄位。後續若處理，先核對 summary 與 logs API 的設計，再決定調整測試或實作。
- 尚待瀏覽器實測：Plan 左右表頭在長 Case 名稱及工具列換行時的對齊、↻ 提示能否完整閱讀、Connection 彈窗儲存與放棄變更、X／Esc 關閉後的焦點。可用測試 Task 驗證，避免改動既有執行證據。
- 上一輪的 HTML 報告與 Repository 背景見 [11 月 24 日交接](2026-11-24-report-repository-handoff.md)。
