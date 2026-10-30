# Worksheet-1 Test Case report layout — 2026-10-28

User-approved reference: 績效考核評估項目表.xlsx, 工作表1. User explicitly authorized reading the visible sheet instead of requiring the disabled Excel add-in. Excel was inspected only and no cells were edited.

## Delivered

Each Test Case renders Case Name and overall Result on one row, Description, Detail Test Method with Step / Criteria / Result columns, then Task Name, FW Package, DUT Configuration, Tester and Execution Date. Missing values are —. Known TBD status is NR. DUT Configuration is strictly a label without a value, input UI or validation rule. The old global DUT hardware/configuration placeholder form and generic test-type-derived expected-result prose were removed; Report Information still identifies the Project/Plan and generated report. No connection settings are inferred as DUT Configuration.

The new context['log'].step(step, criteria=None, result=None) API records one JSON-compatible structured evidence row. It preserves false/zero, rejects invalid/nonfinite values before writing, and leaves overall execution judgement to the existing script assertion/case-result contract. Section/check/http/finish remain compatible. Latest execution result_json retains its description/test_method declaration as current evidence, not a history entity. Old section/check rows use their own labels/expected/actual values; they are not guessed against static method indexes. Declared methods without observations render Result —. Unstructured logs remain attachments and do not become invented method rows.

Author convention: [report-step-output](../agents/report-step-output.md). Complete offline-tested example: ../../test_assets/examples/report_step_case.py. Existing Repository imports, Plan adaptations and external testcases/redfish source files were not silently overwritten or synchronized. Authors can adopt the new output convention through the established import/adaptation workflow.

## Aggregation invariants

Same-Plan Tasks still follow the Task matrix eligible status, latest timestamp and canonical column-order tie rules. No selection/reordering or Reference aggregation rule changed. For each winning case, method rows, description, execution time and evidence come from its winning membership; Task Name, FW Package and Tester use that same source Task's current metadata. Assignee/FW Package are current Task data, not execution-time snapshots. No eligible result has no invented source Task. Reference remains independently grouped and follows formal reports in one PDF with all log attachments retained. Manual-result notes and rerun notices remain visible.

## Verification and delivery

38 focused tests passed: report_case (5), report_exports (12), case_log (7), case_log_integration (8), task_management (6). New checks cover the exact visible labels, source-specific firmware/Assignee on different matrix winners, Step persistence through actual offline API execution, author-example execution, description evidence, missing values, legacy evidence, zero/false, escaped/CJK text and long in-row table pagination. Existing aggregation/ownership/Reference merge/log attachment tests pass.

PDFs rendered and visually inspected: normal Final cases with distinct source Tasks, missing/NR cases, Reference separator (earlier compatible style), and 39-page stress report with oversized step evidence. A suite-only blank page initially found in the long case was fixed; the long first step now starts with its case header on the suite page and continues with repeated table headings. No values were truncated to fit.

Disposable startup copy retained all formal rows. Isolated HTTP export returned a 9-page combined same-Plan Final plus Reference PDF with the new worksheet fields and 3 log attachments. Formal service at http://127.0.0.1:5000 updated after backup/no-active-Task check. Formal Report composer browser check passed without page errors; real current Task/Reference export produced a 7-page PDF. All table row fingerprints, integrity and foreign keys unchanged after restart/export: 9 Tasks, 1 Not Scheduled. Preview 5129 stopped. No real DUT test executed, no GitHub publication.

The earlier unrelated manual-result test differences remain historical notes, not part of the passing test count above.

Artifacts/backup: <LOCAL_PATH> (formal-before-deploy.db, deployment.json, tests.log, rendered PDF fixtures and verification scripts).

Implementation: web_ui/report_case.py; report_generator.py; report_exports.py; case_log.py; app.py; tests/test_report_case.py; tests/test_report_exports.py; tests/test_case_log_integration.py; test_assets/examples/report_step_case.py.
