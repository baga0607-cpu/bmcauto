# Task Status — 2026-10-22

## Behavior
Task planning Status is independent of execution status/results. Allowed values: New, On-Going, Complete, Cancel, Pending. New Tasks start New; legacy missing task_metadata.task_status displays New without backfill. Creation refuses another initial state. Existing Project/Plan/Task ownership and execution locks apply.

Edit Task and Schedule task-bar dialog can change Status. Changes require a nonempty History reason, append immutable old→new Status text and reason, and save in the same transaction. expected_task_status rejects stale edits. Date/Assignee combined edits preserve their existing History behavior; failures roll back metadata. Status History uses existing append-only TaskScheduleHistory storage, no schema migration and no automatic execution/result changes.

Task List/My Task has a Status column with a funnel button in its heading. It opens five checkboxes, supports multiple selected statuses, and combines status choices with comma-keyword search. Defaults include every status. Empty results retain the table heading/filter so the selection can be changed again. Status is also visible in Task Info and Schedule.

## Verification
81 isolated Python tests passed, including six new tests covering both Task types, both update endpoints, all five values, invalid/missing/stale inputs, combined changes, rollback and New defaults. Seven JS assertions cover actual filter events, combined search, empty-results recovery and New form default; three affected JS syntax checks passed.

Isolated browser: Edit Task New→Pending with required History; Schedule Pending→On-Going with a reason; history shows old/new values. Task List filter excludes New and retains the one On-Going Task. Formal read-only browser shows Status column, five choices and nine Tasks. No formal Task data was modified by verification.

Formal backup/copy startup/restart/exact-row verification passed, including integrity/FKs, no active Tasks before restart. Backup: bmca-runtime/backups/task-status-20261022. Existing running service mode and firewall unchanged. Screenshot: bmca-runtime/verification/task-status-filter.png. Preview stopped afterward. Changes are local and not committed/pushed.
