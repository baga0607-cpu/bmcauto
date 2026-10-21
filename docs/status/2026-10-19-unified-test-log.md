# Unified Test log — 2026-10-19

User decision supersedes split execution/API logs. This is a platform change; no test case .py source or Plan copies were changed.

- Each new execution reserves one unique timestamp/Task/Case/run-UUID __test.log file. Structured sections, checks, HTTP evidence, legacy print output and SDK proxy response bodies share it.
- result.log_files now contains test. The Task viewer displays a single Test log and removes both log-switch buttons.
- Existing split database evidence is merged on read. Structured HTTP blocks already present in execution evidence are not duplicated; unique legacy protocol evidence is retained. Original DB columns/files are preserved; new executions clear api_log_text.
- PDF uses the same merged content, with one Test log attachment per case. New names match the physical filename; older naming metadata is converted to __test.log or falls back to test_<case ID>.log.
- Persisted evidence retains the pre-existing Current execution details footer after the raw file content.

Validation: unified_test_log_check.py ran 54 tests: 53 passed, one historical skip, zero failures/errors. Covers one-file generation, collisions, reruns, RF-01-001–003, SDK proxy body preservation, old split evidence, extracted PDF attachment names/content, current Task state and single-case repository regressions. Node --check workbench.js passed.

Formal service restarted after checking no active execution; /api/tasks returned HTTP 200. Browser Task page shows Test log with retained HTTP and result evidence, no split selectors. Formal database rows unchanged compared with before.db; integrity_check and foreign_key_check passed. No physical BMC runs performed by this verification.

Backup: bmca-runtime/backups/unified-test-log-20261019
Test log: bmca-runtime/verification/unified-test-log/tests.log
Screenshot: bmca-runtime/verification/unified-test-log/task-test-log.png
