# Existing RF sources: Step output and file creation time — 2026-10-28

## User requests

Adapt existing test programs to emit Step / Criteria / Result while preserving test logic and acceptance conditions. Follow-up: the displayed .py timestamp must be its original file creation time, not Repository import time.

## Source adaptation

Six working programs RF-01-001 through RF-01-006 in <LOCAL_PATH> now emit explicit report step records through context['log'].step. Each declared test_method step_x and criteria is retained verbatim. Added observability helpers collect the already-computed checks, their expected/actual values and the existing final reason. A completed step records its observations; a failed/error step records its existing failure; unperformed declared steps have result=None (PDF —). Existing section/http/check/finish evidence and final case_result/_tc_status are preserved. No request, redirect, timeout, parameter, prompt, comparison, assertion or Fail/Error classification was changed.

Sources remain independent single-file programs and support standalone execution without a BMCAgent import. If a standalone logger lacks step, the new report evidence prints as structured JSON. No executable step builder was added. All original file birth times were preserved when updating the working files in place.

Initial inventory contained 6 Repository sources and 12 Plan source copies. All 24 variants were independently staged and verified rather than overwriting older wording with the working source. During work the user removed all formal Plan Test Cases. The final rollout re-inventoried and respected that state: zero Plan sources were changed/restored. Six new Repository generations were added from each standard source's own adapted version; six existing standard records and their placements remain byte-for-byte unchanged. Future copies from the new versions include the new output format and source creation metadata. Removed source directories/recovery copies were not revived or edited.

## File creation time

The six source files' actual Windows birth times were captured before modification and written as literal TEST_CASE.created_at with an explicit UTC timezone. Creation time is portable with the Python source through Repository import, Plan copy/adaptation, source import and export. Creation-time validation rejects malformed, timezone-less or non-text values; unknown/missing time remains None. Browser File.lastModified and Repository import time are never substituted for birth time.

Repository, Plan, import-source lists, conflict target choices and Task scope now display source_created_at. Task scope column is Created at / 建立時間. Unknown historical sources display —. Existing source_version remains the internal immutable import-generation key for uniqueness, lineage/conflict checks and export compatibility; it is no longer rendered as a .py creation timestamp. This avoids colliding generations when different revisions share one original file birth time. No schema migration or original generation rewrite was needed.

For future authored sources, retain the original file birth timestamp in TEST_CASE.created_at. A newly authored/copied-as-new testcase file must declare its own actual creation time rather than copying the example's timestamp. Browsers do not expose native file birth time; absent metadata is deliberately shown as —.

## Verification

- Semantic AST comparison: all 24 staged variants have unchanged test logic, parameter declarations and test_method/criteria, excluding only new observability and the newly requested created_at metadata.
- 456 original/candidate comparisons: 24 variants × 19 scenarios, comparing exact request URLs/options/auth/trust_env, prompt calls, case_result observations/evidence/reasons, _tc_status, exception type/message and all pre-existing log record content. New step count and authored criteria checked; skipped results are absent/None.
- 61 platform tests passed: creation time (3), single-file repository (20), report_case (5), report_exports (12), case_log (7), case_log_integration (8), task_management (6). Creation metadata preserves zero/unknown semantics and survives copies/adaptations. The integration fixture executes all six actual adapted sources offline (including XML and RF-01-005 Plan preset), persists their step records and creates a PDF.
- 32 existing RF-01-002–006 offline test groups passed on the updated working files. RF-01-001 additionally covered by the comparison harness and API integration. Old RF-004 verification code was updated from the retired split-log constructor to the current unified log; 004/005 expected-kind assertions now include step. No acceptance checks were weakened.
- JS syntax passed. Isolated Chrome verified Repository and Plan birth-time labels, unknown historical —, preserved source birth time on adding a Plan copy, and Task scope Created at. No page errors. Formal Chrome verified all six new timestamps and that zero Plan cases were restored. Light/dark captures saved.
- PDF from actual RF step output was rendered and visually inspected; full log attachments remain embedded. Matrix and Reference report tests pass; aggregation behavior unchanged.

## Formal rollout and preservation

Local service remains http://127.0.0.1:5000 only. No active Tasks before backup/restart. Startup initially matched every table fingerprint. Normal Repository APIs then created six new rows plus their folder placements. Final logical comparison proves all original Repository rows, all unrelated business rows, Task records, scopes/results/metadata and the user's empty Plan state unchanged; SQLite integrity and foreign keys pass. Preview 5129 stopped. No DUT execution and no GitHub publication.

Backup/evidence: <LOCAL_PATH> Key artifacts: formal-before-deploy.db; initial-source-manifest.json; source-manifest.json; sources/; candidate-manifest.json; behavior.json; birth-time-checks.json; platform-tests.log; working-check-*.log; apply-formal.json; rollout.json; browser.json; formal-browser.json; PDF fixture and screenshots. The initial Plan candidates are verification evidence only, not deployed Plan records.

## Implementation / handoff

Working files: testcases/redfish/rf_01_001 through rf_01_006 .py (workspace sibling of BMCAgent).

Platform: web_ui/single_case.py (metadata/creation serialization), app.py and plan_state.py (creation field propagation), static/workbench.js and zh.js (creation display), tests/test_source_created_at.py, expanded tests/test_case_log_integration.py, example metadata. No new execution API or database column.

Earlier unrelated manual-result expectations remain historical test notes and are not included in the passing counts above.
