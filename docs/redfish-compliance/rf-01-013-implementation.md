# RF-01-013 implementation

Created on 2026-10-30.

Source: testcases/redfish/rf_01_013_local_schema_file_endpoint.py.

## Discovery and requests

Automatic, parameters={}, Task connection settings and fixed 15-second request timeout. GET only; no DUT changes or restoration is required.

Read ServiceRoot and use its advertised JsonSchemas link. Read collection pages and member descriptors, then collect actual Location[].Uri values. Do not guess the collection URI, filenames or a /Schemas/ equivalent. No product-document URI list was supplied, so this implementation uses DUT declarations only; it does not introduce editable presets.

The location model was checked against the fixed [JsonSchemaFile.v1_1_5 definition](https://redfish.dmtf.org/schemas/v1/JsonSchemaFile.v1_1_5.json). PublicationUri is recorded as excluded publication evidence. Archive-only declarations are explicitly unverified; archives are not extracted or used to invent individual endpoints. An external address in the local Uri field is reported as an unusable local declaration. Unsupported/ambiguous filename extensions prevent complete verification.

Use application/json for discovery and declared .json files, application/xml for .xml files. Follow supported local redirects with loop detection and at most five hops. Cache URI/Accept responses and failures; deduplicate file declarations while retaining their sources. Detect collection pagination cycles and continue independent declarations/files after expected failures. Credentials are not forwarded to external origins; Action endpoints are excluded. Redirect safeguards remain provisional pending RF-02.

## Minimum recognition profile

HTTP 200 is required. Keep file acquisition separate from document recognition.

JSON baseline: object, nonempty string $schema and object definitions. This was checked against the fixed published [Resource.v1_0_0](https://redfish.dmtf.org/schemas/v1/Resource.v1_0_0.json) and [ServiceRoot.v1_19_0](https://redfish.dmtf.org/schemas/v1/ServiceRoot.v1_19_0.json) documents; empty placeholder definitions remain acceptable. This review is of named versioned documents, not a claim that an entire release package has been validated.

For recognized 2019-09/2020-12 dialect identifiers, object $defs is also accepted to avoid treating that newer representation as an invalid schema. See [JSON Schema 2020-12 core](https://json-schema.org/draft/2020-12/json-schema-core). Other shapes remain outside this minimum recognition profile: Fail records incomplete recognition, not proof that a valid general JSON Schema is invalid. No referenced schema documents are downloaded and no complete meta-schema/semantic validation is performed.

XML: parse response bytes using the document encoding; require at least one Schema element in http://docs.oasis-open.org/odata/ns/edm. Prefixes are not fixed; direct Schema and wrapped CSDL documents are supported. DTD processing is disabled and reported as an explicit parser-boundary failure. Full schema semantics belong to RSV/RF-03.

## Recommendation and result

Four Step/Criteria/Result rows cover Task settings, declaration discovery, file acquisition/recognition, and recommendation/scope.

Each file retains acquired and recognized results, original/final URI, format/profile and failure reasons. Independently record whether any recognized advertised file is reachable at the single-filename /redfish/v1/Schemas/<SchemaFile> path, either as its initial URI or final redirect destination. This is recommendation evidence, not an overall Pass prerequisite. A declared /Schemas/ alias redirecting to another local path remains evidence that the recommended entry works. Other-path files retain their independent content results.

Under the 2026-11-02 execution-policy.md amendment, missing /Schemas/ recommendation evidence is an accepted PASS check with Note; its observed recommendation_met remains false. Other declared local paths are accepted without a prefix whitelist. No known local filenames, unsupported declarations or incomplete scope remain Fail with reasons, not automatically proof of a mandatory DMTF violation. Overall Pass requires at least one supported file, complete discovery and all tested local files to pass. Missing dependencies and unexpected program defects are Error.

Use section/http/check/finish and explicit step rows, preserve HTTP evidence, and filter sensitive response headers. Unperformed stages retain Result=None. TEST_CASE.created_at is the actual original local filesystem birth time with UTC offset, verified after edits. Both new Python files are English-only ASCII.

## Verification

Command: BMCAgent/.venv/Scripts/python.exe -W error bmca-runtime/verification/rf01_013_check.py.

Thirteen offline unittest groups passed with blocked network access and actual CaseLog integration: metadata/time, JSON success/profiles/boundaries, XML namespaces/UTF-16/DTD, separate content/recommendation results, no-guess discovery, publication/archive handling, duplicates/multiple files, pages/cycles, invalid declarations/types, HTTP failures and continuation, redirects, report attribution and sensitive-header filtering.

No platform changes, formal Repository/Plan import, physical BMC execution or GitHub publication.

## 2026-11-02 standards and Note update

Basis: [DSP0266 1.25.0 section 6.7 Table 4](https://www.dmtf.org/sites/default/files/standards/documents/DSP0266_1.25.0.pdf) (Required=No) and [DSP0268 2026.2 section 6.61](https://www.dmtf.org/sites/default/files/standards/documents/DSP0268_2026.2.pdf), JsonSchemaFile 1.1.5. The Uri property does not prescribe a two-prefix whitelist. Same-origin HTTP(S), JSON/XML recognition and redirect safeguards remain this implementation's verified scope; do not claim a complete validator of every legal URI representation or schema format. Archive-only support remains unimplemented and explicit, not silently passed.

Note identifies missing advertised recommendation evidence and the reason it does not block Pass; it never claims the unprobed /Schemas/ path is absent. Persist on check, step, final log and case_result.note. Thirteen offline groups pass, including /JsonSchemas/, other local paths, absolute same-origin declarations, normal no-Note Pass and genuine file/discovery failures. Original source creation time is preserved. HTML/PDF Note layout is deferred for separate discussion.
