# Plan Task and Test Task workspaces — 2026-10-28

- Plan navigation opens the current Project's Plan Tasks only. New Task fixes type to Plan and Project to the current Project. Global Task List remains available for Test Task creation.
- Execution opens Add Task by default. Select one or more existing Test Tasks from the current Project; adding views does not create/clone Tasks or change scope. Each chosen Task has its own tab and selected case. Views persist during in-page navigation; a browser reload resets them.
- Task panels reuse current execution controls, membership selection, result annotation and logs. Task Info owns scope and connection editing. Existing Test Plan definition authoring remains at the Test Plans link in Execution.
- Filter removed Tasks on refresh; duplicate additions are disabled. Guard stale panel actions and late responses. A background execution cannot replace another Task's selected case. Prevent starting a second execution while this window monitors one.
- No backend/schema/testcase.py changes or formal data mutations.

## Verification

- Node syntax check and task_management_list.test.cjs passed.
- execution_workspace.test.cjs passed with intercepted fixture APIs: Project/type filtering, multiple additions without writes, same-case/different-Task result and Log isolation, exact membership PATCH target, rapid tab switching, duplicate prevention, keyboard navigation, deleted Task pruning, empty scope, Plan-only creation.
- Light/dark screenshots inspected using isolated browser fixtures. Artifacts: bmca-runtime/verification/execution-task-workspaces-20261028.
- Read-only formal service smoke check at 127.0.0.1:5000 returned 200, confirmed Task summary contract and updated static source. No live execution or DUT tests performed.
