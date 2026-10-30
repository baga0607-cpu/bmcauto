# Task Info tabs — 2026-10-28

## Approved organization

Task Info at #/tasks/info/<id> now uses nested information tabs:

- Content: Task name, Task Type, Assignee, Status, Project, SKU, Plan Start/End Date, Actual Start/End Date, Days (Actual/Plan), iDesign ID and FW Package.
- Scope: Test Task only. View that Task's assigned Test Cases, folder, creation time and current status; Edit allows selecting the Plan's cases through the existing scope API.
- Connection: Test Task only. Read-only connection settings by default; Edit uses the existing per-Task environment form and save API.
- DUT Config: Test Task only, between Connection and Note & History. Contains the DUT Configuration heading only. No editable fields, data schema, fill rules or validation rules were invented.
- Note & History: notes and existing History List. Plan Tasks expose this and Content only.

Content is the default when opening a Task. Existing Schedule/Task List/My Task name links still target the same Task Info route. Existing execution workspace remains available; this change does not alter execution logic or backend APIs.

## Editing / data preservation

Content and Note & History share the existing metadata editor. Tab switches between those two preserve all in-progress values without rerendering the form. Save retains the existing optimistic concurrency, dates/status History requirement, Assignee history, iDesign links and Test-only firmware edit rules. Native validation reveals the correct panel before focusing an invalid field (e.g. required History when saving a Content date change).

Scope and Connection have explicit Edit modes and independent save/cancel flows. Switching away from unsaved editing uses the existing discard confirmation. Scope/settings operations resolve the actual Task/Plan from the global Task Info route; they cannot target an undefined legacy workspace Task. Saving stays on the selected information tab. Backend execution locks remain authoritative; the UI disables scope/metadata editing when locked and Connection editing only for its executing Task. Notes/history load on demand; Content read-only does not fetch the history list.

Tabs support arrows, Home/End, selected state, roving tab stops and labeled panels. The existing English tab labels, workbench tokens and light/dark behavior are retained. Content no longer displays notes/history beneath its fields.

## Verification / delivery

- JavaScript syntax passed for workbench.js, task_management_ui.js and zh.js; task_management_list.test.cjs passed.
- Isolated Chrome verified five Test tabs/two Plan tabs; assigned-scope view vs editable Plan scope; scope save using correct Task ID; Connection read/edit/save; unsaved discard cancel/accept; DUT label-only view; Content/Notes draft preservation; required History activation and metadata save; keyboard arrows/End; Plan notes edit and Test-only firmware restriction. No page errors.
- Separate isolated response simulation verified active Task editing locks on Content, Scope, Connection and Note & History, including disabled connection inputs.
- Light desktop Content and Note/History plus dark 1100px Plan Notes captured and inspected. Formal Content screenshot inspected after final field ordering. A keyboard list-selector typo found in browser testing was corrected. Harness waits/reset requests were aligned with asynchronous rendering and the existing date concurrency/History rules; no backend checks were bypassed or weakened.
- Formal browser read-only check passed Test/Plan tab availability, Connection read-only, DUT no inputs and no accidental metadata edit forms. No page errors.
- Formal DB backed up before final check; all table row fingerprints unchanged, integrity and foreign keys pass (9 Tasks / 1 Not Scheduled). No backend restart was needed because only static frontend files changed. Service remains http://127.0.0.1:5000 only. Preview 5129 stopped. No real BMC tests or GitHub publication.

Artifacts: <LOCAL_PATH> (source backups, formal-before-deploy.db, browser.json, locks.json, formal-browser.json, deployment.json, screenshots and isolated fixture verification scripts).

Files: web_ui/static/workbench.js, task_management_ui.js, workbench.css, zh.js. No backend/schema changes.
