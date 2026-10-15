# Test Plan Workspace 功能移植設計

日期：2026-07-23

## 目標

將 Classic View 已有的 Test Plan 編輯能力完整移植到新版 Test Plan Workspace。移植期間保留 Classic View 按鈕作為功能與資料結果的比較基準；確認新版達成功能對等後，再另行移除 Classic View。

本次不改變 Test Plan、Golden Plan 與 Test Case Library 的既有資料語意，也不刪除未被明確指定的既有功能。

## 保留的新版功能

新版 Test Plan Workspace 繼續保留：

- Generate Summary Report
- Export Selected
- Import Test Case
- Delete Plan
- Test Case 全選、單選、Edit 與 Remove
- Plan 統計資料
- Task Summary
- 既有執行鎖定、確認提示與錯誤處理
- Classic View 按鈕

移除新版 Workspace 左右兩側重複出現的綠色 `+ Create Task` 操作。此變更不刪除 Task 資料模型或其他建立 Task 的既有入口。

## 版面結構

新版採用「資料夾樹＋完整清單」設計。

### 標題與主要操作

- Plan 名稱顯示於 Workspace 標題。
- 名稱旁提供重新命名操作。
- 原有報表、匯出、匯入、刪除與 Classic View 操作保留。
- `Add Test Cases` 開啟 Test Case Library 右側抽屜。

### 左側資料夾樹

左側負責資料夾結構與快速篩選：

- 第一個節點為 `All Test Cases`。
- 顯示 `Resource_Systems`、`Resource_Chassis`、`Custom` 等目前 Plan 中的分類。
- 顯示各分類與 Custom 子資料夾的 Test Case 數量。
- 點擊分類只會篩選右側清單，不會改變資料。
- 左側資料夾樹可以收合，讓右側清單使用完整寬度。

資料夾操作規則：

- 原生分類可以拖曳排序。
- 原生分類不可重新命名或刪除。
- Custom 子資料夾可以新增、重新命名、刪除及拖曳排序。
- 刪除非空的 Custom 子資料夾時，沿用既有安全確認與 Test Case 歸位規則。

### 右側 Test Case 清單

右側負責 Test Case 內容與順序：

- 初次開啟 Plan 時預設選取 `All Test Cases`。
- `All Test Cases` 依資料夾分組，一次顯示完整 Plan 的所有 Test Case。
- 預設展開所有分類，並記住使用者後續的展開或收合狀態。
- 點擊左側分類後，只顯示該分類或子資料夾的 Test Case。
- 每列保留選取、名稱、分類、Edit、Remove 與既有狀態資訊。
- 每列增加 `Add to Golden Plan`；已存在於 Golden Plan 時顯示不可重複加入的狀態。
- Test Case 重新命名或詳細編輯由右側 Edit 操作處理。

拖曳規則：

- 在同一資料夾內拖曳會更新 Test Case 順序。
- 在完整清單中跨分組拖曳，會同時改變 Test Case 所屬分類或 Custom 子資料夾及其順序。
- Test Case 可從右側直接拖到左側目標資料夾。
- 原生 Test Case 能否跨原生分類移動，沿用 Classic View 與後端目前允許的既有規則；新版不新增更寬鬆的資料路徑變更。
- 鎖定中的 Plan 不允許拖曳或結構修改，並沿用既有提示。

## Test Case Library 抽屜

`Add Test Cases` 從右側開啟 Library，不離開當前 Plan：

- 預設呈現 Golden Plan／Test Case Library 的既有分類。
- 支援搜尋、單選、全選與批次加入。
- 加入時沿用既有重複 Test Case 檢查。
- 加入完成後更新右側完整清單及左側數量。
- 關閉抽屜後保留原本的 Workspace 篩選與捲動位置。

## Plan 重新命名

- 點擊標題旁重新命名操作後進入行內編輯。
- 空白名稱、重複名稱或後端失敗時，不更新畫面中的正式名稱。
- 成功後同步更新 Project Workspace、Plan 列表與 Classic View。
- 使用既有 `/api/rename_plan` 能力，不建立第二套命名資料流。

## Golden Plan

- 每個 Test Case 的操作選單提供 `Add to Golden Plan`。
- 加入前顯示明確確認。
- 已存在於 Golden Plan 的 Test Case 不可重複加入。
- 成功後立即刷新該列狀態與 Library。
- 失敗時保留原 Plan Test Case，不做部分刪除或移動。

## 資料與元件邊界

新版與 Classic View 共用目前的 `db.projects` 狀態、現有 API 與保存流程。新增的 UI 元件只負責呈現與呼叫既有操作：

- Folder Tree：分類導覽、資料夾排序與 Custom 資料夾操作。
- Plan Case List：完整或篩選清單、選取、編輯與 Test Case 排序。
- Library Drawer：從 Library 選取並加入 Plan。
- Plan Header：重新命名及既有 Plan 級操作。

若現有 Classic View 函式與 DOM 綁定過深，實作時抽出共享的資料操作函式，再由新舊兩個畫面呼叫；不複製兩套 API 邏輯。

## 錯誤與一致性

- 需要保存的拖曳操作採「後端成功後確認畫面狀態」或失敗回復原排序，避免畫面與資料庫不一致。
- API 失敗需顯示具體操作失敗訊息。
- 重複加入 Golden Plan 或 Plan 時維持既有阻擋規則。
- Classic View 與新版切換後必須呈現相同名稱、分類、資料夾與 Test Case 順序。

## 驗證

至少驗證以下情境：

1. Plan 重新命名後，新版、Project Workspace 與 Classic View 名稱一致。
2. `All Test Cases` 能一次顯示全部分類，資料夾篩選與回復全部顯示正常。
3. 原生分類不可改名或刪除，但可依既有資料能力排序。
4. Custom 子資料夾可以新增、改名、刪除及排序。
5. Test Case 在同資料夾排序、跨 Custom 資料夾搬移及拖至左側資料夾均能保存。
6. Library 支援單筆與批次加入，重複項目不會加入兩次。
7. Plan Test Case 可加入 Golden Plan，重複項目顯示已存在。
8. 既有 Export、Import、Report、Delete、Edit、Remove、選取及 Task Summary 功能沒有退化。
9. 綠色 `+ Create Task` 從 Test Plan Workspace 移除。
10. Classic View 在本次功能移植完成後仍可使用。

## 不在本次範圍

- 移除 Classic View。
- 重新命名或刪除原生分類。
- 改變 Golden Plan 或 Test Case 的版本語意。
- 重做 Task Workspace 或執行流程。
- 建立新的後端資料模型，除非驗證證明現有模型無法保存已確認的排序。
