# Report Plan tree and selection export — 2026-10-28

## Delivered behavior

Report retains the Plan overview statistics and Task matrix viewing, without a Create button. Each Plan expands/collapses its Tasks. Select Report reveals Plan/Task checkboxes; Cancel resets selection. Generate Report downloads a PDF.

- One Task: current Task test report.
- Multiple Tasks from one Plan: one Final Report using only selected Tasks as result sources.
- One Plan: Final Report using all current Tasks in that Plan, including an empty Plan.
- Cross-Plan selection is disabled in the UI and rejected by the API. Cross-Plan reports belong to the future Reference feature; no ZIP or Reference workflow was implemented.
- An explicitly selected Plan checks/disables its child checkboxes; partial Task selection makes the Plan checkbox indeterminate. Active Tasks cannot be exported. Errors retain selection and restore controls.

## Final result rule

Same rule as the existing Task matrix: for each case in the complete ordered Plan scope, consider selected Task memberships with Passed, Failed or Block. The latest normalized result timestamp wins; fallback is manual modified_at, then executed_at. Equal/missing timestamps use the later Task column in existing Plan/API order. Running/NR are ignored; no eligible result is NR. Each winning case includes its source Task and current evidence. Full winning logs remain PDF attachments. Final cover lists included Tasks and explains that environments can differ.

Reports use current results, not a historical run snapshot. POST /api/projects/<project_id>/reports accepts plan_ids and task_ids, validates project ownership and one-Plan scope, and renders against a consistent disposable SQLite backup. Synthetic Final Task/memberships exist only in that copy. Live Task records are never created or modified by export. Single-Task environment credentials are redacted. PDF names/XML-sensitive text are escaped, headings stay with their case tables, and long page headers are clipped to available width.

## Validation and deployment

- 26 focused tests passed: report_exports, case_log, case_log_integration, task_management. Includes six new report tests for selection/ownership, aggregation/time ties/manual timestamps, active Tasks, empty Plan, PDF evidence and unchanged live data, render failure cleanup.
- JavaScript syntax checks and task_management_list.test.cjs passed.
- Isolated Chrome checks passed: tree expand/collapse, checkbox state, single/multiple/Plan download, matrix view, cross-Plan rejection, failure recovery, cancellation, dark/narrow view, unchanged Plan Create action; no page errors.
- Test PDFs rendered and visually inspected, including special characters in Plan/folder/case names and case heading/table grouping. Downloaded PDF type/page counts/attachments verified.
- Two pre-existing test_manual_task_results expectations fail both with this change and with the new report API removed: the old split log endpoint expectation (current behavior is unified evidence), and old relative testcase positioning (current natural ordering). Recorded in baseline-known-failures.log; unrelated behavior was not changed.
- Formal startup and export verified at http://127.0.0.1:5000 only. No active Tasks before restart. SQLite backup made before restart; all table row fingerprints unchanged after restart and real Task/Plan PDF export. Integrity and foreign-key checks pass; 9 Tasks, 1 Not Scheduled.
- Preview port 5129 stopped. No real BMC tests executed. No GitHub publication.

Verification artifacts and backup: <LOCAL_PATH> (formal-before-deploy.db, deployment.json, tests.log, browser.json, screenshots, PDFs, baseline-known-failures.log).

## Files

web_ui/report_exports.py; web_ui/report_generator.py; web_ui/app.py; web_ui/static/workbench.js; workbench.css; zh.js; web_ui/tests/test_report_exports.py.
