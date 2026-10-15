# Acceptance evidence matrix

Use this checklist to verify the final branch; a check requires actual evidence, not an implementation claim.

| Spec acceptance criterion | Automated evidence | Browser evidence | Status |
|---|---|---|---|
| 1. Explicit equally editable folders, including empty folders | Folder persistence and CRUD tests | Empty root/child CRUD | Passed |
| 2. Two-level hierarchy, normalized names, ownership and ordering | Invalid depth/collision/reparent/order tests | Move child and reorder | Passed |
| 3. Deterministic migration with Custom fallback | Legacy anomalies, row counts, idempotency, logs | Migrated tree visible | Passed |
| 4. Same-Plan live Task references | Foreign/duplicate scope rejection; live rename/move | Rename/move appears in Task | Passed |
| 5. Cascades preserve empty Tasks | Testcase and subtree cascade tests | Impact/delete and empty Task | Passed |
| 6. Four states, selective latest overwrite | Per-case write/rerun/stop/failure tests | Execute/rerun/stop | Passed |
| 7. Backend Plan lock and concurrency | All mutation entry points + concurrent connections | Locked controls and allowed views | Passed |
| 8. Current summary metadata, scope and results | Summary/report current-state tests | Report after scope change | Passed |
| 9. No history product behavior | Removed attempt endpoints/storage; canonical states | No Run History UI | Passed |
| 10. Atomic migration and DB/files deletion | Failure injection + file restoration + DB rollback | Full impact and acknowledgement | Passed |

## Baselines

- Python: 97 tests passed in 9.709s (`baseline-tests.log`).
- JavaScript: 26 tests passed (`baseline-node.log`).
- Original-format DB copy: 17 testcases, 2 Plans, 2 Tasks, 10 memberships.
- Browser executable assets: all 17 testcase script directories copied; no missing scripts.
- Chrome 153.0.8010.48 starts through bundled Playwright.

## Preservation

Main status and file hashes captured before implementation. Do not compare active log or SQLite bytes while the user's server may be running; compare tracked/untracked source artifacts and status, and record any externally changing files explicitly.

Final evidence: Python119/119; Node46/46; final-fix1-review.md approved at af47c02. Browser references and distinctions between UI/API verification are recorded in docs/status/2026-09-17-plan-folder-current-state-verification.md. Main status identical and all20 source hashes unchanged.
