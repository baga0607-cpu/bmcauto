# Task-owned connection settings, 2026-10-14

User decision: Settings is the BMCAgent/DUT connection environment of one Task, not a global application setting. Each Task owns one independent environment.

Implementation: existing Task.environment_config column stores normalized JSON. GET/PUT/POST /api/tasks/<task_id>/settings edits it transactionally; Task creation, PATCH and bulk updates use the same validation. Existing flat/nested JSON can be read; no global YAML is automatically copied or used. New Tasks begin unconfigured. Global /api/settings and /api/config return 410; the global file is preserved. No schema migration required.

UI: Projects and Repository remain global. Task tabs include Connection settings, with BMC, Console server, DUT console commands and DUT OS groups. Active Task settings are locked by server and disabled fieldset; another Task environment remains independently editable.

Execution: validate the Task BMC URL before clearing selected evidence. The worker uses the saved Task environment for Redfish login/TLS, lazy Console connection and raw/ipmitool remote routing. Connection data cannot override Plan test parameters. No live DUT was contacted during verification.

Environment changes retain results/logs and mark only that Task results as needing rerun. UI/API/PDF notices cover Plan or Task environment changes. Summary responses no longer include connection secrets; dedicated Task settings loads the editor.

Verification: isolated workspace/scripts under bmca-runtime/verification/task-settings, 78 Python tests (77 passed, 1 historical fixture skipped). Five new tests cover independent persistence/no fallback, before-reset validation, owner-only locks/retest, two worker environments with mocked Redfish/Console, and nested JSON. JavaScript syntax validated with Node VM. Headless Chrome actual forms verified independent save, Task switching, refresh persistence, absence of global Settings, desktop and 390px mobile. Screenshots and browser-result.json saved in that verification folder.

Source/database backup: bmca-runtime/backups/task-settings-20261014. Local service update and production-data verification follow below. No commit/push.

Local service updated at http://127.0.0.1:5000. HTTP200 confirmed; retired global Settings returns410. All production table rows match the pre-change backup; integrity and foreign keys valid. Isolated QA service stopped. Existing global connection file and Task records preserved; configure each Task explicitly before executing.
