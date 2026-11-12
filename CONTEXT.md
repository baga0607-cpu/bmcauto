2026-11-12 latest report: Case Name is the only disclosure; Test Data and Test Information expand together. Result Summary and standalone Note removed, method table retained under Test Data. Formal service updated at 16:17. See [report hierarchy](docs/status/2026-11-12-report-hierarchy.md).

2026-11-12 latest deployment: Desktop launcher now offers Restart service and recognizes the Windows Python parent/child chain. Formal service restarted at 15:40; CP migration enabled, all 21 tables preserved. Existing saved FAIL results remain unchanged. See [restart handoff](docs/status/2026-11-12-desktop-restart-cp.md).

2026-11-12 latest: RF-01-008 and shared Log / Execution / preview / HTML / PDF now support CP + mandatory Note, Skip + Reason, and Record COMPLETED. Standalone report Note removed; historical notes retained in table. Formal service restart / independent Plan source update pending. See [docs/status/2026-11-12-rf008-conditional-pass.md](docs/status/2026-11-12-rf008-conditional-pass.md).

2026-11-12 Execution report preview: read-only single-Case modal reuses the production HTML renderer, with refresh and no export or data writes. See docs/status/2026-11-12-execution-report-preview.md for UI integration and publication-baseline differences.

2026-11-12 latest method contract: Step / Type / Description / Result / Judgement. Only Command and Action show numbered main steps; Checkpoint and Record follow with blank Step cells. No displayed S/C/R IDs or Type=Step. Record has no judgement. See docs/status/2026-11-12-numbered-method-types.md.

2026-11-12 report update supersedes earlier omission of method tables: HTML/PDF include compact ID / Type / Description / Result rows for Step, Checkpoint and Record, with explicit source-step links and recorded statuses. Cases remain initially collapsed; opening shows Test Data. See docs/status/2026-11-12-report-method-results.md.

# BMC Agent Test Management

This context defines the language used to organize reusable test cases and execute test work in BMC Agent.

## Language

**Test Plan**:
A reusable scope that owns an ordered hierarchy of folders and test cases for a project.
_Avoid_: Build

**Plan Folder**:
A persistent, user-editable node in a Test Plan hierarchy. A Plan Folder exists independently of whether it currently contains test cases.
_Avoid_: Native category, Custom subfolder

**Default Folder**:
A Plan Folder initially created from the system's standard Redfish organization. After creation it follows the same editing rules as any other Plan Folder.
_Avoid_: System folder, native folder

**Historical Folder Template**:
The retired Golden Plan folder structure from the former UI. The Repository now supplies single-file Test Cases; new Plans can start empty and own their folders.
_Avoid_: Required folder set, system folder list

**Folder Subtree**:
A Plan Folder together with every descendant Plan Folder and every test case contained anywhere below it. Deleting a Folder Subtree permanently deletes all of those contents after explicit confirmation.
_Avoid_: Empty folder deletion

**Task**:
One current test assignment under a Test Plan. Its scope references live test cases owned by that same Plan; it retains only their latest results and current environment fields.
_Avoid_: Task Snapshot, historical execution assignment

**Task Test Case**:
The unique membership of a Plan Test Case in a Task, storing its current ordering, selection, latest status and latest result/log references. Its status is one of `TBD`, `Running`, `Passed`, `Failed`, or `Block` (the 2026-10-16 user decision extends the earlier four-status model). Removing the membership or deleting its Plan Test Case permanently removes its latest evidence from current reports.
_Avoid_: Archived Test Case, execution attempt

**Test Case Family**:
A lineage shared across Plan-local test case copies through `family_id`. An exact named version is identified by `family_id` plus its normalized test case name; no separate `version_id` is currently used.
_Avoid_: Treating `system_id` as cross-Plan identity

**Test Case Repository**:
A store of standard single-file Python Test Cases. Every import receives a UTC timestamp identifying its source generation. Loading a Repository Test Case into a Plan copies its Python source and creates independent editable settings.

**Source Generation**:
The Repository import timestamp identifying the test method generation. Plan-specific adaptations never change this timestamp.

**Plan Test Case Settings**:
Parameters declared by a Test Case and edited only in its Plan. Every Task references the latest Plan definition when executing. Plan changes mark retained existing results as needing a rerun; results and logs remain available.

**Retired Step Test Case**:
A historical multi-module Test Case whose records remain readable. Step editing, import, and execution have been removed. Replace it by importing one independent `.py` through Test Case Repository; no automatic conversion of the test method is performed.


**Task Connection Settings**:
The BMC, Console server, DUT console commands and DUT OS connection environment owned independently by one Task in tasks.environment_config. Edit these in the Task Connection settings tab. Plan Test Case parameters remain Plan-owned. Execution uses the Task environment and never falls back to global config.yaml. Lock only the executing Task environment; changes mark its retained results as needing rerun.


**Task Management**:
The global Task information page lists current Tasks across Projects and Plans, and shows planned dates in a Gantt timeline. A Task belongs to one fixed Plan; creation selects that Plan, and editing preserves its scope, environment and existing metadata. start_date and end_date are optional paired calendar dates in task_metadata. The end date is inclusive. These planned dates do not schedule execution automatically and are not execution history. Unscheduled Tasks remain visible.

Repository exclusive function page (2026-10-14): entering Test Case Repository shows its full-width list without the Project navigator. Add imports one .py, View shows metadata/defaults/source read-only, and Remove confirms the selected source version. Removing a Repository row does not change independent Plan copies, source generations, parameters, Task scope or evidence. Returning to the function resets an old preview so the list is the default view.

Automation classification (2026-10-14): literal TEST_CASE.automation is automatic or semi_automatic; omission displays Unclassified. Repository, Plan and Task display read-only badges from their independent Python source. No runtime inference or execution restrictions. Plan adaptation preserves classification; a changed classification requires a new Repository import.

2026-10-14 Repository presentation update: automation SVG icons precede case names (accessible labels and tooltips). List secondary text is source version, with no description or duplicate version column. Parameters opens read-only editable-field definitions/defaults in the right panel; View opens source in the same panel. Close returns to the full-width list. Desktop Chrome verified 1440/1920, populated/empty parameters, icon order and panel switching. Frontend syntax passed. Backend unchanged; prior 90-pass/1-skip results are historical evidence.

Repository folders (2026-10-14): create a named folder, choose it during import or move a standard case through its Folder selector. Each standard source belongs to at most one folder; existing sources remain Unfiled. Plan Add from Repository allows folder filtering and Add folder to Plan. Batch copies create/reuse a same-name root Plan folder and independent case files/settings. Existing Plan case names and older same-name Repository generations are skipped (latest first), with counts shown; existing definitions are never overwritten. Empty folders can be copied. Repository organization never synchronizes into existing Plan copies. Batch failure rolls back DB rows/folder creation and removes newly written files. Active Plan locks apply.

Repository tree update (2026-10-14): BMC is the fixed root. Selecting any directory exposes New folder; non-root directories also expose Edit/Remove. Directories support arbitrary depth, sibling-scoped case-insensitive names, stable positions, and cycle-safe reparenting. Test Case rows drag onto a directory to change ownership. Directory drops above/below a sibling reorder; center drops move into the target. The root cannot be edited, removed or dragged. Removal confirms subtree removal and moves all contained standard sources to the parent, retaining Plan copies. Existing folders are adopted under BMC and previously Unfiled sources move to BMC through an idempotent additive topology migration.

Whole-folder Plan addition retains the selected directory and every descendant (including empty directories) and their ordering. Plan paths now support arbitrary depth to preserve this user-requested structure, superseding the previous two-level restriction. Plan cycle/ownership validation, recursive impact/deletion and full-path serialization apply. Existing Plan settings/files remain independent; duplicate case names are still skipped.

2026-10-15 UI correction: Repository directories and cases now share one indented table, with BMC and child directory actions inline on each row. The separate left organization workspace is removed. Folder and case drag/drop use the table rows as targets; whole-subtree Plan addition works from directory-row buttons. Read-only Parameters/View still open on the right. Disposable browser verified root protections, inline CRUD, drag/drop, nested Plan copies and 1440/1920 desktop layout; JavaScript syntax passed. Backend unchanged.

2026-10-15 Chinese/batch update supersedes prior retained-case directory deletion: deleting a Repository directory deletes its subtree and standard cases, while independent Plan copies remain. Every UI deletion requires confirmation; confirm is left of cancel. Repository uses Chinese UI labels, no duplicate page heading, collapsible folders and mixed batch checkboxes (BMC root disabled). Selected items drag together to directories or delete as one atomic transaction. Overlapping selections are deduplicated; cycles and sibling collisions roll back.

**Plan Matrix Final Result** (2026-10-16): a per-Plan Test Case rollup across current Task memberships only. Eligible values are PASS, FAIL and Block; NR (TBD) and Running are ignored. Use UTC result_updated_at, falling back to the manual modification or execution timestamp for older results. The latest eligible result wins; equal timestamps resolve to the later displayed Task column. A missing membership renders as a dash; no eligible result yields NR. Completed counts include PASS, FAIL and Block. Manual Block preserves the current-state evidence model; no attempt or execution-history entity is introduced. Result updates persist a UTC result_updated_at timestamp. Summary and report counts expose Block separately.

**Plan BMC root**: A fixed virtual display root. Its direct folders have null parent_id and direct cases have null folder_id. Direct Python imports belong only to that Plan; Repository is unchanged. Migrated Plans preserve root cases on restart. See docs/status/2026-10-16-plan-case-operations.md.

Plan source import (2026-10-16): toolbar Import Test Case replaces folder Add Case icons and the previous Plan .py picker. Choose Repository or a source Project/Plan. The target tree is on the left and the read-only source tree on the right; drag a case or a complete folder subtree (including empty descendants) right-to-left only. Reverse drops are rejected. Repository imports inherit defaults; Plan imports inherit saved parameters and Python source. Both lists show source versions. Conflicts are preflighted atomically: matching name/source metadata identity and version offers overwrite or skip; differing identity/version offers overwrite/update, coexist or skip. Cancellation writes nothing. Coexist keeps the original name; overwrite preserves target identity, placement and Task evidence while advancing revision and marking results for retest. Source records remain untouched. See docs/status/2026-10-16-plan-source-import.md.
Test Case ordering (2026-10-19): all case-list views use folder-local natural numeric name ordering by default. A manual before/after drag stores a folder-specific custom order; folder Actions > Resorting restores automatic numbering for direct cases. Repository case-only batches and Plan case/source-case insertion support before/after anchors. Dashed allowed-area frames and active inside/upper/lower-half boxes show placement; self/cycle/locked/reverse-source targets are rejected. Source panes remain read-only. Persistent overrides are additive case_list_orders records, independent of definitions and Task evidence. See docs/status/2026-10-19-case-ordering.md.

2026-10-19: Platform now emits one complete Test log per execution, displayed in Task and attached once per case in PDF. Split legacy evidence merges on read; test .py contracts unchanged. See docs/status/2026-10-19-unified-test-log.md.


**Plan Task / Test Task** (2026-10-21): Task Type distinguishes Project/SKU-owned planning work from Plan-owned executable test work. PlanningTask has no Plan or executable scope. Test Tasks retain tasks.plan_id and live Task Test Case ownership. Task names are generated, immutable identifiers for display; all relationships and statistics use stable IDs. PlanSKU preserves SKU ownership even when Plan/Project/SKU names change. Per-Project/SKU Plan counters and per-Plan Test counters survive Task deletion and source renames. See docs/status/2026-10-21-task-types.md.


**Task Name / Unique Code** (2026-10-21 correction): Task Name must be globally unique across Projects and Plan/Test types. Candidate suffixes advance over all used/reserved normalized names. GlobalTaskName claims survive Task/Project deletion; generated names remain immutable. Stable UUIDs continue owning relationships and statistics. Earlier per-source series still advance monotonically but never bypass the global uniqueness check. See docs/status/2026-10-21-global-task-names.md.


Task-code format (2026-10-21): newly issued codes prepend the Task Type (Plan-/Test-) to the existing compact source-name prefix and three-digit suffix. Established per-source counters continue; existing issued codes stay unchanged. Global uniqueness checks apply to the complete prefixed code. See docs/status/2026-10-21-task-type-prefix.md.


**Parsed SKU Promotion** (2026-10-22): Automatic Project import first resolves all SKU specification values, then asks the user whether each parsed SKU is actually a separate Project. A promoted SKU becomes an independent no-SKU Project retaining only its already parsed column values as target specifications; retained SKUs stay under the main Project. One confirmed import may create multiple Projects atomically. Existing Projects are never overwritten or retroactively split. See docs/status/2026-10-22-project-promotion.md.


Schedule calendar (2026-10-22): Start/end remain inclusive calendar dates. Task working_days is a derived count using the shared official Taiwan office calendar (2025–2027) plus persisted workspace-wide day overrides; changing a day never shifts Task dates or changes execution evidence. Outside covered years use weekday/weekend defaults with explicit coverage warning. Both PlanningTask and executable Test Task use this calendar.

Schedule rescheduling (2026-10-22): the Task-bar schedule-edit operation requires a fresh reason, validates expected old dates, and appends the UTC date-change description and reason to existing Task Notes. This is planning information, not execution history; preserve execution results/connections/ownership and active Plan locks.

Task Owner (2026-10-22): Task.task_metadata.owner / PlanningTask.task_metadata.owner owns the assignment label. Creation defaults TBD, UI selects from the shared task_owners.json roster. Legacy missing values display TBD without rewriting stored metadata. Owner is independent of tester, stable Project/Plan/Task IDs and execution evidence.

Task schedule History (2026-10-22 user decision): supersedes appending future Schedule reasons to Notes. A successful Schedule reschedule atomically adds an immutable TaskScheduleHistory row with stable Task ID/name snapshot, UTC time, old/new dates and reason. Task Info shows the read-only list. SQLite UPDATE/DELETE triggers enforce immutability; History survives Task removal. Prior Notes remain verbatim without synthesized backfill. This is planning-change history, not retired execution attempt/run-history storage.

Edit Task History (2026-10-22): Edit Task date changes, including setting/clearing paired dates, require a new History reason and original-date expectations. They use the same atomic immutable-history helper as Schedule. Unchanged dates and unrelated metadata edits do not add History; initial New Task dates are setup rather than rescheduling.

2026-10-22 Owner History: actual Edit Task Owner changes append server-generated immutable old/new Owner text in the existing History table, transactionally with metadata; unchanged Owner adds nothing. Combined date changes still require an independent manual reason. expected_owner guards stale edits. History form sits between dates and Owner. Left navigation pointer entry/exit controls expansion; clicks retain its state.

2026-10-22 launch authorization: user says 啟動BMCAgent means loopback-only local service using bmca-runtime/server.py. Only explicit 啟動內網服務 authorizes LAN binding using separate server-lan.py and same-subnet firewall. Never automatically reuse LAN mode for ordinary launch. Current LAN setup was explicitly approved in this conversation.

2026-10-22 Task planning Status lives in task_metadata.task_status and is independent of execution results. Allowed New/On-Going/Complete/Cancel/Pending; new Tasks start New and legacy absent values display New. Status changes through Edit Task or Schedule require manual History and expected_task_status; immutable rows record old/new values with the reason transactionally. Task List Status header opens multi-select filters combined with keyword search.


2026-10-27 Not Scheduled supersedes paired dates and the undated New default: missing either start/end date forces Not Scheduled for both Task types. Single dates are accepted and validated. Completing dates defaults to New or an explicitly chosen valid status; Not Scheduled is unavailable with complete dates. Read-time effective status never backfills legacy metadata. Date/status changes retain immutable transactional History and expected-value checks. See docs/status/2026-10-27-not-scheduled.md.

2026-10-27 Task Info is a global Task-function page for both Plan and Test Tasks, using the former Plan Task layout. Schedule name links use #/tasks/info/<stable-id>. Legacy Test Task /info deep links redirect there. Test execution pages expose only connection settings, scope and execution/results, without an embedded Task Info or outer Task-function tab strip. Metadata and evidence are preserved. See docs/status/2026-10-27-task-info-unified.md.

2026-10-27 Actual Task dates and table editing: optional actual_start_date/actual_end_date live in task_metadata independently of start_date/end_date (Plan dates) and execution evidence. Actual-date changes require expected_actual_start_date/end_date plus History and append immutable text transactionally; no schema migration. Task List/My Task expose Status, Assignee and all four date cells through double-click/keyboard dialogs; removed Scope/Execution/Actions columns. Task Info/New/Edit include Actual dates. See docs/status/2026-10-27-task-cell-edit.md.

2026-10-27 paired date editing: Task table Plan/Actual date dialogs each edit their corresponding start/end pair atomically, focusing the clicked date. Browser validity plus existing backend validation enforce end >= start when both supplied; same-day and partial pairs remain allowed. See docs/status/2026-10-27-task-date-pairs.md.

2026-10-27 Days (Actual/Plan): overview actual_working_days and existing working_days derive inclusive Actual/Plan workday counts independently, using the shared official calendar and manual overrides. Incomplete pairs display — per side, with real zero preserved. No stored count or metadata backfill. See docs/status/2026-10-27-task-day-counts.md.

2026-10-27 iDesign/FW setup metadata: optional idesign={request_id,hyperlink} supports paired HTTP/HTTPS reference values and displays a Request ID hyperlink. Optional fw_package=[{component,version}] is editable only for Test Tasks, enforced by backend and UI. Both fields are independent of dates/results; expected_idesign/expected_fw_package protect stale changes, without date/status History. Task List/My Task replace Type and Project/SKU columns with iDesign ID/FW Package; Task Info adds both. See docs/status/2026-10-27-task-reference-package.md.

2026-10-27 metadata interaction correction: no pencil controls. Task Info iDesign/FW data is read-only until Edit mode; Task table metadata opens on double-click, while single-click Request ID opens its hyperlink. FW editors default BL/1BMC/BMConf, treating blank preset versions as optional placeholders, retaining custom components. Table shows 1BMC and BMConf only, complete firmware in hover text; Plan FW remains read-only. See docs/status/2026-10-27-task-meta-interaction.md.

2026-10-27 Task list Status filter retired by user decision. Task List/My Task combine Task Name, Assignee and Status within the Task column; separate Status/Assignee columns are removed. Status values/History and editing remain unchanged. See docs/status/2026-10-27-task-label-column.md.

2026-10-28 Report page presentation now reuses the current Plan overview/Task matrix renderer, replacing the former per-Task report tables. Plan remains available; existing report generation and data are unchanged. See docs/status/2026-10-28-report-plan-view.md.

2026-10-28 Report refinement: omit Create on Report and retain only Plan overview/Task matrix viewing. Plan page creation remains.


## Report selection (2026-10-28)

A Task Report represents one current Task. A Final Report merges eligible current results from selected Tasks within one Plan, following the Task matrix timestamp/tie rules across the complete Plan case scope. Selecting a Plan includes all its Tasks. Different-Plan combinations are arranged into Report and Reference areas and concatenated in area order (2026-10-28 amendment). Export works on a disposable database backup and creates no live Task or execution history.


**Reference Report** (2026-10-28): supporting current Task/Final reports placed in Reference Area during export. Group same-Plan Task selections independently within each area using Task Matrix rules; references never contribute to formal Final results. A selected Plan includes all current Tasks. Different Plans render independently; all formal report groups precede a Reference separator and all reference groups. Group order follows first appearance in each draggable list; matrix tie precedence stays in canonical Task column order. This is an export arrangement, not stored execution history or a Task type.


**Report Step Evidence** (2026-10-28): one structured Step / Criteria / Result row emitted by context['log'].step. It describes a performed action and observation; it is not an executable step definition or execution-history entity. Missing fields display —. A latest result may retain its literal description/test_method declaration for reporting. Same-Plan Final Report copies the winning membership evidence and uses that source Task's current FW Package and Assignee. DUT Configuration is a label only. See docs/agents/report-step-output.md.


**Source File Creation Time** (2026-10-28): the original .py file birth time, carried as literal TEST_CASE.created_at with a timezone and serialized as source_created_at. Display this in Repository, Plan/source import and Task scope. Preserve it when copying/adapting the same source. Unknown time is —; never infer it from import time or modification time. Source Generation remains the separate internal immutable import key used for lineage/conflicts; it is no longer the file timestamp shown to the user.


**Task Info Sections** (2026-10-28): Content owns assignment/setup/dates/references/firmware; Note & History owns notes and existing change history. Test Tasks additionally expose Scope, Connection and the reserved DUT Config section, in that order. Plan Tasks expose neither test scope nor connection/DUT sections. DUT Configuration remains a label without fill rules. This changes information presentation, not Task ownership, scope or execution semantics.

2026-10-28 workspace navigation: Plan manages Plan Tasks in the current Project; Execution opens existing Test Tasks as independent tabs through Add Task (view selection only). Test Plan definition authoring remains accessible via Test Plans in Execution. See docs/status/2026-10-28-execution-task-workspaces.md.

2026-10-29 Execution tabs: Add Task is a modal-selection button after all Task tabs; X closes only the in-memory view and preserves Task data and execution.

2026-10-29 superseding Execution scope: #/execution is global across all Projects, sharing one tab set. Add Task selects a Project to browse Test Tasks and retains pending choices across Project switches until batch addition. Active Task actions resolve its actual owning Project/Plan.

2026-10-29 Execution persistence: browser localStorage retains tab order and active Task across reload/reopen. X removes a saved view; missing/deleted Tasks are pruned. Supersedes in-memory-only notes.

2026-10-29 Plan navigation correction: the Plan entry opens the Project Plan overview list at #/project/<id>/plans. Supersedes earlier Plan Task management routing for this entry.

2026-10-29 Plan authoring: Project Plan list has expandable Plan names opening the Case editor inline, one active Plan at a time. Authoring list no longer displays statistics or Task matrices; reports retain their existing matrices.

2026-10-29 Plan tabs supersede expandable list: Project Plans are tabs beside the Plan heading. Add Plan stays last and invokes existing creation. Drag order is a browser preference per Project, without changing Report order. New Plans auto-select their tab.

2026-10-29 Execution tab ordering: Task tabs drag before/after peers or to the end before Add Task. Ordered IDs persist in the existing browser tab preference; active Task and editor drafts remain unchanged during reorder.

2026-10-29 Plan import UI: source selection and the two-pane import operation occur in dialogs. The Plan page stays behind the modal; Close/Escape returns to the same Plan tab, with closing blocked during active imports.

2026-10-29 Import batch selection: checked source Cases drag as one group, using case_ids in the existing import-cases API. Batch validation, conflicts and commit/rollback are atomic. Single Case and folder drag remain compatible.

2026-10-29 Case actions: Plan and Repository tables omit Actions columns; right-click Case/folder rows for text menu operations. Context Menu key/Shift+F10 works, roots cannot be deleted, and existing locks/confirmations remain. Parameters column is retained.

2026-10-29 Selection/Schedule update: Case and folder checkboxes are always visible in Plan/Repository/import sources, roots excluded. Mixed selected items support transactional drag move/import with subtree deduplication. Repository batch-mode entry removed. Schedule calendar ends on month-end three calendar months after the latest Task Plan End Date.

2026-10-29 Selection headers: Plan, Repository and import target/source lists offer select-all/unselect with mixed state, including collapsed/filtered items except BMC roots. Multi-selection context menus provide confirmed Delete selected items. Plan mixed deletion is atomic across files, records and current Task evidence.

2026-10-29 Folder selection: Plan, Repository and Import folders cascade checks through the subtree; ancestors are checked/mixed/clear from descendants. Only full folders enter whole-folder selection payloads. Folder row backgrounds are transparent; drag feedback remains.

2026-10-29 Hierarchy layout: Plan/Repository/Import Case and folder checkboxes share a fixed checkbox origin at each depth, with 18px indent per level.

2026-10-29 Folder expansion: collapsed IDs persist in browser localStorage separately per Plan, Repository and import source. Main Plan and its import target share the Plan preference; source preferences are independent.

2026-10-29 Plan selection: active Plan tab is a per-Project browser preference restored on reload/reopen. Newly created Plans become active; missing/deleted saved Plans fall back to an existing ordered tab.


2026-10-29 latest user decision: cancel independent Viewer/Editor windows entirely; right-side main-page panels only. No detach button.
2026-10-29 latest: normal Plan Case list uses Task List bottom gap (24px); Case clicks only update already-open Viewer/Editor, never open them implicitly.
2026-10-29 latest Plan layout: title/Project subtitle, Plan tabs, toolbar (search/Import/Rename/Delete), Case list.

2026-10-30: Read docs/status/2026-10-30-handoff.md. Service started; source updates published to baga0607-cpu/bmcauto main (d3cb74a). Use the publication checkout, never retired origin. Viewer/Editor only dock on the right. Runtime assets and existing binary fixture changes remain local.
