# English platform evidence messages — 2026-10-19

Platform-owned Console/IPMI output, Console helper logging and exceptions, report generation errors and service lifecycle messages now use English. Dynamic interpolated values remain unchanged. No UI localization files or test case .py sources were modified. Existing saved evidence and previously generated PDFs are not rewritten.

Changed: web_ui/app.py, main_program/console_helper.py (platform connection helper), web_ui/report_generator.py. Regression test added to test_case_log_integration.py proving Chinese case name, source print and device response survive in Test log and PDF attachment bytes.

Validation: isolated unified_test_log_check.py ran 55 tests, 54 passed and one historical skip, no failures/errors. Python compilation passed. Platform print/write/logger/raise output scan found no remaining fixed Chinese in the changed paths. Formal service restarted after idle check; HTTP 200 verified. No physical BMC execution was triggered.

Backup: bmca-runtime/backups/english-test-log-20261019.
