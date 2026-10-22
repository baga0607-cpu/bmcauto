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
