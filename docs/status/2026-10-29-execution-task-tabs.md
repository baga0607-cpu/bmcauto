# Execution Task tabs — 2026-10-29

- Removed Project name below Execution heading.
- Add Task is a button at the end of the Task tab row. It opens a modal multi-select dialog for existing Project Test Tasks. Cancel/Escape preserves the active view.
- Chosen Tasks become tabs before Add Task. Already open Tasks cannot be added twice.
- Each Task tab has an accessible X button. Closing changes only in-memory view state, retains Task/scope/results/logs, and does not stop active execution. Active-tab closure selects the next surviving tab, falling back to the previous tab or an empty workspace. Closed Tasks can be reopened through Add Task.
- Updated execution_workspace.test.cjs passed: modal selection/cancel, order, closure/reopen without DELETE or creation, Project/type filtering, result/log ownership, rapid switching, keyboard navigation, deleted Tasks, empty scope and Plan-only creation. Syntax and existing task_management_list.test.cjs passed. Light/dark browser fixture captures checked. No DUT execution or formal DB writes.
