# Cascading folder selection and row backgrounds — 2026-10-29

Plan, Repository and Import source folder checkboxes cascade selection/unselection through all descendants, including collapsed folders and Test Cases. Parent state is derived bottom-up: all children selected checks the parent; some children selected shows indeterminate; no children selected clears it. Empty folders retain independent selection. BMC roots remain disabled but reflect aggregate selection state. Header select-all remains synchronized.

Only fully selected folders are stored as whole-folder selections. Partial parents are excluded from whole-folder move/delete/import payloads. Dragging a partial parent uses the selected descendant items, protecting unselected content. Source/Plan/Repository grouping remains compatible with existing backend subtree deduplication.

Folder row fills are transparent in Plan, Repository and Import lists for both themes. Table headings and drag-target feedback remain distinct.

Verification: hierarchical_selection.test.cjs passed cascade, three-level partial/full ancestors, collapsed descendants, empty folders, select-all sync, partial-parent drag payloads and transparent row backgrounds in light/dark across all three list types. execution_workspace.test.cjs passed the existing complete UI workflow with updated cascade counts. Node syntax and task-management/Schedule tests passed. API mutations were intercepted browser fixtures. No backend changes, formal mutations, service restart or DUT execution.