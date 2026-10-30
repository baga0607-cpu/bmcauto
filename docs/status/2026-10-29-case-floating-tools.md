# Automation declarations, parameter completion and floating Case tools — 2026-10-29

## Automation

TEST_CASE.automation remains the explicit classification source, per user choice. automatic = fully automatic / gear (no operator intervention); semi_automatic = semi-automatic / wrench (pre-entered parameters or runtime answers); manual = fully manual / person, reserved with no new manual workflow. The parser accepts manual. No runtime/code inference or existing Case source rewrites were introduced. Existing undeclared sources remain Unclassified. Plan adaptation still cannot change source classification.

## Parameter status

Projects overview returns parameter_count, parameters_complete and missing_parameters without returning parameter values. Missing fields, null or blank/whitespace strings are incomplete; numeric 0 and boolean False are complete. Plan Parameters buttons are blue for incomplete saved values and white when complete. Updates use the existing definition API, preserving revision conflicts, locks and result rerun marking.

## Floating tools

Python Source Viewer and Parameter Editor are independent modeless browser windows, each movable by its title bar and resizable using its bottom-right handle. Geometry is clamped to the viewport and retained while switching Cases within the session. Both may be open simultaneously. Source remains read-only. Opening through context actions or Parameters buttons selects the matching Case; clicking another Case name updates open tools. No-parameter Cases clear the Editor to an explanatory empty state. Repository parameter defaults remain read-only; editable values belong to Plan copies.

Each window stores its own explicit Case/Plan reference. Stale async responses are dropped, saves use the loaded revision and source, and unsaved parameter switches/closes require discard confirmation. Running Case fields are disabled; save errors retain the draft. Navigation closes tools after draft protection. Saving parameters refreshes list status without rebuilding window geometry. Existing list/sidebar previews are replaced for these actions. New module: web_ui/static/case_windows.js.

## Verification

- 26 Python tests passed: 20 single-Case Repository/definition/lock/conflict tests, 4 automation declaration tests updated for manual, and 2 parameter-completion tests.
- case_windows.test.cjs passed automation/person icon, incomplete/complete colors, 0/False values, both floating windows, move/resize, exact save ownership/revision, draft cancellation, rapid Case race handling, no-parameter/locked Cases and read-only Repository.
- execution_workspace.test.cjs, hierarchical_selection.test.cjs and task_management_list.test.cjs passed with the new tools.
- Light/dark screenshots inspected; syntax checked for both scripts. Isolated Python workspace: bmca-runtime/verification/case-windows-20261029. Browser mutations were intercepted fixtures. No DUT execution.
- Formal service restarted only after verifying no active Task and matching server.py ownership. Existing Projects API content was identical after excluding the two new completion-summary fields; 12 real Cases received summaries. New module returned HTTP 200. Formal browser smoke check opened Viewer and Editor for the same real Case with zero API writes/browser errors. Existing scripts, settings and evidence were not modified.

## 2026-10-29 — Native tool windows
Supersedes viewport-constrained panels: Viewer and Editor now use separate same-origin browser popup windows, with OS title bars and resize borders. They can move outside the main browser and between monitors. Main Case selection still synchronizes both windows; revisions, locks, dirty draft protection, Repository read-only behavior and theme synchronization remain. Popup blocking produces an actionable message. Each main browser tab uses unique window names. Closing a child removes it from synchronization; main navigation closes children after draft protection.

Verification: case_windows.test.cjs passed with independent Playwright pages, separate viewport resizing, two parameter saves, Case switching, dirty cancellation, delayed response races, no-parameter/locked Cases and Repository read-only state. Actual cross-monitor OS dragging requires user hardware verification; headless checks confirm separate top-level browser contexts rather than viewport-bound DOM panels.

## 2026-10-29 — Default right-side tools with explicit detach
Viewer and Parameter Editor now default to a right-side dock in the main page. Main workspace reserves room for the dock; when both tools are docked they share the available height. Each header has Open in Window. Clicking it moves the existing DOM into a native popup, retaining Case identity, loaded revision, unsaved field values and handlers. A blocked popup leaves the original dock intact. Only detached windows receive native focus; completing a definition fetch no longer re-focuses them. Closing and reopening a tool defaults to the page dock. Case selection, locks, saved completeness colors and Repository read-only rules remain.

Verification: case_windows.test.cjs and execution_workspace.test.cjs passed against fixture APIs, including default single-page rendering, explicit detach, unsaved draft retained through detach, Case synchronization, saves, locks, races and navigation. Screenshot inspected at 1440x1000: right-side Viewer and remaining Plan list fit without overlap. Formal /case_windows.js serves the current static code; no backend restart, data mutation or DUT execution required.

## 2026-10-29 — Independent windows cancelled
User cancelled the independent-window approach. Viewer and Parameter Editor now only display in the main page right-side dock. Removed Open in Window controls, window.open, child-window lifecycle and popup focus/theme code. Existing Case synchronization, parameter draft protection, saves and locks remain.
Verification: case_windows.test.cjs passed, including two right-side panels with a single browser page and no detach controls, saves, Case switching, stale responses, locks and Repository read-only behavior.

## 2026-10-29 — Plan list viewport boundary and explicit tools
Normal Plan Case list now ends 24px above the viewport bottom, matching Task List's sizeSchedule rule (minimum height 120px). List contents scroll internally; resize, Plan redraw and tool docking recompute the height. Import dialog sizing remains independent.
Case name clicks/Enter only switch tools that are already open. They never open Viewer or Editor implicitly; context-menu Source and Parameters actions explicitly open the corresponding tool. Closing Viewer while Editor remains open does not reopen Viewer when selecting another Case.
Verification: case_windows.test.cjs passed bottom-boundary assertions at 1000px/850px viewport heights, no-tools click, Viewer-only switching and Editor-only switching, alongside parameter saves/locks/draft/race checks. execution_workspace.test.cjs passed fixture workflows.

## 2026-10-29 — Plan workspace frame
Plan authoring now renders in this order: Plan title with Project name underneath; full-width Plan tabs (Add Plan last); toolbar containing Find Test Case, Import Test Case, Rename and Delete; Case list. Rename/Delete use the selected Plan and retain existing lock behavior. Removed the old title-row actions. Inline editor no longer has the historical 70vh scrolling wrapper, allowing the Case list to retain the Task List-aligned bottom boundary.
Verification: case_windows.test.cjs passed geometry/order assertions and toolbar action order, existing bottom-boundary/tool/save checks. execution_workspace.test.cjs passed including Rename, tab creation/reordering and persistence. Inspected 1440x1000 screenshot. Fixture APIs only; no formal data or DUT execution.
