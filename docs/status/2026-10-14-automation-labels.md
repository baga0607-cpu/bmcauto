# Automation classification badges

Declared literal TEST_CASE.automation accepts automatic and semi_automatic. Omission remains compatible and displays Unclassified. Metadata validation does not execute the Python source or infer behavior. Classification does not alter execution or operator-input behavior.

Repository list/read-only preview, Plan list/editor and Task scope/execution/evidence show badges. Plan copies retain their classification after Repository deletion. Plan adaptations cannot switch classification; import a new standard source generation for that change. No database schema migration.

The downloadable Python example and README declare automatic. Repository timestamps now advance by a microsecond if a unique source timestamp collides under the transaction; frozen-clock coverage verifies distinct generations.

Verification: isolated unittest discovery ran 91 tests, 90 passed and 1 skipped. Frontend Node syntax compilation passed. Disposable Chrome CDP browser verified all badge locations and all three labels at desktop 1440/1920. Screenshots and scripts: bmca-runtime/verification/automation. Backup: bmca-runtime/backups/automation-20261014/source-before.zip and before.db. No real DUT execution, commit or push.

2026-10-14 Repository presentation update: automation SVG icons precede case names (accessible labels and tooltips). List secondary text is source version, with no description or duplicate version column. Parameters opens read-only editable-field definitions/defaults in the right panel; View opens source in the same panel. Close returns to the full-width list. Desktop Chrome verified 1440/1920, populated/empty parameters, icon order and panel switching. Frontend syntax passed. Backend unchanged; prior 90-pass/1-skip results are historical evidence.

Repository .py downloads removed at user request: no example download or source-file download entry/event handler. View retains read-only source inspection. Plan JSON export remains independent.

Repository compact desktop spacing: smaller workspace/header/toolbar gaps, 9px row padding, 28px small buttons, 16px detail-panel padding and denser source/parameter content. Rechecked Parameters/View/close and 1440/1920 desktop layout through disposable Chrome.
