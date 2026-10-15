# Toolbar Project Selection and Plan Folder Drag Feedback Design

## Scope

This change fixes two Test Plan Workspace UI regressions without changing testcase data semantics:

1. Keep the toolbar Project combobox label synchronized with the selected project.
2. Let testcase rows drop directly onto every valid folder in the left Plan Folders tree and make the active drop target obvious.

Classic View and unrelated toolbar actions remain unchanged.

## Project Combobox State

The native project `<select>`, custom combobox button, active menu option, `currentProjId`, and navigation URL must always represent the same selection.

After selecting `-- Select Project --`, `Golden_Project`, or any normal project, the project-change flow will update application state and then call the existing `renderProjectSelect()` function. Selecting the already-active project must also refresh the toolbar before reopening its workspace. Clearing the selection returns to My Dashboard and displays `-- Select Project --`.

The fix will reuse the existing state and renderer rather than add a second label state.

## Plan Folder Drop Behavior

Testcase rows dragged from the Test Plan Workspace list may be dropped directly onto:

- Native system folders such as `Resource_Chassis`.
- The `Custom` parent folder for direct Custom testcases.
- Any Custom child folder such as `Custom / IBM`.

The left folder tree and the expanded middle hierarchy will share `dropPlanTcIntoFolder()` as their testcase-move path. Folder-to-folder sorting continues to use `movePlanFolder()` and remains distinct from testcase movement.

Dropping onto a folder that already owns the testcase is a safe no-op or metadata refresh; it must not duplicate the testcase. Existing project execution locks continue to reject moves.

## Drag Feedback

While a testcase is being dragged over a valid target, the entire folder row will show:

- A blue-purple tinted background.
- A bright accent border or inset outline.
- A brighter folder icon and folder name.
- A compact label such as `Move to Resource_Chassis` or `Move to Custom / IBM`.

The feedback is applied on `dragenter`/`dragover` and removed on `dragleave`, `drop`, `dragend`, or rerender. Invalid targets do not highlight and keep the browser's no-drop behavior.

Folder-reordering feedback uses a separate CSS state so testcase movement and folder sorting cannot trigger each other's handlers.

## Error Handling and State Refresh

The existing backend move and testcase patch APIs remain authoritative. After a successful drop, projects and testcase metadata reload before the plan detail rerenders so folder counts and labels are current.

On failure, the drag state and visual feedback are cleared, data is reloaded, and the existing `Move failed` message is shown. No optimistic state is left behind.

## Verification

Automated frontend contract tests will cover:

- Project toolbar text after clearing, switching to Golden Project, switching to FWA, and reselecting the active project.
- Every left-tree folder type routing testcase drops through the generalized handler.
- Folder sorting still routes through `movePlanFolder()`.
- Drag highlight and cleanup events/classes.
- The `Move to <folder>` target label.

Browser verification will confirm the toolbar label and visual drag target on the isolated 5001 service. The complete `web_ui/tests` suite and JavaScript parsing must pass before merging to `main`.
