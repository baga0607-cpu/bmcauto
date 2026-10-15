# BMC Agent v4.0 Task Management Status

Last updated: 2026-09-30

## Current Direction

BMC Agent is moving from a simple project/plan/build test runner into a Jira/QMetry-style test management workspace. The current UI supports readable light and dark themes in a focused workspace with a global dashboard, project workspace overview, dedicated plan/task/execution detail pages, and a left navigation model.

The product language is now centered on:

- Project
- Test Plan
- Task
- Test Execution
- Reports
- Issues
- User Management

Legacy Build wording should be avoided in new UI, API, and model work. A Task can still carry firmware information through task setup metadata.

## Completed UI / UX Work

- Added a Jira/QMetry-style global dashboard for all projects.
- Added project workspace overview for a selected project.
- Split high-level navigation into dashboard, test cases, executions, reports, projects, and reserved future modules.
- Changed top toolbar behavior so selecting the current project can still navigate back to Project Workspace.
- Improved browser back/forward behavior through URL state.
- Simplified project workspace panels and removed redundant action areas.
- Added Task Detail and Execution Detail surfaces to reduce dependence on the old combined page.
- Kept unavailable modules visually disabled with no modal alerts.
- Fixed `normalizeViewId` initialization so dashboard/project loading no longer fails with a frontend ReferenceError.

## Completed Database / Backend Work

- Renamed the active data model from Build to Task.
- Replaced `builds` / `build_testcases` database tables with:
  - `tasks`
  - `task_testcases`
- Removed legacy model aliases such as `Build`, `BuildTestCase`, `build_id`, and `builds`.
- Added `task_metadata` on `tasks` for Task ID, owner, firmware version, IDesign link, and related setup fields.
- Added task CRUD and task testcase APIs using task terminology.
- Added contract and isolated lifecycle regression coverage in `web_ui/tests`.

## Implemented Current-State Model (2026-09-17)

The approved [Plan Folder and Task current-state design](../superpowers/specs/2026-08-24-plan-folder-and-task-current-state-design.md) supersedes the earlier execution-attempt design. Implementation and verification are tracked in the [implementation plan](../superpowers/plans/2026-09-17-plan-folder-current-state.md); implementation is complete in `codex/plan-folder-current-state-20260917`, with [verification evidence](2026-09-17-plan-folder-current-state-verification.md). The implementation and later UX refinements were integrated into local main and formal port 5000 on 2026-09-30 after user approval. See the [formal release](2026-09-30-formal-release.md).

- Plan Folders are explicit, persistent nodes with at most root and child levels. Empty folders remain visible and all origins share the same CRUD rules.
- Tasks reference only live Plan Test Cases in their own Plan. Renames and moves appear immediately; removed scope and deleted testcases disappear from current reports.
- Task Test Cases retain only their latest result, using TBD, Running, Passed or Failed. A selected rerun overwrites selected results and leaves unselected results intact.
- Active execution locks the Plan against structural and scope mutation. Stop preserves completed results and returns unfinished Running entries to TBD before releasing the lock.
- Summary Reports query current scope, current metadata, live testcase names/folders and latest evidence.
- Task Snapshots, Archived Test Cases, Run History, execution attempts and historical comparisons are not part of the implemented model.

## Historical Verification (2026-09-17)

The isolated implementation passed 119 Python tests and 46 JavaScript tests, inline script parsing, compilation, fresh-copy migration twice, and real Chrome workflow validation. See the [verification report](2026-09-17-plan-folder-current-state-verification.md) for commands, database isolation, browser evidence and limits. Main's original source hashes and Git status are unchanged.

## Latest design and delivery

The [consolidated design](../superpowers/specs/2026-09-30-plan-task-workspace-current-design.md) covers manual results, log display, Plan grouping, navigator/preview, compact menus and theme readability. See the [delivery plan](../superpowers/plans/2026-09-30-plan-task-workspace-delivery.md) and [formal release](2026-09-30-formal-release.md) for the later 138 Python / 68 Node test results and browser verification. These counts describe that release verification, not a new test run.

## Next Action

Publish the approved implementation and current documentation to GitHub as requested. Keep formal and preview databases independent; no additional feature work is scheduled. Historical execution-attempt proposals remain superseded.

## Full formal GitHub synchronization

The user subsequently authorized publishing all formal implementation commits and local TC assets to GitHub main, with runtime data backed up separately. See [synchronization and backup](2026-09-30-github-formal-sync.md) for fresh validation and restore instructions.
