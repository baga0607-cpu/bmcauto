# RF-01-009 implementation

Created on 2026-10-30.

Source: testcases/redfish/rf_01_009_resource_uri_uniqueness.py.

## Execution and evidence

Automatic, no editable parameters. Task connection settings supply the origin, authentication and TLS verification. Each GET has a fixed 15-second timeout.

Start at /redfish/v1/. Follow structured @odata.id links recursively in standard and OEM properties, including Members, and @odata.nextLink / property@odata.nextLink pagination. Retain source resource, field location, original reference, requested and final URI, @odata.id, @odata.type and raw HTTP evidence. Arbitrary string properties are not guessed to be links.

The queue preserves query strings for pages, deduplicates requests and caches redirect destinations, including failures. Continue independent branches after expected HTTP or document failures. Record unread scope and reasons. External service links and Actions subtrees/endpoints are excluded explicitly; redirects into Actions are not followed. Fragment links fetch the containing resource; fragment semantics belong to RF-01-011.

Redirect safeguards remain provisional pending RF-02: supported 301/302/307/308, same origin, no embedded credentials, at most five redirects, loop detection. No credential forwarding outside the Task origin. Sensitive response headers are removed from stored/logged headers.

## Identity decision

Compare declared identity URI paths case-sensitively, without using scheme/authority to distinguish identities. Query strings remain in traversal keys but not identity path groups.

- Repeated references and aliases resolving through HTTP redirects to an already fetched response are one observation.
- Explicit pagination relationships establish equivalence only when the parent and page have matching collection types and declared identity paths.
- Pagination cycles and mismatched page identities are incomplete evidence and Fail.
- Different final response URLs with the same identity path remain unresolved unless equivalence is established. Query variants without pagination evidence also remain unresolved.
- No payload equality, changing sensor values, Id difference or UUID heuristic is used to assert different instances. An unresolved alias/collision group is Fail for insufficient evidence under execution-policy.md, not a claimed proven DMTF violation.
- Pass requires completed discovered scope and no unresolved groups. Report both resource/page response count and identity path count. Missing/unusable identity metadata prevents Pass because uniqueness cannot be assessed.

The result covers only discovered structured links. It does not certify undiscovered resources, custom URI-bearing string properties, or prove that the live service remained unchanged during traversal. Direct aliases without redirect/pagination evidence can require manual review; the test deliberately reports uncertainty instead of guessing equivalence or claiming a confirmed collision.

## Log and source metadata

Reuse section/http/check/finish plus three Step/Criteria/Result rows: Task settings, traversal, uniqueness assessment. Unperformed stages have Result=None. Raw response evidence and scope details remain available. Error is reserved for missing dependencies or unexpected program defects; expected environment/DUT/incomplete evidence failures are Fail.

TEST_CASE.created_at is the actual original filesystem creation timestamp with UTC offset; preserve it on edits. Both newly authored Python files are English-only ASCII. GET only; no DUT configuration changes or restoration is required.

## Offline validation

Run BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/rf01_009_check.py.

Fourteen offline unittest groups passed with real CaseLog integration and blocked network access. Coverage includes metadata/birth time, standard/OEM discovery, resource cycles, exclusions, query and separate-path pages, malformed/cyclic pagination, redirect caching and boundaries, uncertain identity groups, case-sensitive paths, authority-independent identity grouping, fragment/default-port links, unread scope, dependency/program failures, report row attribution and header filtering.

No platform changes, formal Repository/Plan import, physical BMC execution or GitHub publication.
