# BMCAgent workbench UI — 2026-10-07

The user approved an English, operable web UI and selected the file navigator workbench. Complete removal of step/block editing and execution supersedes the earlier compatibility decision.

## Delivered workflow

- Global navigation: Projects, Test Case Repository, Settings.
- Project → Plan → Task tree and breadcrumbs maintain ownership and location.
- Repository imports one `.py` per standard Test Case; timestamped versions can be inspected and downloaded.
- Plan owns copied Python files and independently saved parameters. Python adaptations and declared fields are edited in the Plan. Running cases are locked; other cases remain editable.
- Plan folders support creation, rename, parent changes, deletion with impact confirmation, and case placement.
- Task owns scope, execution selection, current result/log evidence and assignment information. Case settings are not editable in Task.
- Live execution supports indefinite operator input, stop requests, and reconnecting to the current worker after browser refresh.
- Plan changes preserve evidence, mark affected Task cases for rerun, and show the notice in UI and PDF.
- Current Task PDF reports remain available. Test Plan document and Final Report consolidation formats are still deferred.

## Removed paths

The old dashboard/workspace duplication, inactive modules, fake login/user menu, Golden publish/fork flow and builder are removed. `/api/steps`, `/builder`, Golden/fork/move step APIs, step JSON imports and unscoped execution are unavailable. Project reads no longer import executable legacy definitions. The CLI entry now starts the Task-based local service.

Historical step implementation and obsolete UI/Golden test contracts are preserved under `docs/archive/ui-redesign-20261007/`, outside the active application. Existing DB records and definition files remain intact. Retired step cases are visible with a retirement notice; their evidence remains readable and execution is rejected before clearing results.

## Verification

Isolated Flask QA service: `127.0.0.1:5127`, independent database and script root under `D:/bmc_auto_test/bmca-runtime/verification/ui-preview-*`. Its synthetic client cannot contact a DUT.

Python: 73 tests, 72 passed, 1 skipped because the historical deployment fixture is absent. The former UI/source-string and Golden contracts were archived rather than claimed as current tests. Single-file integration, live Task state, scope, lock, migration, rollback, manual results and current reports remain tested.

Chrome end-to-end: Project/Plan creation, Repository .py import, case editing, Task scope, offline runs, operator input, report download, retest notice with preserved logs, folder rename/placement, result and bug annotations, refresh/reconnect, standard Python download, and mobile tree navigation. No page errors. Light/dark screenshots cover desktop 1440px and mobile 390px. JavaScript syntax checks passed; Impeccable detector returned no findings.

Evidence: `D:/bmc_auto_test/bmca-runtime/verification/workbench-browser.json`, `workbench-confirm.json`, `ui-python-release.log`, `ui-console-tests.log`, `ui-report.pdf` and `.impeccable/review/`.

Source and consistent DB backup: `D:/bmc_auto_test/bmca-runtime/backups/ui-redesign-20261007/`. Production data will be compared against the backup after service restart. Review, durable design documentation and deployment verification are recorded at the end of this file after completion.

## Local delivery

Finish review: disposition `ship`; the selection-coherence finding is resolved. Plan/Task rows, aria-pressed and pane titles match after navigation, selection changes and refresh. All seven desktop/mobile/light/dark captures were confirmed after the background transition settled. Evidence: `.impeccable/review/finish-review.md` and `workbench-selection.json`.

The managed local service was restarted on 2026-10-07 at `http://127.0.0.1:5000`. Browser smoke passed for Projects and Repository without page errors; `/workbench.css`, `/workbench.js`, Project and Repository APIs returned 200; step and builder entrances returned 404. Exact production rows match the pre-change backup; SQLite integrity and foreign-key checks pass. Downloaded PDF includes the retest warning. No DUT was contacted. Changes are local and have not been committed or pushed.

Durable visual decisions are recorded in `DESIGN.md` and `.impeccable/design.json`. Test Plan document format and Final Report consolidation remain for the agreed later report-design discussion.
