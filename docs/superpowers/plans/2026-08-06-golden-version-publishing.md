# Golden Version Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make version-up synchronization and manual publishing create Golden Plan copies using normalized exact test-case names rather than `family_id`.

**Architecture:** Centralize Golden Plan lookup, normalized-name duplicate detection, and test-case cloning in backend helpers used by both `/api/import_tc` and `/api/push_to_golden`. Keep `family_id` on cloned records for lineage, return explicit Golden synchronization status to the frontend, and use the same normalized-name rule for workspace membership labels.

**Tech Stack:** Python 3.12, Flask, SQLAlchemy, SQLite, vanilla JavaScript, `unittest`/`pytest`.

## Global Constraints

- Normalize duplicate names with leading/trailing whitespace removed and Unicode-aware case folding on the backend.
- Preserve version suffixes such as `_V2` and `_V3`; they are different names.
- Never use `family_id` as a duplicate or membership blocker.
- Preserve `family_id` on Golden copies to retain lineage.
- A same-name Golden copy is skipped; a different version in the same family is allowed.
- `Save and Version Up` synchronization must not report success if a real Golden copy failure leaves database or script state partially written.
- Preserve Classic View, existing plan actions, folder placement, and the independent worktree database.

---

### Task 1: Centralize Golden Plan exact-name publishing

**Files:**
- Modify: `web_ui/app.py:1520-1790`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Produces: `_find_normalized_name_duplicate(session, plan_id, display_name) -> TestCase | None`
- Produces: `_get_or_create_golden_plan(session) -> ProjectPlan`
- Produces: `_clone_testcase_record(session, src_tc, target_plan, script_dirs) -> TestCase`
- Changes: `POST /api/push_to_golden` returns HTTP 409 with `reason: "same_name"` for normalized exact duplicates and HTTP 200 for a different version in the same family.

- [ ] **Step 1: Write failing API tests**

Add tests that seed Golden `Indicator_LED_Control_V2` and regular-plan V2/V3 records sharing `family_led`. Assert that publishing ` indicator_led_control_v2 ` returns 409 `same_name`, publishing V3 returns 200, the V3 Golden record preserves `family_led`, and Golden contains one V2 plus one V3.

```python
duplicate = client.post("/api/push_to_golden", json={"system_id": "target_v2"})
other_version = client.post("/api/push_to_golden", json={"system_id": "target_v3"})
self.assertEqual(duplicate.status_code, 409)
self.assertEqual(duplicate.get_json()["reason"], "same_name")
self.assertEqual(other_version.status_code, 200)
```

- [ ] **Step 2: Run the API tests and verify RED**

Run:

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests/test_task_api_contract.py -k push_to_golden -q
```

Expected: FAIL because the current endpoint has no exact-name validation and the workspace family behavior is not shared.

- [ ] **Step 3: Implement minimal reusable backend helpers**

Use `_normalized_tc_name()` for matching. Make cloning copy the source `__testcase__.py`, preserve `family_id`, reproduce category and Golden child-folder placement, add the record without committing, and append each created script directory to `script_dirs` for rollback cleanup.

```python
def _find_normalized_name_duplicate(session, plan_id, display_name):
    wanted = _normalized_tc_name(display_name)
    return next((tc for tc in session.query(TestCase).filter_by(plan_id=plan_id).all()
                 if _normalized_tc_name(tc.display_name) == wanted), None)
```

Update `/api/push_to_golden` to validate by exact normalized name before cloning, return `{"error": "TC already exists", "reason": "same_name"}` with 409 for duplicates, and remove created script directories if the transaction fails.

- [ ] **Step 4: Run the API tests and verify GREEN**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```powershell
git add web_ui/app.py web_ui/tests/test_task_api_contract.py
git commit -m "fix: publish exact testcase versions to Golden Plan"
```

---

### Task 2: Make version-up synchronization create the Golden copy

**Files:**
- Modify: `web_ui/app.py:1610-1725`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `_find_normalized_name_duplicate`, `_get_or_create_golden_plan`, and `_clone_testcase_record` from Task 1.
- Changes: `POST /api/import_tc` accepts `push_to_golden: bool` and returns `golden_sync: "added" | "skipped" | null` plus `golden_id` when added.

- [ ] **Step 1: Write failing synchronization tests**

Add one test that posts a version-up import with `push_to_golden: true` and asserts both current-plan and Golden records exist with the same display name and `family_id`. Add a second request whose normalized name already exists in Golden and assert the current-plan version is created while the response reports `golden_sync == "skipped"` and no duplicate Golden record is created.

```python
response = client.post("/api/import_tc", json={
    "project": "Target_Project",
    "plan_id": "plan_target",
    "category": "Resource_Chassis",
    "tc_name": "Indicator_LED_Control_V3",
    "family_id": "family_led",
    "steps": [],
    "push_to_golden": True,
})
self.assertEqual(response.get_json()["golden_sync"], "added")
```

- [ ] **Step 2: Run the synchronization tests and verify RED**

Run:

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests/test_task_api_contract.py -k import_tc_syncs_version_to_golden -q
```

Expected: FAIL because `/api/import_tc` currently ignores `push_to_golden`.

- [ ] **Step 3: Implement coordinated synchronization**

Read `push_to_golden = bool(data.get("push_to_golden"))`. After creating and flushing the current-plan record, find/create Golden Plan and check its normalized exact names. Clone the new record when absent; otherwise report skipped. Commit once after both database records are ready. Track both new script directories and remove them on exceptions before returning an error.

```python
golden_sync = None
golden_id = None
if push_to_golden:
    golden_plan = _get_or_create_golden_plan(session)
    if _find_normalized_name_duplicate(session, golden_plan.id, new_tc.display_name):
        golden_sync = "skipped"
    else:
        golden_tc = _clone_testcase_record(session, new_tc, golden_plan, created_dirs)
        golden_sync, golden_id = "added", golden_tc.system_id
```

Return `golden_sync` and `golden_id` in the JSON response. Do not change direct-overwrite behavior.

- [ ] **Step 4: Run synchronization and existing import tests**

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests/test_task_api_contract.py -k 'import_tc or push_to_golden' -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```powershell
git add web_ui/app.py web_ui/tests/test_task_api_contract.py
git commit -m "fix: sync versioned testcases to Golden Plan"
```

---

### Task 3: Align workspace membership and user feedback

**Files:**
- Modify: `web_ui/static/index.html:4290-4312,5578-5602,6890-6905,9296-9758`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `normalizeTestCaseName(name)` and backend `golden_sync` response.
- Changes: `getGoldenPlanMembership(tc)` and Classic View `alreadyInGolden` use normalized exact names; version-save success messaging states whether Golden synchronization was added or skipped.

- [ ] **Step 1: Write failing frontend contract tests**

Assert that Golden membership calls `normalizeTestCaseName`, the membership functions do not compare `candidate.family_id === tc.family_id`, the version-save paths inspect `resJson.golden_sync`, and the UI contains distinct copy for added and skipped synchronization.

```python
self.assertIn("resJson.golden_sync", html)
self.assertNotIn("candidate.family_id === tc.family_id", membership_block)
self.assertIn("normalizeTestCaseName(candidate?.tc_name)", membership_block)
```

- [ ] **Step 2: Run the frontend tests and verify RED**

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests/test_task_api_contract.py -k golden_membership -q
```

Expected: FAIL because the detail workspace still uses `family_id` and save success ignores `golden_sync`.

- [ ] **Step 3: Implement exact-name membership and feedback**

Resolve each Golden reference to its full test-case record and compare `normalizeTestCaseName` values. Reuse the same helper in Classic View. After both inline-editor save flows receive `/api/import_tc`, append one of these messages when synchronization was requested:

- `Golden Plan: version published.` for `added`;
- `Golden Plan: skipped because the same version already exists.` for `skipped`.

Keep the existing family-lineage success message, but do not use lineage to determine Golden membership.

- [ ] **Step 4: Run frontend contract and JavaScript syntax tests**

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests/test_task_api_contract.py -k golden_membership -q
& 'C:\Users\tom.hsiao\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');const b=[];let p=0;while((p=s.indexOf('<script',p))>=0){const a=s.indexOf('>',p)+1,e=s.indexOf('</script>',a);b.push(s.slice(a,e));p=e+9;}b.filter(Boolean).forEach(x=>new Function(x));console.log('scripts ok:',b.length);"
```

Expected: frontend tests PASS and `scripts ok: 2`.

- [ ] **Step 5: Commit Task 3**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: show exact Golden testcase membership"
```

---

### Task 4: Regression and browser verification

**Files:**
- Verify: `web_ui/app.py`
- Verify: `web_ui/static/index.html`
- Verify: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes all behavior from Tasks 1-3.
- Produces fresh automated and browser evidence for integration readiness.

- [ ] **Step 1: Run the complete web UI suite**

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui/tests -q
```

Expected: all tests and subtests pass; only the existing `telnetlib` deprecation and SQLAlchemy test-class collection warnings may remain.

- [ ] **Step 2: Verify JavaScript syntax and Git diff hygiene**

Run the Task 3 Node command, followed by `git diff --check` and `git status --short`. Expected: JavaScript parses, no whitespace errors, and only intentional source/test changes plus pre-existing worktree runtime artifacts are listed.

- [ ] **Step 3: Restart the worktree service and verify the UI on port 5001**

Open `http://127.0.0.1:5001/`, navigate to FWA-0624 / Plan_A, and verify:

- a V3 sharing V2's family is not labeled `In Golden Plan` unless Golden has the exact V3 name;
- publishing V3 succeeds and changes the action to `In Golden Plan` after refresh;
- publishing the same normalized V3 again is rejected as a duplicate;
- Save and Version Up with synchronization selected reports `Golden Plan: version published.`;
- a repeated synchronized name reports the skipped message without creating a duplicate.

- [ ] **Step 4: Commit any test-only verification adjustments**

If no source changes are needed, do not create an empty commit. Otherwise stage only intentional files and use:

```powershell
git commit -m "test: cover Golden version publishing flow"
```
