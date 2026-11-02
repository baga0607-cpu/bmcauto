# RF-01-011 implementation

Created on 2026-10-30.

Source: testcases/redfish/rf_01_011_uri_fragment_references.py.

## Scope and execution

Automatic, parameters={}, fixed 15-second timeout, Task origin/authentication/TLS settings. GET only; no DUT configuration changes or restoration is required.

Traverse local structured @odata.id links and collection nextLink pages from ServiceRoot. Collect fragments in @odata.id and string properties explicitly containing Uri/URI in their names. Preserve source response URI, escaped field path, original reference and HTTP evidence. Do not guess that arbitrary prose or OEM string properties are references. External services/anchors and Actions are excluded; no Action is invoked.

GET targets omit fragments. Cache requests and redirects, preserve query pages, detect pagination cycles, continue independent branches after expected read failures. Redirect safeguards remain provisional pending RF-02: 301/302/307/308, maximum five redirects, same origin, no embedded credentials or forwarding to external origins.

## Fragment and identity checks

Follow [RFC6901](https://www.rfc-editor.org/rfc/rfc6901): decode percent escapes once as strict UTF-8, then decode ~1 and ~0 in order. An empty pointer addresses the whole document. Object keys must exist; array indexes use canonical nonnegative integers without leading zeroes. Reject the append marker, out-of-range indexes, traversal through scalars, malformed escapes and duplicate JSON object keys. False and null are valid existing values.

For schema-classified resource reference properties, the resolved target must be an object with a nonempty @odata.id. Resolve that identifier and verify that its final document and decoded pointer identify the same target. No body equality or guessed Id field is used.

Character restrictions, including the separate prohibition on non-query percent encoding, belong to RF-01-010; this case evaluates pointer resolution semantics.

## Schema evidence and limitations

Use the source response's single unambiguous Link rel=describedby JSON Schema URI, as described in [DSP0266 1.23.0 section 8.2](https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.23.0.html). Do not guess schema filenames from resource types.

Supported classification: explicit properties, homogeneous items, local/document $ref, one unambiguous type-matching anyOf/oneOf branch, nullable string URI types, and top-level canonical $id/id. A canonical ID can name an already fetched local schema; it does not authorize remote retrieval. Resource reference objects must have a schema-declared string @odata.id; scalar references require string type and uri/uri-reference format.

This is a conservative classifier, not a complete JSON Schema validator. Missing/ambiguous schema links, unknown properties, unavailable external dependencies, allOf/conditional/dynamic constructs, nested schema base IDs, ambiguous union branches, boolean schemas and cyclic/excessive reference chains produce Fail for insufficient evidence. Unversioned schemas with several object alternatives can therefore need further schema support. The test does not claim full schema compliance or coverage of undiscovered/custom string references.

## Results and Log

Latest execution-policy.md overrides the earlier N/A proposal: no applicable fragment references is Fail with the reason "No applicable fragment property references were found". Failed pointer/identity checks, unread scope or unavailable classification evidence are Fail. Missing Python dependencies and unexpected program defects are Error.

Reuse section/http/check/finish and three Step/Criteria/Result rows for settings, discovery, and fragment/schema validation. Unperformed stages have Result=None. Log every applicable reference result and retain detailed failure reasons and scope. Sensitive response headers are filtered.

TEST_CASE.created_at records the actual original filesystem birth time with UTC offset, verified after edits. Both new Python files are English-only ASCII.

## Offline validation

Command: BMCAgent/.venv/Scripts/python.exe -W error bmca-runtime/verification/rf01_011_check.py.

Fifteen offline unittest groups passed using actual CaseLog and blocked network access. Tests cover pointer escaping/UTF-8/object/array behavior, nullable values, duplicate JSON keys, resource target identity, no applicable references, exclusions, fragment-free cached requests, schema classification/canonical IDs/ambiguity/external dependencies, pages and incomplete scope, redirects and HTTP errors, metadata/birth time and report row attribution.

No platform changes, formal Repository/Plan import, physical BMC execution or GitHub publication.
