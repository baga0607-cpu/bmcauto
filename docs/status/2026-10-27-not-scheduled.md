# Task Not Scheduled — 2026-10-27

## User decision
Missing either start_date or end_date means Status **Not Scheduled**. This supersedes the paired-date requirement and the prior rule that every undated Task displays New. Applies to both Plan and Test Tasks.

## Behavior
- Accept either date independently; validate each supplied date. When both exist, end must be on or after start.
- Incomplete dates force Not Scheduled, regardless of another requested status. With complete dates, Not Scheduled resolves to New; existing other statuses remain valid. Completing an unscheduled Task defaults to New, or an explicitly selected valid status.
- New Task defaults to Not Scheduled without complete dates, and New with complete dates.
- New/Edit Task and Schedule date editors update Status immediately. Other statuses are unavailable until both dates exist; Not Scheduled cannot be manually selected for complete dates. Task List/My Task filter includes the sixth status.
- Overview, Project task summaries and Task Info compute the effective status on read; legacy data is not migrated or rewritten by reads.
- Date/status edits retain required reasons, immutable transactional History and expected date/status conflict checks. Dates, status and execution results remain independent of actual execution.

## Validation and deployment
- 68 related Python tests passed in an isolated workspace/main/TEMP; Status filter assertions and three JS syntax checks passed.
- Nine headless Chrome form assertions verified partial dates, automatic status, available choices and History requirement. No real BMC execution.
- Formal DB backed up; startup against a disposable DB/script copy passed with all table rows unchanged.
- Loopback-only service restarted after confirming no active Tasks. Formal nine Tasks and all table rows unchanged; integrity_check and foreign_key_check passed. No formal Task was edited.
- Runtime evidence and backup: bmca-runtime/verification/not-scheduled-20261027 (outside published source).
- Source changes are local and have not been published to GitHub. Schedule replacing Task List remains a discussion, not an implemented navigation change.
