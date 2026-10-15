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

- [ ] Write real API/domain tests first. A representative folder test must create an empty root, fetch it again, rename it, add a child, reject a grandchild, reject casefold sibling collision, reparent the child and verify stable IDs. Assert specific response codes and database rows, for example:

```python
root = client.post('/api/plans/p/folders', json={'name': ' Network '}).get_json()
assert client.post('/api/plans/p/folders', json={'name': 'NETWORK'}).status_code == 409
child = client.post('/api/plans/p/folders', json={'name': 'Ports', 'parent_id': root['id']}).get_json()
assert client.post('/api/plans/p/folders', json={'name': 'Third', 'parent_id': child['id']}).status_code == 400
```

- [ ] Add migration fixtures for category_order, ordinary categories, empty legacy subfolders, orphan/cross-plan/ambiguous placements and repeated migrations. Check unchanged testcase counts, diagnostic redirections, no Migration Issues folder, and full rollback on validation failure.
- [ ] Add Task tests that reject foreign Plan membership and duplicates, observe rename/move live, remove latest results on scope removal and preserve an empty Task after deletion. Add selected-rerun overwrite and unselected-result retention tests.
- [ ] Add deletion failure injection at staging, DB flush/commit and restoration boundaries, validating files and DB state. Add actual concurrent SQLite connections for mutation versus execution start.
- [ ] Run `python -B -m unittest web_ui.tests.test_plan_current_state` and record expected missing-feature failures before implementation.
- [ ] Implement models and migration: normalized sibling constraints including root namespace, testcase folder placement/order, unique membership, canonical four-state values and latest data. Reject invalid same-Plan references; convert old state and remove obsolete attempts storage. Migration runs before application availability and aborts startup on integrity failure.
- [ ] Implement domain-level operations in plan_state.py using SQLite write transactions; normalize only changed sibling/order collections. Resolve paths with trim/casefold, merge normalized template paths, reject third levels, preserve independent copied lineage and exact-name duplicate semantics.
- [ ] Route every prohibited mutation through ownership and Plan lock validation, including legacy bulk project persistence, imports, builder edits, versioning, publishing and Task edits. Source and destination locks apply to copy/publish.
- [ ] Stage executable directories under a private recovery directory; roll back DB and restore staged files on failure. Check subtree impact before destruction; require explicit acknowledgement according to spec.
- [ ] Integrate per-testcase persistence with the server runner. Never add scope from results; map setup/unsupported/connection failures to Failed. Stop resets unfinished Running and selected not-started rows to TBD, preserving completed and unselected results. Remove attempt generation and historical report reads.
- [ ] Update affected legacy tests for deliberately superseded contracts without weakening unrelated API/layout/lifecycle checks; shadow lifecycle copies every required runtime module.
- [ ] Run targeted tests, full Python discovery, compile checks and save concise command/output evidence in `verification/task-1-report.md`.
- [ ] Self-review, commit scoped source/test files, then obtain independent task review against spec and resolve findings.
