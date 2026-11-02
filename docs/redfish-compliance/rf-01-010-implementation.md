# RF-01-010 implementation

Created on 2026-10-30.

Source: testcases/redfish/rf_01_010_uri_character_and_encoding_rules.py.

## Rules and scope

The approved rule set is pinned to [DSP0266 1.23.0, section 6.1](https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.23.0.html), with unsafe characters from [RFC1738 section 2.2](https://www.rfc-editor.org/rfc/rfc1738).

Check original strings before parsing, normalization or decoding. Separate the first fragment delimiter and then the query delimiter; a question mark inside a fragment does not begin a query. Reject raw unsafe characters, control characters and non-ASCII characters. Permit well-formed percent escapes only in query; malformed escapes fail everywhere. More than one raw fragment delimiter fails.

Component-aware interpretation preserves valid IPv6 authority brackets and JSON Pointer ~0/~1 escapes in fragments. These are structural exceptions, not permission for those characters in paths. Fragment target existence and full JSON Pointer semantics belong to RF-01-011.

Discover local standard/OEM structured @odata.id links and collection nextLink references from ServiceRoot. Also inspect Action target, @Redfish.ActionInfo, @odata.context and response Location strings, without invoking Actions or fetching metadata. External reference strings are inspected, but external services are not traversed. General description strings and arbitrary OEM URI-looking strings are not guessed to be URI properties. Link-header interpretation and broader relative-reference coverage belong to RF-01-012.

Every observation retains the original URI, source response URI, field location, rule and offending component/offset. Invalid advertised resource and redirect URIs are recorded and not repaired or requested. Actual HTTP evidence is preserved with sensitive response headers filtered.

## Execution and result

Automatic, no editable parameters, Task connection settings, fixed 15-second timeout per GET. Same-origin redirect safeguards allow 301/302/307/308 up to five redirects, with loop detection and cached requests. These safeguards remain provisional pending RF-02.

Resource cycles and repeated references are deduplicated; query pages remain separate requests. Pagination cycles, invalid links and unread branches prevent Pass. Continue other discovered branches after expected HTTP/environment failures.

Pass applies only to the discovered scope when traversal completes and there are no violations. Expected DUT/environment or incomplete-scope failures are Fail with reasons; missing dependencies and unexpected program defects are Error. No URI uniqueness checks are inherited from RF-01-009.

## Log, metadata and validation

Three Step/Criteria/Result rows cover settings, traversal/evidence, and URI validation. Unperformed stages have Result=None. Existing section/http/check/finish interfaces remain in use.

TEST_CASE.created_at stores the actual original filesystem birth time with UTC offset, verified after edits. New source and verification Python files use English-only ASCII text. GET only; no DUT configuration changes or restoration step.

Verification command: BMCAgent/.venv/Scripts/python.exe -W error bmca-runtime/verification/rf01_010_check.py.

Thirteen offline unittest groups passed with network access blocked and actual CaseLog integration. Coverage includes metadata/time, unsafe characters and raw evidence, query/fragment encoding boundaries, IPv6 authority brackets, fragment references, OEM links and pagination, Actions/external exclusions, prose exclusion, redirect safety/caching, scope failures, Step/Criteria/Result attribution and header filtering.

No platform changes, formal Repository/Plan import, physical BMC execution or GitHub publication.
