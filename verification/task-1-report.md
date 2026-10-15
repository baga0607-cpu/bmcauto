# Task 1 backend implementation report

## Scope and isolation

Implemented only backend models, `plan_state.py`, Flask integration/runner, PDF current-state reads, and Python tests. Worktree: `D:/Pytest/_redfish/plan-folder-current-state`. No merge, push, deployment, or main-workspace database access.

All verification startup migrations use `verification/task1-workspace/testcase_meta.db`, copied from `verification/baseline-workspace/testcase_meta.db`. Lifecycle server overrides its workspace and main-program paths to its own shadow copy. The pristine baseline source SHA256 remained `54B3FD8E1C5D62265C14DFE04104ADE68FBC813E31157E90577EB351C12456D6`.

The inherited baseline lifecycle had contaminated the worktree's original database copy with three generated Golden cases (20 instead of 17). The new lifecycle source override avoids that copy. Production-copy startup verification checks 17 testcases and identical IDs/placement across two complete startups.

## Implementation

- Persisted `PlanFolder` identity, parent, normalized sibling namespace (including root), position; testcase folder placement.
- Domain operations use `BEGIN IMMEDIATE` before lock validation. Legacy mutating handlers share the request's write reservation. Locks are persisted on Task and checked at Plan ownership boundaries; source/destination copy/publish locks are included.
- Migration converts category ordering, categories, empty Custom children, redirects unclassifiable placement to Custom with a technical log, validates ownership/depth/names/counts and rolls back on integrity failure. Startup fails on migration failure. Attempt model, table creation, route, serialization, result history writing and historical result reads are removed.
- Same-Plan Task membership is unique; replacing scope retains current results for retained members and deletes removed rows. Summary resolves current testcase identity and folder placement.
- Four canonical statuses; selected rerun clears only selected latest result/log fields. Result writes reject non-members, unselected members, inactive and stale execution tokens. Stop/finish normalize unfinished Running rows before unlocking.
- Existing runner receives Task identity/token, marks the selected row Running and persists a latest result/log after the testcase completes, including connection/setup errors. Worker setup failures have a recovery wrapper. Stale session IDs cannot be reused.
- Deletion previews exact impact, enforces confirmation/acknowledgement, stages executable directories privately, cascades memberships, retains empty Tasks, restores on flush/commit failure. Restoration retries an atomic filesystem replacement if the high-level move fails. Unrecoverable filesystem restoration keeps private recovery data and returns a diagnostic error.
- PDF queries live folder paths/current Task metadata/current memberships and embeds only logs held on current TaskTestCase records. It never searches historical log files.
- `BMC_MAIN_PROGRAM_DIR` and `BMC_LIFECYCLE_SOURCE_DB` allow safe executable/configuration and lifecycle-source isolation.

## Exact frontend API contracts

All invalid input returns 400, missing identities/destinations 404, normalized conflicts/Plan execution locks/stale tokens 409, internal failures 500. Successful single testcase legacy import/copy/publish remains 200.

- `GET /api/plans/<plan_id>/folders`: bare array, each `{id, plan_id, parent_id, name, position, folder_path}`. Roots have `parent_id: null`; path is `Root` or `Root/Child`.
- `POST /api/plans/<plan_id>/folders`: `{name, parent_id?}`; 201 folder record.
- `PATCH /api/folders/<id>`: `{name?, parent_id?}`; 200 updated record. Explicit null reparents to root.
- `POST /api/plans/<id>/folders/reorder`: `{parent_id: null|id, folder_ids:[...]}`. Must contain the complete sibling collection exactly once; 200 `{status:'ok'}`.
- `GET /api/folders/<id>/impact` and `GET /api/testcases/<id>/impact`: `{name,names,descendant_folder_count,testcase_count,affected_task_count,task_testcase_count,requires_acknowledgement}`.
- `DELETE /api/folders/<id>` or `DELETE /api/testcases/<id>`: `{confirm:true, acknowledgement:true}`. Acknowledgement is required only when impact says so. Response `{status:'ok', impact:{...}}`.
- Legacy `POST /api/delete_tc`: `{plan_id,tcs:[{id}|{testcase}],confirm:true,acknowledgement:true}` uses the same staging/confirmation rules.
- `POST /api/create_plan`: existing `{project,plan_name}` plus `folder_paths:['Root','Root/Child']` and `template_paths:[...]` (alias `golden_folder_paths`). Selecting a Golden root includes its current children. Custom/template normalized paths merge. No testcase copying occurs.
- `POST /api/import_tc` preserves existing fields plus `folder_id` or `folder_path`; supports `FOLDER_PATH` and legacy `CATEGORY` classification in path resolution. Deeper paths reject. Missing classification defaults to Custom.
- `POST /api/fork_tc` preserves `{plan_id,category,testcase}` lookup and accepts optional `folder_id`/`folder_path`; default is source's current folder path. Copy lineage remains `family_id`.
- `POST /api/push_to_golden` preserves `{system_id}` and source current path; exact normalized-name duplicates return 409.
- `PATCH /api/testcases/<id>`: `{tc_name?,display_name?,folder_id?,folder_path?,selected?}`; 200 current testcase record.
- `POST /api/plans/<id>/testcases/move`: `{testcase_ids:[...],folder_id}` or `folder_path`; response `{status:'ok',folder_id,moved:<count>}`. Atomic; selection is retained.
- `POST /api/plans/<id>/testcases/reorder`: `{folder_id, testcase_ids:[...]}` (aliases `ids`/`order`). Complete folder collection only.
- `POST /api/tasks/<id>/testcases/import`: `{testcases:[{id,selected?},...]}` replaces current membership, preserves retained latest results, rejects duplicate and foreign members. Empty list keeps an empty Task.
- `PATCH /api/task_testcases/<task>/<case>` only patches an existing scoped row's `selected`; it cannot create membership.
- `POST /api/tasks/<id>/execution/start`: `{selected_testcase_ids:[...]}`; response `{status:'ok',task_id,execution_token}`. Token is transient concurrency control, not product history; never display it in product/report text.
- `POST /api/run`: Task runs must send `{task_id,testcase_id,execution_token,steps,session_id?,tc_name?}` after start. The runner persists the testcase result before closing the stream. Detached builder scratch runs can omit Task identity; testcase-bound scratch requests still check the owning Plan lock.
- `POST /api/tasks/<id>/execution/result`: `{id,status,execution_token,result?,log_text?,api_log_text?,executed_at?,bug_id?}`. Updates exactly one selected member.
- `POST /api/results/save`: `{task_id,execution_token,testcases:[same result objects without token]}`; latest fields only. It does not unlock the execution.
- `POST /api/tasks/<id>/execution/finish` and `/stop`: `{execution_token}`. Stop signals an active worker and returns `{status:'stopping'}`; its finalizer persists/normalizes/unlocks. Finish rejects an alive worker with 409. No worker: normalize/unlock and return `{status:'ok'}`.
- Legacy `POST /api/stop`: `{session_id,execution_token}` for Task execution; scratch runs require session ID only.
- `POST /api/task_tc/annotate`: `{task_id,testcase_id,bug_id?}`; status updates additionally require current `execution_token` and selected active scope.
- `GET /api/tasks/<id>/summary` and `/results`: `{id,task_id,name,plan_id,execution_active,setup,environment_config,testcases,counts:{Passed,Failed,TBD}}`. Each testcase includes live `tc_name`, `folder_id`, `folder_path`, canonical `status`, `result`, `log_text`, `api_log_text`, selection/order/bug/time. Running counts as TBD.
- `GET /api/projects` includes each Plan's `folders` and `locked`, Task `execution_active`, and live folder IDs/paths on Plan and Task cases. No attempts array.

## Verification

TDD baseline: 4 tests exposed missing folder/execution/summary endpoints and accepted foreign Task membership (3 failures, 1 missing-summary error). Later runner-scope test exposed acceptance of foreign Task execution. Restoration fault injection exposed failed restoration; atomic replacement fallback fixed it.

New suite covers empty folder identity/persistence/name collision/depth/reparent, same-Plan/duplicate scope, current rename/placement, selected-rerun retention/stop, stale result/stop/finish tokens, runner scope rejection, destructive impact/acknowledgement/empty Task retention, staging/flush/commit/restoration failures, actual independent SQLite connections, PDF live scope/metadata/log attachment, full production-copy startup twice, migration idempotency and ownership-failure rollback.

Commands (environment set to the disposable paths above):

```powershell
python -B -m unittest web_ui.tests.test_plan_current_state
python -B -m unittest discover -s web_ui/tests -t .
python -m py_compile web_ui/app.py web_ui/models.py web_ui/plan_state.py web_ui/report_generator.py web_ui/tests/test_plan_current_state.py
```

Final evidence: `verification/task1-final-tests.txt`. Earlier full suite was 107/107; final expanded suite is 110 tests. Compile checks passed. Final full-run result is recorded in the evidence file and commit handoff.

## Review concerns / boundaries

- Explicit import/copy batches currently compose existing single-item endpoints from the client; no dedicated multi-item server import/copy route was added. Partial success must be retained by the frontend batch UI.
- `PlanSubfolder`/Category storage remains only for migration and legacy clients; all new folder UI must use persisted PlanFolder endpoints. Legacy `PATCH /api/plans/<id>` category/subfolder fields are not the canonical structural API.
- Reconnection after a page reload needs operational token recovery: start returns the token, but summary/report intentionally does not expose it. A small dedicated execution-state response may be needed by frontend reconnect work.
- New databases have the canonical status CHECK constraint; migrated SQLite tables are normalized transactionally and all current result APIs enforce the canonical values, but migration does not rebuild the old table to add the CHECK constraint.
- No real BMC was contacted. Browser and frontend integration belong to Task 2. Independent review is still required before acceptance; no integration/deployment was performed.

## Independent review fix round 1

Addressed all three Important findings in `verification/task-1-review.md`:

1. **Worker admission / stop / finalizer race.** Task now persists `execution_worker_id` before committing Running, so a worker remains admitted even before its thread is registered or starts. A second worker under the same Task receives 409. Finish rejects any admitted worker. Stop persists `execution_stop_requested` and returns `stopping` while admission exists; a worker starting after a stop sees that request before executing. Setup, normal, stop, and persistence-error paths release admission in one finalizer, after testcase execution and result persistence have ended; only then can it normalize/unlock. The stream end is emitted after release, preventing an early frontend finish race. A failed thread start also releases admission safely.
2. **Golden copy after folder rename.** The preserved `{category,testcase}` contract resolves the normalized exact testcase name and validates its current persisted root folder name, rather than stale Category storage. `source_testcase_id` additionally supports stable identity; its source must belong to Golden Plan (foreign source returns 400). Destination folder selection remains independent and defaults to the current source path.
3. **Deleted final folder recreated by startup.** `ProjectPlan.folders_migrated` records completion transactionally, independently of folder existence. Once converted, retained category/subfolder rows cannot recreate deleted structure. Canonical folder creation also marks the Plan as converted. A migrated Plan with a deleted final root/empty legacy child remains empty on subsequent migration.

Focused behavioral tests added:

- `test_worker_admission_blocks_finish_before_thread_start`: gates actual `Thread.start` after database admission and proves finish is rejected, stop remains pending, and folder writes remain locked through the gap.
- `test_second_worker_is_rejected_and_stop_keeps_blocked_worker_locked`: gates a real worker in a fake BMC login, rejects admission of B, and proves stop cannot unlock while A remains gated.
- `test_golden_copy_uses_live_folder_after_rename`: Network -> Fabric -> legacy name copy plus stable-ID copy and non-Golden ID rejection; lineage and destination path verified.
- `test_deleted_final_migrated_folder_stays_deleted_on_restart`: converts a root and empty legacy child, deletes the subtree, reruns migration and verifies no folders reappear.

All four tests failed for the expected findings before implementation (`verification/task1-review-red.txt`). After the fixes, the targeted suite passed 18/18 (`verification/task1-review-targeted.txt`). Cross-cutting final discovery passed **114/114 in 18.217 seconds**, exit 0 (`verification/task1-review-final.txt`). Python compile and `git diff --check` passed. The pristine source hash remained `54B3FD8E1C5D62265C14DFE04104ADE68FBC813E31157E90577EB351C12456D6` before/after discovery. Tests used the same explicit disposable workspace, main-program override, and pristine lifecycle source documented above. No frontend or documentation source files were changed.

## Final review ordering correction

Fixed the testcase-deletion ordering gap: after testcase rows are flushed away, `delete_content` normalizes only the affected surviving folder collections, ordered by their prior position and stable testcase ID. Folder-subtree collections being deleted are excluded; unrelated folders are never normalized. This remains inside the existing staging/database transaction, before commit, so a commit failure restores both original ordering and staged executable files.

Behavioral API regressions exercise single deletion and legacy bulk deletion, verify contiguous positions immediately after deletion, then import another testcase and verify the surviving order plus append position. An unrelated Plan folder with an intentionally noncontiguous fixture position remains unchanged. A separate injected commit failure verifies all original positions and executable directories survive rollback.

TDD evidence: `verification/task1-ordering-red.txt` records expected failures for both single and bulk deletion (surviving positions retained gaps). After the fix, `python -B -m unittest web_ui.tests.test_plan_current_state` passed **23/23 in 4.221 seconds**, exit 0 (`verification/task1-ordering-green.txt`). Compile and diff checks passed. The pristine baseline source SHA256 remained `54B3FD8E1C5D62265C14DFE04104ADE68FBC813E31157E90577EB351C12456D6`. No broad full-suite rerun was performed in this fix turn; root will run final integrated verification.
