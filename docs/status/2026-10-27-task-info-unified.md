# Unified Task Info — 2026-10-27

## User decisions
- Plan and Test Task Info share the existing Plan Task information layout.
- Task Info exists only under the global Task function.
- Clicking a Schedule Task name opens that Task Info.

## Implementation
Both types use #/tasks/info/<stable-task-id> and one shared renderer: Task Type, Project, SKU, Assignee, Status, start/end dates, working days, Notes, Edit and read-only History. The existing Edit Task form preserves current locks and metadata merging.

Schedule/My Schedule names now use the same global info URL. Legacy Project/Plan/Test Task /info URLs redirect to it. Execution pages no longer wrap themselves in Task List/My Task/Task Info tabs and no longer contain the old Task information form/history subsection; Connection settings, Task scope and Execution & results remain. Existing tester/firmware metadata is preserved, with no data migration or rewrite.

## Verification
Two JS syntax checks and existing Status filter assertions passed. Formal loopback browser checks were read-only: Plan and Test Schedule names, selected global Task navigation, matching information field labels, History, Edit open/cancel, legacy redirect and the three execution tabs passed. Desktop light and short dark screenshots inspected; no JavaScript page errors. No Task save/delete, backend restart or BMC execution.

Evidence: bmca-runtime/verification/task-info-unified-20261027 (outside source). Updates remain local, not published to GitHub.

Follow-up: Task List and My Task name links also use the shared global Task Info URL for both types. Four formal read-only browser checks (two pages × two types), JS syntax and existing Status filter assertions passed; no page errors or Task changes. Evidence: bmca-runtime/verification/task-info-list-links-20261027.
