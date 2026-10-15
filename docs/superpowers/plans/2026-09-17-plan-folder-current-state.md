# Persistent Plan Folders and Current-State Tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Implement persisted two-level Plan Folders and live, latest-result-only Tasks throughout migration, APIs, UI, execution and reporting.

**Architecture:** Introduce an explicit PlanFolder model and a focused transactional domain service rather than extend category-specific branches. SQLite write transactions serialize structural mutations with execution start; file deletion stages recoverable files before database commit. Existing routes delegate to domain operations while the UI uses folder identities and current Task state.

**Tech Stack:** Python 3.12, Flask, SQLAlchemy, SQLite, vanilla JavaScript, unittest and Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-24-plan-folder-and-task-current-state-design.md`

## Global Constraints

- The hierarchy permits at most two levels: a root folder and one child level.
- Within one Test Plan, `normalized_name` remains unique.
- `display_name.strip().casefold()` defines normalized testcase names.
- A Task can reference only Test Cases currently owned by its own Test Plan.
- Each TaskTestCase has exactly one current status: `TBD`, `Running`, `Passed`, `Failed`.
- The execution engine can update status and result data but can never add or remove Task scope.
- Verification must use a copy of the production-format database, never the active production database.
- Use only `D:/Pytest/_redfish/plan-folder-current-state`; preserve all main changes. Do not merge, deploy or push.
- Use English-first product UI text. No Snapshot, Archived Test Case, execution attempt or Run History behavior remains.
- Partial success applies only to explicit import/copy batches. Structural changes and destructive operations are atomic.

## Preparation and baseline

- [x] Read approved specification, repository architecture, glossary and task architecture skill. The approved spec supersedes the skill's historical attempt vocabulary.
- [x] Create branch `codex/plan-folder-current-state-20260917` from main commit `91d5f5f` in the requested isolated directory.
- [x] Copy the untracked approved spec and glossary without modifying their main originals.
- [x] Back up source SQLite using a read-only connection and SQLite backup API into `verification/baseline-workspace/testcase_meta.db` and copy that backup to the worktree's `web_ui/workspace/testcase_meta.db`.
- [x] Run `python -B -m unittest discover -s web_ui/tests -t .` with `BMC_WEB_UI_WORKSPACE_DIR` pointing to the worktree copy. Record baseline in `verification/baseline-tests.log`.

## File responsibilities

- `web_ui/models.py`: persistent folders, testcase placement, unique live Task membership, latest result and active execution state.
- `web_ui/plan_state.py` (new): domain operations, ownership/lock checks, ordering, migration, file staging and current report projection.
- `web_ui/app.py`: startup migration, routes, execution lifecycle and report integration.
- `web_ui/report_generator.py`: current-state report payload/rendering, no historical source of truth.
- `web_ui/static/index.html`: folder tree and CRUD, template creation, imports, confirmations, live Task execution and reports.
- `web_ui/tests/test_plan_current_state.py` (new): folder, migration, API, locking, scope, execution and deletion regression tests.
- `web_ui/tests/test_task_api_contract.py`, `test_db_lifecycle.py`, `test_test_layout.py`: retain applicable contracts and replace only intentionally superseded expectations; shadow projects must copy new runtime modules.
- `web_ui/tests/plan_workspace_interactions.test.js`, `plan_inline_interactions.test.js`: adapt browser-independent interaction coverage and add new folder behavior tests.
- `CONTEXT.md`, `docs/status/bmc_agent_v4_task_management_status.md`, `docs/status/bmc_agent_v4_next_plan.md`: reconcile current terminology and document verification.

### Task 1: Persist folders and current Task state through transactional APIs

**Files:** models.py, new plan_state.py, app.py, report_generator.py, Python tests listed above.

**Interfaces:**
- `migrate_current_state(engine, log_path)` migrates existing data transactionally and validates counts, ownership and depth. Repeated invocation must preserve IDs and placement.
- `GET /api/plans/<plan_id>/folders` returns ordered folder records (`id`, `plan_id`, `parent_id`, `name`, `position`). POST creates; PATCH `/api/folders/<folder_id>` renames/moves; POST `/api/plans/<plan_id>/folders/reorder` reorders one sibling collection.
- `GET /api/folders/<folder_id>/impact` and `GET /api/testcases/<tc_id>/impact` return names, descendant_folder_count, testcase_count, affected_task_count, task_testcase_count and requires_acknowledgement. DELETE submits confirmation and acknowledgement when required.
- Preserve existing create/import/copy/publish routes; add `folder_id`/`folder_path` inputs and expose folder IDs/paths in plan and testcase responses. Structure-only creation accepts `folder_paths` plus selected Golden template paths.
- `POST /api/tasks/<task_id>/execution/start` validates selected existing scope, takes Plan lock atomically and resets selected results. Completion persists each result; stop/finish normalizes unfinished rows before unlocking.
- `GET /api/tasks/<task_id>/summary` projects current scope, live identity and placement, current Task metadata and counts.
- Existing execution routes must enforce the same lifecycle; remove attempts routes/serialization and history production. JSON latest results/logs belong to TaskTestCase.

- [x] Write real API/domain tests first. A representative folder test must create an empty root, fetch it again, rename it, add a child, reject a grandchild, reject casefold sibling collision, reparent the child and verify stable IDs. Assert specific response codes and database rows, for example:

```python
root = client.post('/api/plans/p/folders', json={'name': ' Network '}).get_json()
assert client.post('/api/plans/p/folders', json={'name': 'NETWORK'}).status_code == 409
child = client.post('/api/plans/p/folders', json={'name': 'Ports', 'parent_id': root['id']}).get_json()
assert client.post('/api/plans/p/folders', json={'name': 'Third', 'parent_id': child['id']}).status_code == 400
```

- [x] Add migration fixtures for category_order, ordinary categories, empty legacy subfolders, orphan/cross-plan/ambiguous placements and repeated migrations. Check unchanged testcase counts, diagnostic redirections, no Migration Issues folder, and full rollback on validation failure.
- [x] Add Task tests that reject foreign Plan membership and duplicates, observe rename/move live, remove latest results on scope removal and preserve an empty Task after deletion. Add selected-rerun overwrite and unselected-result retention tests.
- [x] Add deletion failure injection at staging, DB flush/commit and restoration boundaries, validating files and DB state. Add actual concurrent SQLite connections for mutation versus execution start.
- [x] Run `python -B -m unittest web_ui.tests.test_plan_current_state` and record expected missing-feature failures before implementation.
- [x] Implement models and migration: normalized sibling constraints including root namespace, testcase folder placement/order, unique membership, canonical four-state values and latest data. Reject invalid same-Plan references; convert old state and remove obsolete attempts storage. Migration runs before application availability and aborts startup on integrity failure.
- [x] Implement domain-level operations in plan_state.py using SQLite write transactions; normalize only changed sibling/order collections. Resolve paths with trim/casefold, merge normalized template paths, reject third levels, preserve independent copied lineage and exact-name duplicate semantics.
- [x] Route every prohibited mutation through ownership and Plan lock validation, including legacy bulk project persistence, imports, builder edits, versioning, publishing and Task edits. Source and destination locks apply to copy/publish.
- [x] Stage executable directories under a private recovery directory; roll back DB and restore staged files on failure. Check subtree impact before destruction; require explicit acknowledgement according to spec.
- [x] Integrate per-testcase persistence with the server runner. Never add scope from results; map setup/unsupported/connection failures to Failed. Stop resets unfinished Running and selected not-started rows to TBD, preserving completed and unselected results. Remove attempt generation and historical report reads.
- [x] Update affected legacy tests for deliberately superseded contracts without weakening unrelated API/layout/lifecycle checks; shadow lifecycle copies every required runtime module.
- [x] Run targeted tests, full Python discovery, compile checks and save concise command/output evidence in `verification/task-1-report.md`.
- [x] Self-review, commit scoped source/test files, then obtain independent task review against spec and resolve findings.

### Task 2: Integrate persistent folders and latest-state execution in the UI

**Files:** index.html, builder.html, plan_workspace_interactions.js and JavaScript interaction tests; backend integration adjustments only where required by verified UI defects.

**Consumes:** Task 1 folder, impact, live scope, execution and summary APIs. Read task-1-report.md for exact implemented response shapes.
**Produces:** A usable existing application with all folder origins equally editable and no historical Task interface.

- [x] Add interaction tests for empty folder rendering, root/child movement, normalized destination preservation, template partial selection, destructive acknowledgement and locked controls. Use real function outputs and request payload assertions, for example a child selection must include its parent path and no testcase copy request.
- [x] Run `node --test web_ui/tests/*.test.js` to observe expected failures.
- [x] Replace inferred category/Custom tree generation with ordered persisted folder IDs. Use stable folder IDs for selection and drag/drop; render root and child folders identically for all origins. Support create/rename/move/reorder/delete, empty roots and children, and testcase reorder within a folder.
- [x] Implement empty-plan, template and custom root/child creation with partial parent selection. Golden copy defaults to equivalent path and supports chosen/new destination. Import understands FOLDER_PATH and legacy CATEGORY and retains invalid/duplicate items for retry.
- [x] Update builder.html import/export to preserve FOLDER_PATH, accepting legacy CATEGORY on load; route inline testcase edits through locked backend APIs.
- [x] Replace destructive dialogs with server-calculated impact and required I understand acknowledgement; on stale destination/409 preserve user input and refresh lock state.
- [x] Display Task live references, canonical statuses and latest logs. Remove Run History/attempt UI and obsolete pending/skipped/interrupted statuses. Start selection through execution/start, persist completion through server lifecycle, stop safely and refresh current summaries.
- [x] Disable all structural/scope operations for executing Plans while retaining viewing/search/log/report/stop controls; backend remains authoritative.
- [x] Run Node tests and inline script parse; run Python contract/layout tests if integration changed. Save evidence in `verification/task-2-report.md`, commit and obtain independent task review.

### Task 3: Reconcile documentation and verify complete isolated workflows

**Files:** CONTEXT.md, status docs, verification report and local browser evidence.
**Consumes:** Tasks 1 and 2; database backup and worktree executable assets.
**Produces:** Accurate glossary/status and reproducible test/browser evidence; retained unmerged worktree.

- [x] Remove Task Snapshot and Archived Test Case definitions from copied glossary; replace with Task and Task Test Case live-reference definitions. Describe Folder Template as structure only without historical semantics.
- [x] Update status and next-step docs to describe implemented current state and any remaining verified limitations. Do not silently leave old history guidance as current architecture.
- [x] Run migration twice on a fresh copy of the original-format backup; compare folder identities, testcase counts and placement, inspect diagnostic log and foreign-key integrity.
- [x] Run Python discovery, compile checks, Node interaction tests and inline JavaScript parse once the final code is stable.
- [x] Launch only the worktree server against its copied DB on an unused localhost port; use safe fake execution steps and isolated scripts. Use browser UI to exercise empty/template plan creation, full folder CRUD, import/copy, live Task rename/move, selected execution/rerun/stop, locking, impact confirmation and current report. Record observed UI outcomes and screenshots.
- [x] Compare main git status to initial evidence, confirming no main file edits; inspect complete branch diff and obtain final independent review. Fix verified findings and rerun affected checks.
- [x] Record commands, counts, browser evidence, migration results and any limitations in `docs/status/2026-09-17-plan-folder-current-state-verification.md`.
- [x] Report branch/worktree, changes and verification results. Leave worktree intact; no merge or deployment.

## Completion evidence

Implementation verified at `af47c02`: Python 119/119, Node 46/46, compilation/parsing, final-copy migration twice, Chrome workflows, unchanged main hashes/status and approved independent final review. See [verification report](../../status/2026-09-17-plan-folder-current-state-verification.md). Worktree retained; no merge or deployment.
