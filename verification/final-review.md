# Final independent whole-branch review

Scope: stable branch range `91d5f5f..67ea431`, including backend models/domain/routes/runner, frontend folder/Task integration, report projection, tests and current domain/status documentation. Reviewed against the approved `2026-08-24-plan-folder-and-task-current-state-design.md` and implementation plan. Earlier independent reviews and their fix dispositions were retained as evidence rather than restarted.

**Spec compliance verdict: Changes required.**
**Code quality/correctness verdict: Changes required.**

No Critical findings. One new Important finding remains.

## Important: Normalize surviving testcase positions inside deletion

Location: `D:/Pytest/_redfish/plan-folder-current-state/web_ui/plan_state.py:199–205` (`delete_content` testcase deletion); related append calculation at line 95 in `assign_folder`.

Deleting individual testcases removes database rows but never normalizes the surviving testcase collection in each affected folder. Subsequent imports/copies append using the remaining row count. For A/B/C at positions 0/1/2, delete B then add New: the persisted order becomes A0, C2, New2. With several earlier deletions, a new testcase can receive a smaller position than surviving later testcases and appear before them instead of appending. This violates the explicit persisted-order invariant that create/move/reorder/delete normalize the affected collection transactionally.

Capture the affected surviving folder IDs and normalize their remaining TestCase positions, in stable prior order, after deletes flush and before the same deletion transaction commits. Do not reorder unrelated folders; whole-subtree deletion need not normalize folders being removed. Cover individual and bulk deletion followed by import/copy, asserting contiguous positions and preserved relative order.

Evidence: a narrow Python reproduction imported only `models` and `plan_state`, used a freshly created disposable SQLite fixture and temporary executable root, and exercised actual create/assign/delete/assign domain operations. Output: `delete b then append new: [('a', 0), ('c', 2), ('new', 2)]`. No application startup or existing/production database was accessed.

## Closed findings

- Task 1 worker-admission/early-unlock race: addressed in `b92c9c3`; persistent worker admission, single-worker enforcement and gated concurrency regressions inspected.
- Task 1 Golden copy after folder rename: addressed in `b92c9c3`; current folder lookup/stable source ID and ownership tests inspected.
- Task 1 deleted folders resurrecting on startup: addressed in `b92c9c3`; transactional conversion marker and delete/restart regression inspected.
- Task 2 empty/missing definition remaining TBD: addressed in `67ea431`; current Failed evidence and continuation/error regressions inspected. Scoped re-review approved in `verification/task-2-fix1-review.md`.

## Evidence and limits

Recorded automated evidence is Python full discovery 117/117, current Node 46/46, and relevant Python contracts 95/95 after the frontend-only fix, plus reported compile/parse checks and copy-isolation/source-hash evidence. Broad suites were not rerun. The only new execution in this final review was the disposable ordering reproduction above. No source edits, production data access, merge, push or deployment occurred.

Root reports real Chrome checks passing folder CRUD/order, template selection, retryable import, Golden named-version copy and deletion independence, selected execution/current logs, recovery Stop/Plan locks and builder roundtrip. Those are root's browser observations, not independent browser claims by this reviewer; final scope/PDF checks were still underway when this report was written.

Current domain/status documentation consistently supersedes historical attempts and directs readers to the current-state design without claiming deployment. Current report code reads live Task membership, folder paths, metadata and latest row-held logs; no historical-file report fallback was found. Client-composed explicit import/copy batches and read-only token recovery fit the authorized boundaries. The ordering finding is the remaining independently confirmed acceptance blocker from this pass.
