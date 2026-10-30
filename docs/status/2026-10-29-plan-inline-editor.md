# Plan list inline editing — 2026-10-29

Plan and Test Plans list entries render expandable Plan names without statistics or Task Matrix columns. Expanding one Plan shows the existing Case editor in place: import, folder actions, parameters, source viewing, Rename/Delete and existing locks. One Plan is expanded at a time so shared editor state and Case ownership remain unambiguous. Discard checks apply before switching/collapsing. Direct Plan routes remain compatible. Report behavior is unchanged.

Inline context resolves the selected Plan for every existing API operation. Deleting an inline Plan clears editor state and redraws the list even when the hash is unchanged. Project navigation remembers the list route while inline editing.

Verification: Node syntax and task_management_list.test.cjs passed. Extended execution_workspace.test.cjs passed with Plan expansion/collapse, no statistics table, staying at list URL, Case parameter PUT to the owning Plan and exact edited value, switching to a locked Plan and disabled structural/parameter controls. Dark-theme inline editor screenshot inspected. No formal mutations or DUT execution; browser writes were intercepted fixture APIs.

Plan row action refinement: Rename and Delete now sit on the right of each Plan name row, including collapsed Plans. Row actions resolve their own Plan ID before using the existing edit/delete flow, retain discard checks and execution locks. Removed duplicate buttons inside the expanded editor. Node syntax and browser regression passed, including Rename on a collapsed row selecting the correct Plan.
