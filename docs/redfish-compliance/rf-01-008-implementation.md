# RF-01-008 implementation

> RF-01-008 current acceptance rule: HTTP 400 is PASS with Note only when one Redfish @Message.ExtendedInfo entry contains both MessageId Base.1.16.InvalidURI and the exact Message “The URI /redfish/v1/openapi.yaml was not found.” Other 400 responses fail. The existing explicit-message HTTP 404 rule still applies.

Created on 2026-10-30.

- Source: testcases/redfish/rf_01_008_openapi_document_endpoint.py.
- Automatic, no editable parameters; uses Task connection settings and a fixed 15-second request timeout.
- GET /redfish/v1/openapi.yaml with Accept: application/yaml. Validate final HTTP 200 documents, directly or through supported same-origin redirects; HTTP 404 is an accepted optional-endpoint absence.
- Safely parse one YAML document using PyYAML safe_load; require a mapping with string openapi, mapping info and mapping paths. Additional properties are allowed. Full OpenAPI validation belongs to RF-03.
- 2026-11-02 decision supersedes the earlier missing-endpoint Fail rule: DSP0266 1.25.0 section 6.7 Table 4 marks this endpoint Required=No. Final HTTP 404 is PASS with an explicit Note identifying the response, non-mandatory recommendation and unperformed content validation. Other HTTP/environment errors and malformed provided documents remain Fail.
- Missing requests or PyYAML dependencies and unexpected program defects are Error. PyYAML is needed only after an HTTP 200 response; it is installed in the current platform environment.
- Redirect safeguards are provisional pending RF-02: supported 301/302/307/308, maximum five redirects, loop detection, no credential forwarding outside the Task origin.
- Unified section/http/check/finish logging and three Step/Criteria/Result rows. Unperformed steps have Result=None. Raw response evidence is retained, sensitive response headers are filtered, and YAML property checks log type evidence to accommodate dates and recursive aliases.
- TEST_CASE.created_at is the actual original filesystem creation time with timezone. Preserve it on future edits. Source and verification Python files use English-only ASCII text.
- GET only; no DUT settings are modified and no restoration step is necessary.

## Verification

Run BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_008_check.py.

Eight offline test groups passed: metadata, creation timestamp and English source, valid YAML/JSON documents, malformed/unsafe/multiple documents and content types, HTTP/dependency/environment errors, redirects, actual CaseLog step attribution, and sensitive-header filtering. Network connections are blocked in the harness.

No platform changes, formal Repository/Plan import, or physical BMC execution.

## 2026-11-02 Note update

Nine offline groups passed. Note is emitted on the check, performed step, final result and case_result.note. Unperformed YAML/content steps retain Result=None. Original source creation time is preserved. HTML/PDF layout changes are deferred for separate discussion.
