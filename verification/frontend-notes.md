# Frontend integration reconnaissance

Read alongside task-2-brief.md and backend task-1-report.md. This is navigation, not a substitute for requirements.

- index.html: getPlanFolderModel / renderPlanFolderTree / renderPlanAllCaseHierarchy currently infer native categories and special Custom children. Every folder must instead come from persisted IDs, including empty folders.
- resolvePlanTestCases and resolveTaskTestCases currently combine potentially stale ref placement over current base placement; live reference should prioritize Plan testcase identity and folder.
- movePlanFolder and savePlanStructure currently rewrite category_order/custom_subfolders. Replace those mutations with domain folder APIs.
- newPlan currently creates plan through legacy workflow; add structure-only template/custom paths and partial parent selection.
- getPlanMoveFolderOptions / requestPlanTestCaseMove / pointer commit helpers currently pass cat:/custom: keys. Shift to stable folder identity while retaining context-cancellation safety covered by existing Node tests.
- lockedProjectIds and pointer isLocked(projectId) currently over-lock siblings. Use active Plan identity; execution locks a Plan, not all Plans in a Project.
- startTaskAttempt/runPlan/_executeTCs/saveTaskResults/loadTaskResults contain historical attempts and final-only file persistence. Replace with backend execution lifecycle; failures must surface, and finally must release/normalize through backend.
- _executeTCs currently references taskId without declaring it in local scope; eliminate during lifecycle integration rather than preserving a swallowed annotation error.
- stopPlan currently only signals current session. Ensure active Task selection releases through backend even between testcases.
- builder.html export currently emits CATEGORY only, import only reads CATEGORY; retain FOLDER_PATH and legacy CATEGORY fallback.
- Execution/run/report functions must not manufacture scope or trust historical files. Review generatePlanReport as well as downloadTaskPDFReport.
- Existing Node tests: 26 pass at baseline. Existing Python layout tests may assert intentionally superseded Run History source text; replace those expectations with useful current behavior coverage.
- Pre-integration Chrome screenshot shows Dashboard still renders a Blocked testcase KPI, matrix row and board column. Remove this fifth testcase outcome along with skipped/interrupted/pending; only TBD/Running/Passed/Failed remain. Do not merely remove Run History from Task Detail.
- Real Chrome initial Dashboard against new backend loads with zero page errors or failed requests (favicon404 only); screenshot browser-preintegration.png. This is baseline UI evidence, not final verification.

## Backend handoff specifics (dea541f)

- Read task-1-report.md for exact endpoints. Folder GET is bare array; canonical folder keys should be folder:<id> or consistent ID handling. Reorder now requires one complete sibling collection; testcase reorder requires folder_id and that folder's complete IDs.
- Template request must send only partially selected child paths when root is partial. Sending the root path means select all current Golden children; parent existence is implicit for a child path. Full root selection can send the root path.
- Store transient execution_token only operationally; send it on Task /api/run, explicit results and finish/stop. The server runner persists completion, so avoid overwriting its detailed latest log with a second empty client result.
- Scope /testcases/import REPLACES current membership. Add-to-Task UI must send existing+new members; remove must send retained members, and preserve latest evidence for retained rows.
- GET Task /results now returns current summary directly, not {found,data}; do not backfill from old result-file payloads.
- summary counts keys are Passed/Failed/TBD; Running belongs to incomplete count. /api/projects includes Plan folders+locked and Task execution_active.
- Scope, move, import and export workflows must re-fetch authoritative Plan data after mutations; do not save a stale whole-project snapshot that reintroduces removed scope.
- Backend review found old Category source lookup breaks Golden copy after folder rename; fix is underway. Prefer stable source testcase ID when final backend contract provides it, while keeping target folder_id separate.
- Active execution token must survive reload operationally (for example sessionStorage keyed by Task) or use dedicated recovery API; never display token or treat it as history.
- Fix-round backend contract: /api/fork_tc additionally accepts source_testcase_id and validates Golden ownership. Prefer this stable ID over category/name lookup. Migration completion is persisted independently of empty folder state. Only one worker per Task is admitted at a time; do not overlap selected-case requests.
