# Test Case ordering and drag/drop — 2026-10-19

## Behavior

- Repository, Plan, import source, Task scope/results and Plan matrix use folder-local natural number ordering (RF-01-2 precedes RF-01-10).
- Explicit before/after moves persist a custom order. New items follow the custom selection in natural order. Resorting on a folder clears its override and restores automatic number sorting for its direct Test Cases; child folders retain their own order. The virtual Plan BMC root is supported.
- Folder Actions expose a sort SVG button with the Resorting tooltip/accessibility name, including the current Plan pane during import. The source pane remains read-only.
- Valid drop rows have dashed frames; the active inside/upper-half/lower-half frame indicates folder placement or before/after insertion. Self/descendant drops and reverse import drops are rejected. Both dragenter and dragover accept valid targets; dragleave/end clear feedback.
- Repository case-only batches support anchored insertion; batches containing folders can only move to directories. Plan case moves and source-case imports support anchored insertion. Existing conflict overwrite semantics preserve existing target placement/evidence; newly added cases use the requested anchor.

## Implementation and preservation

`case_order.py` owns natural comparison and folder-specific persistent overrides in the additive `case_list_orders` table. No existing table columns or source/settings/evidence are rewritten by default sorting. Reorder operations retain ownership, Plan execution locks and transaction rollback. Source copies remain independent. Task display ordering uses Plan folder order without rewriting Task evidence or execution positions.

Local backup: `D:/Codex/bmc_auto_test/bmca-runtime/backups/case-ordering-20261019/`. Preview: port 5137, explicit workspace/main-program overrides under `bmca-runtime/verification/case-ordering/`. No public commit/push or tunnel.

## Verification

- `python -m unittest test_case_ordering test_single_case_repository test_repository_tree test_plan_current_state -q`: 53 tests, 52 passed and 1 historical fixture skipped. Isolated workspace/main-program/TEMP/TMP overrides.
- `node --test web_ui/tests/case_order_drag.test.cjs`: 4 passed; folder dragenter acceptance, before/after halves, clearing feedback, self/cycle rejection, case-only batch restriction, Plan lock, root and read-only source.
- `node --check web_ui/static/workbench.js`: passed.
- Copied-database application startup twice: all pre-existing table rows identical, integrity_check ok, foreign_key_check empty; only new table is case_list_orders.
- Native browser on isolated 5137: Repository before/after insertion, persistence after reload, cross-folder move, Resorting; Plan before insertion and Resorting; source split layout, reverse rejection, source-to-case conflict and cancel.
- An initial UI check exposed missing dragenter acceptance on folder rows; fixed and actual cross-folder drag then succeeded. A backend test exposed the generic Plan write guard treating the Repository resort folder as a Plan folder; endpoint classification corrected.
- Desktop scope only. No physical BMC execution tested.

Formal deployment completed: no active Tasks before restart; HTTP 200 and native browser verified ascending Repository cases and Resorting controls on port 5000. Every pre-deployment existing table row is identical after startup; SQLite integrity/FK checks pass. Only the additive case_list_orders table was created. Screenshot: bmca-runtime/verification/case-ordering/formal-repository.png. Formal data was not used for mutating verification.


## Import-mode project navigator (2026-10-19)

The left Project navigator is hidden while the Plan import workspace is present, and its column is released so the target/source panes use the full width. Every exit from import mode restores the navigator, including source Close, opening a current Case View and route changes. CSS keys off the rendered import workspace, with no persisted hidden state.

Read-only formal browser checks: import mode navigator display=none and workspace left=0, no horizontal overflow; source Close restores display=flex and the 260px sidebar; opening current Case View also exits import mode and restores the sidebar. No data mutation or backend restart. Screenshot: bmca-runtime/verification/case-ordering/import-sidebar-hidden.png.
