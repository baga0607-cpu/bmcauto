# Task 1 independent re-review: fix round 1

Scope: fixed diff `dea541f..b92c9c3` in `verification/task-1-fix1-review.diff`, updated implementation report, and the three findings in `verification/task-1-review.md`. Reviewed changed production logic and the four added behavioral regression tests. No source changes or test reruns were performed.

**Spec compliance verdict: Approved for the reviewed backend scope.**
**Code quality/correctness verdict: Approved for this fix round.**

No new Critical or Important findings in this fix diff.

| Original Important finding | Disposition | Review evidence |
| --- | --- | --- |
| Keep execution locked until all workers have stopped | ADDRESSED | `web_ui/app.py` persists worker admission in the same write transaction as Running, rejects a second admitted worker, checks persisted stop before execution, and releases admission after execution/result persistence. `web_ui/plan_state.py` refuses finish while admission exists and persists stop through the thread-start gap. The regression tests gate actual thread start and a fake BMC login, verify 409 for finish/second-worker admission, and verify folder mutations remain locked until release. |
| Golden copy must use current folder identity | ADDRESSED | `/api/fork_tc` resolves the normalized testcase name within Golden and checks its current persisted root; it also accepts `source_testcase_id` with Golden ownership validation. The added API test renames Network to Fabric, copies through both contracts, checks the current destination path and lineage, and rejects a foreign source ID. |
| Deleted final folder must stay deleted after restart | ADDRESSED | `ProjectPlan.folders_migrated` records conversion independently of folder existence and is updated transactionally. Legacy category/subfolder structure is converted only before that marker is set. The regression migrates an empty legacy child, deletes its final root subtree, reruns migration, and asserts the Plan remains empty. |

Verification evidence inspected: `verification/task1-review-targeted.txt` reports 18/18 passing; `verification/task1-review-final.txt` reports 114/114 passing in 18.217 seconds and exit 0, with unchanged pristine-source SHA256 `54B3FD8E1C5D62265C14DFE04104ADE68FBC813E31157E90577EB351C12456D6`. The implementation report records compile and whitespace validation. The focused tests exercise the original triggers; repeating broad discovery was unnecessary. This review made no database accesses.

The prior integration boundaries remain: frontend UI acceptance is Task 2; client-composed batches must preserve explicit partial success; active-execution token persistence/recovery must be resolved for reload/stop behavior. These are not new regressions in this fix and do not reopen the three addressed findings. Frontend Task execution should issue one testcase worker at a time and wait for stream termination before submitting the next worker or finish request.
