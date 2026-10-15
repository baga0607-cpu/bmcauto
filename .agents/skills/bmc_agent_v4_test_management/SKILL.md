---
name: bmc_agent_v4_test_management
description: Use when modifying BMC Agent v4 Plan folders, TC import/export, Task scope, manual results, execution logs, reports, or the test-management UI.
---

# BMC Agent v4 Test Management

Last updated: 2026-10-07

2026-10-07 amendment: read `docs/superpowers/specs/2026-10-07-single-file-case-design.md` and `docs/status/2026-10-07-workbench-ui.md`. The user's later decision completely retires step editing and execution, superseding earlier compatibility. Existing records and evidence remain readable. `web_ui/single_case.py` owns Repository and independent Plan copies. Plan-specific adaptations do not bump source generations. Only the Running TC's Python source/settings are locked; structural Plan changes retain the Plan lock. Tasks execute server-resolved Plan definitions and cannot override presets.

## Read first

Paths below are relative to the repository root.

1. Read `CONTEXT.md` for domain vocabulary.
2. Read `docs/superpowers/specs/2026-09-30-plan-task-workspace-current-design.md` for the consolidated approved behavior and links to the original specification.
3. Read `docs/status/2026-09-30-formal-release.md` before deployment or database migration. Read `docs/status/bmc_agent_v4_next_plan.md` for current next steps.

## Architecture and invariants

- `web_ui/models.py` defines PlanFolder, TestCase, Task and TaskTestCase. `web_ui/plan_state.py` owns transactional folder, scope, ordering, deletion, migration and lock rules.
- A Plan owns persistent folders, including empty folders. Depth is limited to root and child. The Repository replaces the former Golden workflow.
- A Task references live test cases in its own Plan. Each membership retains only its latest status, result and execution evidence. Status is TBD, Running, Passed or Failed.
- Deleting a Plan TC removes all of its Task memberships and current evidence. Retain the Task itself. Current reports use current scope. Previously saved reports and external backups are independent artifacts.
- The current-state model supersedes historical Snapshot, Run History and TaskExecutionAttempt designs. Keep execution history out of task_metadata; that field contains Task setup information only.
- Manual overrides support TBD, Passed and Failed, including never-run TCs. Preserve existing execution logs and mark the latest manual change with its reason/time. Never invent execution logs for never-run TCs.
- Active execution locks structural changes, scope changes and manual overrides. Partial reruns update only selected memberships.
- Import/export carries full FOLDER_PATH within the target Plan. Resolve or create both path segments. Same-name TC collisions require user correction; exporting TCs does not export empty folders.

## UI responsibilities

- Global navigation is Projects, Task management and Test Case Repository. Connection settings belong to each Task. The file navigator follows Project → Plan → Task.
- Plan has Test Cases, Folders, Tasks and Reports sections. The selected Test Case opens editable declared parameters and progressive Python adaptation. Task has Scope, Execution & results, Connection settings and assignment information; no case settings editor.
- Source selection and execution checkboxes have independent purposes. The highlighted source/evidence row must always match the right pane.
- Keep light/dark themes, desktop navigation, visible focus, loading, errors, empty states, retest notices and active execution locks readable.
- Use English UI and Task terminology. Do not reintroduce placeholder modules, a builder, Golden publish/fork, or unscoped execution.

## Verification workflow

1. Identify the checkout, service port, database path and script root before changes. Formal and preview environments use independent databases.
2. Preserve existing work. Run migrations and mutating tests against database/script copies; never replace formal data with preview data.
3. Run relevant Python tests in `web_ui/tests` with BMC_WEB_UI_WORKSPACE_DIR and BMC_MAIN_PROGRAM_DIR pointing to disposable copies. Set TEMP/TMP to a writable isolated directory on Windows. Check `workbench.js` syntax with Node and verify affected flows in a disposable browser/service. Old UI source-string tests are archived and do not describe the replacement UI.
4. Verify affected browser workflows, API/DB ownership and ordering, SQLite integrity and foreign keys. Include destructive-operation rollback and Plan locks when those paths change.
5. Record commands, environment, results and limits under `docs/status/`. Refresh the current status and next-step pointers. Describe saved historical test counts as historical evidence, not a new run.

2026-10-14 amendment: Task.environment_config owns DUT/BMC/Console connections; /api/tasks/<task_id>/settings is the sole Settings UI endpoint. No global config.yaml fallback. The executing Task connection settings are locked, peer Task settings remain independently editable. Environment changes preserve evidence and mark only that Task results for rerun. See docs/status/2026-10-14-task-connection-settings.md.

2026-10-14 desktop scope: mobile support is deferred by the user. Review and implement desktop UI only. Existing mobile CSS and historical mobile test evidence are not a current support promise. See docs/status/2026-10-14-desktop-layout-review.md.

2026-10-14 Task management: global #/tasks opens Task information with list/Gantt and CRUD. GET /api/tasks returns safe overview records. Planned daily start_date/end_date live in Task.task_metadata; paired dates must be valid and end>=start. Merge setup edits to preserve other Task fields. No automatic execution scheduling or Task Plan transfer. Existing Plan execution locks apply. See docs/status/2026-10-14-task-management.md.

Repository page amendment: no Project sidebar in #/repository; default is list with Add/View/Remove. DELETE /api/repository/testcases/<id> requires confirm:true and only removes the standard source row. Plan files/settings/source_version/Task evidence remain independent. See docs/status/2026-10-14-repository-page.md.

Automation classification (2026-10-14): literal TEST_CASE.automation is automatic or semi_automatic; omission displays Unclassified. Repository, Plan and Task display read-only badges from their independent Python source. No runtime inference or execution restrictions. Plan adaptation preserves classification; a changed classification requires a new Repository import.

Repository folders (2026-10-14): create a named folder, choose it during import or move a standard case through its Folder selector. Each standard source belongs to at most one folder; existing sources remain Unfiled. Plan Add from Repository allows folder filtering and Add folder to Plan. Batch copies create/reuse a same-name root Plan folder and independent case files/settings. Existing Plan case names and older same-name Repository generations are skipped (latest first), with counts shown; existing definitions are never overwritten. Empty folders can be copied. Repository organization never synchronizes into existing Plan copies. Batch failure rolls back DB rows/folder creation and removes newly written files. Active Plan locks apply.

Repository tree update (2026-10-14): BMC is the fixed root. Selecting any directory exposes New folder; non-root directories also expose Edit/Remove. Directories support arbitrary depth, sibling-scoped case-insensitive names, stable positions, and cycle-safe reparenting. Test Case rows drag onto a directory to change ownership. Directory drops above/below a sibling reorder; center drops move into the target. The root cannot be edited, removed or dragged. Removal confirms subtree removal and moves all contained standard sources to the parent, retaining Plan copies. Existing folders are adopted under BMC and previously Unfiled sources move to BMC through an idempotent additive topology migration.

Whole-folder Plan addition retains the selected directory and every descendant (including empty directories) and their ordering. Plan paths now support arbitrary depth to preserve this user-requested structure, superseding the previous two-level restriction. Plan cycle/ownership validation, recursive impact/deletion and full-path serialization apply. Existing Plan settings/files remain independent; duplicate case names are still skipped.

2026-10-15 Chinese/batch update supersedes prior retained-case directory deletion: deleting a Repository directory deletes its subtree and standard cases, while independent Plan copies remain. Every UI deletion requires confirmation; confirm is left of cancel. Repository uses Chinese UI labels, no duplicate page heading, collapsible folders and mixed batch checkboxes (BMC root disabled). Selected items drag together to directories or delete as one atomic transaction. Overlapping selections are deduplicated; cycles and sibling collisions roll back.
