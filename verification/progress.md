# Implementation progress

- Baseline: commit 91d5f5f; 97 Python tests passed in 9.709s using copied database.
- Worktree: D:/Pytest/_redfish/plan-folder-current-state.
- Branch: codex/plan-folder-current-state-20260917.
- Task 1: backend implementation dispatched; brief task-1-brief.md, report task-1-report.md.
- Task 3 documentation: copied glossary reconciled with approved live-state vocabulary; main original untouched.
- Windows sandbox process startup fails; explicitly escalated shell calls work.

- JavaScript baseline: 26/26 passed.
- Browser: bundled Playwright with installed Chrome, headless fallback because cua_repl kernel fails sandbox initialization.
- Task 1 Ruling: Use a transient execution token for start/result/stop/finish concurrency validation, cleared at termination and never presented as run history or report data. This prevents callbacks from a stopped execution corrupting a newly started one. Cost if wrong: clients need a small protocol revision; no historical product model is introduced.
- Test-isolation finding: existing lifecycle shadow inherited BMC_WEB_UI_WORKSPACE_DIR from parent and added 3 cases to the worktree test copy. The pristine verification/baseline-workspace copy remains at 17 cases. Backend task is explicitly binding both workspace/main overrides to each shadow and using BMC_LIFECYCLE_SOURCE_DB for immutable source selection.
- Pre-integration browser: Chrome Dashboard loaded without page errors; discovered legacy Blocked status surface and added to frontend brief notes. Isolated server stopped after capture.
- Task 1 implemented: dea541f, full Python 110/110 passed, compilation/diff check passed; independent review in progress. See task-1-report.md and task-1-review.diff.
- Task 1 review: spec and quality both changes required; three Important findings in task-1-review.md. Fix round 1/5 dispatched to original implementer: worker admission/finalizer lock lifetime, Golden copy after persisted folder rename, migration resurrection after deleting final folder.
- Browser execution verification uses the existing lifecycle FAKE_REDFISH_MODULE copied into browser-main/redfish.py and one controlled pass/fail/wait step. No real BMC networking is required.
- Task 1 fix round 1/5: b92c9c3 addresses all 3 Important findings; targeted18/18 and full114/114 pass, pristine source SHA256 unchanged. Scoped re-review pending.

- Task 1 complete: b92c9c3, independent scoped review approved all 3 fixes; Task2 frontend dispatched.
- Fresh production-format migration verification:17 preserved cases,14 folders, two startup states identical, integrity ok, no FK violations, pristine SHA unchanged.

- Task2 complete: 5f4ffcd + fbac18e, reviewed definition failure fixed67ea431, scoped review approved.
- Final review ordering finding fixedaf47c02; scoped final spec/quality review approved, all reported findings closed.
- Final evidence: Python119/119 (19.700s), Node46/46, parse/compile/diffchecks pass, final-copy migration two startups identical17cases14folders, main20sourcehashes/status unchanged.
- Chrome checks completed: folderCRUD/template/importretry/Goldenversions+independence/selectedrerun+logs/fresh-tabStop+locks/livescope+cascade/currentPDF+summary/builderroundtrip/emptydefinitionfailurecontinuation.
- Documentation and glossary reconciled; branch retained unmerged, unpushed and undeployed. No realBMC contacted.
