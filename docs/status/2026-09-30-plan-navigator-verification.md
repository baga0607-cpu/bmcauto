# Plan 導覽與 Test Executions 分組驗證（2026-09-30）

測試網站：http://127.0.0.1:5127/

本次依使用者核准的局部設計，沿用隔離 Worktree `D:\Pytest\_redfish\plan-folder-current-state` 與分支 `codex/plan-folder-current-state-20260917`，未合併或部署。

## 新版操作

1. Plan 左側現在依「父資料夾 → 子資料夾 → TC」呈現內容。點 TC 名稱會在右側顯示唯讀預覽；勾選框仍控制原本的選取用途，與閱讀中的 TC 分開。
2. TC 的 `⋮` 選單位於左側，保留 Move to Folder／Move selected、Edit、Remove；Add to Golden Plan 與 In Golden Plan 文字和圖示也保留。
3. 右側列出所選 TC 名稱、所在路徑、步驟總數，以及依原始順序排列的步驟名稱、說明、模組和參數。尚未選取、載入中、沒有步驟和讀取錯誤各有提示。
4. 透過 Edit 開啟既有 Builder，儲存後回到同一 Plan 畫面並立即更新預覽。未儲存離開仍有既有確認。
5. 左右比例預設約 40:60，可拖動分隔線並記住寬度；窄視窗將導覽與內容上下排列。既有搜尋、父子收折、範圍選取、拖曳排序與跨資料夾移動保持可用。
6. Test Executions 按 Plan 名稱及數量分組，可個別收折；保留進度、通過率及 Run / Review。重名 Task 仍可辨別所屬 Plan。

## 預覽資料規則

新增按 Plan 與 TC 身分讀取的唯讀介面。預覽從檔案靜態解析，不執行 testcase 或 step 程式。一般 STEPS 字典、二元素組合及字串格式皆支援。動態計算的 STEPS 會明確提示不支援靜態預覽；缺少步驟檔或說明時保留該步驟與順序，顯示提示，不偽裝成零步驟。既有資產相容性抽查：28 個 testcase、309 個步驟可解析；其中 9 個原本缺失的步驟檔造成 68 次 metadata 提示，未修改原有資產。

## 驗證

- Python：**138 / 138 通過**。
- JavaScript：**68 / 68 通過**。
- 頁面 inline scripts 與 Python compile 檢查通過；git diff --check 通過。
- Chrome / Playwright 在 5128 的獨立資料庫及程式資產副本驗證：左右欄內容、所有步驟、零步驟、錯誤重試、搜尋、收折、TC 同資料夾及跨資料夾拖曳、寬度記憶、Golden 發布／標記、Edit／Save、Remove、執行鎖、深淺主題與 Plan 分組。
- 瀏覽器驗證無 JavaScript pageerror；已檢視深淺主題與分組截圖。
- 獨立審查提出的「編輯儲存後舊預覽」與「離頁再返回持續載入」均已修正，新增回歸測試，複審無待解決項目。
- 5127 更新前備份資料庫至 `verification/2026-09-30/user-before-restart.db`，重啟後比對八張資料表完全一致；main 的 112 個既有修改／未追蹤檔案雜湊不變。首頁、資料 API 與真實 TC 預覽皆正常。

本機測試證據位於 `verification/2026-09-30/`（Python／Node 輸出、三組瀏覽器驗證結果、截圖及重啟比對紀錄）；資料副本、Log、截圖未加入 Git。審查報告：`verification/2026-09-30-review.md`。

## 同日追加：精簡操作列

資料夾列保留展開／收折、TC 數量與新增子資料夾 `+`，Rename／Move／Delete 收入 `⋮` 選單；原本的資料夾勾選仍保留。TC 名稱、Golden 狀態與 `⋮` 改成同一行，Golden 文字不換行，長 TC 名稱省略並以懸停提示顯示完整內容。已驗證選單可開啟 Rename 對話框、Escape 關閉選單，以及各 TC 三個元素垂直中心對齊。此驗證僅讀取既有資料並取消對話框，未修改使用者資料。JavaScript 68 項、Python 相關契約 91 項通過。5127 靜態頁面已提供更新，重新整理即可。

## 同日追加：文字尺寸與主題層次

依核准方案，主要 TC／資料夾文字調為 14px、Golden 與輔助資訊 12px、區塊標題 16px、TC 預覽標題 22px，操作圖示點擊區至少 32px。白色主題加深外框、使用淡灰區塊標頭與白色步驟卡片，選中 TC 使用淡藍底與左側色條；深色主題同步提高次要文字對比。保留單行名稱／Golden／選單和原有操作。實際 Chrome 檢查 340／480／700px 左欄寬度皆無操作溢位或 Golden 換行，深淺主題、選單與步驟預覽正常；JavaScript 68 項通過。此輪僅修改 CSS，未改動資料模型或使用者資料。新版截圖與量測記錄為 `verification/2026-09-30/readability-*.png`、`readability-results.json`。5127 已恢復啟動，可重新整理查看。
