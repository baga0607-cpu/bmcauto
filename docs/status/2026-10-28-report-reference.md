# Report / Reference composition — 2026-10-28

This supersedes the earlier same-Plan-only selection constraint in 2026-10-28-report-tree-export.md. Report retains expandable Plans, summary statistics and matrix viewing, without Create.

## Approved behavior

Select Report can select Plans/Tasks across different Plans within the current Project. Checking a Plan means all its current Tasks: children display checked/disabled, and the composer represents the Plan once. Partial Task choices make the parent indeterminate. Selecting the parent replaces individual child selections, avoiding duplicates.

Generate Report opens a native dialog titled "Move reference data to reference area:". All selected items initially appear in Report Area in tree order. Users can drag items between Report Area and Reference Area, and reorder within both areas. Up/down and move-to-area buttons offer the same operations without dragging. Both areas scroll for long lists. At least one formal report is required. Cancel/Escape discard arrangement but retain table selection; Cancel selection clears table selection. Idle browser navigation closes the composer. During generation controls and Escape are locked; errors preserve the arrangement for retry and appear within the dialog.

## Aggregation and order

- Group items by Plan independently in each area. A same-Plan group occupies its first item's position in that area's ordered list.
- A selected Plan includes all its current Tasks and always renders a Final Report. Explicit Plan plus child Task inputs in one area normalize to one whole-Plan scope.
- Multiple selected Tasks from one Plan render one Final Report. A single explicitly selected Task renders its current Task Report.
- Same-Plan Final results strictly follow the existing Task matrix: current Passed/Failed/Block only; latest normalized result_updated_at, falling back to manual modification/executed_at; equal or missing timestamps use the later original Plan/Task matrix column. Running/TBD are ignored, no eligible result is NR. Drag order never changes this precedence.
- Same-Plan disjoint Task sets split between areas are evaluated separately. Reference results never affect the formal Final result.
- Each different Plan renders independently. Formal reports are concatenated in group order, then one Reference Reports separator page, then reference reports in their group order. No separator is added when Reference Area is empty.
- Output is one PDF. A lone group retains the existing Task/Final filename; multiple groups use BMC_Reports.pdf. Each constituent report retains its own page numbering. PDF outline groups formal/reference reports. Log attachments are explicitly preserved with section/report prefixes to prevent filename collisions.

## API / data invariants

POST /api/projects/<project_id>/reports now accepts ordered report_area and reference_area arrays of {kind:"plan"|"task",id:string}. The old plan_ids/task_ids payload remains compatible for one-Plan exports. Mixed payload formats, malformed entries, duplicates, cross-Project IDs, empty Report Area, active selected Tasks, and overlapping Plan/Task coverage across areas are rejected. Maximum 100 explicit selection entries.

All scopes are resolved before synthetic report Tasks are prepared in one consistent disposable SQLite backup. Rendering and merging never modify formal Tasks, memberships, results, metadata, connections, or execution history. The synthetic Tasks cannot become source candidates for later groups. No ZIP workflow or persisted Reference records were added.

## Verification / local delivery

32 focused Python tests passed (12 report tests, plus case_log, case_log_integration and task_management). New coverage includes group/area order, canonical matrix tie order despite drag order, Plan-all deduplication, cross-area overlap/ownership/active validation, split-scope isolation, merged PDF order/bookmarks, colliding log attachment retention, and unchanged live rows. JavaScript syntax checks and task_management_list.test.cjs passed.

Isolated Chrome checks passed: cross-Plan selection, whole-Plan children, cross-area drag and both list reorderings, keyboard alternatives, empty formal guard, Plan and mixed Task PDF downloads, ordered API payload, generation failure/retry, cancellation/Escape, Chinese labels, idle browser navigation, and dark desktop overflow. No page errors. Light/dark screenshots and PDF separator/case pages visually inspected. Two browser harness issues (waiting for a hidden dialog to become visible and an out-of-bounds drop point) were corrected; neither required product changes. Duplicate background errors were removed so generation failures stay in the dialog.

Formal service was updated at http://127.0.0.1:5000 only after a fresh SQLite backup and no-active-Task check. Formal Report composer and PDF export verified, including a 7-page formal/reference PDF from existing Task records. All table row fingerprints unchanged after restart and exports; integrity and foreign keys pass (9 Tasks, 1 Not Scheduled). Preview 5129 stopped. No DUT execution or GitHub publication.

Prior handoff records two unrelated manual-result test expectation differences; those were established before this change and were not counted as new passing tests here.

Artifacts and backup: <LOCAL_PATH> (formal-before-deploy.db, deployment.json, tests.log, browser.json, screenshots, PDF fixtures and formal verification scripts).

Changed implementation: web_ui/report_exports.py; web_ui/static/workbench.js; index.html; workbench.css; zh.js; web_ui/tests/test_report_exports.py.
