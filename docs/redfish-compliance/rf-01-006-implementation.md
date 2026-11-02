# RF-01-006 Service Root URI Alias

2026-10-19: Created testcases/redfish/rf_01_006_service_root_uri_alias.py. English-only Python, automatic, parameters={}, fixed 15-second HTTP timeout. No formal Repository/Plan import or physical BMC execution; platform code unchanged.

Initial GET is exactly /redfish/v1 (no trailing slash), Accept application/json, using Task connection settings. requests automatic redirects are disabled. Direct HTTP 200 with valid ServiceRoot is accepted. After supported same-origin redirects, the final path must be /redfish/v1/ and the response must be HTTP 200. Intermediate same-origin hops are allowed within the existing five-redirect limit. Loop, missing Location, invalid URL and cross-origin redirects fail explicitly. These remain provisional RF-02 safeguards.

Content checks follow RF-01-002: valid JSON object, ServiceRoot type with any Schema version (or unversioned identifier), @odata.id exactly /redfish/v1/. Extra properties allowed; RedfishVersion recorded without expected-version comparison. No requirement to redirect when the alias directly serves valid content. Records include initial/final URI, redirect count and each HTTP response. section/http/check/finish use the current unified Log API; platform owns file naming and rendering.

Verification: BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_006_check.py — 6 unittest groups passed, including direct responses, supported redirect statuses, relative/absolute canonical targets, wrong final paths, loop/cross-origin/limit safeguards, content failures, environment/program classification, metadata and actual CaseLog output. The initial URL and requests-prepared path both preserve the missing trailing slash. Requests are mocked and sockets blocked. Syntax and Chinese-source scans passed. No app/formal DB import.

Known platform SDK-login prerequisite and Error-to-Failed storage behavior remain outside this case's scope.
