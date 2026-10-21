# Project information view/edit and workbook import — 2026-10-21

## Delivered
- Project information defaults to text and tables. Edit Project explicitly enters editing; Save returns to viewing; Cancel restores the original record. Existing unsaved navigation protection remains.
- Dashboard > Project list > New Project accepts an optional .xlsx document, previews the suggested project name, category/item/SKU counts and source sheets, then creates the Project and information in one transaction. Manual name-only creation remains available.
- Import supports the supplied product-requirement layout: Category / Item / Guidance / Target Specification / Remarks plus optional SKU comparison sheet. Duplicate item names match in occurrence order. Original text, blanks, No, N/A, remarks and SKU values are preserved.
- Unsupported layouts, unresolved formula caches, spreadsheet errors, oversized workbooks, unmatched SKU rows and duplicate project names produce errors without creating partial projects. Supported files: .xlsx up to 10 MB; contents up to 50 MB. Macros are rejected; formulas are never executed.
- Source filename, sheet names, SHA-256 and import timestamp are recorded. No reference project was created in the formal database.

## Verification
- Six isolated backend tests pass (information revision/isolation/cascade and import preview/atomicity/duplicates/raw text).
- Original ProductRequirement_FWA-6084.xlsx parses as 28 categories, 196 rows including headings, 4 SKUs.
- Browser verified view/edit/cancel/save return to view; actual file upload, preview and creation on isolated port 5001 succeeded. Screenshot: bmca-runtime/verification/project-readonly-import-20261021.png.
- Formal port 5000 restarted after checking no active Tasks and SQLite backup to bmca-runtime/backups/project-import-20261021/testcase_meta.db. Formal dashboard loads normally.

## Limitations
- Documents must follow the reference workbook column layout. Arbitrary PDF, Word, legacy .xls and unrelated Excel formats are not supported.
- Import creates reference information only; it does not infer executable Plans, Tasks or Python cases.

## Follow-up: remove Guidance from information views
- Removed Guidance control and explanatory text from Product specifications and SKU comparison, in both view and edit modes. Stored source guidance remains available in imported records.
- Confirmed shared categories/items but separate values: Product specifications uses target/remarks from the requirement sheet; SKU comparison uses per-SKU values from the comparison sheet. Editing either value does not synchronize the other.
- Checked frontend syntax and rendered output in both tabs/modes.

## Follow-up: SKU matrix as default information page
- Removed Basic information and Source document tabs; default is Product specifications. Category selector and SKU comparison remain.
- Product specifications now renders SKU columns and item rows from sku_values, sharing values with SKU comparison. Comparison additionally includes the Difference column and SKU management. Existing metadata/source/aggregate target data remains stored.
- Corrected live difference updates to target the dedicated comparison cell, preventing edits from replacing the last SKU input in Product specifications.
- Verified browser view/edit/tab switching/save and original workbook parsing (FWA-6084 BMC, FWA-6084 HWM, FWA-6084 GPU, FWA-5084; independent 2U/2U/2U/1U values). Frontend syntax passes.
- Screenshot: bmca-runtime/verification/project-sku-matrix-20261021.png. Static changes require a browser refresh, no backend restart.

## Follow-up: grouped specification view
- Project name is the page heading; Edit Project is right-aligned on the same row. Removed saved label, SKU comparison tab and category dropdown.
- One SKU-column table now contains all categories with independent accessible expand/collapse buttons. Collapse state survives edit/cancel/save redraws; hidden inputs remain captured on save. SKU management remains available only in edit mode.
- Browser verified category collapse and preservation through edit/cancel, 776 SKU value inputs rendered in the preview document, and title/action alignment. Both frontend scripts pass Node syntax checks. Screenshot: bmca-runtime/verification/project-category-groups-20261021.png.

- Category headers now show only the collapse arrow and category name; removed item counts at user request. Frontend syntax verified.

- Added Expand all / Collapse all above Product specifications. All categories expand on entry. SKU values differing from the first SKU are blue (light/dark colors), including live editing updates. Browser verified 28 initially expanded categories, 28 collapsed then 28 expanded, and 32 differing cells in reference preview. Both JavaScript syntax checks pass. Screenshot: bmca-runtime/verification/project-expand-differences-20261021.png.

## Sliding sidebar
- Referenced the user-selected Chrome DQIP page: fixed 64px icon rail expands on hover without pushing content. BMCAgent now uses a 64px rail expanding to 280px on hover or keyboard focus, with labelled icons and searchable Project selector. Workspace stays at x=64 in both states. Reduced-motion preference respected. Formal dashboard and keyboard expansion visually verified; JavaScript syntax passes. Screenshot: bmca-runtime/verification/sliding-sidebar-20261021.png.

- Sidebar auto-retract follow-up: replaced hover/focus-within expansion with explicit state. Pointer leave and navigation/project selection close the rail and return focus to workspace; pointer re-entry or keyboard Tab opens it. Workspace x remains 64. Browser verified Task navigation and moving focus to workspace closes the rail; Node syntax passes.

## Project Spec tabs and frozen labels
- Replaced specification heading with Project Spec and Members tabs; removed Expand all / Collapse all controls. Members is an explicitly unconfigured entry only; no member data model was requested or added.
- Specification table has a bounded two-axis scroll region, sticky SKU headers and sticky Item column with an elevated corner cell. Category collapse and blue differences remain. Draft values are captured before switching tabs.
- Verified both tab panels in formal browser, vertical scrolling keeps header at region top, Item sticky left=0, and JavaScript syntax. Screenshot: bmca-runtime/verification/project-spec-sticky-20261021.png.

- Tightened project-name heading to tab spacing by 50 percent: margin-bottom 24px to 12px, scoped to Project Information only.

- Further reduced project heading-to-tabs spacing by 50 percent, from 12px to 6px.

## Explicit Project creation modes
- New Project first offers Automatic creation and Manual creation. Automatic mode requires an XLSX file and successful preview before creation; clearing the file disables creation. Manual mode only asks for a name, then navigates to the new Project with editing enabled and original record captured for Cancel.
- Back resets the pending import and preserves the existing unsaved-discard guard. Browser verified automatic file requirement and disabled creation, switching modes, and actual manual creation into edit mode on isolated port 5001. No formal test project created. Frontend syntax passes. Screenshot: bmca-runtime/verification/project-create-choice-20261021.png.

- Automatic creation no longer requests a Project name. Preview displays the parsed name; creation sends only the workbook and navigates by the returned Project ID. Manual creation retains its name field.
