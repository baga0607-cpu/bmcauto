# Permanent multi-selection and Schedule range — 2026-10-29

## Case and folder selection

Plan, Repository and import-source lists show Case/folder checkboxes directly. BMC root checkboxes are disabled. Repository no longer has a Batch operations / Finish batch mode button; existing Delete selected appears when anything is selected. Folder clicks and right-click actions remain separate from checkbox selection. Selection survives search/collapse.

Dragging a selected item carries its mixed Case/folder selection. Repository uses its existing atomic batch endpoint. Plan uses POST /api/plans/<id>/items/move; source imports use kind=selection with folder_ids/case_ids. Parent/descendant selections are deduplicated, preserving folder trees and current Task evidence. Validation/lock/cycle checks and commit rollback are transactional. Root selection is rejected. Normal single-item dragging and context actions remain compatible.

## Schedule

Calendar end is the last day of the month three calendar months after the latest available Task Plan End Date (including an end-only Task). Example: 2026-10-29 → 2027-01-31. If no Task has an end date, retain the existing today+60-day fallback. Upper bound remains 9999-12-31. Start date retains its existing rule except it cannot exceed the computed end.

## Verification

- 40 backend tests passed: 4 mixed-selection, 5 batch import, 20 single-Case Repository/import, 4 ordering and 7 Repository tree tests. Isolated workspace/scripts/temp: bmca-runtime/verification/mixed-selection-20261029.
- Browser workflow passed: always-visible Case/folder checks, disabled root, no Repository mode toggle, mixed Plan drag payload, mixed source batch import, selection clearing, context-menu/rename and existing Plan/Execution workflows. Screenshot inspected; browser writes intercepted with fixtures.
- Schedule unit checks passed for multiple Tasks, end-only Tasks, January/February month ends, leap year, crossing year and max supported date. JavaScript syntax checks passed.
- Formal restart only after no active Tasks and verified server.py ownership; Projects API state identical before/after, HTTP 200. No formal import/move/delete or DUT execution performed.
