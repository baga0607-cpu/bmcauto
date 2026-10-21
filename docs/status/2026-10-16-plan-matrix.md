# Plan Matrix and Block status — 2026-10-16

The approved Test Plan list now shows Plan, total, completed/total, PASS, FAIL, Block, NR and Task count. Task count toggles an inline Case-by-Tasks matrix with Final. Final takes the latest eligible PASS/FAIL/Block across current memberships using UTC result_updated_at, with manual modification/execution timestamps as legacy fallbacks. NR and Running are ignored; missing scope is a dash; ties prefer the later Task column. Block is manually assignable and counts toward completion. No history model is introduced.

Implementation: web_ui/static/plan_matrix.js, workbench.js, workbench.css, index.html and zh.js; web_ui/models.py, plan_state.py, app.py and report_generator.py. The model check migration retains rows/indexes and adds UTC result_updated_at support. Manual API, summary and report counts include Block. Existing desktop tokens remain unchanged.

Verification reported by the implementation pass:

- test_block_migration.py: 1 passed; extended manual-result tests: 12 passed; current-state tests: 21 passed, 1 historical fixture skipped.
- Isolated browser service 5135 passed examples, timestamp ordering, manual results, NR/Running, empty states, expansion toggles, Block persistence/reload and JavaScript syntax checks at 1440 and 1920 pixels. Screenshots: D:/Codex/bmc_auto_test/bmca-runtime/verification/plan-matrix/.
- Independent review: Ship. Formal service 5000 started and verified with data-row equality, SQLite integrity and foreign-key checks. Pre-startup backup: D:/Codex/bmc_auto_test/bmca-runtime/backups/plan-matrix-20261016/before-startup.db.

PRODUCT.md, DESIGN.md, .impeccable/design.json and CONTEXT.md record this scoped decision. Older four-status guidance is superseded for Block; broader report-format decisions remain open. No publication was performed.

Plan creation refinement: brand is BMCAgent. Create adds an autofocus empty draft row; Save/Enter creates in place. Identical trimmed Plan names within the same Project are rejected with HTTP409 by create and both rename APIs. UI retains draft and shows bilingual duplicate-name message. Case remains significant. Verified on isolated port5136 (duplicate create/rename, unchanged self name, error/focus preservation). Formal5000 restarted only after checking no active execution. Existing records were not renamed or removed.

Latest user amendment: Create now opens a named Test Plan dialog, superseding the inline draft row. Required name receives focus; submit creates a row and keeps the Plan list. Duplicate errors remain inside the modal with the input retained. Cancel/Escape dismiss without creation. Isolated browser verification passed autofocus, required input, duplicate rejection, save/list and cancel.

Parent navigation rule: deleting a Plan returns to its Project /plans list (not default project information). Task deletion returns to its Plan workspace; Project deletion returns to Projects. Rendering a missing Project/Plan/Task route redirects to the nearest existing parent, replacing invalid URL history. Normal project entry still defaults to information. Disposable browser verification passed confirmed Task/Plan deletion and missing-route fallbacks; no formal data mutations.


Home / Projects navigation (2026-10-16): BMCAgent brand links to #/dashboard, which owns the existing all-project list without a sidebar. Projects links to the last valid project ID stored as bmc-last-project in browser localStorage and opens its default information page. Visiting a project or switching the dropdown updates that memory. No selection or deleted remembered project falls back to Dashboard. #/projects resolves the Projects entry for bookmarks. Tasks/Repository unchanged; breadcrumbs and deleted-project fallback use Dashboard. Read-only browser checks passed Home, selection, dropdown, reload persistence, missing-project fallback and global routes.

Repository creation refinement: each folder Actions now has Add Case (+), New folder (folder-plus), then existing Remove (trash; root remains protected). Removed top Add Test Case. Add Case synchronously opens a hidden native .py file input, captures clicked folder ID, imports automatically on selection, and expands that destination. New folder opens a required-name dialog, captures parent ID, displays API errors inline, creates on submit and reveals the child. Existing delete confirmation retained. Isolated port5136 browser test passed icon order, modal focus/validation, parent ownership, file-input import and canceled deletion. No formal data mutations.
