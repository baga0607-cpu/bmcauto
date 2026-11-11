# Workspace summary and on-demand evidence

Navigation previously downloaded 18,518,915 bytes from /api/projects. Execution downloaded 38,978,844 bytes per summary every two seconds even when idle. Structured result evidence survived the old removal of log_text from project responses.

Project and Task summaries now omit result/log_text/api_log_text and defer the large database columns. Full results and per-case logs APIs preserve their contracts. The logs endpoint supports text_only=1 for complete unified text without duplicate structured evidence. Log dialogs load one case on demand and retain full Export with the existing 65,536-character preview. Closed/switched dialog responses are discarded. Changed results reload evidence; local running cases use their stream, remotely running cases refresh only while their log is open.

Execution polling is 2 seconds active, 15 seconds idle, 30 seconds hidden. A two-second scheduler means idle changes can take approximately 16 seconds to appear. Visibility restoration permits the next tick to refresh. Backend execution locks remain authoritative.

## Verification

- Python command: python -m unittest test_workspace_summary.WorkspaceSummaryTest.test_summary_excludes_evidence_and_log_endpoint_preserves_full_text test_case_log_integration test_report_exports. All 21 tests passed with disposable workspace/fixtures. SQL assertions verify evidence columns are absent from summary SELECTs; complete logs and wrong-Task rejection are checked.
- node --check web_ui/static/workbench.js passed.
- node web_ui/tests/execution_controls.test.cjs passed with evidence-free summary fixtures and separate log responses: execution/stop scopes, prompts, locks, ownership, dialogs and complete downloads.
- node web_ui/tests/execution_log_performance.test.cjs passed: full live/saved log export, 3.97 seconds replay, maximum heartbeat gap 61.4 ms.
- node web_ui/tests/workspace_summary.test.cjs passed: no eager log requests, idle/active polling using virtual time, lazy full log, bounded preview and complete Unicode export, no repeated completed-log loads. Initial virtual-clock assertion raced mock request arrival; corrected to await the response before counting.

## Formal deployment

Local backup: bmca-runtime/verification/workspace-performance/pre-deploy.db. Zero active Tasks confirmed before restarting server.py. No DUT operation or schema migration.

| Endpoint | Response bytes | Three total-time samples (seconds) |
| --- | ---: | --- |
| /api/projects | 31,575 | 0.199 / 0.209 / 0.203 |
| Task summary | 13,103 | 0.091 / 0.088 / 0.072 |

All stored statuses, result_json, log_text and api_log_text match the pre-deployment backup. SQLite integrity ok; foreign-key violations zero. The largest case log endpoint returns 6,511,400 characters matching stored unified text exactly. Existing browser tabs need refresh. Report layout remains unchanged; PDF table performance is separate.
