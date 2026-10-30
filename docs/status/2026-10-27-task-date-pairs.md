# Paired Task date dialogs — 2026-10-27

Task List/My Task: double-click either Plan date cell to edit Plan Start Date and Plan End Date together; either Actual date cell opens Actual Start Date and Actual End Date together. Initial focus follows the clicked cell. Both values are submitted in one guarded PATCH with existing History and expected-value checks.

A shared browser date-range binder updates the end input minimum and reports a validity error whenever both dates exist and end < start. It also applies to New/Edit Task and Schedule through existing date/status binding. Backend normalize_dates already rejects reversed Plan and Actual date pairs; retained unchanged. Same-day pairs and partial/blank dates remain valid, with Not Scheduled derived only from incomplete Plan dates.

Validation: 42 relevant Python tests passed in 4.204s; two JS syntax checks and existing Status-filter assertions passed. Fourteen isolated browser checks covered both Task types, both date-cell entry points, focus, reversed-date blocking before any request, saving both values, same-day dates and partial planned dates. My Task paired Actual dialog inspected. Formal read-only verification opened/cancelled the dialogs and confirmed paired fields; all formal rows unchanged, integrity/FKs passed. Preview stopped. No backend restart, schema change or formal test edit. Evidence: bmca-runtime/verification/task-date-pairs-20261027.

Applied locally; not published to GitHub.
