# Parsed SKU promotion during Project import — 2026-10-22

## Approved sequence
1. New Project > Automatic creation uploads the PRD workbook. Parse and match each SKU's specification values first. The first preview shows the parsed SKUs and a selectable, read-only per-SKU specification table.
2. Continue to Project review. Ask for each parsed SKU whether to retain it under the main Project or promote it to an independent Project. No choice is assumed. Parsed specifications remain available in a disclosure.
3. Show every resulting Project name; require explicit review confirmation. Commit the main Project and all promoted Projects as one transaction, then show links to all created Projects.

This sequence implements the user's correction: do not classify raw worksheet columns into Projects before resolving their SKU specifications. Promotion consumes the already parsed SKU document.

## Data rules
- Retained SKUs keep their original IDs/names and only their own SKU values under the main Project.
- Each promoted SKU becomes a Project named from that SKU, with no SKU entries of its own. Its original per-SKU values become that Project's independent target specification values.
- Preserve categories, row order/identity, headings, duplicate item occurrences, guidance, remarks, source file fingerprint/sheets, and exact values including blanks/No/N/A. Never replace a blank with aggregate target prose. Each promoted row records its original comparison column in source_ref.
- Project Information displays imported Projects without SKUs using one Project specification column. View/edit/save uses item.target for these Projects. Manual empty Projects retain the established Add SKU empty state.
- Project, Plan and Task relationships remain ID-based. This import creates no Plans or Tasks and never modifies existing Projects.
- Every comparison SKU needs exactly one valid decision; require confirmation and the SHA256 from the parsed preview. A changed upload must be previewed again.
- Preflight all output Project names against each other and the database, case-insensitively. Any conflict or later failure rolls back the entire batch. No overwrites or partial Project creation.
- With no comparison SKUs, the workflow reviews one Project without promotion decisions. Automatic main Project naming remains derived from the workbook.

## API / files
- POST /api/projects/import/preview remains read-only, now returning parsed columns (SKU IDs/names), specifications and source_sha256 alongside the earlier summary.
- POST /api/projects/import takes classifications as JSON [{id,kind:sku|project}], source_sha256 and review_confirmed=true. The main id/name fields remain in the response; projects lists every created Project.
- project_import_review.py resolves the parsed document into isolated validated Project documents. project_information.py handles transactional persistence.
- workbench.js owns the two preview/review stages and creation result links; project_information_ui.js supports imported no-SKU specifications; workbench.css and zh.js supply local styles/copy.

## Verification and local delivery
- 13 Project import/information tests passed. Coverage includes parsed preview values, single/multiple output Projects, per-SKU value isolation, independent edits, invalid/unconfirmed/stale/incomplete decisions, case-insensitive existing/output name conflicts, and rollback after an injected failure on the second Project document.
- 48 existing Task tests passed; total 61 relevant tests. Modified JavaScript syntax checks passed. Full repository suite was not run.
- Actual ProductRequirement_FWA-6084.xlsx: FWA-6084 retains BMC/HWM/GPU; FWA-5084 promotes separately with no SKU. All 196 source rows were compared to that parsed SKU's values; the main Project no longer carries its column.
- Isolated browser service 5002 verified per-SKU parsed preview (FWA-5084 1U), explicit promotion choices, one-action creation of both Projects with result links, no-SKU Project display, and editing/saving/reloading a target value. Preview DB integrity and foreign keys passed; main Project BMC 2U remained unchanged after editing the promoted Project.
- Formal SQLite connection.backup: bmca-runtime/backups/project-promotion-20261022, after checking no active Tasks. Copied startup and post-restart formal checks confirmed every existing row/name unchanged, integrity_check ok and no foreign-key violations.
- Formal port 5000 updated using bmca-runtime/server.py. Browser verified both preview stages with the actual workbook, then canceled without creating/modifying formal Projects.
- Screenshots (local): verification/2026-10-22-project-promotion-result.png and 2026-10-22-project-promotion-formal.png. Test logs: verification/project-classification-tests/results.log and task-regression.log.
- Temporary preview service closed after verification. No DUT was contacted; private runtime data was not published.


Updated: [Dashboard/import Skip](2026-10-22-dashboard-import-skip.md) supersedes the specification preview stage and adds Skip; omit main Project when no SKU is retained.
