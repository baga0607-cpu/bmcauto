# Task workspace tabs — 2026-10-19

Top-level Tasks now opens Schedule by default. Schedule displays Task Timeline only; My Task displays Task List only. Until ownership/users are implemented, My Task lists all Tasks. Existing search and New Task remain available; edit/delete stay in the list. Tab changes respect unsaved-form confirmation. Project navigation memory is retained.

Changed workbench.js and task_management_ui.js. Both passed Node syntax checks. Browser verified Schedule default, My Task list, empty search state, and leaving/re-entering Tasks resets to Schedule. No browser errors, data changes or restart. Screenshot: bmca-runtime/verification/task-schedule-tab.png.
