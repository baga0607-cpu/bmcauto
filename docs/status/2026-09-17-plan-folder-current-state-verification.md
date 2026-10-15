# Plan Folder and Task Current-State Verification

Date: 2026-09-17
Status: Implementation and verification complete in the isolated branch; not merged or deployed.

## Isolation

- Worktree: `D:/Pytest/_redfish/plan-folder-current-state`
- Branch: `codex/plan-folder-current-state-20260917`
- Base: `91d5f5f` on main.
- Main modifications were retained in place. The untracked approved specification and glossary were copied into this branch before editing.
- SQLite source was copied using a read-only connection and SQLite backup. Pristine verification source has 17 testcases, 2 Plans, 2 Tasks and 10 memberships.
- Browser assets have copies of all 17 executable directories and a sandbox.invalid configuration.
- No merge, push or deployment has been performed.

## Baseline evidence

- Python unittest discovery: 97 passed in 9.709 seconds.
- Node interaction tests: 26 passed.
- Chrome 153.0.8010.48 launched through bundled Playwright. Pre-integration Dashboard loaded with no page errors or failed requests.

## Verification findings addressed during work

- Existing lifecycle server inherited the outer database workspace environment variable. The new isolation setup must explicitly select its shadow database and executable directories and preserve the pristine source hash.
- The existing Dashboard renders a Blocked testcase state beyond the four approved states. Frontend verification includes removing this legacy surface.
- A transient execution token is needed to reject delayed callbacks from a stopped execution after a new execution begins. This is concurrency control only, cleared at termination, with no product history or report field.

## Backend and migration evidence

- Backend commits: `dea541f`, followed by reviewed fixes in `b92c9c3`.
- Independent review identified worker lock lifetime, Golden copy after rename, and deleted-folder resurrection; all three were fixed and approved in scoped re-review.
- Backend Python discovery: 114 tests passed in 18.217 seconds; targeted current-state suite: 18 passed. Compilation and diff checks passed.
- Fresh original-format copy startup twice: 17 testcases preserved, 14 persisted folders, identical folder IDs/placement/order across startups.
- SQLite `integrity_check`: ok; `foreign_key_check`: no violations.
- Pristine source SHA256 unchanged: `54B3FD8E1C5D62265C14DFE04104ADE68FBC813E31157E90577EB351C12456D6`.
- Migration evidence: `verification/migration-verification.json` and technical log in `verification/migration-workspace`.

## Offline runner integration evidence

Actual HTTP/SSE requests against the isolated localhost server used the existing offline Redfish fixture and a deterministic verification step:

- One selected pass persisted before execution finish; counts became Passed 1, Failed 0, TBD 2.
- While a wait step was running, structural mutation of its Plan returned 409; a sibling Plan in the same Project accepted folder creation with 201.
- Stop returned stopping; mutation remained blocked with 409 until the worker exited.
- After stop, the prior Passed result remained, the unfinished testcase returned to TBD, and execution_active was false.
- Evidence: `verification/browser-fixture.json` and `verification/runner-stop-verification.json`.

## Final automated evidence

Verified implementation commit: `af47c02` (documentation-only commits follow).

- Full Python discovery: **119/119 passed**, 19.700 seconds (`verification/final-python-tests.txt`).
- JavaScript interaction tests: **46/46 passed**, no skipped tests (`verification/final-node-tests.txt`).
- Both index.html and builder.html inline scripts parsed; changed Python runtime/tests compiled; `git diff --check` passed.
- Final-code fresh database migration ran twice: 17/17 testcases retained, 14 folders, identical IDs/placement/order, integrity ok and no foreign-key violations. Pristine backup hash unchanged.
- Main Git status matches the initial snapshot. All 20 captured source-file hashes match, including existing modified/untracked files; `verification/main-preservation.json` records this.

Commands run from the isolated worktree:

```powershell
$env:BMC_WEB_UI_WORKSPACE_DIR = "$PWD/verification/final-workspace"
$env:BMC_MAIN_PROGRAM_DIR = "$PWD/verification/browser-main"
$env:BMC_LIFECYCLE_SOURCE_DB = "$PWD/verification/baseline-workspace/testcase_meta.db"
python -B -m unittest discover -s web_ui/tests -t .
node --test web_ui/tests/*.test.js
python -m py_compile web_ui/app.py web_ui/models.py web_ui/plan_state.py web_ui/report_generator.py web_ui/tests/test_plan_current_state.py
python verification/verify_migration.py --final
python verification/verify_main_preservation.py
```

The final workspace was freshly copied from the pristine SQLite backup before running discovery. The migration harness refuses to overwrite an existing verification database. Local copied databases, executable fixtures, screenshots, and PDFs are retained as verification artifacts, not application changes.

## Chrome verification

Chrome 153.0.8010.48 ran headless through bundled Playwright against localhost:5127, the copied database, copied scripts and deterministic offline Redfish/step fixtures. No real BMC was contacted.

| Workflow | Observed result | Evidence under verification/ |
| --- | --- | --- |
| Empty folders and CRUD | Root/child creation, reload, rename, child reparent/root move, drag reorder and acknowledged subtree delete passed | browser-folder-crud.json; browser-folder-move-delete.json |
| Plan templates and import | Partial root selection, template/custom path merge, structure-only creation, FOLDER_PATH/CATEGORY/default mapping, retained invalid-depth item and corrected retry passed | browser-template-import.json |
| Golden copies | Same-family named versions coexist; default path retained; duplicate disabled; source-folder rename works; deletion leaves independent copies | browser-golden-copy.json |
| Selected execution | Selected failure overwrote its latest result/log; unselected Passed result and timestamp retained; Plan unlocked | browser-execution-results.json |
| Definition error | Empty definition persisted Failed with current log; valid successor completed Passed | browser-definition-failure.json |
| Stop and recovery | New tab did not finish a worker gap; recovered Stop; all folder controls disabled while locked; sibling Plan editable; completed results retained | browser-recovery-lock.json; runner-stop-verification.json |
| Live Task and cascade | Renamed/moved identity displayed with prior Passed state; scope removal dropped result; re-add was TBD; subtree deletion retained empty Task; current report excluded removed row | browser-task-scope.json |
| Reports | Actual PDF downloaded, current name/path/firmware verified by text extraction; all four pages rendered and visually checked; empty Task summary showed zero counts | browser-current-summary.pdf; browser-empty-task-report.png |
| Builder | Actual file import/download preserved FOLDER_PATH, family and executable steps | browser-builder-roundtrip.json |

Successful browser harnesses record no page errors. Fixture creation and assertions use API requests where noted in the harnesses; live rename/move was changed through the API and observed in Task UI, while scope removal, folder cascade, report generation and execution used visible UI controls. Backend-only invalid ownership/depth/concurrency/rollback cases are covered by automated tests, not claimed as additional manual UI checks.

## Independent reviews and fixes

Both spec-compliance and code-quality reviews are approved at `af47c02` (`verification/final-fix1-review.md`). All reported Important findings were closed:

1. Worker admission/finalizer lock lifetime, copy after folder rename, and deleted-folder resurrection: `b92c9c3`.
2. Current failure detail persistence found during Chrome verification: `fbac18e`.
3. Empty/missing execution definition must persist Failed and continue valid selected cases: `67ea431`.
4. Single/bulk testcase deletion must normalize remaining folder positions before append, with rollback safety: `af47c02`.

The explicit implementation ruling is the transient execution token described above. It is operational concurrency control, cleared at termination, never a report field or historical execution record. A separate read-only execution endpoint supports fresh-tab Stop recovery; viewing does not finish or resume unstarted work.

## Delivery boundary

The glossary now defines live Task and Task Test Case membership; obsolete Snapshot/Archived Test Case definitions are removed. Status notes describe the implemented branch, not a deployed main version.

The branch and worktree remain intact for review. No merge, push, deployment, active production database mutation, or real-device verification was performed. The dedicated localhost preview process was stopped after verification; retained fixtures are isolated from the user's application. Real-device behavior beyond the tested offline runner remains outside this verification scope.
