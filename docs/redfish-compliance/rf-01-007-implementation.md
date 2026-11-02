# RF-01-007 implementation

Created on 2026-10-30.

- Source: testcases/redfish/rf_01_007_version_discovery_uri_alias.py.
- Automatic, no editable parameters, Task connection settings, fixed 15-second request timeout.
- GET /redfish/ preserves the trailing slash. Accept a direct HTTP 200 response or supported same-origin redirects ending at /redfish.
- Require a JSON object whose exact v1 property is a string equal to /redfish/v1/. Additional properties are allowed.
- Redirect loop detection, maximum five redirects, and origin restrictions follow the existing provisional RF-02 safeguards.
- Unified section/http/check/finish logging plus three Step/Criteria/Result rows. Unperformed steps have Result=None; content checks belong to step 3.
- TEST_CASE.created_at records the original local filesystem creation time with a UTC offset. Preserve this value during future edits.
- All new Python source, metadata, comments and messages are English.
- GET only; no DUT configuration changes or restoration required.
- Seven offline unittest groups passed, including actual CaseLog integration, step result attribution, redirects, content failures, error classification, secret-header filtering, and filesystem creation-time equality.
- Verification: BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_007_check.py.
- No platform changes, formal Repository/Plan import, or physical BMC execution in this task.
