# Test Plan Drag and Bulk Move Design

## Goal

Improve Test Plan Workspace organization for both small plans and plans with hundreds of test cases. Keep drag-and-drop as a fast option for short moves, while adding a scalable, searchable batch move workflow.

## Scope

This design changes only Test Plan Workspace interactions and presentation. It preserves Classic View, Golden Plan behavior, project selection, folder ordering, plan locking, and existing test case data semantics.

## Folder Drop Feedback

- A valid test-case drop target uses the same neutral gray treatment as a normal row hover.
- Do not use purple or blue highlighting, an accent outline, or a `Move to <folder>` label.
- Invalid folder-sort targets retain the no-drop cursor and receive no highlight.
- Test-case moves and folder sorting remain separate drag modes so one cannot trigger the other.

## Drag Scrolling

- While dragging a test case near the browser viewport's top or bottom edge, continuously scroll the page in that direction.
- Scroll speed increases gradually as the pointer approaches the edge.
- Stop automatic scrolling immediately when the pointer leaves the edge zone, the test case is dropped, the drag is cancelled, the route changes, or the window loses focus.
- Preserve mouse-wheel scrolling during a test-case drag.
- The Plan Folders body has its own vertical scroll area with a fixed header.
- When the pointer is inside Plan Folders and near its top or bottom edge, scroll only the folder list. Do not scroll the page at the same time.

## Resizable Plan Folders

- Add a subtle resize handle to the right edge of Plan Folders.
- Constrain the panel to a practical minimum and maximum width so folder names remain readable without consuming the test-case workspace.
- Store one shared width for all Test Plans in browser-local storage.
- Restore the default width if the stored value is missing, invalid, or outside the current allowed range.
- The folder tree remains usable and scrollable throughout resizing.

## Row Action Menu

- Replace the current per-row `Remove` control with a vertical `⋮` menu in the same location.
- Keep `In Golden Plan` in its current visible position.
- The menu contains:
  - `Move to Folder` for an unselected row, or `Move selected (N)` for a selected row when multiple selections exist.
  - `Edit`, always scoped to the row whose menu was opened.
  - `Remove`, always scoped to the row whose menu was opened.
- Batch selection never changes the scope of Edit or Remove. This prevents accidental batch deletion.

## Selection Model

- Test-case selections persist while switching Plan Folder filters and while changing search terms.
- Opening Move from a selected row moves all currently selected test cases.
- Opening Move from an unselected row moves only that row and leaves the existing batch selection unchanged.
- The interface continues to show the total selected count across folders and search results.

## Destination Folder Picker

- `Move to Folder` opens a confirmation dialog; it never moves immediately.
- The dialog title shows the number of test cases being moved.
- The dialog contains a searchable, expandable folder tree covering native folders, Custom, and Custom child folders.
- Folder names retain their hierarchy, and the selected destination is shown as a full path such as `Custom / IBM`.
- The confirmation button repeats the affected count, for example `Move 3 test cases`.
- Cancel and close leave data and selection unchanged.

## Move Result Behavior

- Validate that the destination still exists when the move is submitted.
- Submit a batch move as one request rather than issuing one request per test case.
- Test cases already assigned to the destination are skipped; the remaining items still move successfully.
- After success:
  - preserve the active Plan Folder view and search term;
  - clear selection only for successfully moved or skipped submitted items;
  - refresh folder counts and visible test-case rows;
  - report the result and full destination, such as `3 test cases moved to Custom / IBM` or `9 moved · 1 skipped (already in destination)`.
- If the destination no longer exists, keep the selection and reopen or retain the picker so the user can choose again.
- If the request fails, do not optimistically change folder assignments. Preserve the selection and show the server's useful error message.

## Implementation Boundaries

- Reuse the existing test-case-to-folder assignment semantics and permission/lock checks.
- Add a dedicated batch endpoint only if the current endpoint cannot atomically accept multiple test cases. Its contract must return moved, skipped, and failed identifiers plus a display-safe message.
- Keep drag feedback, edge scrolling, panel resizing, selection state, and folder picking as separate units with explicit cleanup paths.
- Do not introduce a new drag-and-drop dependency unless native browser events cannot meet the verified wheel and edge-scroll requirements.

## Verification

Automated and browser verification must cover:

- valid native, Custom parent, and Custom child folder drops;
- neutral gray hover feedback and absence of purple/blue styling and destination labels;
- invalid folder-sort targets remaining non-droppable;
- page edge scrolling, folder-list edge scrolling, wheel scrolling during drag, and cleanup on every drag termination path;
- Plan Folders minimum/maximum resizing, one shared saved width, and invalid-value fallback;
- single-row Move, cross-filter and cross-search batch selection, and batch Move;
- Edit and Remove remaining single-row actions even when multiple rows are selected;
- searchable hierarchy and full-path display in the destination picker;
- native and Custom destinations, already-in-destination skips, missing destinations, locked plans, and backend errors;
- preservation of current view/search state and accurate counts after a successful move;
- regression coverage for project selection, folder sorting, Golden Plan indicators, and Classic View availability.

## Out of Scope

- Batch editing or batch deletion.
- Renaming native folders.
- Changing Golden Plan membership or version rules.
- Removing Classic View.
- Replacing the current drag system with a third-party library unless later verification proves it necessary.
