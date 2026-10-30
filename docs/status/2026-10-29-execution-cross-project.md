# Execution across Projects — 2026-10-29

Supersedes Project-scoped Execution views. Execution uses #/execution and one shared in-memory tab set. Legacy #/project/<id>/execution redirects to the shared workspace. Plan Task management remains Project-scoped.

Add Task opens a Project selector and that Project's existing Test Tasks. Pending selection is retained in a Set across Project switches until Add Selected Tasks or dialog dismissal. A selected-items area shows Project / Task and permits removing pending choices. Adding opens all pending Tasks at once, deduplicating already open tabs. Cancel/Escape does not add Tasks.

Each active Task resolves its owning Project and Plan independently of the navigation Project. Scope, result, log, connection and execution actions keep the selected Task identity. Closing a tab affects only the view.

Verification: Node syntax, task_management_list.test.cjs and execution_workspace.test.cjs passed. Browser fixtures cover three Tasks across two Projects, pending-selection retention, combined addition, cross-Project evidence, shared tabs through legacy Project routes, Task membership PATCH ownership, close/reopen without DELETE or creation, race handling and Plan-only management. Modal screenshot inspected. No formal data writes or DUT execution.
