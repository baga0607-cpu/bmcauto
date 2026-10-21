# Persistent sidebar layout — 2026-10-20

Replaced the top navigation and contextual navigator with one persistent left sidebar and a right workspace. Brand has no link. Sidebar order: Dashboard (Project list, Task timeline); searchable Project selector with Project label opening information, then Plan, Execution, Report, bug; Case Repository. Language and theme controls sit at the bottom. This supersedes previous sidebar-hiding behavior, including Repository and Plan import.

Execution lists only the selected Project's Tasks. Report groups existing Task report actions by Plan. Existing Task detail routes, settings, scope and report generation endpoint are retained. Project information and bug retain their existing content. Switching Projects preserves the current project section when applicable. No database/schema or case Python changes.

Validation: Node --check workbench.js passed. Read-only browser checks on localhost:5000 verified keyword filtering (SKY), project switching, Project information, Plan list, project Execution list, Task timeline, Repository sidebar visibility, Report actions and empty Project report state. English/Traditional Chinese and light/dark toggles verified and restored. Browser console had no errors. No execution, report generation, or formal data mutations were performed. Screenshot: bmca-runtime/verification/sidebar-layout-20261020.png (workspace root).

## 2026-10-21 follow-up
Renamed Task timeline to Schedule and added Task immediately below it. Task opens #/tasks/list with My Task selected; Schedule opens #/tasks. Tab switching uses matching routes so reload and sidebar navigation preserve the intended view. Node syntax check and read-only browser Schedule-to-Task navigation passed. Screenshot: bmca-runtime/verification/schedule-task-nav-20261021.png.

Task/Schedule tabs separated: Task list and Task details show My Task + Task Info only; Schedule shows Schedule + My Schedule only. My Schedule uses #/tasks/my-schedule and displays the timeline (currently all Tasks until Owner/user exists). Node syntax and browser tab/navigation checks passed on 2026-10-21.

2026-10-21 clarification: Task tabs are Task List, My Task, Task Info in that order. Sidebar Task defaults to Task List (#/tasks/list); My Task has its own #/tasks/my-task route. Both currently show all Tasks until users/owners exist. Syntax checks for both JS files and browser tab switching/default selection passed.

2026-10-21 Project selector: replaced disclosure plus separate search with one editable combobox. Focus/click opens options; typing filters in the same field. Selection navigates; outside click, focus leaving, and Escape restore the selected name and close. Arrow keys and Enter support selection. Syntax and browser checks passed for SKY filtering, selection, no matches and Escape; no console errors. Screenshot: bmca-runtime/verification/project-combobox-20261021.png.

2026-10-21 Project List deletion: each row has Delete Project, disabled when any Plan is locked. Uses existing POST /api/delete_project and its server Plan-lock guard. Confirmation names the Project and explains cascade deletion while Repository cases remain. Successful deletion clears stale selected-project and Task Info navigation memory and refreshes the list. Confirm dialog supports an untranslated item name plus translated explanation. JS syntax and browser confirmation/cancel checks passed; no real Project was deleted during verification. Existing backend cascade/lock logic unchanged. Screenshot: bmca-runtime/verification/project-delete-20261021.png.
