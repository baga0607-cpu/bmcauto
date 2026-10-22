# Plan / Test Tasks — 2026-10-21

## Approved behavior
- New Task starts with Task Type: Plan or Test, then Project, SKU, Plan, Start date and End date. Names are generated and read-only.
- Plan Task is Project/SKU planning work. SKU is disabled for Projects without SKUs; Plan is disabled/not applicable. A Project needs no existing Plan to create planning work.
- Test Task must select a Plan from its Project and selected SKU. Test execution, scope, connections and results continue using existing Task/TaskTestCase ownership.
- Plan Task naming uses the full SKU name or the Project name without a SKU. Test Task naming uses its Plan name. NFKC-normalized letters/numbers form the name prefix; other characters are removed, then -001 is appended.
- Plan Task series are scoped by Project ID/SKU ID; Test series by Project ID/Plan ID. Issued names persist after deletion and the counter never recycles. Names are allocated under the existing SQLite BEGIN IMMEDIATE request transaction, including concurrent creation. A series stops at 999 rather than silently changing the three-digit format.
- Dates retain the established optional paired-date behavior; they do not automatically execute tests.
- Original SKU wording is preserved. project_naming.full_sku_name adds the Project name when the normalized SKU does not already begin with it. Plan suggestions and Task naming use this shared resolver.
- Existing Task names are retained; Task rename is removed from UI and rejected by direct and bulk APIs. New Tasks ignore supplied names and are named by the backend.

## Ownership and rename stability
- PlanningTask is a non-executable Project-owned work item with saved sku_id; executable Test Tasks retain their existing plan_id foreign key. No fake Plans or test memberships are created for planning work.
- New Plans save PlanSKU with stable Plan/SKU IDs, including when the user changes the suggested Plan name.
- Startup adopts only unambiguous historical Plans whose names exactly match their raw/full SKU name. Unknown custom historical names are not guessed.
- Project, Plan and SKU renames preserve ownership, Task counts and series scopes. Existing Task names remain fixed; new Tasks use current source names and continue the prior counter. Task lists display current Project/SKU/Plan labels, with saved SKU labels as fallback for removed SKUs.
- Dashboard Project Task counts include planning_task_count plus Plan-owned Test Tasks. Existing Plan result/matrix counts include executable Tasks only.

## Implementation
- Additive tables: planning_tasks, plan_skus, task_name_series, task_name_reservations. Existing Task schema and execution relationships are unchanged.
- Shared endpoints: GET/POST /api/tasks and PATCH/DELETE /api/tasks/<id>.
- GET /api/tasks/options exposes Project/SKU/Plan choices without connection secrets.
- GET /api/tasks/name-preview previews the next name without reserving it. Submission allocates the authoritative number atomically.
- Plan Task links open their Project's Plan workspace; edit actions manage dates/notes. Execution endpoints continue requiring an executable Task.
- Files: models.py, task_management.py, project_naming.py, app.py, plan_state.py, task_management_ui.js, workbench.js, zh.js.

## Verification and delivery
- Final Task suite: 42 passed, including concurrent creation, invalid-date rollback, deletion without reuse, cross-Project/SKU rejection, Plan locks, immutable names, and Project/SKU/Plan rename ownership/count/sequence checks.
- Additional relevant checks: Project import/information 6 passed; current-state suite 22 total, 21 passed and 1 skipped because the historical 17-case fixture is absent.
- Modified JavaScript syntax checks passed for all three scripts.
- Browser on isolated port 5002 created a SKU Plan Task, custom-named-Plan Test Task, and no-SKU/no-Plan planning Task. Verified field order, disabled fields, dates, read-only names, SKU Plan filtering, successful creation and fixed edit ownership.
- Formal SQLite backup used connection.backup after checking no active Tasks: bmca-runtime/backups/task-types-20261021/before.db and before-rows.json (private/local only).
- Copied-database startup and formal post-restart checks passed integrity_check and foreign_key_check. Existing records were preserved; only the established startup folders_migrated false-to-true bookkeeping changed for existing newly created Plans.
- Formal 5000 restarted through bmca-runtime/server.py. Browser verified existing FWA-6084 -> FWA-6084 BMC -> matching Plan, and read-only FWA6084BMC-001 preview. Canceled without creating any formal Task.
- Local screenshots: bmca-runtime/verification/2026-10-21-plan-task.png, 2026-10-21-test-task.png, 2026-10-21-task-types-formal.png. Test log: verification/task-types-tests/final-task-tests.log.
- Full repository suite was not run; no real DUT was contacted. No private runtime data was published.


## Superseding name-uniqueness correction
Task Name is a global unique code across all Projects and Task Types. Collisions increment the three-digit suffix. Permanent global name claims survive Project/Task deletion. See [global Task names](2026-10-21-global-task-names.md), including the formal 001/002 repair and 47 passing Task tests.
