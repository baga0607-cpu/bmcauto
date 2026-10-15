# Persistent Plan Folders and Current-State Tasks Design

Date: 2026-08-24

Status: Approved design; specification only

## Purpose

Replace the mixed native-category and Custom-subfolder behavior with one persistent Plan Folder model, and simplify Tasks so they represent only their current scope and latest testcase results.

This design intentionally favors a small, direct current-state model over historical execution evidence. It supersedes earlier directions that introduced Task Snapshots, Archived Test Cases, Run History, execution attempts, `Skipped`, or `Interrupted` outcomes.

## Scope

This specification covers:

- persistent Test Plan folder structure and folder CRUD;
- migration from legacy category and Custom-subfolder data;
- Test Plan creation from an empty structure or Golden Plan folder template;
- testcase import, Golden Plan copy, identity, placement, and deletion rules;
- Task scope as live references to testcases in the same Test Plan;
- latest-result-only Task execution semantics;
- Plan-wide locking while any Task is executing;
- current-state-only Summary Reports;
- required migration, API, transactional, and verification behavior.

This specification does not implement any schema, backend, frontend, runner, report, or migration change.

## Superseded Decisions

The target model removes these existing or previously proposed concepts:

- native categories with separate permissions from Custom folders;
- `PlanSubfolder` as a special folder type limited to `Custom`;
- folder existence inferred from testcase placement;
- `TaskExecutionAttempt` and `task_execution_attempts`;
- Run History and run numbers;
- Task Snapshot and Archived Test Case;
- environment or configuration snapshots and change history;
- `Pending`, `Skipped`, `Interrupted`, `Invalidated`, and `Superseded` testcase outcomes;
- retention of removed or deleted Task testcase history.

Existing repository documentation and code that describe these concepts represent the pre-migration state, not the target behavior in this specification.

## Domain Model

### Test Plan

A Test Plan owns an ordered hierarchy of Plan Folders and Plan-local Test Cases. It is the consistency and lock boundary for all structural changes.

### Plan Folder

A Plan Folder is a persistent, user-editable node that exists independently of its contents.

- Every folder is stored explicitly.
- Empty folders remain visible and usable.
- Every folder supports create, rename, move, reorder, and delete.
- Default Redfish folders, `Custom`, Golden-derived folders, and user-created folders follow identical CRUD rules after creation.
- The hierarchy permits at most two levels: a root folder and one child level.
- A folder has at most one parent.
- A Test Case belongs to exactly one Plan Folder.

`All Test Cases` is a derived view and is not a persisted Plan Folder.

### Plan Test Case

A Plan Test Case is an executable testcase owned by one Test Plan. Its `system_id` identifies that Plan-local executable copy. Its `family_id` preserves lineage across copies in different Plans.

An exact named family version is represented by:

```text
family_id + normalized_name
```

No separate `version_id` is introduced. `normalized_name` continues to be generated from:

```text
display_name.strip().casefold()
```

Within one Test Plan, `normalized_name` remains unique.

### Task

A Task is one current test assignment under one Test Plan. Its scope consists only of live references to Plan Test Cases owned by that same Plan.

A Task is not a historical snapshot. It does not preserve deleted scope, prior testcase definitions, prior results, attempts, runs, or prior environment values.

### Task Test Case

A Task Test Case is the membership and latest-result record connecting a Task to one Plan Test Case.

Conceptually:

```text
TaskTestCase.testcase_id -> TestCase.system_id
```

The same Plan Test Case can appear at most once in a Task. The record stores only the current membership, current ordering or selection data needed by the Task, latest status, and latest result/log references needed by the current UI and report.

## Plan Folder Invariants

### Depth

- Root folders have no parent.
- Child folders have exactly one root-folder parent.
- A third level is never valid.
- Validation occurs before a move is committed.
- A child folder may move to another root folder.
- A child folder may move back to the root level.
- A root folder containing child folders cannot move under another folder because that would create a third level.

The backend enforces depth constraints even if a client bypasses frontend controls.

### Names

- Folder names are trimmed before storage and comparison.
- Names are compared case-insensitively using a normalized key.
- Sibling folder names must be unique within the same parent.
- Root folders share one sibling namespace.
- The same child name may exist under different root folders.
- Rename and move operations validate uniqueness in the destination parent.

### Ordering

- Root folders have a persisted position within their Test Plan.
- Child folders have a persisted position within their parent.
- Test Cases have a persisted position within their assigned folder.
- Reordering one collection does not silently reorder another collection.
- Positions are normalized transactionally after create, move, reorder, or delete operations.

### CRUD

All persisted folders support the same operations, including folders originally created from default Redfish organization or Golden Plan templates.

Creating a folder validates parent, depth, normalized sibling name, and Plan lock state. Renaming preserves identity and testcase membership. Moving preserves identity and contained Test Cases while validating depth, uniqueness, and Plan ownership. Reordering changes only sibling order.

Deleting a folder means deleting its complete Folder Subtree:

```text
folder
-> descendant folders
-> contained Plan Test Cases
-> affected TaskTestCase records and latest results
```

Folder deletion is permanent in the product UI and requires an impact confirmation before submission.

## Legacy Data Migration

Migration converts the current mixed representation into explicit Plan Folders without losing a valid Plan Test Case.

### Folder Conversion

- Each valid entry in a Plan's `category_order` creates or orders a root Plan Folder.
- Each existing testcase category creates or reuses the corresponding root Plan Folder when it is not already represented by `category_order`.
- Existing `Custom` becomes an ordinary root Plan Folder named `Custom`.
- Each existing `PlanSubfolder` becomes a child Plan Folder beneath that Plan's `Custom` folder.
- Existing category and subfolder order is preserved where deterministic data exists.
- Empty legacy subfolders are migrated and remain empty persisted folders.

### Test Case Placement

- A testcase with a valid legacy category and no Custom child assignment moves to the corresponding root Plan Folder.
- A testcase with a valid Custom child assignment moves to the corresponding child Plan Folder beneath `Custom`.
- A testcase whose legacy category or child-folder relationship is missing, invalid, ambiguous, or orphaned moves to that Plan's `Custom` root.
- Migration does not create a `Migration Issues` folder.
- Migration does not drop or hide an unclassifiable testcase.

### Migration Safety

- Migration is idempotent: rerunning it does not duplicate folders or move already migrated data unpredictably.
- Migration runs transactionally for database changes.
- Migration validates maximum depth, sibling-name uniqueness, folder ownership, testcase ownership, and row counts before completion.
- A technical text log records created folders, moved Test Cases, and every testcase redirected to `Custom`.
- The migration log is a backend diagnostic artifact only. It is not stored as product data and is not shown in the Web UI, Task, or Summary Report.
- A failed migration rolls back database changes and reports enough context to diagnose the affected Plan and testcase.

## Creating a Test Plan

Users may create a Test Plan in any of these ways:

- start with no folders;
- select folders from the current Golden Plan Folder Template;
- define custom root and child folders;
- combine Golden-derived and custom folders.

The Folder Template contains structure only, including empty Golden folders. It does not copy Test Cases.

Template selection follows these rules:

- selecting a root selects all its children;
- clearing a root clears all its children;
- selecting a child includes its parent;
- selecting only some children gives the parent a partial-selection state;
- duplicate normalized paths from template and custom input are merged into one path;
- path merging never creates a third level.

Once the Test Plan is created, template-derived folders have no special protection or origin-based restriction.

## Adding and Importing Test Cases

### Golden Plan Library

Copying a testcase from Golden Plan creates an independent Plan Test Case in the target Plan while retaining `family_id` lineage.

- The default destination is the equivalent Golden folder path.
- Users may choose or create another valid destination before submission.
- Existing normalized folder paths are reused.
- Missing valid paths may be created as part of the operation.
- A path deeper than two levels is rejected for user correction.
- Duplicate testcase detection uses the target Plan's normalized exact name, not `family_id` alone.
- Different named versions from the same family may coexist.
- Batch operations use partial success: normalized exact duplicates are skipped, valid items succeed, and failed items remain available for correction or retry.

Deleting a Golden Plan Test Case later does not affect independent copies already created in other Plans.

### External Import

- The new import format uses `FOLDER_PATH`.
- Legacy `CATEGORY` maps to a root Plan Folder.
- Missing or unresolvable classification defaults to the target Plan's `Custom` root.
- Folder paths deeper than two levels are not flattened automatically; the user must choose a valid destination.
- A valid folder path reuses an existing normalized path or creates the missing valid folder nodes.
- Batch import is partially successful: valid items commit, while invalid items remain for correction.

### Publishing to Golden Plan

Manual publishing and version-up synchronization use the same normalized exact-name rule as Golden Plan import.

- `family_id` preserves lineage but does not block another named version.
- An exact normalized-name duplicate is skipped or reported as a conflict according to the operation contract.
- A different normalized name within the same family is eligible.
- Publishing is forbidden while the source Plan is locked by execution.

## Task Scope Rules

- A Task can reference only Test Cases currently owned by its own Test Plan.
- It cannot directly reference Golden Plan or another Plan's Test Cases.
- Adding a Test Case creates one TaskTestCase with status `TBD`.
- Duplicate membership in the same Task is rejected.
- Users may change Task scope only while no Task under the Plan is executing.
- The execution engine can update status and result data but can never add or remove Task scope.

Because the reference is live:

- renaming a Plan Test Case is immediately reflected in every Task;
- moving a Plan Test Case is immediately reflected in Task views and reports;
- editing its executable definition changes what the next execution runs;
- existing latest `Passed` or `Failed` status is not automatically reset by rename, move, or content edit;
- users create or version a distinct Plan Test Case when they need independent version identity.

Removing a Test Case from Task scope permanently deletes that TaskTestCase's latest status, result, and log references. It immediately disappears from the Summary Report.

## Cascade Deletion and Atomicity

Deleting one Plan Test Case performs this logical operation:

```text
delete Plan Test Case database row
delete its executable files
delete every referencing TaskTestCase and latest result/log association
remove it from every affected Summary Report
```

If the deletion removes the last TaskTestCase from a Task, the empty Task remains. Users may later add other Test Cases or explicitly delete the Task.

Deletion must be atomic across database and executable files:

1. Validate Plan lock and calculate impact.
2. Move executable files to a private temporary recovery location.
3. Apply database deletes in one transaction.
4. Commit only after every required operation succeeds.
5. Restore files and roll back the transaction if any operation fails.
6. Permanently remove temporary files after successful completion.

The product exposes no restore action after a successful delete.

Deletion confirmation displays:

- the folder or Test Case name;
- descendant-folder count when applicable;
- Plan Test Case count;
- affected Task count;
- TaskTestCase count that will be removed.

The confirmation does not expose implementation-level script counts.

An explicit `I understand` acknowledgement is required for:

- deleting any Golden Plan folder;
- deleting any Golden Plan Test Case;
- deleting a non-empty folder in a regular Plan.

Other destructive deletes still show their complete impact before confirmation.

## Execution State Model

Each TaskTestCase has exactly one current status:

```text
TBD
Running
Passed
Failed
```

Status behavior is:

- Newly added or not yet executed: `TBD`.
- Currently executing: `Running`.
- Completed successfully: `Passed`.
- Assertion failure, connection error, unmet condition, unsupported condition, setup failure, or other inability to execute successfully: `Failed`.
- A rerun overwrites the selected Test Case's previous status, result, and latest log.
- Test Cases not selected for a rerun retain their latest state.
- No automatic behavior removes a testcase from Task scope.

When a user stops execution:

- already completed `Passed` and `Failed` results remain;
- currently unfinished `Running` entries return to `TBD`;
- not-yet-started entries remain `TBD`;
- the system does not create an `Interrupted` testcase state or execution-attempt record.

Results are persisted after each testcase completes rather than waiting for the full Task execution to end.

## Plan Execution Lock

If any Task under a Test Plan is executing, the entire Test Plan structure is read-only.

Forbidden operations include:

- create, import, edit, version, publish, move, reorder, or delete a Plan Test Case;
- modify executable testcase content;
- create, rename, move, reorder, or delete a Plan Folder;
- add or remove Test Cases from any Task under the Plan;
- delete the Test Plan.

Allowed operations include:

- view and search the Test Plan;
- view Task and execution state;
- view current logs;
- view the Summary Report;
- stop the active execution.

The lock is enforced by every mutating backend API, not only by disabled frontend controls. Lock acquisition and execution start are atomic so two concurrent requests cannot begin execution and mutate the Plan at the same time. The lock is released only after execution reaches a terminal or stopped state and unfinished `Running` rows have been normalized back to `TBD`.

## Summary Report

The Summary Report is a projection of current Task state only.

It includes:

- the Task's current testcase scope;
- each scoped Test Case's current name and folder path;
- each scoped Test Case's latest status and latest result details;
- current Task firmware, hardware, and environment fields;
- counts for `Passed`, `Failed`, and `TBD`.

For reporting counts, a transient `Running` testcase is included with incomplete work and must not be counted as Passed or Failed. The UI may display `Running` while execution is active; a finalized report cannot retain `Running` after execution is stopped or completes.

It excludes:

- Test Cases removed from Task scope;
- Test Cases deleted from the Test Plan;
- prior results and overwritten logs;
- run or attempt numbers;
- Run History;
- prior environment or configuration values;
- Task Snapshots and Archived Test Cases;
- comparison across executions.

Report generation always queries the current Task, live Plan Test Case references, and latest TaskTestCase states. Previously generated report files are artifacts outside the live Summary Report contract and are not used as a source of current truth.

## API and Transaction Boundaries

The implementation should expose domain-level operations rather than allowing clients to compose unsafe row updates:

- create, rename, move, reorder, and delete Plan Folder;
- assign, move, reorder, import, copy, publish, and delete Plan Test Case;
- add and remove Task scope;
- start, update, stop, and finish execution;
- calculate destructive-operation impact;
- generate the current Summary Report.

Every mutation validates ownership and Plan lock state on the server. Multi-row ordering, subtree deletion, testcase cascade deletion, scope changes, and execution state transitions are transactional.

Responses distinguish validation errors, lock conflicts, normalized-name conflicts, stale or missing destinations, and internal failures. Partial-success contracts are limited to explicit batch import or copy operations; structural moves and destructive operations are atomic.

## Error Handling

- Invalid depth or a normalized sibling-name collision rejects the folder operation without partial mutation.
- A missing or stale destination preserves the user's selection and asks for a valid destination.
- A locked Plan returns a conflict from the backend even if the client appeared unlocked.
- A missing same-Plan testcase rejects Task scope creation.
- File staging or database deletion failure restores the pre-delete state.
- A migration anomaly places the testcase in `Custom`, records it in the technical log, and continues when integrity remains valid.
- A migration integrity failure rolls back the affected transaction and reports the Plan and offending records.
- A result-write failure marks the testcase `Failed` when the current result can still be persisted; if persistence itself is unavailable, execution stops and surfaces an operational error without fabricating a successful state.

## Verification Requirements

Automated verification must cover:

### Folder Model

- persistence and visibility of empty folders;
- CRUD parity for default, `Custom`, Golden-derived, and user-created folders;
- maximum two-level depth enforced by backend rules;
- normalized sibling-name uniqueness on create, rename, and move;
- root, child, and testcase ordering;
- valid child reparenting and invalid third-level moves;
- Folder Subtree impact calculation and deletion.

### Migration

- conversion of `category_order`, categories, `Custom`, and `PlanSubfolder`;
- preservation of deterministic ordering and empty folders;
- placement of orphaned or ambiguous Test Cases into `Custom`;
- no `Migration Issues` product folder;
- idempotency, row-count checks, rollback, and technical log output.

### Test Case Workflows

- Folder Template structure without automatic testcase copy;
- Golden copy preserving folder path by default;
- normalized exact-name duplicate rules and family-version coexistence;
- import mapping for `FOLDER_PATH`, legacy `CATEGORY`, missing classification, and excessive depth;
- partial-success batch import and Golden copy;
- Golden deletion leaving other Plan copies intact.

### Task Current State

- same-Plan live reference enforcement and duplicate-scope prevention;
- immediate Task display updates after Plan Test Case rename or move;
- scope removal permanently removing the latest result and report row;
- Plan Test Case deletion cascading to all TaskTestCase rows;
- empty Task retention after cascade deletion;
- absence of snapshot, archive, attempt, and Run History behavior.

### Execution and Reporting

- only `TBD`, `Running`, `Passed`, and `Failed` states;
- latest-result overwrite on selected rerun and preservation of unselected results;
- per-testcase result persistence;
- stop behavior preserving completed results and returning unfinished `Running` rows to `TBD`;
- backend-enforced Plan lock across every prohibited mutation;
- concurrent execution-start and mutation safety;
- Summary Report showing only current scope, live names and folders, current metadata, and latest results;
- report counts excluding removed or deleted Test Cases and excluding historical execution data.

### Atomic Deletion

- impact preview counts;
- required confirmation policies;
- executable-file staging;
- database and filesystem rollback on each failure point;
- successful permanent cascade deletion with no half-deleted state.

The existing frontend parse, Python compilation, API contract, layout, and isolated lifecycle suites must continue to pass after implementation. Verification must use a copy of the production-format database, never the active production database.

## Acceptance Criteria

The design is satisfied when:

1. Every visible Plan Folder is a persisted, equally editable folder and can exist empty.
2. Folder hierarchy never exceeds two levels, and the backend enforces all name, ownership, ordering, and depth invariants.
3. Legacy folders and Test Cases migrate deterministically; unclassifiable Test Cases remain available in `Custom`.
4. Tasks reference only live Test Cases from the same Plan and retain no snapshot or archived identity.
5. Deleting a Plan Test Case removes all TaskTestCase references and latest results while preserving any Task that becomes empty.
6. Task testcase states are limited to `TBD`, `Running`, `Passed`, and `Failed`, with reruns overwriting only selected latest results.
7. Any active Task execution locks the complete Test Plan against structural and scope mutations at the backend.
8. Summary Reports contain only current scope, current metadata, live testcase identity and placement, and latest results.
9. Run History, execution attempts, snapshots, archived testcases, skipped/interrupted states, and historical comparisons are absent from the target product behavior.
10. Migration and destructive operations cannot leave partial database or executable-file changes.

## Documentation Follow-up

After this Spec is reviewed and approved for implementation, later work must reconcile repository documentation that still describes the superseded model, including the root domain glossary and Task-management status notes. That reconciliation is intentionally not performed in this Spec-only task.
