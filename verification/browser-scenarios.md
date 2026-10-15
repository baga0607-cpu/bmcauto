# Browser verification scenarios

All actions target the isolated localhost server with BMC_WEB_UI_WORKSPACE_DIR=verification/browser-workspace and BMC_MAIN_PROGRAM_DIR=verification/browser-main. The original-format copy contains 17 testcases. Never run these cases against port 5000 or a user server; reserve a new port.

## Visible UI workflows

1. Open Dashboard, navigate copied Project and Plan; verify no JS errors and migrated folders appear.
2. Create an empty Plan; create an empty root and child; reload and verify persistence. Rename root, move child to another root and back to root; reorder roots and children. Attempt third level and normalized duplicate.
3. Create a Plan from partial Golden structure plus custom root/child; verify root partial selection and zero copied testcases.
4. Import a synthetic testcase with FOLDER_PATH and safe steps; verify chosen path. Import valid plus invalid-depth items as a batch; preserve failed items for correction. Copy Golden testcase with default equivalent path; copy another named version from same family and skip exact duplicate.
5. Create Task from live Plan cases; rename and move case, then reopen Task and verify current identity/placement.
6. Execute only synthetic safe cases; inspect per-case persistence before Task finishes. Rerun selected case; verify unselected latest result remains. Start slow synthetic case, inspect locked structural controls, then stop; verify completed state preserved and unfinished state TBD.
7. Open Summary Report; verify current scope, name/path, latest evidence and current environment. Remove one Task scope item and verify report row disappears.
8. Preview testcase/folder deletion impact. Verify I understand required for a nonempty folder and Golden objects; inspect counts without script counts. Confirm synthetic subtree deletion; verify empty Task retained.
9. Verify other Plan in same Project remains editable during execution; active Plan remains viewable/searchable with logs/report/stop available.
10. Export/import builder JSON with FOLDER_PATH and load legacy CATEGORY; verify no path loss.

Capture screenshots and console/network failures. Report unverified scenarios explicitly; do not mark them passed from API-only evidence.
