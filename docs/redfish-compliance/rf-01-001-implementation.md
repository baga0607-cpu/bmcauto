**2026-11-11 更新**：RF-01-001／002 已採獨立 Step／Checkpoint／Record 與關聯 ID，取代下方舊 Step／Criteria 綁定描述；詳見 [最新實作交接](../status/2026-11-11-rf01-method-items.md)。

# RF-01-001 first implementation

Current metadata naming: TEST_CASE.test_method is the ordered list; each item contains its numbered method key (step_1, step_2, step_3) and criteria. description is retained. This naming supersedes the earlier steps list / nested test_method convention below. Execution logic is unchanged.

Latest metadata decision: retain description and replace top-level test_method/criteria with a steps list, each item containing test_method and criteria. List order supplies Step_1, Step_2, Step_3 for export. The literal structure is JSON-compatible; execute logic and the fixed 15-second timeout are unchanged. This is documentation metadata, not executable step modules. Earlier top-level field notes below are historical and superseded by this structure. Platform export rendering still needs integration.

2026-10-14 metadata update: removed the opening module docstring at user request. TEST_CASE now declares literal string test_method and criteria for Test Plan columns Test Case | Test Method | Criteria. These describe the implemented actions, acceptance conditions and current redirect boundary. All future cases must provide these fields. HTML/PDF Test Plan exporter integration is still pending; this change only supplies the source metadata.

2026-10-14. File: testcases/redfish/rf_01_001_version_discovery_endpoint.py.

Task configuration impact verified from current local BMCAgent/web_ui/app.py and task_environment.py: execution reads task.environment_config, normalizes it and supplies redfish, console_server, dut_console and dut_os in context. Plan parameters remain in case_settings. The case reads no global YAML and uses Task redfish credentials, host and verify_ssl. Changing a Task environment marks prior results for retest.

The case declares literal TEST_CASE and execute(client, context=None, preset=None). Fixed protocol expectations: GET /redfish, final HTTP 200, JSON object, string v1 exactly /redfish/v1/. Per user decision, parameters is empty and HTTP request timeout is fixed at 15 seconds, independent of case_settings. This is an HTTP timeout, not a tester-input timer. Fully automatic.

The SDK get path automatically follows redirects. This case therefore uses requests with Task settings and logs raw response evidence to stdout/Task result log. It does not use private SDK interfaces. It does not populate the platform dedicated API log through WebLoggingRedfishClient; a future public raw-request/evidence API would unify logging. Runner pre-login remains a dependency: if that fails, the case cannot execute. No platform code changed.

Provisional redirect safeguards pending RF-02: 301/302/307/308, same origin only, loop detection, up to five redirects. Cross-origin redirects Fail with reason without forwarding credentials; this does not assert the redirect itself violates DMTF. This provisional limitation must be reviewed with RF-02 before claiming full coverage.

case_result records Pass/Fail/Error, reason and HTTP evidence. CaseFailure signals non-program failure; RuntimeError signals program failure. Current runner maps both exceptions to Failed and discards return values; true Error UI/persistence and automation badge support remain platform changes. Do not claim the existing UI already supports these metadata/result fields.

Validation: 9 mocked scenarios passed (success, wrong mapping, invalid JSON, HTTP 404, same-origin redirect, cross-origin rejection, request failure, program fault, non-object JSON). Task host and verify_ssl forwarding, redirect disabling and credential boundary checked. Literal AST metadata parsed. No real BMC or network requests; Repository/Plan/Task browser import and execution not yet verified. File authored only; not imported into live Repository.
