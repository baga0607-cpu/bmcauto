# Test Plan Workspace Library, Hierarchy, and Search Design

Date: 2026-07-24

## Goal

Improve the new Test Plan Workspace without removing existing plan actions or Classic View. The change makes Golden Plan test cases easier to browse and add, makes folder hierarchy visible in the complete test-case list, and makes plan-wide search compact and obvious.

## Scope

This design covers:

- combining the Golden Plan and file-import entry points;
- organizing the Golden Plan Test Case Library by folders;
- selecting test cases across folders and reporting batch results;
- displaying folder hierarchy in the All Test Cases pane;
- refining the plan-wide search control;
- making duplicate-version behavior consistent in the new workspace and Classic View.
- making version-up synchronization and manual publishing to Golden Plan use the same exact-name rule.

Classic View remains available for comparison. Existing actions such as Delete Plan, Export Selected, and Generate Summary Report remain unchanged.

## Add Test Case Entry

The Test Plan Workspace action bar keeps one purple `+ Add Test Case` button. Clicking it opens a small menu with:

1. `Add from Golden Plan`
2. `Import Test Case`

The separate `Import Test Case` button is removed. Selecting `Import Test Case` invokes the existing file-import flow without changing its behavior.

Selecting `Add from Golden Plan` opens the Test Case Library overlay without navigating away from the current plan.

## Golden Plan Test Case Library

### Layout

The existing overlay remains, but becomes wide enough for a two-column workspace:

- Header: Golden Plan label, Test Case Library title, and library search.
- Left column: folder quick filters.
- Right column: test cases in the selected folder.
- Sticky footer: selection summary and batch actions.

The folder tree contains:

- All Test Cases
- native category folders such as Resource_Chassis, Resource_Manager, Resource_Systems, and Session_Service
- Custom
- Custom child folders such as IBM and 000

Custom follows exclusive folder membership:

- Custom shows only test cases placed directly in Custom.
- IBM, 000, and other Custom child folders show only their own test cases.
- All Test Cases is the only aggregate view.

Selecting a folder only changes the visible list. It never selects test cases automatically.

### Search

Library search spans all Golden Plan test cases and matches test-case name, ID, category, and Custom child-folder name.

When a query is active, the results are not limited by the currently selected folder. Each result shows its folder path so the source remains clear.

Clearing the query restores the previously selected folder.

### Selection

The right-side list header contains a selection checkbox:

- In a folder view, it selects all eligible test cases in that folder.
- In All Test Cases, it selects all eligible test cases in the complete library.
- With an active search, it selects all eligible matching results.

The control is an explicit checkbox. Opening or switching folders never changes selection.

Selections persist when the user changes folders or searches. Test cases already present in the current plan are disabled and excluded from select-all.

The sticky footer always displays:

- total selected test cases, for example `5 test cases selected`;
- `Clear selection`;
- `Cancel`;
- `Add Selected (5)`.

### Batch Results

Adding selected test cases uses partial-success behavior. One duplicate or failed item does not cancel other valid items.

After the operation, the overlay displays a summary such as:

`9 added · 1 skipped (same version already in plan)`

If system errors occur, the summary also includes the failed count. Failed items remain selected so the user can retry or inspect them. Successfully added and skipped duplicate items are removed from the current selection.

The overlay closes automatically only when every selected item was added successfully. It remains open when anything was skipped or failed so the result is visible.

## Exact-Version Duplicate Rule

Version lineage and duplicate prevention are separate concepts:

- `family_id` records that V1, V2, and V3 belong to the same test-case family.
- `family_id` does not prevent different versions from coexisting in one plan.
- Duplicate prevention compares test-case display names.

Before comparison, leading and trailing whitespace is removed and letter case is ignored. Version suffixes are not removed.

Example when the plan already contains `Indicator_LED_Control_V2`:

- `Indicator_LED_Control` is eligible.
- `Indicator_LED_Control_V3` is eligible.
- `indicator_led_control_v2` is a duplicate and is ineligible.

The Library marks known duplicates before selection with `Already in plan`. The backend revalidates the target plan when each item is submitted to handle stale UI state or concurrent changes.

This exact-version rule applies consistently to:

- the new Golden Plan Library;
- Classic View single-item add;
- Classic View batch add;
- backend Golden Plan fork operations.
- Save and Version Up synchronization to Golden Plan;
- manual Add to Golden Plan publishing and membership display.

Classic View batch add also changes from all-or-nothing family rejection to partial success with a result summary.

## Publishing Versions to Golden Plan

There are two ways to publish a test case from a regular plan to Golden Plan:

1. choose synchronization while using `Save and Version Up`;
2. click `Add to Golden Plan` for an existing plan test case.

Both paths use the same normalized exact-name comparison as the Library. `family_id` is copied to preserve lineage but is never used to block publishing.

When `Save and Version Up` requests synchronization, the backend creates the new version in the current plan and its Golden Plan copy as one coordinated operation. The response reports the created plan test-case ID and whether the Golden copy was added or skipped. If Golden Plan already contains the normalized exact name, the current-plan version still succeeds and Golden synchronization is reported as skipped. A real Golden copy failure rolls back the database changes and removes any newly created script directories so the UI does not report a partially synchronized success.

Manual `Add to Golden Plan` performs the same backend exact-name validation. A normalized exact duplicate returns a conflict result; a different version in the same family is published successfully.

The workspace displays `In Golden Plan` only when Golden Plan contains a test case with the same normalized exact name. For example, Golden Plan containing `Indicator_LED_Control_V2` does not mark `Indicator_LED_Control_V3` as present even when both share one `family_id`.

## All Test Cases Hierarchy

When the user selects All Test Cases in Plan Folders, the right-side complete list displays all categories as expanded hierarchical groups.

- Every native category header has a yellow folder icon.
- Custom is a top-level group with a yellow folder icon.
- Test cases directly in Custom appear directly beneath Custom.
- Custom child folders are indented beneath Custom.
- A vertical guide line reinforces the parent-child relationship.
- Child-folder headers have yellow folder icons.
- Test cases inside child folders are indented again.

All groups are expanded by default so the user can still see the entire plan at once. Group headers may be collapsed for visual convenience.

Folder and test-case drag-and-drop behavior remains available. Native folders remain non-renamable. Custom child-folder rename behavior remains unchanged.

## Plan-Wide Search

The plan-wide search input moves into the right side of the Plan Scope header. It remains above and semantically applies to both Plan Folders and the test-case pane.

The input:

- is approximately 290 pixels wide on desktop;
- has a search icon;
- uses the placeholder `Search test cases in this plan…`;
- shows a clear `×` only when text is present;
- clears when the user clicks `×` or presses Escape;
- moves below the Plan Scope title at narrow responsive widths.

Search continues to match name, ID, category, and Custom child-folder name across the complete plan, independent of the selected folder. Clearing it restores the previously selected folder.

The header text `Drag folders on the left; drag test cases in the list.` is removed.

## Error Handling

- Loading failure: show an inline Library error with Retry; keep the overlay open.
- Individual add failure: continue processing remaining selected items.
- Duplicate detected during submission: count it as skipped, not failed.
- Network or server failure: count it as failed and retain that item in selection.
- Project locked or tests running: prevent submission before processing and preserve all selection.
- Import Test Case continues to use its existing error handling.

## Testing

Automated tests cover:

- the combined Add Test Case menu and preserved import action;
- Golden Plan folder grouping and exclusive Custom membership;
- folder switching without automatic selection;
- select-all behavior for All Test Cases, a native folder, a Custom child folder, and active search results;
- selection persistence across folder and search changes;
- selected-count and clear-selection behavior;
- pre-disabled exact-name duplicates;
- V1, V2, and V3 from one family being independently eligible;
- case-insensitive, trimmed exact-name duplicate detection;
- partial success when one item is duplicate or fails;
- Classic View single and batch behavior using the same duplicate rule;
- backend duplicate revalidation;
- Save and Version Up creating both the current-plan version and Golden copy when synchronization is selected;
- Save and Version Up skipping only a normalized exact-name Golden duplicate;
- manual Golden publishing allowing a different version from the same family;
- Golden membership display using normalized exact names instead of `family_id`;
- All Test Cases nested rendering and folder icons;
- compact search placement, clear button, Escape behavior, and responsive layout.

The full existing web UI and lifecycle suite must also pass.
