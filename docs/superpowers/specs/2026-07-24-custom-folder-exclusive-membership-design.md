# Test Plan Folder Semantics and Search Design

## Goal

Make the new Test Plan Workspace treat `Custom` and its child folders as a
real folder hierarchy instead of overlapping aggregate filters.

Add a plan-scoped test-case search that remains practical when a plan contains
hundreds of test cases.

## Folder semantics

- `All Test Cases` remains the only aggregate view and shows every test case
  in the plan.
- `Custom` shows only Custom test cases whose `custom_subfolder` is empty.
- A child folder such as `000` or `IBM` shows only Custom test cases whose
  `custom_subfolder` equals that folder name.
- A test case appears in exactly one location under the Custom hierarchy:
  either directly under `Custom` or in one child folder.
- Moving a test case into a child folder removes it from the `Custom` root
  view. Moving it back to `Custom` clears `custom_subfolder`.

## Counts and full list

- The count beside `Custom` is the number of test cases directly stored in
  the Custom root; it does not include child-folder test cases.
- Each child-folder count is its own direct test-case count.
- The complete list renders separate sections for `Custom`,
  `Custom / 000`, `Custom / IBM`, and other child folders. These sections are
  mutually exclusive.
- Empty root and child sections remain visible so they can be used as drag
  targets.

## Existing data compatibility

No database migration is required. Existing `custom_subfolder` values already
represent exclusive membership:

- null or empty value means the Custom root;
- a folder name means that child folder.

If a test case references a child-folder name that is not present in the
plan's saved folder list, the UI must still expose that folder rather than
hiding the test case.

## Interaction behavior

- Dragging within the same folder changes ordering only.
- Dropping a Custom test case on the Custom root clears its child-folder
  assignment.
- Dropping a Custom test case on a child folder assigns that folder.
- Plan and Task views continue synchronizing the same `custom_subfolder`
  assignment as they do today.
- Native categories remain unchanged.

## Plan search

- Place one search field at the top of `Plan Scope`, above both the folder tree
  and the test-case list. This communicates that the search covers the current
  Test Plan rather than only the selected folder.
- The placeholder is `Search test cases by name, ID, category, or folder...`.
- An empty query preserves the existing folder selection and normal grouped
  list.
- A non-empty query searches the entire current Plan regardless of the
  selected folder.
- Matching is case-insensitive and checks:
  - test-case display name;
  - test-case ID;
  - native category name;
  - Custom child-folder name.
- Step names and module paths are outside the first-version search scope.
- Search results use a flat list so one test case appears only once. Each row
  includes its category path, such as `Custom / IBM`, to preserve location
  context.
- Clearing the query restores the folder filter that was selected before the
  search began.
- Searching does not mutate selection, ordering, folder assignment, or saved
  folder counts.
- The UI shows a clear empty state when no test case matches.

## Verification

Automated tests must cover:

- Custom root count excludes child-folder cases;
- Custom root filter excludes child-folder cases;
- child folders contain only their assigned cases;
- complete-list sections do not duplicate Custom test cases;
- orphaned child-folder assignments remain visible;
- plan search matches name, ID, category, and Custom child-folder name;
- plan search ignores the active folder while a query is present;
- clearing search restores normal folder-filter behavior;
- search results contain no duplicate Custom test cases;
- existing reorder, folder move, and Plan Workspace contract tests continue
  to pass.

Manual verification uses a plan with three Custom test cases: two assigned to
`000` and one assigned to `IBM`. The expected tree is `Custom 0`, `000 2`,
`IBM 1`, while `All Test Cases` still includes all three.

The same plan is searched from a selected child folder. A query matching a
test case in another folder must find it and show its full folder path.
Clearing the query must return to the previously selected child folder.
