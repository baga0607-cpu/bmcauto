# BMC Agent

A local Windows-friendly test workbench for BMC validation. The Flask web UI manages Project → Plan → Task → Report, with a standard Test Case Repository. No Node.js or npm setup is required to run the application.

## Start locally

Install Python dependencies in your virtual environment, then start the service:

```powershell
python -m pip install flask flask-cors sqlalchemy pyyaml redfish urllib3 reportlab pypdf paramiko
python main_program/main.py
```

Open http://127.0.0.1:5000. The service binds to localhost with debug and reloader disabled. The current local installation also has a managed launcher at `D:/Codex/bmc_auto_test/bmca-runtime/start.ps1`.

## Workflow

1. Create a Project and a Test Plan for a SKU or test scope.
2. In Test Case Repository, import one `.py` per standard Test Case. Each import receives a UTC timestamp as its source version.
3. Add Repository cases to the Plan. The Plan owns independent Python files and editable parameters.
4. Adapt test parameters or Python source in the Plan. The source version stays fixed; all Tasks use the latest Plan definition. Existing evidence remains readable with a rerun notice.
5. Create a Task and save its scope. Run checked cases and inspect execution/API logs. Operator input waits until a response or stop request. Use Resume monitoring after a browser refresh.
6. Generate the current Task PDF report.

Open each Task and configure its BMC and optional console/DUT connections in Connection settings before running tests. Settings are saved independently for each Task, and locked while that Task is executing. The global config.yaml is no longer used by Task execution. The running Test Case cannot be edited. Active execution also locks Plan structure and Task scope. Test Plan documents and Final Report consolidation are pending the report-format decision.

## Single-file interface

A file declares literal `TEST_CASE` metadata and a synchronous `execute(client, context, preset)` function:

```python
TEST_CASE = {
    "name": "Service root check",
    "automation": "automatic",
    "parameters": {
        "preset": {"type": "string", "default": "/redfish/v1/", "label": "Request path"},
        "expected_status": {"type": "integer", "default": 200, "label": "Expected HTTP status"}
    }
}

def execute(client, context=None, preset=None):
    response = client.get(preset)
    assert response.status == context["case_settings"]["expected_status"]
```

Declare `TEST_CASE["automation"]` as `"automatic"` or `"semi_automatic"`. Repository, Plan and Task show Automatic or Semi-automatic badges. Omitted declarations show Unclassified for compatibility; explicit unsupported values are rejected. Classification is read without executing or inspecting behavior and does not restrict execution. Plan copies retain the declaration; changing classification requires importing a new Repository source generation.

Supported parameter types are string, integer, number and boolean. Metadata is parsed without running the source. `preset` is passed to execute; the complete saved parameter dictionary is available as `context['case_settings']`. A case signals failure by raising an exception or setting `context['_tc_status'] = 'FAIL'`.

## Source and runtime layout

- `web_ui/app.py`: local HTTP service and Task execution worker.
- `web_ui/single_case.py`: Repository imports, Plan copies, metadata and editable definitions.
- `web_ui/plan_state.py`: transactional scope, folder, deletion, migration and lock rules.
- `web_ui/static/index.html`, `workbench.js`, `workbench.css`: English file navigator UI.
- `web_ui/workspace/`: SQLite database, current logs and generated reports.
- `main_program/testcase_database/scripts/<case-id>/case.py`: independent Plan Python files.
- `main_program/console_helper.py`: console support shared by cases.
- `docs/status/`: delivery and verification records.

Step/block editing and execution, builder, Golden publishing and unscoped runs are removed. Historical implementations and obsolete test contracts are preserved under `docs/archive/ui-redesign-20261007/`. Existing DB records and evidence are retained; retired cases must be replaced through the Repository to execute.

## Verification

Run Python tests with isolated `BMC_WEB_UI_WORKSPACE_DIR`, `BMC_MAIN_PROGRAM_DIR` and writable TEMP/TMP paths. Do not point mutating tests at your runtime database. See `docs/status/2026-10-07-workbench-ui.md` for the current offline browser and backend verification. Real DUT execution has not been performed by those checks.

## Task management

Open Task management in the top bar. Task information displays all Tasks and a planned-date Gantt chart. New Task selects an existing Project and Plan; Edit changes its name, start/end dates and notes; Delete requires confirmation. Leave both dates blank for an unscheduled Task. End dates are inclusive and dates do not start tests automatically. Click a Task name to open its scope, connection settings, execution and results. Editing preserves existing metadata, scope and connections. Project/Plan assignment stays fixed after creation. Active Plan execution locks management writes.

## Repository folders

BMC is the fixed root in the single Repository directory/Test Case list. Use each directory row?s New folder button to create a child. Non-root rows also offer Edit and Remove. Drag Test Case rows onto a directory to move them. Drag a directory onto the top/bottom edge of another directory to reorder, or onto its center to move inside it. Changes persist after refresh. Removing a directory and its descendants deletes their standard cases after confirmation; Plan copies remain independent.

In a Plan, select Add from Repository, select a directory, then Add folder to Plan. This copies the selected directory and its full subtree into the Plan with independent Python files/settings. Existing Plan case names are skipped with a count. Later Repository changes do not update existing Plan copies.

The Chinese Repository list supports folder collapse and mixed batch selection. Batch-selected directories/cases can be dragged together or deleted after confirmation. Confirm deletion is left of Cancel.
