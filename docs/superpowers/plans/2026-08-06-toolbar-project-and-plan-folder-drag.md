# Toolbar Project Selection and Plan Folder Drag Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the toolbar project label synchronized and restore direct testcase drops onto every left Plan Folders target with clear visual feedback.

**Architecture:** Reuse `renderProjectSelect()` as the single project-combobox renderer, and route all testcase folder drops through `dropPlanTcIntoFolder()`. Add small drag-state helpers and CSS classes that distinguish testcase movement from folder sorting without changing backend APIs.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, Flask APIs, pytest source-contract tests, Node JavaScript parsing, browser verification on isolated port 5001.

## Global Constraints

- Do not change testcase data semantics or backend API contracts.
- Classic View and unrelated toolbar actions remain unchanged.
- Native system folders, the direct `Custom` parent, and every Custom child folder are valid testcase targets.
- Folder sorting continues through `movePlanFolder()` and must remain distinct from testcase movement.
- Existing execution locks continue to reject testcase moves.
- The formal port 5000 service and formal database must not be mutated during implementation or verification.

---

### Task 1: Synchronize the Toolbar Project Combobox

**Files:**
- Modify: `web_ui/static/index.html:4112-4185`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `currentProjId`, `currentPlanId`, `renderProjectSelect()`, `reopenCurrentProjectWorkspace(pid)`, and `showView(viewId)`.
- Produces: `changeProject(pid)` and `chooseProjectFromToolbar(pid, event)` flows whose visible button, hidden native select, active option, URL state, and workspace state agree.

- [ ] **Step 1: Write failing project-combobox contract tests**

Add focused assertions that the project-change code refreshes the shared renderer on all state branches:

```python
def test_toolbar_project_selection_rerenders_visible_combobox():
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    choose_start = html.index("function chooseProjectFromToolbar(pid, event)")
    choose_end = html.index("document.addEventListener('click'", choose_start)
    choose_project = html[choose_start:choose_end]
    change_start = html.index("async function changeProject(pid)")
    change_end = html.index("function switchSidebarTab(tab)", change_start)
    change_project = html[change_start:change_end]

    assert "currentProjId = null" in change_project
    assert "renderProjectSelect()" in change_project
    assert "currentProjId = proj ? proj.id : null" in change_project
    assert "renderProjectSelect()" in choose_project
```

Also assert that `renderProjectSelect()` remains the only code assigning `project-select-button.textContent`.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui\tests\test_task_api_contract.py -k toolbar_project_selection -q
```

Expected: FAIL because `changeProject()` does not rerender the custom button after clearing or switching projects.

- [ ] **Step 3: Implement the minimal state synchronization**

Update the project selection flow so state changes precede one shared render:

```javascript
if (!pid) {
  currentProjId = null;
  currentPlanId = null;
  setCurrentTaskId(null);
  renderProjectSelect();
  showView('dashboard');
  return;
}

const proj = findProj(pid);
currentProjId = proj ? proj.id : null;
currentPlanId = proj?.plans?.[0]?.id || null;
setCurrentTaskId(null);
renderProjectSelect();
```

When the already-active project is selected, call `renderProjectSelect()` before `reopenCurrentProjectWorkspace(pid)`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command again.

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```powershell
git add -- web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: synchronize toolbar project selection"
```

---

### Task 2: Unify Left-Tree Testcase Drop Routing

**Files:**
- Modify: `web_ui/static/index.html:5480-5790`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `dragSrcIdx`, `planFolderDragKey`, `dropPlanTcIntoFolder(event, targetKey)`, and `movePlanFolder(sourceKey, targetKey)`.
- Produces: `handlePlanTreeDrop(event, targetKey)` that routes testcase drops for `category:*` and `custom:*` targets through the generalized testcase mover while preserving folder sorting.

- [ ] **Step 1: Write failing drop-routing contract tests**

Add assertions covering native, Custom parent, Custom child, and folder-sort dispatch:

```python
def test_left_plan_tree_routes_testcases_through_generalized_drop_handler():
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    start = html.index("function handlePlanTreeDrop(event, targetKey)")
    end = html.index("function closePlanAddMenu()", start)
    handler = html[start:end]

    assert "dropPlanTcIntoFolder(event, targetKey)" in handler
    assert "dropTcInCustom" not in handler
    assert "dropPlanDetailTc" not in handler
    assert "movePlanFolder(planFolderDragKey, targetKey)" in handler
```

Add markup assertions proving every native and child folder uses the same `handlePlanTreeDrop(event, targetKey)` entrypoint.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui\tests\test_task_api_contract.py -k left_plan_tree_routes -q
```

Expected: FAIL because the left tree still calls the Custom-only legacy helpers and ignores native testcase targets.

- [ ] **Step 3: Implement generalized routing**

Replace the testcase branch with the shared path:

```javascript
function handlePlanTreeDrop(event, targetKey) {
  event.preventDefault();
  clearPlanTreeDropFeedback(event.currentTarget);
  if (dragSrcIdx !== null) {
    dropPlanTcIntoFolder(event, targetKey);
    return;
  }
  movePlanFolder(planFolderDragKey, targetKey);
}
```

Do not remove `dropTcInCustom()` because Classic View still consumes it. Remove `dropPlanDetailTc()` only if a repository search proves it has no remaining callers.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 2 command again.

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```powershell
git add -- web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: route plan tree testcase drops"
```

---

### Task 3: Add Explicit Drag-Target Feedback

**Files:**
- Modify: `web_ui/static/index.html:1850-1890`
- Modify: `web_ui/static/index.html:5480-5790`
- Modify: `web_ui/static/index.html:7570-7600`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: testcase drag lifecycle from `dragTcStart(event, idx)` and folder drag lifecycle from `startPlanFolderDrag(event, key)`.
- Produces: `showPlanTreeDropFeedback(element, targetKey)`, `clearPlanTreeDropFeedback(element)`, and `clearAllPlanTreeDropFeedback()`; CSS states `.tc-drop-target` and `.folder-drop-target`.

- [ ] **Step 1: Write failing feedback contract tests**

Add assertions for distinct CSS and lifecycle cleanup:

```python
def test_plan_tree_drag_feedback_has_target_label_and_cleanup():
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    drag_start = html.index("function dragTcStart(event, idx)")
    drag_end = html.index("async function persistCurrentEntityOrder", drag_start)

    assert ".plan-tree-node.tc-drop-target" in html
    assert ".plan-tree-node.folder-drop-target" in html
    assert "Move to ${" in html
    assert "showPlanTreeDropFeedback(this" in html
    assert "clearPlanTreeDropFeedback(this)" in html
    assert "clearAllPlanTreeDropFeedback()" in html[drag_start:drag_end]
```

Also assert that the rendered feedback element uses a dedicated `.plan-tree-drop-label` class and that native and Custom child rows register `ondragenter`, `ondragover`, `ondragleave`, and `ondrop` cleanup.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui\tests\test_task_api_contract.py -k plan_tree_drag_feedback -q
```

Expected: FAIL because the left folder rows have no visual drag lifecycle.

- [ ] **Step 3: Implement feedback helpers and styles**

Add distinct visual states:

```css
.plan-tree-node.tc-drop-target {
  background: rgba(99, 102, 241, .22);
  box-shadow: inset 0 0 0 2px var(--accent);
  color: #f8fafc;
}
.plan-tree-node.tc-drop-target .plan-tree-icon,
.plan-tree-node.tc-drop-target .plan-tree-name { color: #c4b5fd; }
.plan-tree-node.folder-drop-target { box-shadow: inset 0 0 0 2px #64748b; }
.plan-tree-drop-label { margin-left: auto; color: #c4b5fd; font-size: 10px; font-weight: 800; }
```

Add helpers that only highlight testcase targets when `dragSrcIdx !== null`; folder sorting receives `.folder-drop-target`. Generate labels as `Move to ${targetKey.startsWith('custom:') ? 'Custom / ' + targetKey.slice(7) : targetKey.slice(9)}`. Clear all feedback on `drop`, `dragend`, failed move, successful rerender, and a new drag start.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 3 command again.

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```powershell
git add -- web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: highlight plan folder drop targets"
```

---

### Task 4: Complete Regression and Browser Verification

**Files:**
- Modify only if verification exposes a defect: `web_ui/static/index.html`
- Modify only if verification exposes a missing regression: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: completed Task 1-3 behavior.
- Produces: verified feature branch ready for review and merge.

- [ ] **Step 1: Run the complete automated suite**

```powershell
& 'C:\Users\tom.hsiao\AppData\Local\Programs\Python\Python312\python.exe' -m pytest web_ui\tests -q
```

Expected: all tests and subtests pass; only the known telnetlib deprecation and SQLAlchemy TestCase collection warnings may remain.

- [ ] **Step 2: Parse every inline JavaScript block**

```powershell
& 'C:\Users\tom.hsiao\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');const a=s.split('<script>').slice(1).map(x=>x.split('</script>')[0]);a.forEach(x=>new Function(x));console.log('Parsed '+a.length+' inline scripts successfully.');"
```

Expected: `Parsed 2 inline scripts successfully.`

- [ ] **Step 3: Start the isolated 5001 service with a copied formal DB snapshot**

Use SQLite backup from `D:\Pytest_redfish\v4.0\web_ui\workspace\testcase_meta.db` into the worktree DB. Start the worktree Flask app on port 5001; do not stop or modify port 5000.

- [ ] **Step 4: Verify the project combobox in the browser**

Confirm the visible toolbar button changes to:

1. `-- Select Project --` after clearing.
2. `Golden_Project` after selecting Golden Project.
3. `FWA-0624` after selecting FWA.
4. `FWA-0624` after selecting the already-active FWA project again.

- [ ] **Step 5: Verify drag feedback and routing in the browser**

Using a disposable worktree DB snapshot, drag one testcase over a native folder, Custom, and a Custom child. Confirm the whole target row highlights, shows `Move to <folder>`, clears after leaving/dropping, and the testcase/count moves only after drop. Confirm folder sorting still works independently.

- [ ] **Step 6: Run final diff and status checks**

```powershell
git diff --check main..HEAD
git status --short
```

Expected: committed source changes contain no whitespace errors; only explicitly identified runtime artifacts may remain unstaged.

- [ ] **Step 7: Commit any verification-only regression additions**

If Step 1-6 required a source or test correction:

```powershell
git add -- web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "test: cover toolbar and folder drag interactions"
```

If no correction was required, do not create an empty commit.
