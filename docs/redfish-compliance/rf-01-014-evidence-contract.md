# RF-01-014 Task Monitor URI: integration into RF-14

Status: user-approved implementation direction, 2026-10-30; planned, not implemented or executed.

This decision supersedes the earlier separate evidence-evaluator/cross-case adapter proposal. Retain RF-01-014 as the requirement and report tracking ID. Implement its checks inside the applicable RF-14 .py; do not create a standalone RF-01-014 .py or separately scheduled execution.

## Ownership and evidence

RF-14 owns the authorized asynchronous operation, initial response, monitor polling, lifecycle checks and DUT restoration. When that operation returns its initial response, evaluate RF-01-014 using the same execution's evidence. Do not trigger another operation or poll a monitor just for this URI check.

Use the original HTTP 202 Location, resolved against the actual request URI. Never substitute the Task body's @odata.id, a TaskService/Tasks entry, a polling response's Location or a guessed identifier. Preserve the original response and its log-record reference, operation identity and observation time in the same RF-14 result.

RF-01-014 checks the recommended path /redfish/v1/TaskService/TaskMonitors/<nonempty-single-segment-ID>. Preserve raw Location; do not decode or rewrite the path before comparison. Monitor behavior and lifecycle remain RF-14 responsibilities.

## Unified Log and Step / Criteria / Result

Use the existing section/http/check/step APIs inside RF-14. Label the relevant sections and report rows with RF-01-014. Record the original HTTP response once and refer to that record from the URI check.

| Step | Criteria | Result |
|---|---|---|
| RF-01-014: Identify the initial asynchronous response. | Same RF-14 operation; original status 202 and one usable Location; no Task URI substitution. | PASS/FAIL/ERROR, operation ID, source HTTP record, time, status and original Location. |
| RF-01-014: Resolve the TaskMonitor URI and assess the recommended path. | Confirmed monitor identity; path matches the recommended form without an additional DUT request. | Independent URI verdict, resolved URI/path and reason for each operation. |
| RF-01-014: Summarize the assessed scope. | All applicable operations in this RF-14 execution are accounted for; do not select only successful paths. | Aggregate RF-01-014 verdict, operation count and evidence references. |

All future Python source and Log text must be English. Unperformed rows retain Result=None. Emit observed results before propagating failures, but do not let a URI check failure bypass RF-14 monitoring or required finally-based restoration. Call log.finish once for the enclosing RF-14 execution after required cleanup; do not finish the shared logger prematurely for this subcheck.

## Separate verdicts

Keep the RF-01-014 URI verdict distinct from RF-14 lifecycle/operation/restoration verdicts. A valid URI can coexist with a failed lifecycle check; a non-recommended path does not by itself prove the operation or lifecycle failed. Do not copy RF-14's overall status into RF-01-014 or overwrite RF-14's verdict with this subcheck.

When the RF-14 case is authored, explicitly define how its existing single platform-level outcome represents its own acceptance criteria, while retaining RF-01-014 as an independently labeled sub-result. The current platform does not automatically create a second case result from a log.step row. Do not claim a dedicated RF-01-014 result row already exists.

Apply execution-policy.md to the RF-01-014 sub-result:
- Valid evidence and all assessed recommended paths: Pass.
- Confirmed monitor at another path: Fail for a missing recommendation, not proof of a mandatory DMTF violation.
- No applicable 202 evidence, missing/ambiguous Location or inability to confirm monitor identity: Fail with evidence/applicability reasons once the subcheck is evaluated.
- Not evaluated: not run; program defects: Error; block remains a tester decision.
- No N/A or fabricated Pass.

## Platform and next work

No cross-case evidence transfer, separate offline runner, extra BMC login or standalone evaluator is required for the approved same-execution design. These were requirements of the superseded proposal, not prerequisites for implementing this subcheck.

Initially trace RF-01-014 through its labeled RF-14 Log and Step/Criteria/Result rows. If a separate RF-01-014 Plan/report result row is later requested, platform work must explicitly map that row to the independent sub-result and its source RF-14 execution. Such platform support is not implemented or required to begin the merged check.

Next: when authoring the applicable RF-14 .py, add these steps and offline tests for valid/invalid Location, missing/non-202 response, Task URI substitution, multiple operations, independent URI/lifecycle outcomes and restoration after a URI failure. Then validate against actual RF-14 responses. No new RF-01-014 source creation timestamp is needed because no standalone source will exist; the RF-14 file keeps its own actual birth timestamp.

This update changes planning documents only. No RF-14 code, platform behavior, production data or DUT settings were changed.
