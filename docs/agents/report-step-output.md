# Per-step report output contract

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
