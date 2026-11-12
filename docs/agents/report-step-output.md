2026-11-12 Spec Ref. contract: cite only normative documents, versions, sections/tables and subjects. Place project acceptance/coverage policies in the applicable Checkpoint, explicitly labeled as project policy. Put observed conditional-acceptance reasons in execution Note. A section citation does not claim full coverage. Preserve captured historical report definitions and logs when updating sources. See [handoff](../status/2026-11-12-rf01-spec-ref.md).

2026-11-12 current contract: All RF-01-001–013 sources use numbered Command/Action with associated Checkpoint/Record. C-PASS replaces CP for new results and display; CP remains a read-compatible historical alias. C-PASS requires a Note and applies only to Checkpoint/final Case. Record uses COMPLETED; Skip requires a Reason. No section [n] prefixes in new logs; HTTP evidence numbers and Step associations remain. Preserve every repeated URI/member result by captured method_index. Only Case Name collapses all report content; no independent Result Summary or Note. See [series handoff](../status/2026-11-12-rf01-series-c-pass.md). Historical amendments below yield to this contract.

2026-11-12 amendment: Record success is COMPLETED; NOT_RUN / NOT_EVALUATED / NOT_RECORDED display as Skip with Reason. Only Checkpoint and final Case accept CP, with mandatory Note. Notes appear in Result cells; the separate report Note field is removed. Final report eligible states include CP. This supersedes earlier Record dash / old status instructions below. See ../status/2026-11-12-rf008-conditional-pass.md.

2026-11-12 latest: use numbered Command/Action groups with Checkpoint/Record children, not S/C/R IDs. Five report columns separate Result from Judgement; Record has no judgement. The previous dated amendments below are historical. See ../status/2026-11-12-numbered-method-types.md.

2026-11-12: Reports now render typed method IDs, source-Step relationships and recorded results in a compact table. Legacy evidence remains readable. See ../status/2026-11-12-report-method-results.md for precedence, missing-result and excerpt rules.

## 2026-11-11 Step / Checkpoint / Record amendment

RF-01-001/002 now use independent typed test_method entries with id/type/step_id and readable step labels, without embedded criteria. CaseLog.method_item writes their associated execution results while retaining kind=step for persistence compatibility. Record is informational, not an intermediate evidence-storage step and never a PASS/FAIL check. This supersedes the one-Step/one-Criteria authoring convention for these two cases. Other cases retain the existing contract. See [implementation and verification](../status/2026-11-11-rf01-method-items.md).

# Per-step report output contract

## HTML default and attachment-only logs (latest 2026-10-30 decision)

The default delivery is a ZIP containing an HTML report plus separate .log attachments. Cases show name/status/summary; secondary test information is collapsed. Log contents must not be displayed inside the report, including in a preview/modal. Open attachment uses a relative link to the separate log file. PDF remains optional; browser printing expands metadata but cannot embed attachments, while the existing server PDF export still includes full log attachments. Execution Date displays Taiwan time as YYYY/MM/DD HH:MM:SS (UTC+08:00). See ../status/2026-10-30-html-report.md.

## Current PDF layout (2026-10-30 supersedes the layout below)

The PDF no longer prints Detail Test Method or Step/Criteria/Result tables. Each case shows Case Name/Result, Description, Result Summary, Task Name, FW Package, the empty DUT Configuration label, Tester, Execution Date, applicable manual/retest notes, and full Test log attachment names. Normal case blocks stay together when they fit on a page; no mandatory one-case-per-page rule.

Result Summary uses the latest explicit finish reason (legacy top-level reason fallback); manual overrides use their recorded reason instead. Missing reasons point to available log evidence without inferred criteria/verdicts. Summary text is capped at 600 characters including an explicit excerpt notice. The complete log remains embedded unchanged, and missing logs are clearly marked. A supporting PDF reader can save/open these attachments. Existing log.step and report_definition recording contracts remain required for full evidence and compatibility; only their PDF table rendering is removed. Final/Reference selection and winner ownership are unchanged.

The following Worksheet 1 table layout is historical; evidence-authoring rules still apply.

The per-Test-Case PDF block follows the approved Worksheet 1 layout:

1. Case Name and Result on the same row.
2. Description from the latest execution's report_definition.description, falling back to the current Plan script literal metadata only for older/unexecuted cases.
3. Detail Test Method with Step / Criteria / Result columns.
4. Task Name, FW Package, DUT Configuration, Tester (Task Assignee), Execution Date.

DUT Configuration is a label only. No value, input rule, validation rule or connection/environment inference is defined. Missing information in other fields renders as an em dash (—). Overall known TBD state displays NR.

## Required author convention for new/adapted test programs

Use the supplied context['log'] and record one complete report row for each performed action:

~~~python
log = context['log']
log.step(
    step='Send GET /redfish/v1/',
    criteria='HTTP status equals 200',
    result='PASS; observed HTTP status 200',
)
~~~

- Step describes the action actually performed.
- Criteria states its acceptance condition.
- Result records the observed value and explicit judgement or error. Text and JSON-compatible values are supported; 0 and False are real values, not missing data.
- Record the row immediately after observing the result and before raising a failed assertion. If an action errors, record its actual error then re-raise. Do not create results for unperformed actions.
- None / empty fields are allowed for incomplete or legacy evidence and render as —. Non-JSON values and non-finite numbers are rejected before a row is written.
- log.step records evidence; it does not determine case status. Keep the existing assertion / exception / context case-result contract. A script must not return normally with a failed condition unless it explicitly sets its case outcome as failed.
- Existing section, check, http and finish APIs remain compatible. Complete raw evidence stays in the Test log PDF attachment.

See ../../test_assets/examples/report_step_case.py for a complete single-file example. Import into Repository and load/adapt a Plan through the normal workflow. Existing Repository/Plan sources are not automatically overwritten or synchronized.

## Compatibility / missing data

Explicit kind=step log_records are authoritative report rows, preserving call order. If absent, existing section/check records render using their own section titles and check label/expected/passed/actual values. They are not matched to declared steps by guessed indexes. A section without checks displays its title and — in the other columns.

If no structured method observations exist, literal TEST_CASE.test_method entries can display declared actions/criteria, with Result —. Canonical declarations use {step: text, criteria: text}; existing {step_1: text, criteria: text} declarations are readable. Unstructured print output is retained as a log attachment; it is never parsed to invent steps or criteria. No generic HTTP 200 / schema / timeout criteria are supplied by the report renderer.

Each new execution retains its description/test_method declaration alongside its latest result_json evidence. This is current evidence only, not execution history. Source metadata is read through AST and never imported/executed during report generation. Manual overrides and rerun notices remain visible.

## Final and Reference reports

Same-Plan Task selection still uses the existing matrix rule: latest eligible Passed/Failed/Block result, NR/Running ignored, ties resolved by the later original Task matrix column. Drag order does not change precedence.

Copy the winner's Step/Criteria/Result, description, execution date and evidence as one unit. Task Name, FW Package and Tester come from that same source Task's current metadata. FW Package/Assignee are not historical execution-time snapshots. No eligible result yields NR and no invented source Task context.

Group independently in Report Area and Reference Area. Reference results never change the formal Final result. Formal groups precede the Reference separator and reference groups. Full Test log attachments are retained during PDF merging.


## Existing RF sources and source creation time (2026-10-28)

RF-01-001–006 now emit one explicit row per declared method using the existing computed checks and final reason. Unperformed declared steps emit Result=None (PDF —). Their requests, timing, parameters, prompts and acceptance conditions are unchanged. Existing Log evidence is retained. See ../status/2026-10-28-existing-source-step-output.md.

Declare the original source file birth time in literal TEST_CASE.created_at, for example an ISO timestamp with timezone. The platform normalizes it to UTC and propagates it as source_created_at. Unknown time displays —. Do not use modification time or import time. Preserve this value during adaptations and normal source copies; a newly authored testcase must record its own actual file birth time. Browser file selection cannot supply native birth time by itself. Internal source_version remains a distinct immutable generation identifier and is not the displayed file timestamp.

## 2026-11-02 execution Note data contract (report layout deferred)

The user requested separate discussion before changing report format. Keep current HTML/PDF layouts. New executions may use `log.check(..., note="...")`, `log.step(..., note="...")` and `log.finish(status, reason, note="...")`; existing calls remain compatible. Note explains an accepted non-mandatory deviation while the check/case is PASS; actual observations remain truthful. Never convert a required failure to PASS merely because Note exists.

Structured records and full Test log retain Note. Save result_json.note plus task_testcases.result_note for lightweight summaries; old rows default to empty. Rerun clears prior Note, manual override preserves execution evidence, and the winning result retains its note in Final aggregation data. Report attachment logs naturally contain new Note text, but no new HTML/PDF field is rendered pending discussion.

## 2026-11-02 approved layout supersedes layout deferral

The user approved and deployed the Case Name disclosure layout. HTML uses Bahnschrift 22px/600, same-row status, default collapsed cases, Test Data then Test Information. PDF displays the same sections fully expanded, with 16.5pt headings and embedded full logs. Test Data order is Description / Result Summary / Note / Spec Ref. (compliance) / Log; Test Information is Task Name / Tester / Execution Time / FW Package / DUT Configuration. Note reads existing result_json.note only. New optional TEST_CASE.spec_ref is captured in report_definition together with test_type/compliance; no historical backfill. See ../status/2026-11-02-approved-report-layout.md for fallback, validation and preservation details.
