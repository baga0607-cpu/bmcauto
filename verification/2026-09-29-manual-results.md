# Manual Task testcase results — 2026-09-29

Backend implementation for the approved current-state workflow. No execution history model or synthetic execution evidence was added.

## API contract

- `PATCH /api/tasks/<task_id>/testcases/<tc_id>/status`: JSON `{status, reason}`. Status must be exactly `TBD`, `Passed`, or `Failed`. Reason is an optional string, defaults to empty, and is trimmed. Returns HTTP 200 with the current testcase object.
- `GET /api/tasks/<task_id>/testcases/<tc_id>/logs`: returns HTTP 200 with the same current testcase object, including `status`, `result`, `log_text`, `api_log_text`, `executed_at`, and `manual_override`.
- Summary testcase objects expose `manual_override: null` or `{status, reason, modified_at}`; timestamp is UTC ISO 8601 with timezone.
- Missing Task/testcase or missing live same-Plan membership returns 404. Invalid manual status or reason type returns 400. An executing Task anywhere in the Plan blocks manual updates with 409.

Manual changes update only status and the latest manual metadata. Existing execution timestamps, structured results, console logs, API logs, bug IDs, and scope are preserved. Cases that never ran can be changed without invented execution evidence. The existing write reservation serializes changes with execution admission. Starting execution clears manual metadata only on selected cases.

The nullable `task_testcases.manual_override_json` column is added through the existing transactional, idempotent migration. Current PDF details include escaped manual status, reason, and modification time; execution attachments remain actual stored evidence.

## Red / green evidence

New `web_ui/tests/test_manual_task_results.py` first ran against unchanged production code: seven tests ran, six failed with missing-route 404 responses (one negative membership test already passed). After implementation, all seven passed. Tests cover never-run status changes and counts; evidence preservation and logs retrieval; invalid input and same-Plan execution locks; live membership; selected-only reset; PDF text and absence of fabricated attachments; additive migration and repeated-startup preservation.

Targeted validation:

- `python -B -m unittest discover -s web_ui/tests -p test_manual_task_results.py`: 7 passed.
- `python -B -m unittest discover -s web_ui/tests -p test_plan_current_state.py`: 23 passed.
- `python -B -m unittest discover -s web_ui/tests -p test_task_api_contract.py`: 91 passed.
- `git diff --check`: passed.

Total: 121 passing targeted tests. The parent task owns the full integrated suite after frontend work.

New tests instantiate Flask routes directly with temporary SQLite databases and never import application startup. Existing suites imported app only with `BMC_WEB_UI_WORKSPACE_DIR` pointing to a fresh temporary copy of `verification/baseline-workspace/testcase_meta.db`, `BMC_MAIN_PROGRAM_DIR` pointing to `verification/browser-main`, and `BMC_LIFECYCLE_SOURCE_DB` pointing to the baseline. Browser DB/server were not changed or restarted. Existing legacy test logging produced untracked worktree-local logs; these were not committed.
