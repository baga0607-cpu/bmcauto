# Multi-select Case drag import — 2026-10-29

Source Test Case rows have checkboxes. Dragging a checked Case carries all checked Cases from the current source in source order; dragging an unchecked Case retains single-Case behavior. Search/collapse preserves selection; changing source resets it. Successful import clears the imported selection. Folder drag remains unchanged.

POST /api/plans/<id>/import-cases accepts case_ids for kind=case, retaining the single id contract. The endpoint validates all IDs, source ownership, destination and locks before writing. All Cases share one conflict-resolution flow and transaction. Added rows preserve batch order at an insertion anchor; commit failures roll back rows and copied files.

## Verification

- 5 new batch tests passed: Repository/Plan source batches, anchor order, malformed/duplicate/foreign IDs, execution locks, conflict preflight/skip, and commit rollback.
- 20 existing single-Case Repository/import tests and 4 ordering tests passed (29 backend tests total). Disposable workspace/scripts/temp: bmca-runtime/verification/batch-case-import-20261029. No DUT execution.
- execution_workspace.test.cjs passed: multi-check, selection retained across search, one batch request with both IDs, both target Cases visible, cleared checks after success, and prior Plan/Execution workflows. Browser mutations intercepted with fixtures. Screenshot inspected.
- Node syntax and task_management_list.test.cjs passed.
- Formal service restarted only after confirming no active execution and matching its server.py process. API returned 200; complete Projects API state matched before/after restart. No formal Test Cases were imported during verification.
