2026-11-12 latest deployment: Desktop launcher now offers Restart service and recognizes the Windows Python parent/child chain. Formal service restarted at 15:40; CP migration enabled, all 21 tables preserved. Existing saved FAIL results remain unchanged. See [restart handoff](2026-11-12-desktop-restart-cp.md).

2026-11-12 latest: RF-01-008 and shared Log / Execution / preview / HTML / PDF now support CP + mandatory Note, Skip + Reason, and Record COMPLETED. Standalone report Note removed; historical notes retained in table. Formal service restart / independent Plan source update pending. See [2026-11-12-rf008-conditional-pass.md](2026-11-12-rf008-conditional-pass.md).

**最新功能（2026-11-12）**：Execution 新增單一 Test Case 報告預覽；本機按鈕在 Log 右側，彈窗共用正式報告渲染並支援 Refresh。驗證、遠端舊版接點與精確本機 patch 見 [報告預覽交接](2026-11-12-execution-report-preview.md)。

**最新規則（2026-11-12）**：取消 S/C/R ID；採 Step／Type／Description／Result／Judgement 五欄，Type 僅 Command／Action／Checkpoint／Record。RF-01-001／002、Log 與報告同步更新，見 [編號與 Type 交接](2026-11-12-numbered-method-types.md)。

**最新報告更新（2026-11-12）**：HTML／PDF 加入 Step、Checkpoint、Record 關聯 ID 與結果表，採緊湊列距；驗證與發佈範圍見 [報告交接](2026-11-12-report-method-results.md)。

**最新測項更新（2026-11-11）**：RF-01-001／002 已採 Step／Checkpoint／Record 與關聯 ID，Log 同步更新；其他測項及正式 Repository／Plan 副本未改。見 [S/C/R 交接](2026-11-11-rf01-method-items.md)。

**同日後續：Connection UI** 已改為 BMC／Console Server／DUT OS 三個可收折區塊與九欄；Console Port 儲存使用 telnet 0，cpc 僅記錄為待實作連線規格，未修改 case.py。見 [Connection 更新](2026-11-11-connection-groups.md)。

**最新統合交接（2026-11-11）**：[三個開發對話統合交接](2026-11-11-consolidated-handoff.md)。已整合55回合需求與結論、未完成事項、驗證限制與子代理人接手方式；下方為歷史紀錄。此次發布限文件，本機產品程式仍有未提交差異。

# 最新本機更新 — 2026-11-11

同日後續：Task Info 卡片縮至560px，移除Overview底部說明；點選計畫／實際日期或Status直接開啟Task List共用編輯視窗，在同一視窗填寫必填Note並儲存。隔離操作與正式唯讀檢查通過。

[Task Info 緊湊排版與 Scope 樹狀結構](2026-11-11-task-info-compact-scope.md)：Overview 欄位寬度減半、列間距與上下內距縮減25%，iDesign 兩欄提升至主層級。Scope 採 Plan 資料夾樹狀表格，移除 Folder 欄位，支援資料夾勾選及收折。隔離瀏覽器及正式唯讀比例檢查通過。

# 最新本機更新 — 2026-11-10

[New Task 卡片／任務軟刪除與緊湊欄位](2026-11-10-task-create-soft-delete.md) 已套用：刪除必填原因寫入 Note，狀態 Deleted，保留資料並從一般列表隱藏。Overview／Connection 每列標籤與欄位；Note 新到舊不收折；FW Component／Version 改欄內提示。78 項任務測試、13 項報告測試及隔離／正式唯讀瀏覽器通過，正式服務已重啟且資料比對未變。Status 篩選 UI 與 DUT Config 欄位仍待後續需求。

[Task Info 右側卡片與英文介面](2026-11-10-task-info-drawer.md) 已套用。Test Task 五頁籤、Plan Task Overview／Note 兩頁籤，直接編輯及未儲存提示；Task Info History 文字統一為 Note。Connection 七欄映射至既有 context，保留其餘連線設定。Task List 的 Assignee／Status 改為獨立欄位，My Task 頁面移除。36 項後端測試、隔離瀏覽器及正式唯讀檢查通過。DUT Config 尚待欄位定義，未測實體 DUT。

# 最新本機更新 — 2026-11-02

[RF-01-008／013 與結果 Note](2026-11-02-result-note.md) 已完成並套用。報告格式另議，HTML/PDF 渲染未變。

# 最新交接 — 2026-10-30

先讀[最新handoff](2026-10-30-handoff.md)與[發布驗證](2026-10-30-release-verification.md)。BMCAgent已啟動，Task/Report/Plan/Execution更新已推送baga0607-cpu/bmcauto main。Viewer/Editor僅右側面板，獨立視窗取消。Plan依序為名稱+Project、頁籤、搜尋/Import/Rename/Delete、Case列表；點Case只切換已開啟工具。下方「尚未發布」屬歷史狀態。依使用者下一指示繼續。
# 最新本機更新 — 2026-10-28 Task Info 頁籤

[Task Info 分頁](2026-10-28-task-info-tabs.md) 已套用。Test：Content／Scope／Connection／DUT Config／Note & History；Plan：Content／Note & History。DUT Config 僅名稱，編輯草稿／History／執行鎖定已驗證。僅前端變更，正式資料未異動，尚未發布 GitHub。

# 最新本機更新 — 2026-10-28 既有測項與建立時間

[RF-01-001～006 逐步輸出與建立時間](2026-10-28-existing-source-step-output.md) 已套用工作檔與 6 個 Repository 新版本。使用者在工作期間清空 Plan 測項，未還原任何刪除內容。時戳改為來源 .py 建立時間，未知為 —。456 組行為比對、61 項平台測試及 32 組 RF 測試通過；尚未發布 GitHub。

# 最新本機更新 — 2026-10-28 測項報告格式

[依工作表1調整報告](2026-10-28-report-case-layout.md) 已套用；[Step／Criteria／Result 輸出規範](../agents/report-step-output.md) 與可執行範例已建立。DUT Configuration 僅名稱；同 Plan 矩陣與 Reference 規則維持。38 項相關測試通過，正式資料未異動，尚未發布 GitHub。

# 最新本機更新 — 2026-10-28 Reference

[Report／Reference 分類與合併](2026-10-28-report-reference.md) 已套用。可跨 Plan 選取、兩區拖曳排序；同 Plan Task 仍依矩陣規則整合。取代以下「跨 Plan 留待討論」描述。尚未發布 GitHub。

# 最新本機更新 — 2026-10-28 Report 匯出

先讀 [最新交接](2026-10-28-handoff.md)。[Report 樹狀選取與 PDF 匯出](2026-10-28-report-tree-export.md) 已套用本機；跨 Plan 的 Reference 留待討論，尚未發布 GitHub。

# 最新本機更新 — 2026-10-28

[Report 使用 Plan 頁面](2026-10-28-report-plan-view.md) 已套用，尚未發布 GitHub。先前 Task 決定仍見 2026-10-27 handoff 與後續補充。

# 最新本機更新 — 2026-10-27

Task 新增日期推導的 Not Scheduled，詳見 [功能紀錄](2026-10-27-not-scheduled.md)。已套用本機，尚未發布 GitHub。

# 最新交接 — 2026-10-27

新對話先讀 [2026-10-27 handoff](2026-10-27-handoff.md)。包含Status、Assignee、多關鍵字搜尋、固定欄寬與目前本機啟動模式。

# Current handoff

先讀 [2026-10-22 handoff](2026-10-22-handoff.md)。目前最終決定、內網/本機啟動規則與發布注意事項均以該文件為準。

# Earlier updates

2026-10-22: [Owner History and hover navigation](2026-10-22-owner-history.md) deployed; 86 related tests and formal data-preservation checks passed.

2026-10-21: [Test Plan SKU naming](2026-10-21-plan-sku-naming.md): SKU selection or Project-name fallback fills an editable Plan name; duplicate names require correction.

2026-10-21: See [Project view/edit and workbook import](2026-10-21-project-import.md). New Project workbook import is now implemented; this supersedes earlier notes describing it as future work.

# BMC Agent next steps

Last updated: 2026-10-21

Project Information framework: [delivery and future import mapping](2026-10-21-project-information.md). Workbook upload/automatic Project creation remains future work.

Latest navigation update: [persistent sidebar](2026-10-20-sidebar-layout.md), superseding earlier navigation and sidebar visibility rules.

Start here: [latest handoff](2026-10-16-handoff.md). Its current UI and import rules supersede older descriptions below.

The current local checkout implements the single-file Repository and English file navigator workbench. The user approved complete removal of step/block editing and execution, replacing the earlier compatibility decision.

- Current UI and verification: [workbench delivery](2026-10-07-workbench-ui.md).
- Ownership and single-file contract: [approved design](../superpowers/specs/2026-10-07-single-file-case-design.md).
- Prior facet evidence: [single-file delivery](2026-10-07-single-file-case-delivery.md).

Continue case by case with environment injection and the agreed result states. Test Plan documents, report formats and Final Report aggregation remain pending discussion. Do not add placeholder controls for undecided functions.

This change is local; it has not been committed or pushed. Historical 2026-09-30 deployment/publishing permissions and counts belong to that earlier delivery and do not describe the current checkout. Preserve current work and use disposable databases/scripts for verification. The offline checks do not validate real BMC behavior.

Task-owned connection environment delivered locally: [Task connection settings](2026-10-14-task-connection-settings.md).

Desktop-only UI scope and current layout findings: [desktop layout review](2026-10-14-desktop-layout-review.md). Mobile support is deferred.

Task management first increment delivered locally: [Task information, CRUD and Gantt](2026-10-14-task-management.md). Further task management features remain for separate decisions.

Repository function page add/view/remove and exclusive workspace: [Repository page](2026-10-14-repository-page.md).

Automation declaration and badges delivered locally: [classification delivery](2026-10-14-automation-labels.md).

Repository folders and whole-folder Plan copies: [delivery](2026-10-14-repository-folders.md).

Current Repository BMC tree, recursive directories and drag/drop: [delivery](2026-10-14-repository-tree.md). Supersedes the prior flat Repository folder UI and two-level Plan depth constraint for subtree preservation.

Latest handoff (2026-10-15): [complete current decisions, paths and verification](2026-10-15-handoff.md). Read this before resuming in a new conversation.

RF-01-001 integration audit (2026-10-15): [current local records, isolated runner verification and remaining gaps](2026-10-15-rf01-integration-audit.md). Repository and Plan already contain the exact current case; no Task exists in the audited live database. Next proposed increment is method metadata validation and Plan presentation.


2026-10-16: Plan Case operations now use the fixed BMC root, direct Python import, folder inline rename and drag/drop. Verified and deployed locally; see [Plan Case operations](2026-10-16-plan-case-operations.md).

## Latest status pointer — 2026-10-16 Plan source import

Read docs/status/2026-10-16-plan-source-import.md before continuing. The implemented toolbar/dual-tree workflow and version-aware conflict rules supersede earlier Plan .py picker and folder Add Case plans. Tests, copied-database startup checks and formal port 5000 deployment passed. All existing rows remain unchanged, integrity/FK checks passed, and the version-aware index and import endpoint are loaded. Preserve before-deploy.db and deploy-rows.json in the backup directory.
Test Case ordering (2026-10-19): all case-list views use folder-local natural numeric name ordering by default. A manual before/after drag stores a folder-specific custom order; folder Actions > Resorting restores automatic numbering for direct cases. Repository case-only batches and Plan case/source-case insertion support before/after anchors. Dashed allowed-area frames and active inside/upper/lower-half boxes show placement; self/cycle/locked/reverse-source targets are rejected. Source panes remain read-only. Persistent overrides are additive case_list_orders records, independent of definitions and Task evidence. See docs/status/2026-10-19-case-ordering.md.

Unified logs (2026-10-19): `context['log']` supplies section/http/check/finish; RF-01-001–003 use it. Platform-owned filenames include Task and case names. Formal service and six matching Plan copies updated with prior evidence preserved. See [Log interface, verification and deployment](2026-10-19-structured-case-logs.md), including the independently reproduced existing ordering-test failure.

Log filenames (2026-10-19): per-execution timestamp/Task/Case ID/type plus UUID; exclusive creation retains all prior disk logs. Supersedes fixed overwrite naming. See [delivery and validation](2026-10-19-log-naming.md).

2026-10-19: Task Log viewing and new-name PDF attachments verified with nine passing isolated tests; see `2026-10-19-task-log-attachments.md`.

2026-10-19: Single Test log deployed; supersedes split API/Execution logs. 54 tests (53 passed, one historical skip); see `2026-10-19-unified-test-log.md`.

2026-10-19: Platform-owned Test log / PDF messages now English; user, test source and device text retained. See `2026-10-19-english-test-log.md`.
2026-10-19: Test log checks now render inside their section, with explicit no-check notices and clear HTTP/final-result boundaries. See `2026-10-19-grouped-test-log.md`.


Latest local delivery: [2026-10-22 Dashboard/import Skip](2026-10-22-dashboard-import-skip.md). Read this and the 10/22 handoff before continuing.

Latest local delivery: [2026-10-22 Schedule working calendar](2026-10-22-schedule-calendar.md). Shared persistent manual day overrides affect both Task types; official holidays currently cover 2025–2027.

Latest UI delivery: [Schedule compact controls / drag panning](2026-10-22-schedule-compact.md). This supersedes the 120-day window and previous/next/date controls.

Latest delivery: [Schedule schedule editing / date dialog](2026-10-22-schedule-editing.md). Task bars now edit dates with mandatory new Note; date header uses a modal with two working-state choices.

Latest delivery: [Task Owner](2026-10-22-task-owner.md). Roster is web_ui/task_owners.json, initially TBD/David; add further user-supplied names there.

Latest UI delivery: [Schedule Task Info and reschedule dialog](2026-10-22-schedule-info-dialog.md). Name links and bars have independent navigation/edit behaviors.

Latest delivery: [Immutable Task History](2026-10-22-task-history.md). New Schedule reasons go to the append-only table; never put them in Notes or mutate/delete History.

Latest delivery: [Edit Task mandatory History](2026-10-22-edit-task-history.md). PATCH /api/tasks date changes now require History and original-date expectations.

2026-10-27 local refinement: [Task List compact layout](2026-10-27-task-list-compact.md) applied; source not yet published.

2026-10-27 local refinement: [Unified Task Info](2026-10-27-task-info-unified.md) applied for both Task types under global Task only; Schedule names link there. Not yet published.

2026-10-27 local update: [Task cell editing and Actual dates](2026-10-27-task-cell-edit.md) deployed to loopback service, 74 Python tests and isolated browser mutation checks passed; not published.

2026-10-27 local refinement: [paired Task date dialogs and range validation](2026-10-27-task-date-pairs.md), not yet published.

2026-10-27 local update: [Task iDesign ID and FW Package](2026-10-27-task-reference-package.md) deployed; 67 tests and preview browser edits passed. Not published.

2026-10-27 local refinement: [metadata double-click and firmware summary](2026-10-27-task-meta-interaction.md), not published.
