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
The unique membership of a Plan Test Case in a Task, storing its current ordering, selection, latest status and latest result/log references. Its status is one of `TBD`, `Running`, `Passed`, or `Failed`. Removing the membership or deleting its Plan Test Case permanently removes its latest evidence from current reports.
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
