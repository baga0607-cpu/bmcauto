# Task 1 independent backend review

Reviewed fixed range `33a2c55..dea541f`, `verification/task-1-review.diff`, Task 1 brief/report, and approved `docs/superpowers/specs/2026-08-24-plan-folder-and-task-current-state-design.md`. Source was not edited. Frontend implementation is explicitly outside this review.

**Spec compliance verdict: Changes required.**
**Code quality/correctness verdict: Changes required.**

No Critical findings. Three Important findings follow.

## Important: Keep the execution lock until all workers have stopped

Location: `D:/Pytest/_redfish/plan-folder-current-state/web_ui/app.py:1973` (also worker registration at lines 1740–1758 and `web_ui/plan_state.py:449–467`).

Start a Task selecting A and B, then submit `/api/run` for each. The backend permits both because it rejects only an already-Running membership, not another active worker in the Task. Stop the Task while B is still blocked in a BMC call. When A stops first, its finalizer calls `finish_execution` immediately. This normalizes B and clears the Plan lock/token while B's thread is still executing. Structural mutations can then succeed during execution, and B's eventual result is rejected as stale. Setup/persistence error finalizers have the same unconditional finish behavior. The worker registry also has a startup gap: `/api/run` commits Running before registering/starting the thread, allowing a concurrent finish/stop to see no alive worker and unlock before that worker begins.

Coordinate worker registration, start, and terminal transitions; either enforce one worker per Task atomically or retain the lock until every admitted worker has terminated. A deterministic test with a gated second worker should prove mutations remain blocked until it exits. This is a static control-flow finding, not a claim of an executed concurrency reproduction.

## Important: Resolve Golden copies using current folder identity

Location: `D:/Pytest/_redfish/plan-folder-current-state/web_ui/app.py:1325–1336`.

After creating a Golden testcase under Network, rename its persisted root to Fabric. The rename returns 200 and `/api/projects` now returns testcase category Fabric, but `/api/fork_tc` with that current category returns 404 `Category Fabric not found`. Folder rename changes PlanFolder only; the copy handler still resolves the old Category table and filters `category_id`. If the new Category already exists, the stale filter still fails to identify the source. This breaks ordinary Golden library copy after a supported folder rename/reparent operation.

Resolve the source by stable testcase identity with Golden ownership validation, or join the current PlanFolder placement for the preserved name-based contract. Keep destination folder selection separate. Add a rename-then-copy API regression.

Evidence: narrow isolated API reproduction printed `import 200`, `rename 200`, `live case Fabric`, `fork current category 404 {'error': 'Category Fabric not found'}`.

## Important: Do not rerun legacy folder conversion after the user empties a Plan

Location: `D:/Pytest/_redfish/plan-folder-current-state/web_ui/plan_state.py:246–250`.

The migration uses absence of root folders as proof that legacy conversion has not run. After a migrated Plan's final folder is deleted, startup therefore reads retained `category_order` and `PlanSubfolder` rows again and recreates deleted folders with new IDs. A valid intentionally empty Plan does not survive restart; this violates permanent folder deletion and migration idempotency.

Persist migration completion independently of folder existence, or transactionally retire converted legacy structure so an empty canonical Plan cannot trigger reconversion. Add a migrate/delete-all/restart regression.

Evidence: an isolated Plan with legacy `category_order=["Legacy"]` migrated successfully; final folder DELETE returned 200; GET returned `[]`; calling migration again recreated `Legacy` with a new UUID.

## Coverage and boundaries

The recorded verification evidence reports 110 tests passing in 14.638 seconds, successful compile checks, and unchanged pristine-copy SHA256. I did not rerun that suite. The two targeted reproductions used a temporary copy of `verification/baseline-workspace/testcase_meta.db` for app startup plus a separate disposable fixture engine and temporary executable directory. No active/main production database was used. Both reproductions completed and printed the evidence above; final TemporaryDirectory cleanup failed on a Windows open database handle, causing that one command to exit 1 after the reproductions.

The implementation substantially covers folder identity/depth, same-Plan live scope, canonical current statuses, transactional write reservations, staged testcase/subtree deletion, and current report reads. The central before-request guard was inspected; apparent missing per-handler lock checks are generally covered by that guard and are not reported as findings.

The candid report boundaries do not themselves justify rejecting client-composed import/copy batches or deferring actual frontend UI to Task 2. Retained legacy storage is acceptable only while it cannot override canonical state; the restart finding demonstrates that it currently can. The missing migrated CHECK constraint is documented and API normalization is present. Token recovery remains an explicit frontend integration risk: summary and `/api/run/active` do not provide a recoverable operational token. Task 2 must preserve it across reloads or obtain a dedicated execution-state API so viewing/stopping an active execution remains usable. This was not counted as an additional confirmed backend blocker because frontend persistence has not yet been implemented.
