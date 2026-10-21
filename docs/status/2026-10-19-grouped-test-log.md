# Grouped Test log checks — 2026-10-19

Platform CaseLog rendering now groups check results directly under their current section heading. PASS | label and FAIL | label retain Expected / Actual; separate Validation result boxes were removed. HTTP evidence within a section uses a subordinate divider. Final result retains a prominent independent heading.

Sections with no check() calls explicitly say “No check results recorded for this section.” when the next section or final result starts. This is informational, not an invented pass/fail. No section/check/http/finish public signature or structured evidence fields changed. No test case source was modified. Existing saved logs are not rewritten.

Validation: unified_test_log_check.py ran 56 tests: 55 passed, one historical skip. Checks cover passing/failing checks, no-check and HTTP-only sections, exact emitted-text/file equivalence, retained structured records, raw language preservation, PDF attachments and Task regressions. Formal service restarted only after confirming no active Task; /api/tasks returned HTTP 200. No physical BMC run triggered.

Evidence: bmca-runtime/verification/unified-test-log/tests.log.
