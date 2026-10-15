# Task management first increment, 2026-10-14

Requested: top-level Task management entrance, default Task information page showing task list and task-time Gantt, and add/edit/delete from that page. User prioritizes functions over UI redesign; desktop only.

Delivered: #/tasks and top navigation. Existing Task identity/Plan ownership is retained. New Tasks select existing Project/Plan and optional paired start/end dates. Edit changes name, dates and notes, preserving tester/firmware/other metadata, scope, connection environment and results. Plan assignment stays fixed. Task links open existing execution workspace. Search filters the list and Gantt together.

Dates are YYYY-MM-DD calendar days in Task.task_metadata.start_date/end_date. End date is inclusive; same-day Tasks are 1d. Blank pairs mean unscheduled and remain listed in both areas. Dates are validated in create, PATCH and bulk write routes. Gantt axes use UTC date arithmetic/formatting to avoid timezone day shifts; today is the browser local date. These are planned dates only, no automatic execution scheduling. No schema changes.

GET /api/tasks returns Task/Project/Plan names and IDs, setup, current execution/Plan-lock flags and scope counts, without connection secrets, testcase source or full logs. Existing create/PATCH/DELETE endpoints are reused. Plan execution locks protect mutation. Deleting one Task removes its memberships/current DB evidence while preserving Plan Test Cases and other Tasks.

Implementation: web_ui/task_management.py validates and lists Task information; task_management_ui.js renders the table, form and Gantt; workbench.js owns navigation/API actions. Existing workbench tokens and desktop layout remain. No new accounts, owners, notifications or scheduler were invented.

Verification: isolated database/main_program and Chrome under bmca-runtime/verification/task-management. Python 84 tests: 83 passed, 1 missing historical fixture skipped. Six new tests cover overview/legacy unscheduled data, create/edit/clear dates, invalid dates/names atomicity, deletion ownership, active locks/Plan immutability and bulk validation. JavaScript syntax and inclusive one-day/escaped-name rendering checked in Node VM. Chrome actual forms verified CRUD, inclusive 1d/3d Gantt, scope/environment preservation, locked controls, shared search, deletion/reload persistence. Desktop 1440x900 and 1920x900 plus dark capture confirmed; no mobile acceptance work. No DUT contacted.

Evidence: python-tests.log, browser-result.json and task-information-*.png in the verification directory. Backup: bmca-runtime/backups/task-management-20261014/source-before.zip and before.db. Local only; no commit/push. Production reload/data validation follows below.

## Local service delivery

Reloaded http://127.0.0.1:5000 after confirming no active Task/worker. Root HTTP200 and GET /api/tasks200 confirmed. Production has zero Tasks at delivery. Integrity and foreign-key checks pass. Compared with the initial backup, all non-Project tables match exactly; Projects changed during development (one addition and one name change). Current Project data was retained; no backup restoration or Project edits were performed by this deployment. The Project changes are not described as unchanged data.
