# Compact Task Info and Scope hierarchy — 2026-11-11

## Latest follow-up: narrow drawer and immediate field dialogs

The drawer now measures 560px (viewport-capped), down from 790px. Overview controls fill the remaining field track, preserving their approximately 234px compact width rather than halving them again; firmware inputs cap at 136px. Overview footer explanations (date scheduling and Test-only firmware guidance) are removed.

For existing Tasks, clicking Plan Start/End Date, Actual Start/End Date or Status immediately opens the same `TaskManagement.openCellEditor` dialog used by Task List. It edits the relevant date pair or Status and requires a Note in that dialog. Cancel does not change the Task. There is no inline mandatory Note or second prompt at Overview Save. New Task initial dates and other fields retain their original direct-edit behavior. Deletion keeps its required-reason dialog. Pending unrelated drawer edits use the existing Save/Discard/Keep editing guard before opening a field dialog. Task List and Task Info share validation, expected values and save API; labels in the shared mandatory reason field now say Note.

Latest verification: updated isolated drawer regression checks immediate date dialog, whitespace reason rejection, cancel without changing dates, successful save and other drawer flows; create/delete browser checks pass. Formal read-only Chrome (non-GET blocked) confirms all five fields open the shared required-Note dialog for Test and Plan Tasks, 560px width and removed explanations. JavaScript syntax and Task List rendering regression pass. Screenshots inspected. No formal Task mutation or backend restart.

The earlier 50%-of-track width description below records the initial compact pass and is superseded by the 560px drawer above.

Task Info content spacing is reduced: field row gap 10→7.5px, input vertical padding 6→4.5px, table cell vertical padding 8→6px. Overview controls occupy 50% of their former field track width, including firmware inputs. Existing one-field-per-row structure is retained. iDesign's enclosing fieldset/legend is removed from the drawer; iDesign Request ID and iDesign Link become direct sibling fields. Original input names, metadata binding and API contract are unchanged. New Task shares this rendering.

Scope uses the Plan folder hierarchy and position ordering, including nested and empty folders, under a BMC root. The table has one Directory / Test Case column; Folder is removed. Folders expand/collapse and select their eligible descendant cases, with mixed selection state. Hidden cases remain mounted so collapse does not affect scope, selection counts, dirty detection or save payloads. Retired cases and execution locks retain their existing restrictions. Scope still imports only case IDs and retains the existing result-removal confirmation.

Verification: JS syntax; formal read-only Chrome checks (non-GET APIs blocked) verify Test/Plan drawer labels, direct iDesign hierarchy, 50% computed width, 7.5px row gaps and 4.5px vertical padding. Isolated port 5017 Chrome verifies nested/empty folders, collapse without dirty changes, selection through collapsed rows, folder selection, save/remove/re-add scope and existing drawer regression flows. Light 1440×900 and dark 1280×720 screenshots inspected. No browser page errors. Tests use disposable workspace/main/temp directories under bmca-runtime/verification/drawer-isolated; formal Task data is not modified. Static source changes need browser refresh, no backend restart or migration. No DUT execution.

Scripts: bmca-runtime/verification/task-drawer-compact.cjs, task-scope-tree.cjs, task-drawer-check.cjs. Preview stopped after checks.
