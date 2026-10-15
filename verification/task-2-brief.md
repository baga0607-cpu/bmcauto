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


### Task 2: Integrate persistent folders and latest-state execution in the UI

**Files:** index.html, builder.html, plan_workspace_interactions.js and JavaScript interaction tests; backend integration adjustments only where required by verified UI defects.

**Consumes:** Task 1 folder, impact, live scope, execution and summary APIs. Read task-1-report.md for exact implemented response shapes.
**Produces:** A usable existing application with all folder origins equally editable and no historical Task interface.

- [ ] Add interaction tests for empty folder rendering, root/child movement, normalized destination preservation, template partial selection, destructive acknowledgement and locked controls. Use real function outputs and request payload assertions, for example a child selection must include its parent path and no testcase copy request.
- [ ] Run `node --test web_ui/tests/*.test.js` to observe expected failures.
- [ ] Replace inferred category/Custom tree generation with ordered persisted folder IDs. Use stable folder IDs for selection and drag/drop; render root and child folders identically for all origins. Support create/rename/move/reorder/delete, empty roots and children, and testcase reorder within a folder.
- [ ] Implement empty-plan, template and custom root/child creation with partial parent selection. Golden copy defaults to equivalent path and supports chosen/new destination. Import understands FOLDER_PATH and legacy CATEGORY and retains invalid/duplicate items for retry.
- [ ] Update builder.html import/export to preserve FOLDER_PATH, accepting legacy CATEGORY on load; route inline testcase edits through locked backend APIs.
- [ ] Replace destructive dialogs with server-calculated impact and required I understand acknowledgement; on stale destination/409 preserve user input and refresh lock state.
- [ ] Display Task live references, canonical statuses and latest logs. Remove Run History/attempt UI and obsolete pending/skipped/interrupted statuses. Start selection through execution/start, persist completion through server lifecycle, stop safely and refresh current summaries.
- [ ] Disable all structural/scope operations for executing Plans while retaining viewing/search/log/report/stop controls; backend remains authoritative.
- [ ] Run Node tests and inline script parse; run Python contract/layout tests if integration changed. Save evidence in `verification/task-2-report.md`, commit and obtain independent task review.
