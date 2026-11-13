## Superseding user decision

Case-level note fallback rows are now omitted entirely from reports. Step/Checkpoint notes remain visible; original saved notes and log attachments remain unchanged. Removed the fallback and its now-unused association accumulator. Updated regression and legacy CP expectations. 19 tests passed: test_report_note_association, test_report_case, test_report_method_table, and ConditionalCaseTest.test_policy_and_legacy_display, using the same disposable workspace TEMP/TMP. Formal-service deployment/restart remains pending.

# Report note association correction

2026-11-13, Asia/Taipei.

Report rendering now collects complete notes from observations actually rendered in the method table, before display truncation. Case notes are compared against these complete blocks at line boundaries, longest first. Only the unassociated remainder receives the historical case-note row. Multiple checkpoint notes no longer produce a duplicate aggregate row after RF-01-013 Step 5. Source results and judgements are unchanged.

Changed web_ui/report_case.py; added web_ui/tests/test_report_note_association.py. Seven regression cases cover aggregate, multiline, truncated, mixed, historical-only and substring notes plus legacy nested checkpoints. The new tests first reproduced five failures, then all passed after the fix.

Validation: unittest discover with patterns test_report_note_association.py (7), test_report_case.py (7), test_report_method_table.py (4): 18 tests passed, including HTML/PDF export checks on disposable test databases. PYTHONPATH points to BMCAgent/web_ui; TEMP/TMP point to bmca-runtime/verification/note-test-temp. Initial default temporary-directory runs failed due to sandbox permissions; reruns with the workspace temporary directory passed. No browser session, production database mutation or formal-service deployment/restart performed. Existing exported files are not rewritten.
