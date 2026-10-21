# Unified Test Case logs

Delivered locally on 2026-10-19 (Asia/Taipei). The platform owns formatting, filenames and persistence; a Test Case describes its phases, HTTP evidence and checks. These are log sections, not executable step definitions.

## Author interface

The runner supplies `context['log']`, a per-execution `CaseLog` instance from `web_ui/case_log.py`:

```python
log = context['log']
log.section('Document validation')
log.http('GET', uri, response.status_code, response.headers, response.text,
         request_headers={'Accept': 'application/json'})
log.check('Final HTTP status', response.status_code == 200,
          expected=200, actual=response.status_code)
log.finish('Pass', 'All criteria met')
```

- `section(title)` produces a numbered section.
- `http(method, uri, status, headers, body, request_headers=None)` writes one numbered HTTP block to both execution and API files and emits one live event. JSON is indented for display; the original body remains in the structured record.
- `check(label, passed, expected=None, actual=None)` records a validation result.
- `finish(status, reason)` writes one final result. The runner supplies a final result for legacy cases and connection failures if the case has not supplied one.
- Logging does not change execution status. Test Cases still use the existing result/context/exception contract. In particular, case Error remains Failed in current platform status; the detailed log can distinguish Error. The broader status migration is not part of this change.

Authorization, proxy authorization, Cookie, Set-Cookie and X-Auth-Token headers are redacted by the common interface. URL user information is removed and common credential query keys are redacted. Response body content is retained as evidence; this is not a blanket scrub of arbitrary secrets within payloads. The RF cases also retain their existing response-header filtering.

`PrintLogWriter` preserves legacy `print()` usage, including fragmented writes, indentation, blank lines and a final partial line. The explicit Log interface writes directly to the current execution's sinks. Live events retain the existing `type='log'` contract; stored `result_json.log_records` contains the structured evidence.

RF-01-001, RF-01-002 and RF-01-003 now call this interface. Their standalone/offline fallback does not import platform modules. Existing criteria, 15-second timeout, empty parameters, automatic classification and provisional redirect safeguards are preserved.

## Local filenames and reports

Location: `D:/Codex/bmc_auto_test/BMCAgent/web_ui/workspace/logs/`.

```text
result_<Task name>__<Test Case name>__<identity>.log
api_<Task name>__<Test Case name>__<identity>.log
```

The platform sanitizes Windows-invalid characters, caps the Task and Test Case labels at 24 and 64 UTF-16 code units, and appends 16 hexadecimal characters derived from both stable IDs. The full names and IDs appear inside the file header. Unchanged Task/case names reuse the same pair on rerun. Renaming produces a new readable filename; old files are not deleted. No execution-history UI or retention policy was introduced.

`result_json.log_files` records the actual filenames. PDF attachments use these names for new results, with the old fallback retained for older records. Structured cases show a bounded result/check summary in the PDF table; their complete readable logs remain attached. This prevents a long evidence block from overflowing an unsplittable report row.

## Verification

- Isolated full backend suite: **123 tests: 121 passed, 1 failed, 1 skipped**. The failure is `test_manual_task_results.ManualResultTest.test_relative_testcase_move_preserves_target_position_and_source_order`. Running that test with the pre-change `app.py` reproduces the same ordering failure; it was not changed in this delivery. The skip is the existing historical fixture test.
- All 7 new Log unit/integration tests pass, covering redaction, raw body retention, live/file parity, readable filenames, legacy print buffering, real Repository/Plan/Task runner execution for all three RF cases, failure/error/login paths and PDF attachment names.
- RF offline verification scripts pass: `rf01_002_check.py` (5 tests), `rf01_003_check.py` (6 tests), `rf01_integration_check.py` (3 tests including 10 runner scenarios).
- Disposable browser service on port 5138: saved execution log and API log visibly preserve sections, line breaks and JSON indentation. No frontend source changes were needed.
- Formal port 5000 was idle before restart. Startup preserved every existing database row. Three new Repository source generations were imported into their existing folders. Six matching Plan copies across two Plans were updated through the definition API; parameters and source generations were preserved. The two old 003 copies differed only by additional blank lines.
- Existing Task status/result/log/executed_at fields are unchanged by the source updates; affected retained results follow the existing needs-retest rule. SQLite integrity and foreign-key checks pass. Formal Repository loads in the browser after deployment.
- No physical DUT was contacted and no formal Task was executed. Prior logs retain their original formatting; new sections are generated on the next execution.

Reproduction and evidence under `D:/Codex/bmc_auto_test/bmca-runtime/verification/structured-log/`: backend-tests.log, baseline-test.log, RF script logs, synthetic samples, api-log-preview.png and preview-report.pdf. Runner: `bmca-runtime/verification/structured_log_check.py`; `--baseline` reproduces the unrelated ordering failure with the saved original application.

Backups: `D:/Codex/bmc_auto_test/bmca-runtime/backups/structured-log-20261019/`, including original application/report/RF source files, before-deploy.db, the pre-startup digest, prior Plan definitions and deployment.json. Do not restore an older database over subsequent user activity.
