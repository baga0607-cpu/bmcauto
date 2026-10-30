# Task table field editing and Actual dates — 2026-10-27

## User decisions and interface
Task List/My Task remove Scope, Execution and Actions columns. Ten fixed columns now are Task, Task Type, Status, Assignee, Project / SKU, Plan Start Date, Plan End Date, Actual Start Date, Actual End Date and Working days. Keep the compact viewport scroll surface, sticky headings, filters and Task Info name links.

Double-click Status, Assignee or any of the four date cells to edit that field in a native dialog. Enter/Space/F2 provide keyboard access. Save validates and refreshes while retaining table scroll; cancel/Escape writes nothing. Locked Test Tasks disable their cell controls. Assignee uses the existing shared roster; its immutable History is automatic. Date/status edits require a manual History reason. Incomplete plan dates still force Not Scheduled.

Task Info and its New/Edit form display Plan Start/End Date and the new Actual Start/End Date. Actual dates are manual planning metadata, independent of execution/results and planned dates; no automatic execution synchronization is introduced.

## Data and History
Plan dates retain start_date/end_date keys. Actual dates use optional task_metadata.actual_start_date/actual_end_date, supporting either date independently, ISO date validation and end >= start when both exist. Legacy absent values display empty without read-time migration.

Actual changes require expected_actual_start_date/end_date and a reason, adding immutable Actual dates: old range → new range text in TaskScheduleHistory within the metadata transaction. Existing table date columns retain plan-date snapshots. Existing History UPDATE/DELETE triggers remain unchanged. Combined date/status/Assignee/Actual changes roll back atomically. Bulk project setup containing Actual fields uses the guarded management path. Unrelated metadata updates preserve Actual values; no database schema migration.

## Validation and local deployment
- 74 related Python tests passed in 7.741s in disposable workspace/main/TEMP. Added Actual-date roundtrip, invalid date, stale expectations, reason, combined rollback, execution-evidence preservation, locks and bulk-history protection checks.
- Three JS syntax checks and existing Status filter assertions passed.
- Isolated browser verified both Task types saving all six editable fields, reload persistence, keyboard/cancel, two-tab stale-write rejection, Not Scheduled derivation, Task Info full-form Actual edit, History, stable empty columns and short dark layout. No page errors.
- Formal DB backup and startup against a DB/script copy passed before deployment. Restarted loopback-only service after confirming zero active Tasks. All formal table rows unchanged; integrity/FKs passed. Nine Tasks, including one already unscheduled, preserved.
- Formal read-only browser opened/cancelled all six dialogs from Task List and My Task, and confirmed ten Task Info fields. Preview service stopped. No real BMC execution and no test edits to formal Tasks.
- Runtime evidence/backups: bmca-runtime/verification/task-cell-edit-20261027, outside source publication. Changes applied locally, not published to GitHub.
