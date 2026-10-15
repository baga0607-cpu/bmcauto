# Plan / Task 最新設計交付計畫

日期：2026-09-30。這是已核准工作與後續調整的整合交付清單，不是新一輪功能提案。

設計：[最新整合規格](../specs/2026-09-30-plan-task-workspace-current-design.md)。原始實作步驟：[2026-09-17 計畫](2026-09-17-plan-folder-current-state.md)。

- [x] 在隔離 Worktree 實作持久化資料夾、live Task membership、最新結果與刪除連動；移除過時 Snapshot glossary 定義。
- [x] 完成九項 UX 改善：排序、主題、資料持久化、全選、父子收折、匯入介面、人工結果、Log、Tasks 按 Plan 分组。
- [x] 完成左側資料夾／TC 導覽、右側完整步驟預覽，Test Executions 按 Plan 分組。
- [x] 精簡資料夾選單、固定 Golden 操作同列，放大字體與改善白色主題對比。
- [x] 以資料庫副本與離線 fixture 完成自動化及瀏覽器驗證。正式整合紀錄中的 Python 138、Node 68 為該次測試結果。
- [x] 經使用者後續核准整合到 main 和本機 5000，保留 main 既有變更與正式資料；5127 保持獨立。
- [x] 核對正式／測試 DB、API、Plan UI 清單與匯出路徑／步驟，整理驗證範圍。
- [x] 更新專案 skill 與目前狀態索引，讓後續代理遵循 current-state 模型。

## GitHub 交付

追蹤索引：[GitHub Issue #1](https://github.com/Ulrox0880/BMC-Agent_Codex/issues/1)。

使用者已授權上傳本次設計、計畫與 skill。推送既有實作提交及本次文件更新至 origin/main；以遠端 commit SHA 核對結果。依 repository 規範建立 GitHub Issue 作為已交付設計／計畫索引。此步驟不發布本機資料庫、設定或執行 Log。

## 後續

目前沒有新增功能待實作。維持資料庫副本驗證；實體 BMC 執行需依另外的測試範圍安排。若變更刪除或人工結果語意，應先同步整合規格與 skill。

## 後續明確授權：完整正式版同步

使用者確認要 GitHub main 與正式版完整來源一致，包含既有實作提交及本機 TC 資產；先前文件專用 PR #2 交付方式由本次完整同步取代。備份與驗證見 [同步紀錄](../../status/2026-09-30-github-formal-sync.md)。
