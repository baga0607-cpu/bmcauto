# RF-01-012 implementation

Created on 2026-10-30.

Source: testcases/redfish/rf_01_012_relative_uri_references.py.

## Scope and rule

The approved relative-reference form rule follows [DSP0266 1.23.0 section 6.7](https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.23.0.html): relative references use an absolute path beginning with /, or a network path beginning with // and containing an authority. Absolute URIs are outside this particular restriction.

Inspect original strings before URL resolution can hide bare-path or dot-relative defects. Empty, bare-path, dot-relative, query-only and fragment-only references fail. Unknown/unparseable references prevent Pass. Detailed unsafe-character and fragment semantics belong to RF-01-010 and RF-01-011.

Body discovery covers structured @odata.id, nextLink, Action target, @Redfish.ActionInfo, @odata.context, and explicitly named string Uri/URI properties, including OEM objects. Do not scan general prose or guess arbitrary string properties.

Inspect actual GET response Location, Content-Location and Link target/anchor URI references, including redirect and unsuccessful responses. Header names are case-insensitive. Link parsing respects angle brackets, quoted commas/semicolons and escaped quotes, following the serialization model in [RFC8288](https://www.rfc-editor.org/rfc/rfc8288). Uninterpretable headers are recorded as incomplete evidence; no silent Pass. General Link parameters such as title and rel are not treated as resource references.

## Traversal and evidence

Automatic, parameters={}, Task connection/authentication/TLS settings and fixed 15-second timeout. Traverse local structured resource links and collection pages from ServiceRoot. Cache requests/redirect destinations, preserve query pages and detect pagination cycles. Expected read failures retain their reasons and independent branches continue.

Actions, metadata/non-resource URI properties and header links are inspected without being invoked or fetched as JSON resources. External references are inspected but external services are not traversed. Do not create resources or send non-GET requests merely to obtain headers. Header-only navigation is outside traversal scope.

Provisional RF-02 redirect safeguards: 301/302/307/308, same origin, maximum five redirects, loop detection, no embedded credentials or redirect into Action endpoints. Relative-form violations are recorded before a request is made; invalid advertised resource/redirect references are not repaired and requested.

Evidence includes original URI, response URI, Body field/header position, relative/absolute/unknown classification, violation reason, raw HTTP response evidence with sensitive headers filtered, excluded resources and unread scope. Count Body and header observations separately. List missing header types per response and across the observed run. Absence alone does not imply a violation or coverage of other HTTP methods.

## Result and report

Pass requires at least one applicable relative reference, complete discovered scope and no violations. Under the latest execution-policy.md, no applicable relative references is Fail, superseding the earlier N/A proposal. Environment/DUT or incomplete-scope issues are Fail; missing dependencies and unexpected program defects are Error.

Use existing section/http/check/finish interfaces and three Step/Criteria/Result rows: settings, discovery/evidence, and relative-form checks. Unperformed stages retain Result=None. The test is read-only; no DUT configuration restoration is required.

TEST_CASE.created_at is the original local filesystem birth time with UTC offset, verified after edits. Source and verification Python files are English-only ASCII.

## Verification

Command: BMCAgent/.venv/Scripts/python.exe -W error bmca-runtime/verification/rf01_012_check.py.

Fourteen offline unittest groups passed with blocked network access and actual CaseLog integration. Coverage includes metadata/time, relative/absolute classification, original Body violations, OEM/page traversal, Link quoting/commas/anchors and malformed headers, header counts/absence, headers on redirect/error responses, exclusions, absolute-only scope, network-path traversal, HTTP failures, report row attribution and sensitive-header filtering.

No platform changes, formal Repository/Plan import, physical BMC execution or GitHub publication.
