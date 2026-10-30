# Task iDesign ID and FW Package — 2026-10-27

## User decisions
Defer abnormal reminders. Task List/My Task remove Task Type and Project/SKU columns and add iDesign ID and FW Package. Task Info includes both new items; its existing ownership/type fields remain.

## Data and UI
- task_metadata.idesign is an optional {request_id, hyperlink} object. Both values must be filled together, or both empty to clear. Display only Request ID as an HTTP/HTTPS link opening a new tab with noopener/noreferrer. A separate pencil button opens editing without intercepting link navigation. Both Task types may edit it.
- task_metadata.fw_package is an optional ordered list of {component, version}. Each row requires both text values; add/remove rows in the draft editor and save atomically. Component names are case-insensitively unique; limits are 100 rows, 200-character Component and 255-character Version.
- FW Package is editable only for Test Tasks. Plan Tasks have no FW edit button; their full form fieldset is disabled and omitted from submissions. Backend create/manage/bulk paths enforce the type restriction independently of the UI.
- New/Edit Task and the metadata dialogs expose the same fields. Keep dates, Assignee, Status and execution evidence unchanged when updating metadata. Existing execution locks apply.
- expected_idesign / expected_fw_package protect changed fields and full-form submissions from stale overwrites. Missing legacy values remain absent until edited; no DB schema migration or read-time backfill. These setup fields do not create date/status History records.

## Validation/deployment
67 related Python tests passed in 7.347s. Coverage includes both Task types, normalization, paired link values, unsafe/malformed URLs, duplicate/invalid FW rows, Test-only creation/update/bulk enforcement, stale writes, atomic invalid submissions and active execution locks. Three JS syntax checks and existing Status filter assertions passed.

Isolated browser verified new table columns, both iDesign editors, Request ID link navigation using an intercepted example target, firmware add/remove/version edits, repeated Task Info edits, full Edit form, New Task type toggle, Plan UI/API restriction, stale iDesign rejection, duplicate firmware rejection, cancel, empty column stability and short dark layout. Also created new Plan/Test Tasks in the preview through the real UI, confirming metadata persistence and no FW field for Plan. No page errors.

Formal DB backed up, copy startup preserved all rows, no active Tasks confirmed before loopback-only restart. All formal rows unchanged; integrity/FKs passed. Formal read-only Task List/My Task and Task Info metadata editors/type restrictions verified. Preview stopped. No formal test edit, real BMC test or GitHub publication. Runtime evidence/backups: bmca-runtime/verification/task-reference-package-20261027, outside source publication.
