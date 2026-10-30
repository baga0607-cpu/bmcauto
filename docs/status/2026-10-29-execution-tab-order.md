# Execution tab drag order — 2026-10-29

Test Task tab labels are draggable. Dropping before/after another Task reorders the complete tab item, including its X button. Dropping on Add Task moves to the end of the Task tabs; Add Task itself cannot be dragged and stays last. Saving uses the existing bmc-execution-tabs-v1 localStorage record, retaining active Task identity. Order restores on refresh/reopen in the same browser profile/origin.

Reordering moves DOM nodes without redrawing the Task pane, preserving result/log context and input drafts. Drag events are isolated from Case/Folder drag handlers. Closing/reopening and cross-Project selections retain existing behavior. No backend or formal data changes.

Verification: Node syntax and task_management_list.test.cjs passed. execution_workspace.test.cjs passed with drag-before, drop-at-end, fixed trailing Add Task, draft/active-Task preservation, reload and reopened-page ordering, plus existing Execution and Plan tab workflows. All API mutations intercepted in browser fixtures; no DUT execution.
