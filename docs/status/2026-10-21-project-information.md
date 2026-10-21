# Project Information framework — 2026-10-21

## Delivered

Project Information now has Basic information, Product specifications, SKU comparison and Source document sections. Users can edit/save metadata, per-item target specifications and remarks, add/name/remove SKU columns, and edit independent SKU values. Category selection keeps the page manageable. Differences update from current SKU values; blank means unspecified. User text and source wording are preserved, with HTML escaping in the UI. Source fields are read-only in the UI and remain empty for manual data.

This is the requested information framework for future workbook import. There is no workbook upload/import control in the Project creation page yet. No FWA-6084 production Project or reference target specifications were created automatically. Existing/new Projects get an empty template on GET; storage is created only on Save. The information does not change Plan definitions, Task connection settings, scope or evidence.

## Reference evidence and import contract

Source: user-supplied ProductRequirement_FWA-6084.xlsx, downloaded through the authenticated Chrome Excel UI. Local source: C:/Users/david.huang/Downloads/ProductRequirement_FWA-6084.xlsx. SHA-256: b99468915209f9d78aa26a7375692a459d28a439ec6e3a5c45614555de3ca643.

FWA-6084!A1 contains title/product/author. Row 2 headers are Category, Item, Guidance / Example, Target Specification, Remarks / Comment. Rows 3–226 define 28 categories and 196 item rows (including subsection headings). Category labels fill down only within their category; preserve subsection rows such as Management Port and Traffic Port. The blank shipped template includes names/guidance, not this product's target values or remarks.

SKU 比較!A1:H195 has category, item, difference marker, four SKU columns and remarks. D1:G1 are FWA-6084 BMC, FWA-6084 HWM, FWA-6084 GPU, FWA-5084. Do not collapse variants into one value or interpret No/N/A/blank as equivalent. Never convert the separate FWA-5084 column into a new Project implicitly. The 194 comparison rows matched the source category+item+occurrence sequence in the isolated reference preview. Duplicate labels (e.g. Ethernet controller) require section/occurrence disambiguation; do not join by label alone.

Future import mapping:
- Product/title/author -> document.metadata; document version remains empty if absent.
- Category -> categories[].name with stable IDs; item -> items[].name with unique IDs.
- Guidance, target, remarks -> guidance, target, remarks, preserving original text.
- SKU column header -> skus[{id,name}]; cell -> item.sku_values[sku_id].
- Cell locations -> item.source_ref; filename, sheet names, timestamp and file hash -> document.source.
- Difference column is reference evidence only; compare current values for UI differences.
- Import must preview detected project name, categories, SKUs and unmapped/ambiguous rows, then create Project + ProjectInformation atomically. Same-name existing Projects must not be overwritten implicitly. Formula cells need cached displayed values or an explicit unresolved warning; no macro execution or external link fetching. Keep parser rules separate from UI/storage and preserve nonmatching fields until mapped.

## Storage and validation

New additive project_information table: project_id FK with ON DELETE CASCADE, document JSON, revision, updated_at. GET/PUT /api/projects/<id>/information. schema_version=1. Revision comparison prevents stale overwrites. Request-owned transaction follows existing platform serialization. Bounds: 2 MB encoded document, 100 categories, 2000 items, 32 SKUs; unique category/item IDs and case-insensitive SKU names. Reference information is independently editable while a Task executes.

## Verification

- Four isolated API tests passed: empty template/no seed write, Unicode/SKU/source round trip and project isolation, stale write/invalid payload rollback, Task execution independence and project-delete cascade.
- Node syntax checks passed for workbench.js, project_information_ui.js and zh.js.
- Separate localhost:5001 preview used workspace/main under bmca-runtime/verification/project-information-preview. Reference data never entered formal workspace.
- Browser verified all four sections, category switching, edit across tabs, Save and reload retaining original Chinese/English text, BMC/HWM/GPU comparison, source filename/sheets/hash, no console errors.
- Initial test caught a separate-session SQLite lock; fixed by using plan_state.request_session. Final four-test run passed.
- Before formal restart checked no executing Tasks and backed up SQLite to bmca-runtime/backups/project-information-20261021/testcase_meta.db. Formal GET returned 200 with revision 0 and 28 categories; integrity_check=ok, foreign_key_check empty, saved information rows=0. The formerly used FWA-Test001 had been removed by ongoing user work; formal verification used an existing Project.
- Screenshot: bmca-runtime/verification/project-information-sku-20261021.png (reference preview).
