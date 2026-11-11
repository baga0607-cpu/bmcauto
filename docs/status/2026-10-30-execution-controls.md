# Execution controls and dialogs — 2026-10-30

## User-approved behavior
- Execution starts with the persisted, draggable Task tabs; remove the visible page heading, Test Plans link, duplicate Task name/Task Info link, summary and instructional rows, and right-side evidence workspace.
- Keep the Task toolbar above an independently scrolling, full-width case table. The list ends 24px above the viewport bottom.
- Toolbar: automation filter (All / Fully automatic / Semi-automatic + Manual), select all / clear selection, Run Selected Cases, stop, Scope, Connection. Batch selection and run apply to the filtered visible cases; hidden selections stay retained. Unclassified remains accessible under All and is not inferred.
- Row order: execution checkbox, automation icon/name, result button (NR/PASS/FAIL/Block; Running while active), Parameters, Run, Stop, Log.
- Any active Task disables execution selection and new starts across the Execution workspace. Selection writes also lock controls until persistence completes. Poll current Task/global activity every two seconds; keep one-window monitoring and reconnect support.
- Scope, Connection, Result Annotation, Parameters and Log use native dialogs. Capture Task/Plan/Case IDs when opening; protect dirty drafts and saves against close/navigation. Scope removal confirms evidence removal.
- Parameters continue editing the Plan-owned definition, with the original source and settings_revision, not a Task override. Running case parameters remain locked. The dialog states that all Tasks using this Plan case share the saved values.
- Row Stop stops only the bound current case, retains the Task execution token/queue/selection lock and continues with the next selected case after worker cleanup. Toolbar Stop stops the entire Task and remaining queue. This supersedes the initial Task-wide row stop behavior.
- Log dialogs retain live logs and operator input. An input request opens the current case log when no dialog is open; Response required in the toolbar reopens it. Log identity remains stable across monitoring refreshes.

## Implementation
- web_ui/static/workbench.js: Execution layout, controls, bound dialogs, selection persistence, live status/log synchronization.
- web_ui/static/workbench.css: compact toolbar/table, viewport scroll region, dialogs using existing light/dark tokens.
- web_ui/tests/execution_controls.test.cjs: new behavior regression coverage with simulated APIs/EventSource only.
- web_ui/tests/execution_workspace.test.cjs: adapt existing evidence assertions to Log dialogs; retain tab, ownership, Plan and Repository regression flows.

## Validation
- PASS: JavaScript syntax check.
- PASS: execution_controls.test.cjs — filters, visible selection/run scope, global lock/unlock, single/batch start, stop, operator input, Task ownership, parameter revision conflict, draft cancellation, dialogs, sticky toolbar and desktop layouts.
- PASS: execution_workspace.test.cjs — existing Execution/Plan/Repository regression flows.
- PASS: test_task_environment.py — 5 tests, isolated workspace/main_program/TEMP/TMP.
- test_manual_task_results.py — 10 passed, 2 failed. The unchanged legacy assertions expect separate console/API log fields and the older relative-order placement. Current backend combines logs and uses the newer ordering model. These backend files were not modified by this UI change; failures remain recorded, not hidden or rewritten.
- Formal read-only check: HTTP 200; 4 Test Tasks; active Tasks = 0; SQLite integrity_check = ok; foreign_key_check = 0.
- Formal read-only browser: new toolbar and 6 rows rendered; no page errors. Desktop 1440x900 / 1920x900, light/dark checked. Theme transitions require 200ms before capturing final colors.
- No physical DUT run, no formal data mutation, no backend restart, no publication. Refresh the browser to load the updated static assets.
- Existing binary fixture changes and runtime generations were retained.

## Local evidence
Runtime verification directory: bmca-runtime/verification/execution-20261030 (read-only health/browser scripts and formal screenshots). Simulated visual artifacts: .impeccable/execution-20261030. Keep these local.

## Follow-up: separate Case Stop from Task Stop
- Added POST /api/tasks/<task_id>/testcases/<tc_id>/execution/stop, bound to the execution token and current session ID. Reject stale/cross-case/cross-Task requests so a delayed click cannot interrupt the next worker.
- Case-only interruption retains NR (TBD) and its stopped Log. Task stop still wins if requested during a case-only stop. Errors still terminate execution.
- Execution GET exposes closed case IDs for the current token. Resume monitoring skips those cases, including stopped NR cases, instead of rerunning them.
- PASS: 4 new offline worker tests (case continuation, Task cancellation, stale/cross-Task requests, Task-stop precedence); 13 environment/log integration tests; updated frontend controls regression including natural continuation and reconnect. No physical DUT execution.
- Formal service restarted after active Tasks = 0 and verified SQLite backup at bmca-runtime/verification/execution-20261030/before-case-stop.db; HTTP 200 after restart.

## Parameters lock and Log export
- While any Task is executing, every Execution Parameters button is disabled. An already-open parameter dialog is also disabled by activity polling, preserving its draft; saving rechecks current activity before writing. Plan ownership/revision checks remain unchanged.
- Log dialog header places Export directly left of Close. Downloads the displayed case’s current test log as UTF-8 text, using Task__Case__test.log with safe filenames. Live execution exports the current log snapshot; empty logs cannot be exported.
- Frontend regression covers global Parameters locking/unlocking, already-open editor locking, Export placement, filename and exact downloaded contents.
- Validation: JavaScript syntax and the updated controls regression passed. Sandbox Chrome canceled file downloads; the same isolated mock-only test passed outside the sandbox, including the downloaded file content assertion. Frontend-only update; no service restart or formal data changes.

## Combined icon controls
- Toolbar uses icon-only Select All, Clear Selection, Run/Stop, Scope and Connection. Its single Run/Stop control switches from play to Task-wide stop while the selected Task executes.
- Each row uses icon-only Parameters and one Run/Stop control; only the running row switches to case-only stop. Other rows cannot start while execution is active. The table now has six columns.
- All icon buttons have native tooltips and accessible labels. Log and result buttons remain text. Existing selection/parameter locks and stop scope are preserved.
- Validation: controls regression covers one Run/Stop per toolbar/row, state switching, SVG-only controls with accessible names, existing execution behavior and desktop light/dark layout. Frontend-only; refresh to load.

- Latest presentation adjustment: remove the visible Execution case-table header row. Keep the six data columns, their widths, toolbar and accessible action labels.

- Execution rows classified automatic hide Parameters entirely, retaining the empty column for aligned Run/Log controls. Semi-automatic/manual/unclassified rows retain the existing parameter control and execution locks. Plan parameter ownership/editing remains unchanged.

- Row actions now follow Status / Run–Stop / Log / Parameters. Status buttons use a fixed 80px width accommodating Running, 700 font weight and horizontal/vertical centering; automatic cases still omit Parameters.

- Log now uses the same icon-button component as Run/Stop and Parameters: 34×34px button, 18×18px SVG, with Log tooltip/accessibility label. Dialog and Export behavior are unchanged.

- Run triangles and Stop squares are solid (fill: currentColor; no stroke) in both toolbar and case rows; existing dimensions and state colors remain.

- Rerun confirmation removed by user request. Both single-case and selected-case runs start directly even when current results exist, using the existing latest-result replacement behavior.

- Scope dialog spacing: title top inset reduced from 36px to 18px; Close shares the title top. Task-name-to-select, list-to-save and save-to-bottom gaps are 18px. Select-to-list remains 12px. Scoped styles do not affect other dialogs. Browser bounding-box assertions and controls regression passed.
