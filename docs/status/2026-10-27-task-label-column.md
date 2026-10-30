# Task column follows Schedule — 2026-10-27

Task List/My Task now place Task Name on the first line and Assignee / Status on the secondary line, following Schedule's hierarchy and typography. Task name still opens Task Info. Assignee/Status retain keyboard and double-click editing through inline text controls.

Remove the separate Assignee and Status columns and the complete Status-filter UI, selected-state logic and event handlers/styles. All statuses are visible unless excluded by the existing keyword search. Remaining eight fixed columns: Task, iDesign ID, FW Package, four Plan/Actual dates, Days (Actual/Plan). Keep the 61px data row height, sticky header, viewport bottom margin, metadata/date editors and complete hover text.

Validation: JS syntax and revised task_management_list.test.cjs assertions passed (replaces obsolete status-filter test). Formal read-only checks covered 1440x900, 1920x900 and 1100x600 My Task: eight columns, all nine Tasks, no filter controls, matching assignment/status values, 61px rows, open/cancel inline editors, stable populated/empty widths, restored search and 24px bottom gap. Screenshot inspected. No backend change/restart or Task edits. Evidence: bmca-runtime/verification/task-label-column-20261027. Applied locally, not published.
