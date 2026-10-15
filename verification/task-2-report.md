# Task 2 frontend integration report

## Scope

Integrated persisted PlanFolder identities and current Task state in `index.html`, `builder.html`, and `plan_workspace_interactions.js`. Existing style and navigation are retained. Classic Plan navigation now routes to the current folder workspace; Task execution remains available through Execution Detail.

- All origins share root/child create, rename, move, reorder and delete controls, including empty folders. Folder and testcase drag destinations use stable IDs. Cross-parent/folder drops make one domain move request; same-folder drags reorder the complete sibling collection.
- New Plans support empty structure, partial Golden template selection and custom root/child paths. Partial selection displays an indeterminate minus. Template creation never copies testcases.
- Golden copy uses stable source testcase IDs and default equivalent paths, a named destination selector or a new path. Failed/duplicate items remain selected for retry.
- Import review retains invalid and duplicate items as editable JSON; success removes only successful items. `FOLDER_PATH`, legacy `CATEGORY`, and default Custom are supported. Builder and Plan export preserve folder paths.
- Deletes preview server impact, gate required acknowledgment, and use atomic domain deletion. Task scope add/remove replaces membership while retaining existing members and their current evidence. Successful mutations reload authoritative state.
- Task displays use live names/folder paths and only TBD/Running/Passed/Failed. Run History and old result-file restoration are removed. Current logs come from TaskTestCase fields. Summary report reads each current Task summary and links its current PDF.
- Execution uses start/token/run/finish/stop lifecycle. The runner owns persistence; the browser does not overwrite logs with a second empty result. Definitions are explicitly loaded with `include_steps=true` under the execution lock, overriding stale scope steps.
- Controls use Plan locks rather than project-wide locks. Stop remains available from active persisted Task state. Viewing and reconnecting are read-only, including legitimate between-worker gaps.

## Approved backend integration fixes

Root approved two small backend additions, implemented in `plan_state.py` with focused tests:

1. A regular folder containing empty descendant folders requires `I understand`, even with zero testcases.
2. `GET /api/tasks/<id>/execution` returns operational `{task_id, execution_active, execution_token, session_id}`. It requires an existing Task and owning Plan, is read-only, and returns no token when inactive. Summary/results/PDF do not expose the token. A new tab can recover stop controls after the starting tab closes.

## Verification

- Initial Node baseline: 26 tests. Initial new contracts failed for missing persisted empty folders, category-based destination payloads, stale Task identity and missing partial-template selection.
- Final Node: **42/42**, evidence `verification/task2-node-tests.txt`.
- Full isolated Python discovery: **116/116 in 18.523 seconds**, evidence `verification/task2-python-tests.txt`.
- Both HTML inline scripts parsed using Node `vm.Script`; Python compile passed for changed Python files; `git diff --check` passed.
- Python verification explicitly used `verification/task1-workspace`, `verification/browser-main` and the pristine `verification/baseline-workspace/testcase_meta.db` lifecycle source. No active production database or real BMC was used.
- Focused red/green coverage additionally includes recovery without history, read-only viewing between workers, acknowledgment, uniform locked folder controls, atomic moves, and fresh executable definitions.

## Browser selectors / workflows

| Workflow | Entry and controls |
| --- | --- |
| New Plan | Existing New Plan button; `#new-plan-dialog`, `#new-plan-name`, `[data-template-id]`, `[data-folder-path]`, `#new-plan-folders`, `#new-plan-submit`. Partial root is indeterminate; selecting one child includes its path only. |
| Folder create/rename/move | Plan Folders header plus or row title `Add child folder`, `Rename folder`, `Move folder`; `#folder-edit-dialog`, `#folder-name`, `#folder-parent` (named roots and Root level), `#folder-submit`, `#folder-error`. Errors retain input. |
| Folder/testcase delete | Row `Delete folder` or testcase Remove; `#impact-dialog`, `#impact-ack`, `#impact-delete`, `#impact-cancel`. Required Delete is disabled until acknowledged. |
| Folder/testcase drag | `[data-plan-drop-key="folder:<id>"]`; testcase `[data-plan-tc-index]` drag handle. Same-folder row drop reorders; cross-folder drop appends via one atomic move. |
| Move selected cases | Existing testcase row action menu -> Move; `#plan-move-dialog`, `#plan-move-search`, destination buttons. Stable selected destination survives folder rename/reload; server conflict preserves selection/input. |
| Golden copy | Add Test Case -> Golden drawer -> select -> Add; `#copy-destination-dialog`, `#copy-folder`, `#copy-path`, `#copy-confirm`. Empty selector means source paths. |
| Import/retry | Add Test Case -> Import; `#import-file`, then `#import-review`, `[data-import-index]`, `#import-submit`, `#import-summary`. Correct retained JSON then retry. |
| Task scope | Task Detail -> Add TCs from Plan; `#add-from-plan-list`, `#add-from-plan-select-all`; Remove deletes membership/result only. |
| Execution | Task Detail -> Execution; `#execution-run-btn` shows Run or Stop from current Task state. Select cases, run; selected prior results clear, unselected results remain. Reload/new tab recovers the active stream and Stop token. |
| Latest logs | Task testcase Log -> `#current-log-dialog`; current normal/API logs only. |
| Reports | Task Export PDF Report; Plan Generate Summary Report reads current per-Task summaries, not historical files. |

## Review boundaries

Root is performing real Chrome verification against the disposable offline fixture. Root already reported folder CRUD/persistence, partial template selection and retryable import passing. Execution was retested after the missing-step definition fix. Independent review and final browser evidence are owned by root.

A viewing tab does not resume unstarted selected testcases or automatically finish an orphaned execution. It exposes explicit Stop; the original active coordinator finishes normally. This avoids a second tab ending a legitimate gap between workers. A dropped execution stream surfaces an operational error and preserves the server lock until completion/recovery/Stop.

No merge, deployment, push, or main-workspace writes were performed.

## Browser verification follow-up: latest failure details

The real Chrome selected-rerun check passed status overwrite, preservation of the unselected Passed testcase and timestamp, and Plan unlock. It exposed that SSE-only failure messages were missing from the saved current log/result.

With root authorization, `app.py` now persists the current session's structured step events and error messages in `result.steps` and `result.errors`, and appends actual step/connection errors to the current log. It does not read prior sessions or old files. A focused offline regression failed before the fix and now verifies step-error persistence, connection-error persistence, and replacement of the old error on rerun.

Final full isolated discovery after this fix: **117/117 in 21.179 seconds**. Node remains **42/42**; Python compilation and diff checks pass. The source/test fix is a separate follow-up commit after the UI integration commit `5f4ffcd`.

## Independent review fix: executable-definition failures

Addressed the Important finding in `verification/task-2-review.md`. After lifecycle start, an empty, malformed-step-list or missing per-case executable definition now writes a current Failed result through `/api/tasks/<id>/execution/result` using the current token. The result/log contains an actionable definition error and execution timestamp. The UI refreshes current state and continues the next selected testcase. No stale executable steps or new Task membership is substituted.

A result-write rejection or transport error stops remaining execution and surfaces the operational error through `runPlan`; it does not fabricate a saved Failed result. A system-wide definition fetch failure similarly stops without inventing individual testcase outcomes. Normal lifecycle cleanup still runs.

Actual `runPlan` and `_executeTCs` function tests reproduce lifecycle start/reset, empty and missing definitions, remaining valid execution, unselected evidence retention, result-write rejection, and definition-fetch outage. Three new tests failed before the fix (empty/missing rows stayed TBD and no failure result was written); all targeted tests now pass.

- Red evidence: `verification/task2-review-definition-red.txt`
- Targeted green: **20/20**, `verification/task2-review-definition-green.txt`
- Complete Node suite: **46/46**, `verification/task2-node-tests.txt`
- Relevant isolated Python API/frontend/layout contracts: **95/95**, `verification/task2-review-definition-python.txt`
- Both inline HTML scripts parse; `git diff --check` passes.

Only frontend source, its interaction tests and this report changed for this review fix. The prior full backend discovery remains 117/117; no backend code changed in this round.
