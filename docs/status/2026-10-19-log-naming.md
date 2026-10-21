# Platform Log naming — 2026-10-19

User requested execution time, Task name, Test Case ID and log type, retaining previous files on rerun. This supersedes the fixed naming/overwrite rule in 2026-10-19-structured-case-logs.md.

Platform owns naming; RF-01-001–003 Python sources are unchanged in this increment. case_log.py generates:

`YYYYMMDD_HHMMSS_microseconds+offset__Task__CaseID__runUUID__result.log`
`YYYYMMDD_HHMMSS_microseconds+offset__Task__CaseID__runUUID__http.log`

Time uses the execution host local timezone with explicit offset (+0800 on this installation). Both files share the same timestamp and UUID. Case ID uses a leading protocol identifier such as RF-01-001; cases without that naming convention use their platform Test Case ID. Task labels are sanitized and bounded to 24 UTF-16 units; case identifiers to 36. Full names and platform Task/Case IDs remain in the log header. The UUID distinguishes runs even with identical timestamps/names.

open_log_files creates files with exclusive x mode. Result or HTTP filename collisions retry with a new pair; only an empty result file created by that failed reservation is removed. Existing files are never truncated. Other filesystem failures propagate normally.

Location: D:/Codex/bmc_auto_test/BMCAgent/web_ui/workspace/logs. No existing files were renamed or rewritten. Task DB/UI and PDF remain latest-result views; older disk files remain available locally. No history entity or task_metadata history was introduced. report_generator.py accepts the new bounded attachment names, retaining old-format fallback.

Validation: `BMCAgent/.venv/Scripts/python.exe bmca-runtime/verification/log_naming_check.py` ran 9 tests, all passed. Disposable workspace, scripts and mocked BMC/SDK only. Coverage includes repeated execution of the same Task/Case (Pass then Fail), byte-for-byte preservation of both prior files, forced collisions on both filenames, safe names, structured log content, legacy print, three RF cases and PDF attachment names. Evidence: bmca-runtime/verification/log-naming/tests.log. No physical BMC test.

Formal service port 5000 restarted after API/DB idle checks and exact process-command verification. Backup: bmca-runtime/backups/log-naming-20261019/before.db. All formal rows match the pre-restart logical hash; integrity_check OK and foreign_key_check empty. No Repository or Plan source import needed. Changes are local, uncommitted.

Platform ownership handoff: notify the existing conversation Plan_Task功能; future platform work belongs there, while 增加測項 focuses on independent case .py files.
