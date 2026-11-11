# Task creation drawer, soft deletion and compact fields — 2026-11-10

This update extends `2026-11-10-task-info-drawer.md`. New Task opens the same right drawer with an Overview creation form. Task Type, Project, SKU and Plan continue using existing name preview and validation. Successful creation opens the saved Task with its five Test tabs or two Plan tabs. No formal Tasks were created during verification.

Existing Task drawers have a top Delete Task button. Its modal requires a nonblank reason of at most 4000 characters. DELETE now atomically appends an immutable Note record (`Status: previous → Deleted` and reason) and stores task_status=Deleted; it does not remove Task, scope, environment, result or log rows. Plan execution locks remain enforced. Retries after successful deletion are idempotent. Deleted Tasks cannot be edited, rescheduled, assigned scope/settings or executed. Ordinary task/project lists and new-report selections exclude them. `GET /api/tasks?status=Deleted` provides explicit filtered records for the future filter UI; no filter/restore UI is added now. Existing history endpoint/schema remains compatible. Parent Project/Plan removal rules are outside this Task deletion change.

Overview and Connection use one label/field pair per row. FW Package rows retain paired Component/Version inputs, with their names as placeholders and accessible labels. Firmware-only edits now participate in drawer dirty detection. Scope stays a table. DUT Config remains pending field definition. Note records are newest first and always expanded, without a collapse row.

## Verification and deployment

- Isolated Python: `python -m unittest test_task_soft_delete test_task_management test_task_types test_task_schedule test_task_status test_task_owner_history test_task_environment test_task_actual_dates test_task_reference_package`: 78 passed. Separate `test_report_exports`: 13 passed.
- Tests cover both Task types, missing/blank/oversized reasons, atomic Note failure rollback, active peer locks, retained result/log rows, hidden default lists, explicit Deleted query, immutable prior records, idempotent retry, and rejected edits/execution.
- Node syntax checks and `web_ui/tests/task_management_list.test.cjs` passed.
- Disposable Chrome on port 5017: existing drawer regression script passed; `task-drawer-create-delete.cjs` verified Test/Plan creation, single-row layout, FW-only save, seven connection fields, deletion cancel, whitespace reason rejection, soft deletion and preserved Note. No browser page errors. Desktop screenshots inspected.
- Test workspace/main/temp directories: `bmca-runtime/verification/drawer-isolated`. No physical BMC/DUT tests were run.
- Formal SQLite online backup: `bmca-runtime/backups/2026-11-10-task-soft-delete/testcase_meta-before.db`. Integrity check ok; no foreign-key violations.
- Formal service restarted only after confirming zero active Tasks, preserving localhost-only binding (127.0.0.1:5000). Launcher PID recorded in `bmca-runtime/server.pid`. Formal read-only Chrome verification passed with non-GET API requests blocked.
- Before/after full-row comparisons of tasks, planning_tasks, task_testcases and task_schedule_history are unchanged. Formal DB integrity remains ok with zero foreign-key violations. No schema migration or GitHub publication.

Runtime browser checks and screenshots live under `bmca-runtime/verification/`. Existing browser tabs need a reload. The disposable preview service is stopped after checks.
