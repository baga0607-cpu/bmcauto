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

Flask / SQLAlchemy / SQLite backend, local Windows service, browser UI. Report formats and cross-Task Final Report rules are still undecided. Full automation classification and revised result states remain separate upcoming discussions. Do not invent support or add placeholder modules for these.

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
