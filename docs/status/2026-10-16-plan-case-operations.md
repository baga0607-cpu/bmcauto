# Plan Case operations - 2026-10-16

The Plan Case list uses a fixed virtual BMC root. It cannot be renamed, removed or dragged, but accepts folders and cases. Root folder parent_id and root case folder_id are null. First-time legacy migration still converts old categories; already migrated Plans preserve intentional root cases across startup.

Folder controls follow Repository: plus imports a .py into that folder, folder-plus creates a named child, trash confirms subtree removal. Select a folder then click its name to edit; Enter saves and Escape cancels. Folder drops above/below reorder siblings; center reparents; Case drops change their folder. Structural execution locks and Plan ownership checks remain enforced.

POST /api/plans/<plan_id>/testcases/import-python parses literal metadata without executing source, writes an independent Plan script/default parameters, and creates no Repository row. Duplicate names, invalid Python metadata, foreign folders and locked Plans are rejected. Imports roll back files on commit failure. Moving cases accepts explicit folder_id:null for BMC.

## Verification in disposable environments
- test_single_case_repository.py: 14 passed, including direct root/folder import, Repository independence, root move/restart persistence, invalid/foreign/duplicate rejection and active lock.
- test_plan_current_state.py: 21 passed, 1 historical fixture skipped.
- Browser: folder/root file chooser imports, inline rename, child creation, Case/folder drag, delete cancel/confirm and unchanged Repository. Desktop 1440/1920 with no horizontal overflow.
- Script: bmca-runtime/verification/plan-operations-check.py. Screenshots: bmca-runtime/verification/plan-tree/operations-{1440,1920}.png.
- Finish review: Ship, no blockers.

## Local deployment
Formal port 5000 restarted after confirming no active execution. SQLite backup: bmca-runtime/backups/plan-operations-20261016/before.db; row baseline: rows.json. Migration ran first on the backup copy, with all existing rows unchanged. Formal startup verified the new endpoint, unchanged existing rows, integrity_check=ok and no foreign-key violations. Preview 5136 and QA browser closed. No external tunnel or Git push.


## Plan detail pane follow-up
Parameters and View now use the Repository pane layout: only name and 27px Close in the fixed header, independently scrolling content, shared width resizer. Parameters shows editable Plan values; View shows editable Python source. Source version, revision, descriptions and the old organization/export section are removed from this pane. Save retains the other mode's values and existing execution locks. Chinese labels added for Plan editor controls.

Disposable browser test plan-pane-check.py passed fixed-header scrolling with 25 fields, parameter save, source save preserving parameters, separate visible modes, resizing, closing and 1440/1920 overflow checks. Screenshots: plan-tree/pane-{1440,1920}.png. Static-only update; formal service serves the new assets without restart.


### View is read-only (latest user decision)
Plan View now renders escaped Python in a read-only code block, without Read editable fields, Save Plan Test Case or any editing controls. Parameters retains the editable fields and save action, preserving the loaded source unchanged. This supersedes the editable-source pane described above. Disposable browser verification plan-readonly-check.py passed exact source display, absence of editor/buttons, scrolling and parameter save without source changes. Static update served by the running local service.


Zero-parameter cases now omit Parameters buttons in both Plan and Repository lists. Project overview exposes parameter_count from the independent Plan Python metadata. Disposable browser parameter-count-check.py verified zero/one-parameter cases in both lists, with View retained. Local service restarted after confirming no active execution.
