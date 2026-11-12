# Numbered steps and four method types — 2026-11-12

## Approved contract

This supersedes the S/C/R ID presentation and the earlier four-column report table. Reports use **Step | Type | Description | Result | Judgement**.

| Type | Meaning | Step column | Judgement |
| --- | --- | --- | --- |
| Command | Send a command or request | Main-step number | COMPLETED / FAILED / ERROR / NOT_RUN |
| Action | Other operations: connect, parse, read, wait | Main-step number | COMPLETED / FAILED / ERROR / NOT_RUN |
| Checkpoint | Compare an observation against an expectation | Blank, follows its main step | PASS / FAIL / NOT_EVALUATED |
| Record | Record information without evaluating acceptability | Blank, follows its main step | — |

Result contains Expected / Actual / Reason as available; execution status is in Judgement. Record never displays a verdict. If a Record could not run, Result says Not recorded and gives the reason; Judgement remains —. An absent recorded result is No recorded result with no invented status. A recorded JSON null, false, zero, empty string and Not present remain distinct.

## Source and Log changes

RF-01-001 and RF-01-002 now declare step_number, type and readable step text, without id / step_id or S/C/R label prefixes. GET is Command; JSON parsing and property reads are Action. Other RF source files were not converted. Request behavior, checks and final case verdict rules are unchanged.

The public CaseLog.method_item adapter accepts the numbered contract and still accepts older S/C/R items from independent Plan copies. New text logs use Step N / Type headings, complete descriptions, Expected/Actual/Reason and a separate Judgement. Failure summaries identify the Step number and complete failed check description. HTTP evidence records carry numeric step_number. Original HTTP payloads remain in full logs.

The structured kind remains step for persistence compatibility. A zero-based method_index identifies the position in the captured test_method list solely for internal result matching; it is not displayed as a user ID. Checkpoint/Record entries retain numeric step_number for grouping. method_index values must be updated when editing the method list; do not apply new positions to historical results.

Internal Record execution states remain RECORDED / NOT_RECORDED so the renderer can distinguish a real null from missing execution. Neither is shown as a judgement. Old log.step-only platforms retain the structured numbered result through the existing fallback. A platform with the previous S/C/R-only method_item implementation must load the new CaseLog before executing the new source.

## Report compatibility

Both HTML and server PDF use the same five-column adapter and retain the compact spacing. PDF child Step cells are truly blank, not an em dash. Tables repeat headers across page breaks. Browser print and disclosure/attachment behavior remain intact.

Saved definitions are authoritative. Numbered records join by their captured method_index; old records join by existing historical IDs. Missing observations stay in definition order with No recorded result. Current source is never joined to old evidence. Historical Step types render as Action because the old schema did not declare Command; historical S/C/R prefixes are removed from display only. Legacy section/check and untyped evidence remain readable, without invented verdicts or changed stored data.

The existing 1,200-character result excerpt threshold, full attachments, manual/retest notes and Final/Reference winner selection remain in effect.

## Verification and rollout boundary

- Local: 53 Python tests passed (RF method contracts, runner/storage integration, report adapter, PDF/HTML exports, report presentation).
- Publication: 49 Python tests passed on the independent bmcauto checkout.
- Actual offline RF-01-002 execution feeds the HTML/PDF fixture. Assertions cover all five headers, numbered main steps, blank child Step cells, separated judgements, informational Record values, ordered partial results, old IDs, legacy results, escaping and complete attachments.
- Offline Chrome passed disclosure, five-column contents, compact spacing, attachment opening, print expansion/restoration and no horizontal overflow or external requests. Rendered PDF pages were visually checked for readable columns, blank child numbers, Record's em dash, Chinese text and repeated headers across a 60-row table.
- Fixtures/logs/screenshots: bmca-runtime/verification/report-types-20261112, excluded from Git. Tests use isolated TEMP/TMP, workspace and main roots; DUT/network calls are mocked.
- Work sources in outer testcases/redfish and product test_assets/redfish are byte-identical. No formal Repository/Plan imports, DB writes, service restart or physical DUT execution. Existing Plan copies are independent; load the new backend and deliberately import/update the desired source copies to execute this version. Regenerate downloaded reports to apply the new presentation.
- Publication is scoped to this feature on baga0607-cpu/bmcauto main, based on b66622f. Unrelated local changes remain preserved; the retired original origin is not used.
