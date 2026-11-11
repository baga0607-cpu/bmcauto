# RF-01-001/002 Step, Checkpoint and Record — 2026-11-11

## Delivered

The two source files now use the user-approved descriptions and independent Step / Checkpoint / Record entries. Each literal TEST_CASE.test_method entry carries id, type, step_id and step (the readable ID/type/description label retained for existing metadata/report readers). There is no per-entry criteria field. This is metadata and evidence, not a return to executable step blocks.

- S<n>: operation. C<n> or C<n>a/b/...: checkpoints belonging to S<n>. R<n> or R<n>a/b/...: informational records belonging to S<n>.
- A Step need not have a Checkpoint or Record. Record does not save the intermediate response for another check; raw HTTP evidence remains a Log responsibility.
- RF-01-001: S1/C1, S2/C2a/C2b, S3/C3a/C3b/C3c. No Record. C2a says "Verify that the response body can be parsed as JSON."
- RF-01-002: S1/C1, S2/C2a/C2b, S3/C3a/C3b, S4/C4a/C4b, S5/R5. R5 records RedfishVersion or "Not present" without judging presence, format or value.
- Step descriptions omit Task connection/header/timeout boilerplate. The implementation still uses Task connection settings, Accept: application/json, timeout=15, no automatic redirects, supported 301/302/307/308 same-origin redirects with a five-redirect cap, loop detection and no cross-origin credentials. No DUT write operation is introduced.
- Python json.loads remains the parser: this is a parseability check, not new strict JSON validation. NaN/Infinity observations are represented as strings when needed for JSON-safe structured evidence; original HTTP body is retained.
- All required Checkpoints must pass for overall Pass. Independent ServiceRoot type, URI and version recording continue even when another field fails. Missing prerequisite data produces NOT_EVALUATED, not fabricated downstream FAILs.

## Runtime and Log mapping

CaseLog.method_item(item, result) emits a readable heading with the ID and type, the complete description, Source Step, status, expected/actual values where applicable, and a reason when skipped or failed. IDs are not used as a replacement for prose.

| Type | Execution statuses |
| --- | --- |
| Step | COMPLETED, FAILED, ERROR, NOT_RUN |
| Checkpoint | PASS, FAIL, NOT_EVALUATED |
| Record | RECORDED, NOT_RECORDED |

Record has no PASS/FAIL status or expected-value criterion. Missing RedfishVersion is successfully recorded as "Not present"; it does not fail RF-01-002. A present JSON null is recorded as null, distinct from absent.

The structured record keeps kind=step for compatibility with existing runner persistence and report readers; it adds method_id, method_type and step_id. result also includes id/type/step_id/status/actual and optional expected/reason. criteria is None and does not bind a Step to a Checkpoint. HTTP records produced under the named S1 section carry step_id=S1.

Older platforms without method_item fall back to the public log.step adapter with the same readable label and structured result. Such platforms retain traceability but may still display their legacy "Report step / Criteria" wrapper. The updated CaseLog must be loaded to obtain the new dedicated headings. Existing section/check/http/step/finish APIs remain compatible for the other cases.

RF-01-001 no longer assigns its v1 check to Step 2. Example: absent v1 yields C3a FAIL and C3b/C3c NOT_EVALUATED, explicitly referencing C3a. JSON parse failure yields S2 FAILED, C2a FAIL, and dependent work unperformed/unassessed. RF-01-002 records independent C3 and C4 failures together, then still records R5 when the JSON object is available.

The final result is written once. Overall Fail/Error retains the current runner mapping; this change does not add an Error DB/UI state. Historical logs and report layouts are not rewritten. IDs are local to this test-method version; modifying step order requires updating all dependent IDs, not renumbering saved historical evidence.

## Files and integration boundary

- Work sources: outer workspace testcases/redfish/rf_01_001_version_discovery_endpoint.py and rf_01_002_service_root_endpoint.py.
- Repository/publication sources: test_assets/redfish, byte-identical to the work sources.
- Shared Log: web_ui/case_log.py.
- Tests: web_ui/tests/test_rf01_method_items.py and test_case_log_integration.py.

created_at remains unchanged; modified_at is updated. No other RF source is edited. Existing Repository generations, Plan copies, Task settings/results/logs, and the formal database are not automatically replaced or migrated. To use these versions in the live platform, import the new source versions and deliberately update the desired Plan copies through the supported workflow. Review local Plan adaptations first. Restart the backend only when no active execution exists and after a backup, so the new CaseLog is loaded; no formal restart was performed in this task.

## Validation

- 13 new offline tests cover literal metadata and report fallback, exact IDs/parents, success, absent/wrong-type/wrong-value fields, invalid/top-level nonobject JSON, independent failures, informational values including absent/null/false/0, accepted ServiceRoot formats, HTTP failure, redirects/limits, request settings, sensitive-header filtering, runtime/dependency errors, old logger fallback, and invalid association/status rejection.
- Local targeted suite: 38 tests passed (new method tests, existing CaseLog, runner/storage integration and report-case compatibility).
- Publication checkout targeted suite: 35 tests passed; its baseline has fewer existing tests than the local development checkout.
- Actual isolated Repository → Plan → Task execution preserves the new method IDs, typed results and HTTP source Step in saved log_records. Failure-path tests verify R5 survives independent checkpoint failures and parse failure does not create a cascade of failed checks.
- Existing RF-01-003–006 integration remains successful. PDF attachment and method-row compatibility checks pass; no report-layout changes were made.
- No physical BMC, SSH, Telnet or cpc operation. Network is mocked/blocked in case tests. Test workspace/main/temp directories are isolated under bmca-runtime/verification/scr-20261111.
- Initial legacy assertions expected every row to be PASS and a separate kind=check entry; updated to explicitly verify the new contract for 001/002 while retaining the old contract for other RF cases. An initial temporary-directory permission failure was resolved by using the isolated writable TEMP/TMP.

## Next work

The remaining RF cases still use the earlier Step/Criteria output. This increment is the agreed two-case exercise, not a global conversion. General UI/report presentation of dedicated Step/Checkpoint/Record columns can be designed separately; current metadata readers, saved results and complete Log remain usable.
