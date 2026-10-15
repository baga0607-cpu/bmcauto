# Test Plan Workspace Follow-up Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Plan test-case ordering durable, keep rename navigation stable, repair Golden Plan publishing, align the folder tree, and fully collapse the Workspace sidebar.

**Architecture:** Extend the existing Flask/SQLAlchemy API with a plan-scoped reorder operation and keep the current single-page JavaScript renderer as the UI integration point. Behavioral contract tests cover frontend wiring and Flask test-client tests cover persistence; browser checks cover the visual and navigation outcomes.

**Tech Stack:** Python, Flask, SQLAlchemy, SQLite, `unittest`, vanilla JavaScript, HTML, CSS.

## Global Constraints

- Keep Classic View and every existing plan action.
- Native folders remain non-renamable.
- Do not redesign the test-reference module.
- Use immutable plan UUIDs for navigation.
- Persist ordering transactionally and restore optimistic UI state on failure.

---

### Task 1: Persist Plan Test-case Ordering

**Files:**
- Modify: `web_ui/app.py`
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `TestCase.plan_id`, `TestCase.system_id`, and `TestCase.position`.
- Produces: `POST /api/plans/<plan_id>/testcases/reorder` with JSON `{ "order": ["<system_id>", ...] }`.

- [ ] **Step 1: Write failing endpoint tests**

Add tests that create a plan with three test cases, post the reversed ID list, then assert the response is 200 and database positions are `0, 1, 2` in the requested order. Add cases asserting 400 for a non-list `order`, 400 for duplicate/foreign IDs, and 404 for an unknown plan.

- [ ] **Step 2: Run endpoint tests and verify RED**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_testcase_reorder_persists_positions -v
```

Expected: FAIL because the route returns 404.

- [ ] **Step 3: Implement the endpoint**

Add a route that validates the payload before mutation:

```python
@app.route("/api/plans/<plan_id>/testcases/reorder", methods=["POST"])
def reorder_plan_testcases(plan_id):
    order = (request.get_json(silent=True) or {}).get("order")
    if not isinstance(order, list):
        return jsonify({"error": "order must be a list"}), 400
    normalized = [str(tc_id) for tc_id in order]
    if len(normalized) != len(set(normalized)):
        return jsonify({"error": "order contains duplicate test cases"}), 400
    session = DbSession()
    try:
        plan = session.query(ProjectPlan).filter_by(id=plan_id).first()
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        cases = session.query(TestCase).filter_by(plan_id=plan_id).all()
        by_id = {tc.system_id: tc for tc in cases}
        if set(normalized) != set(by_id):
            return jsonify({"error": "order must contain every plan test case exactly once"}), 400
        for position, tc_id in enumerate(normalized):
            by_id[tc_id].position = position
        session.commit()
        return jsonify({"status": "ok"})
    except Exception as error:
        session.rollback()
        return jsonify({"error": str(error)}), 500
    finally:
        session.close()
```

- [ ] **Step 4: Write and run the failing frontend contract test**

Assert that `dragTcDrop` snapshots the order, awaits the plan reorder endpoint when no task is selected, and restores the snapshot in `catch`. Run the new test and confirm it fails because Plan Detail currently saves only task ordering.

- [ ] **Step 5: Implement awaited client persistence**

Add `persistCurrentEntityOrder(entity)` which selects the task or plan endpoint, posts `entity.testcases.map(tc => tc.id)`, decodes backend errors, and throws on failure. Use it after same-category and cross-category moves; preserve a snapshot and restore it before rerendering when persistence fails.

- [ ] **Step 6: Run focused and full tests**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add web_ui/app.py web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: persist plan testcase ordering"
```

### Task 2: Preserve Plan Detail During Rename

**Files:**
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `renamePlan(pid)` and the immutable `pid`.
- Produces: refreshed project data rendered through `openPlanDetail(pid)` without changing `currentPlanId` to a name.

- [ ] **Step 1: Write a failing contract test**

Extract the `renamePlan` block and assert it does not contain:

```javascript
currentPlanId = newName.trim();
selectPlan(currentPlanId, true);
```

Assert it records the source view and calls `openPlanDetail(pid)` when renaming from `plan-detail`.

- [ ] **Step 2: Run the test and verify RED**

Run the focused unittest and expect failure on the existing name assignment/navigation.

- [ ] **Step 3: Implement stable rename navigation**

Keep `pid`, refresh `/api/projects`, set `currentPlanId = pid`, render the sidebar, and call `openPlanDetail(pid)` when the source view was Plan Detail. Other views rerender their current content without redirecting to Dashboard.

- [ ] **Step 4: Run tests and commit**

Run the full contract suite, expect PASS, then:

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: keep plan detail open after rename"
```

### Task 3: Repair Golden Plan Publishing

**Files:**
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `POST /api/push_to_golden`, whose required field is `system_id`.
- Produces: `addSingleTcToGolden(realIdx)` that reports backend `error` text and refreshes Plan Detail.

- [ ] **Step 1: Write a failing contract test**

Assert the function body contains:

```javascript
body: JSON.stringify({ system_id: tcMeta.id })
```

and decodes the response JSON before throwing for a non-OK response. Assert it refreshes both projects and test cases, then calls `renderPlanDetail()`.

- [ ] **Step 2: Run the test and verify RED**

Expected: FAIL because the current payload uses `tc_id`.

- [ ] **Step 3: Implement the contract correction**

Send `system_id`, parse JSON once, throw `payload.error || \`HTTP ${res.status}\``, then `await Promise.all([reloadProjects(), refreshAllTestcases()])` and render the current Plan Detail.

- [ ] **Step 4: Run tests and commit**

```powershell
python -m unittest web_ui.tests.test_task_api_contract -v
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: publish plan testcase to golden plan"
```

Expected: PASS.

### Task 4: Align Folder Tree and Fully Collapse Workspace

**Files:**
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `.plan-tree-node`, `.app-sidebar`, and the `app-nav-collapsed` body class.
- Produces: stable `.plan-tree-icon`, `.plan-tree-name`, `.count`, and `.plan-tree-end` columns; a zero-width collapsed sidebar.

- [ ] **Step 1: Write failing markup and CSS contract tests**

Assert folder rows contain dedicated icon/name/end wrappers and CSS includes:

```css
.plan-tree-node { grid-template-columns:18px minmax(0,1fr) 28px minmax(54px,auto); }
body.app-nav-collapsed .app-sidebar { width:0; border-right:0; overflow:hidden; }
```

Also assert the old `width: 72px` collapsed rule is absent.

- [ ] **Step 2: Run tests and verify RED**

Expected: FAIL because the folder rows use free-form flex and the sidebar retains a 72 px icon rail.

- [ ] **Step 3: Implement folder grid markup and styles**

Wrap icons, names, and trailing policy/actions in their named elements. Apply the same four-column grid to All Test Cases, native folders, and Custom subfolders. Permit name wrapping with `overflow-wrap:anywhere`, keep counts centered, and indent subfolder icons without changing column alignment.

- [ ] **Step 4: Implement full sidebar collapse**

Change the collapsed sidebar to zero width, zero border, hidden overflow, and no shadow. Keep `toggleAppSidebar()` and its `localStorage` preference unchanged so the header hamburger restores it.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m unittest web_ui.tests.test_task_api_contract -v
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: align plan folders and collapse workspace"
```

Expected: PASS.

### Task 5: End-to-end Verification

**Files:**
- Verify: `web_ui/app.py`
- Verify: `web_ui/static/index.html`
- Verify: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: all changes from Tasks 1–4.
- Produces: evidence that the five reported behaviors work together.

- [ ] **Step 1: Run syntax and automated tests**

```powershell
python -m py_compile web_ui/app.py
python -m unittest web_ui.tests.test_task_api_contract -v
node -e "const fs=require('fs'); const s=fs.readFileSync('web_ui/static/index.html','utf8'); const m=s.match(/<script>([\\s\\S]*)<\\/script>/); new Function(m[1]); console.log('scripts ok');"
```

Expected: compilation succeeds, tests pass, and output includes `scripts ok`.

- [ ] **Step 2: Run browser validation**

At `http://127.0.0.1:5001`, verify:

1. Reorder two Plan test cases, reload, and confirm the order remains.
2. Rename the Plan and confirm the same Plan Detail and folder filter remain open.
3. Publish a non-Golden test case and confirm it becomes “In Golden Plan.”
4. Confirm long native and Custom folder names align with counts and actions.
5. Collapse Workspace, confirm no icon rail remains, then restore it from the header.

- [ ] **Step 3: Inspect the final diff**

Run `git diff --check` and `git status --short`. Expected: no whitespace errors and only intended files changed.

