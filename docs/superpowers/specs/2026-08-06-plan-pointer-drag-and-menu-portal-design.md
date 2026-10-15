# Test Plan Pointer Drag and Action Menu Portal Design

## Goal

Fix two usability failures in Test Plan Workspace:

1. Opening a testcase action menu must not create horizontal or vertical scrollbars inside each folder section, and the menu must always remain visible.
2. A user holding the left mouse button to drag a testcase must be able to scroll the center testcase page with the mouse wheel.

## Root Causes

- The row action menu is rendered inside a table wrapper whose `overflow-x:auto` also causes vertical overflow handling. At narrow widths the fixed Category and Actions columns make the table wider than its container, and the menu can be clipped or hidden.
- Chrome's native HTML5 drag-and-drop may suppress wheel events for the duration of a drag. Moving the listener between `window` and `document` cannot make this reliable.

## Action Menu Design

- A testcase row renders only the visible Golden Plan status and the vertical ellipsis trigger.
- The opened Move/Edit/Remove menu is rendered once as a fixed-position portal outside all table and folder containers.
- Its position is calculated from the ellipsis trigger rectangle and clamped to the viewport.
- The menu opens below the trigger when space permits and above it near the viewport bottom.
- Scrolling, resizing, closing, or opening another menu closes the existing portal.
- Table wrappers use visible overflow. The table uses a fixed responsive layout; Category and Actions columns shrink to practical widths and long text truncates instead of creating local scrollbars.

## Pointer Drag Design

- Testcase rows no longer use native `draggable=true` for Test Plan Workspace.
- Pressing the left mouse button on the drag handle starts a pending pointer drag. A small movement threshold prevents an ordinary click from becoming a drag.
- Once active, a lightweight fixed drag preview follows the pointer and the source row receives a dragging state.
- Because this is pointer-based rather than native HTML5 drag, normal `wheel` events remain available.
- During an active drag, wheel input scrolls the center `#view-plan-detail` container. If the pointer is over the Plan Folders list, it scrolls that list instead.
- Pointer proximity to the top or bottom edge continues to provide automatic scrolling.
- `document.elementFromPoint()` identifies the current target:
  - testcase row: reorder relative to that testcase;
  - middle folder header: move into that folder;
  - left Plan Folders node: move into that folder.
- The current valid target receives only the neutral gray `tc-drop-target` feedback.
- Releasing the left button commits the operation through the existing reorder or transactional move APIs. Escape or loss of focus cancels without mutation.

## Compatibility

- Folder-to-folder drag remains on its current mechanism; this change applies only to testcase drag in Test Plan Workspace.
- The `Move to Folder` dialog remains available as an alternative for single and batch moves.
- Golden Plan status stays visible outside the ellipsis menu.
- Classic View behavior is unchanged.

## Error Handling

- No destination under the pointer: cancel without changes.
- Locked/running project: show the existing lock message and cancel.
- API failure: reload server state, remove drag feedback and preview, and show the existing failure message.
- Pointer cancellation, Escape, blur, or view change: clear listeners, preview, source state, and target feedback.

## Verification

- Unit tests cover movement threshold, target classification, wheel routing, and drag cleanup.
- Source-contract tests ensure Test Plan rows do not use native `draggable`, the menu portal is outside table markup, and table wrappers do not use auto overflow.
- Browser checks at wide and narrow viewport widths confirm:
  - zero local table scrollbars;
  - menu visible and positioned within the viewport;
  - wheel changes the center page scroll position while pointer drag remains active;
  - left and middle folder targets show neutral gray feedback.
- Run the complete Python and Node regression suites before integration.
