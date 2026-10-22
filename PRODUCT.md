# BMC Agent

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

BMC test engineers preparing reusable compliance Test Cases, adapting Test Plans to Project / SKU requirements, executing Tasks and examining evidence.

## Product Purpose

Manage standard single-file Python Test Cases, independent Plan adaptations and current Task results in a local test environment.

## Operating Context

Project → Test Plan → Task → Report. A Project may have multiple SKU Plans. Repository owns standard .py imports; each import has a timestamp identifying its source generation. Plan copies own Python source and editable parameters. Tasks select a scope and execute current Plan definitions.

## Capabilities and Constraints

English interface retaining Project, Plan, Task and Test Case terminology. The user explicitly requested complete removal of step / block editing and execution. Existing records are preserved rather than deleted automatically. Plan adaptations do not bump source generations. Plan edits mark prior Task results as needing a rerun; retain their evidence. Running Test Cases cannot be edited.

Flask / SQLAlchemy / SQLite backend, local Windows service, browser UI. Report formats and cross-Task Final Report rules are still undecided. Full automation classification and revised result states remain separate upcoming discussions. Do not invent support or add placeholder modules for these, except for the explicitly approved project section landing pages described below.

## Brand Commitments

BMC Agent product name. No other visual constraints have been specified.

## Evidence on Hand

Approved domain model in CONTEXT.md and docs/superpowers/specs/2026-10-07-single-file-case-design.md. Runtime data and API execution evidence are real; preview demonstrations must remain in isolated databases.

## Product Principles

- Make Project / Plan / Task ownership visible during every operation.
- Provide a single clear location for each action.
- Edit Test Cases in Plans; execute them in Tasks.
- Show current state and retained evidence without hiding changed test conditions.
- Remove unsupported and obsolete operations from the interface.

Task connection settings (2026-10-14): each Task independently owns its BMC, Console and DUT environment. Global navigation has Projects and Test Case Repository. Edit Connection settings inside the Task; Plan parameters retain their existing ownership. No global connection fallback.

Desktop support scope (2026-10-14 user decision): BMCAgent currently targets desktop browser operation. Mobile support is deferred until explicitly requested. Do not spend design or acceptance effort on mobile layouts; existing narrow-width CSS is historical compatibility, not a support commitment.

Task management (2026-10-14): a top-level Task management entry opens Task information with a task list and planned-date Gantt. Add/edit/delete Tasks under existing Plans. Daily inclusive start/end dates, unscheduled legacy Tasks, independent Task connection settings and execution locks remain explicit. Automatic schedule execution and other management pages are outside this first increment.

Repository exclusive function page (2026-10-14): entering Test Case Repository shows its full-width list without the Project navigator. Add imports one .py, View shows metadata/defaults/source read-only, and Remove confirms the selected source version. Removing a Repository row does not change independent Plan copies, source generations, parameters, Task scope or evidence. Returning to the function resets an old preview so the list is the default view.

Project navigation (2026-10-15 user decision): global navigation is Projects, Tasks and Test Case Repository; Tasks replaces the former Task management label. Projects opens a full-width project list without a sidebar. Entering a Project shows a project-switching dropdown followed by Project information, Test Plan, Test Report and Bug List, in that order. The project default route opens Project information; /plans shows the existing Plan list. The /info, /reports and /bugs routes intentionally show empty pages marked for later design; this explicit decision supersedes the earlier prohibition on placeholder modules only for these three pages. Existing Plan and Task deep links remain available. Global Tasks and Repository pages have no project sidebar. This is a desktop navigation extension; report formats, bug workflows and Project information contents remain undecided.
Project navigation refinement (2026-10-15): the sidebar begins with inline Project: [dropdown]. The Test Plan list omits breadcrumbs, page heading, description and Rename Project / Delete Project controls. Add Test Plan is the sole footer action below the list, including its empty state. Existing Plan detail remains unchanged.
Plan Matrix (2026-10-16 user decision): the Test Plan list shows Plan, total, completed/total, PASS, FAIL, Block, NR and Task count. Clicking the Task count toggles an inline Test Case-by-Task matrix with a Final column. Final uses the latest eligible current membership result (PASS, FAIL or Block); NR and Running do not override a result. Missing Task scope displays a dash. Completion includes Block. Manual Block is supported in the result API, summaries and report counts. This explicitly extends the former four-status model; it introduces no execution history or cross-Task Final Report format.

Home / Projects navigation (2026-10-16): BMCAgent brand links to #/dashboard, which owns the existing all-project list without a sidebar. Projects links to the last valid project ID stored as bmc-last-project in browser localStorage and opens its default information page. Visiting a project or switching the dropdown updates that memory. No selection or deleted remembered project falls back to Dashboard. #/projects resolves the Projects entry for bookmarks. Tasks/Repository unchanged; breadcrumbs and deleted-project fallback use Dashboard. Read-only browser checks passed Home, selection, dropdown, reload persistence, missing-project fallback and global routes.

Plan workspace refinement (2026-10-16): breadcrumb/path navigation is deferred across all routes. Plan detail shows Test Plan: <name>, no description and only Rename / Delete at the right. A Repository-style folder/case tree replaces the former tabs and top Add / New Task controls. Tasks remain reachable through global Tasks and Matrix Task columns. Folder actions copy cases from Repository into the selected Plan folder, create a child folder through a name dialog, or delete after confirmation. Search and folder collapse retain compact navigation. Parameters and source open a resizable side editor; edits remain Plan-owned, preserve Repository source and honor existing locks.
Plan source import (2026-10-16): toolbar Import Test Case replaces folder Add Case icons and the previous Plan .py picker. Choose Repository or a source Project/Plan. The target tree is on the left and the read-only source tree on the right; drag a case or a complete folder subtree (including empty descendants) right-to-left only. Reverse drops are rejected. Repository imports inherit defaults; Plan imports inherit saved parameters and Python source. Both lists show source versions. Conflicts are preflighted atomically: matching name/source metadata identity and version offers overwrite or skip; differing identity/version offers overwrite/update, coexist or skip. Cancellation writes nothing. Coexist keeps the original name; overwrite preserves target identity, placement and Task evidence while advancing revision and marking results for retest. Source records remain untouched. See docs/status/2026-10-16-plan-source-import.md.

Automatic import review (2026-10-22): parse SKU specifications before asking which parsed SKUs should be promoted to independent Projects. Show all resulting Project names, require explicit confirmation, and create all or none. Promoted Projects keep their exact specifications and support view/edit without inventing a SKU.
