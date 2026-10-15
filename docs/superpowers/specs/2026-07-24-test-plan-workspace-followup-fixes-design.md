# Test Plan Workspace Follow-up Fixes

Date: 2026-07-24

## Scope

This change fixes five issues in the new Test Plan Workspace without removing
Classic View or any existing plan actions:

1. Persist test-case drag ordering across reloads.
2. Keep the user in the current Plan Detail after renaming a plan.
3. Repair publishing a plan test case to Golden Plan.
4. Align folder icons, names, counts, policy labels, and actions.
5. Fully hide the left Workspace navigation when it is collapsed.

## Design

### Plan test-case ordering

Add a plan-specific reorder endpoint that accepts a plan ID and an ordered list
of test-case system IDs. The endpoint validates the plan, updates the
plan-scoped test-case positions in one transaction, and returns a clear 4xx
response for malformed or unknown input.

After a same-category drag in Plan Detail, the client optimistically updates the
list, awaits this endpoint, and keeps the new order only when persistence
succeeds. On failure it restores the previous order and displays the server
error. Task ordering continues to use the existing task reorder endpoint.

Cross-category and Custom-folder moves retain their existing semantics and must
also persist the final plan order after the move completes.

### Rename navigation stability

Plan identity remains the immutable plan UUID. Renaming updates only the plan
name, reloads the project data, and reopens/renders the same Plan Detail using
the original UUID. The active project, folder filter, collapsed folder groups,
and library state remain unchanged.

### Golden Plan publishing

The client sends the source test-case identifier using the backend contract
field `system_id`. Non-success responses are decoded and the backend `error`
message is shown when available instead of reducing every failure to an HTTP
status. After success, project and test-case data are refreshed so the action
changes to “In Golden Plan” without leaving Plan Detail.

### Plan Folders layout

Each folder row uses a stable CSS grid with separate columns for:

- Folder icon
- Wrapping folder name
- Test-case count
- System-folder policy or Custom-folder actions

Subfolders use the same column structure with indentation applied to the icon
column. Long names may wrap, but counts, policy labels, rename, delete, and add
buttons remain aligned. Native folders remain non-renamable.

### Workspace navigation collapse

The top hamburger button controls a single collapsed state. In the collapsed
state, the entire `.app-sidebar` has zero width and no border, padding, labels,
or icon rail remains visible. The main content expands into the released space.
The hamburger button remains in the top header, so it is always available to
restore the navigation. The state continues to use the existing persistence
mechanism if one is present.

## Error Handling

- Reorder operations roll back the optimistic UI state when persistence fails.
- Rename failures leave the current Plan Detail and its identifiers untouched.
- Golden Plan failures display the backend error body when available.
- Network and malformed-response failures use a concise fallback message.

## Testing

Automated tests will cover:

- The plan reorder endpoint persists positions and rejects invalid input.
- Plan Detail uses the plan reorder endpoint and awaits the response.
- Rename retains the immutable plan ID and stays in Plan Detail.
- Golden Plan publishing sends `system_id` and surfaces backend errors.
- Folder-tree markup and CSS expose the fixed alignment structure.
- Collapsed Workspace CSS removes the sidebar width rather than leaving an icon
  rail.

Existing API-contract and lifecycle tests must remain green. Browser validation
will additionally verify reorder persistence after reload, rename navigation,
Golden Plan publishing, long folder-name alignment, and collapse/restore at the
current desktop viewport.

## Out of Scope

- Removing Classic View.
- Renaming native folders.
- Redesigning the test-reference module.
- Changing existing plan actions such as Delete Plan or Export Selected.
