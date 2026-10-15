# Plan Pointer Drag and Action Menu Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace unreliable native testcase dragging with pointer-based dragging and eliminate local folder-table scrollbars and clipped action menus.

**Architecture:** Extend the focused `PlanWorkspaceInteractions` module with pure pointer-drag calculations and target classification, then connect those helpers to Test Plan Workspace in `index.html`. Render one fixed action-menu portal outside table wrappers and make plan testcase tables responsive without local overflow containers.

**Tech Stack:** Vanilla JavaScript, Flask static assets, Node built-in test runner, Python `unittest`/pytest source-contract tests, in-app browser verification.

## Global Constraints

- Testcase drag in Test Plan Workspace must not use native HTML5 `draggable` behavior.
- Mouse wheel and edge scrolling must work while the left button remains held.
- Left Plan Folders nodes and middle folder headers use neutral gray target feedback only.
- Folder-to-folder drag, Move to Folder, Golden Plan status, and Classic View behavior remain unchanged.
- Pointer cancellation, Escape, blur, view change, and API failures must clear all transient drag state.

---

### Task 1: Pure pointer-drag interaction helpers

**Files:**
- Modify: `web_ui/static/plan_workspace_interactions.js`
- Test: `web_ui/tests/plan_workspace_interactions.test.js`

**Interfaces:**
- Produces: `hasPointerDragStarted(origin, current, threshold): boolean`
- Produces: `classifyPointerDropTarget(element): {kind: 'row'|'folder', index?: number, key?: string}|null`
- Produces: `getFloatingMenuPosition(rect, viewport, menuSize, gap): {top:number,left:number}`
- Consumes: DOM-like elements exposing `closest()` and `dataset`.

- [ ] **Step 1: Write failing Node tests**

```js
test('pointer drag starts only after the movement threshold', () => {
  assert.equal(api.hasPointerDragStarted({x:10,y:10}, {x:13,y:14}, 6), false);
  assert.equal(api.hasPointerDragStarted({x:10,y:10}, {x:20,y:10}, 6), true);
});

test('drop target classification distinguishes rows and folders', () => {
  assert.deepEqual(api.classifyPointerDropTarget(fakeRow('4')), {kind:'row', index:4});
  assert.deepEqual(api.classifyPointerDropTarget(fakeFolder('custom:IBM')), {kind:'folder', key:'custom:IBM'});
});

test('menu position stays inside the viewport and flips above near the bottom', () => {
  assert.deepEqual(
    api.getFloatingMenuPosition({left:700,right:730,top:570,bottom:600}, {width:800,height:620}, {width:210,height:130}, 5),
    {top:435,left:582}
  );
});
```

- [ ] **Step 2: Run tests and verify failure**

Run: `node --test web_ui/tests/plan_workspace_interactions.test.js`

Expected: FAIL because the three helper functions are not exported.

- [ ] **Step 3: Implement the pure helpers**

```js
function hasPointerDragStarted(origin, current, threshold = 6) {
  return Math.hypot(current.x - origin.x, current.y - origin.y) >= threshold;
}

function classifyPointerDropTarget(element) {
  const folder = element?.closest?.('[data-plan-drop-key]');
  if (folder?.dataset?.planDropKey) return {kind:'folder', key:folder.dataset.planDropKey};
  const row = element?.closest?.('[data-plan-tc-index]');
  if (row?.dataset?.planTcIndex !== undefined) return {kind:'row', index:Number(row.dataset.planTcIndex)};
  return null;
}
```

Implement `getFloatingMenuPosition` by clamping horizontal placement and selecting below/above placement from the available viewport space, then export all three functions.

- [ ] **Step 4: Run Node tests and verify pass**

Run: `node --test web_ui/tests/plan_workspace_interactions.test.js`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add web_ui/static/plan_workspace_interactions.js web_ui/tests/plan_workspace_interactions.test.js
git commit -m "feat: add pointer drag interaction helpers"
```

---

### Task 2: Responsive testcase tables and action-menu portal

**Files:**
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `PlanWorkspaceInteractions.getFloatingMenuPosition(...)`
- Produces: `renderPlanRowActionsPortal(plan): string`
- Produces: `closePlanRowActions(): void` that removes the portal state.

- [ ] **Step 1: Write failing source-contract tests**

```python
def test_plan_tables_do_not_create_local_scrollbars(self):
    html = INDEX.read_text(encoding="utf-8")
    assert ".plan-detail-table-wrap {\n      overflow:visible;" in html
    assert "table-layout:fixed" in html

def test_plan_action_menu_is_rendered_as_a_single_portal(self):
    html = INDEX.read_text(encoding="utf-8")
    rows = slice_function(html, "function renderPlanDetailCaseActions", "function renderPlanDetailRows")
    assert "plan-row-menu" not in rows
    assert "function renderPlanRowActionsPortal(plan)" in html
    assert "${renderPlanRowActionsPortal(plan)}" in html
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest web_ui/tests/test_task_api_contract.py -k "local_scrollbars or single_portal" -q`

Expected: both tests fail against the current in-table menu and `overflow-x:auto` wrapper.

- [ ] **Step 3: Implement responsive layout and portal rendering**

Change `.plan-detail-table-wrap` to `overflow:visible`, set plan tables to `table-layout:fixed`, add ellipsis/truncation rules for testcase and category cells, and reduce fixed Action/Category widths. Remove `.plan-row-menu` markup from each row. Render one portal after the Plan Scope grid using the selected row, `actionMenuPosition`, and existing Move/Edit/Remove callbacks.

Use the pure positioning helper when opening the menu and close it on `#view-plan-detail` scroll, window resize, outside click, view change, or another trigger.

- [ ] **Step 4: Run focused and syntax tests**

Run: `python -m pytest web_ui/tests/test_task_api_contract.py -k "local_scrollbars or single_portal or row_actions" -q`

Run: bundled Node syntax validation over every inline `<script>` block.

Expected: focused tests and syntax validation pass.

- [ ] **Step 5: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: render plan row actions outside tables"
```

---

### Task 3: Replace native testcase drag with pointer drag

**Files:**
- Modify: `web_ui/static/index.html`
- Test: `web_ui/tests/test_task_api_contract.py`
- Test: `web_ui/tests/plan_workspace_interactions.test.js`

**Interfaces:**
- Consumes: `hasPointerDragStarted`, `classifyPointerDropTarget`, existing `requestPlanTestCaseMove`, existing reorder persistence, and existing drag scroll controller.
- Produces: `startPlanTcPointerDrag(event, realIdx): void`
- Produces: `updatePlanTcPointerDrag(event): void`
- Produces: `finishPlanTcPointerDrag(event): Promise<void>`
- Produces: `cancelPlanTcPointerDrag(): void`

- [ ] **Step 1: Write failing pointer-drag contract tests**

```python
def test_plan_rows_use_pointer_drag_instead_of_native_html_drag(self):
    rows = slice_function(INDEX.read_text(encoding="utf-8"), "function renderPlanDetailRows", "function togglePlanDetailGroup")
    assert 'draggable="true"' not in rows
    assert 'onpointerdown="startPlanTcPointerDrag(event,' in rows
    assert 'data-plan-tc-index="${tc.realIdx}"' in rows

def test_pointer_drag_can_route_wheel_and_folder_targets(self):
    html = INDEX.read_text(encoding="utf-8")
    assert "document.elementFromPoint" in html
    assert "handlePlanPointerDragWheel" in html
    assert 'data-plan-drop-key=' in html
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest web_ui/tests/test_task_api_contract.py -k "pointer_drag" -q`

Expected: FAIL because plan rows still use native draggable events.

- [ ] **Step 3: Implement pointer lifecycle and preview**

On left-button pointer down, record pointer ID, source index, origin, and handle. On movement past six pixels, create a fixed preview, add document-level pointermove/pointerup/pointercancel/wheel listeners, and start edge scrolling. Update the preview and classify `document.elementFromPoint(clientX, clientY)` on every move; clear the old neutral target and highlight the new valid target.

Add `data-plan-drop-key` to both left Plan Folders nodes and middle folder headers, plus `data-plan-tc-index` to rows. Wheel routing scrolls `.plan-tree-list` only while the pointer is above that list; otherwise it scrolls `#view-plan-detail` and prevents the page-level default.

- [ ] **Step 4: Commit row reorder or folder move on pointerup**

For a row target call the existing reorder path with the source and target indices. For a folder target call the existing transactional `requestPlanTestCaseMove`. If there is no target, cancel. Always clear listeners, preview, source class, target class, edge-scroll controller, and pointer state in `finally`.

- [ ] **Step 5: Run focused, Node, and syntax tests**

Run: `python -m pytest web_ui/tests/test_task_api_contract.py -k "pointer_drag or plan_tree or middle_plan_group" -q`

Run: `node --test web_ui/tests/plan_workspace_interactions.test.js`

Run: bundled Node inline-script syntax validation.

Expected: all commands pass.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py web_ui/static/plan_workspace_interactions.js web_ui/tests/plan_workspace_interactions.test.js
git commit -m "feat: support wheel scrolling during testcase drag"
```

---

### Task 4: Browser and full regression verification

**Files:**
- Modify only if a browser-discovered defect requires a TDD fix.

**Interfaces:**
- Consumes: Test Plan Workspace on worktree service port 5001.
- Produces: browser evidence and a clean verified branch.

- [ ] **Step 1: Verify narrow-width action menu behavior**

Open Plan_A at a viewport comparable to the user's screenshot. Expand action menus in the first, middle, and bottom visible groups. Confirm every `.plan-detail-table-wrap` has equal client/scroll dimensions, the menu is inside viewport bounds, and Move/Edit/Remove remain visible.

- [ ] **Step 2: Verify pointer drag wheel scrolling**

Press and hold a testcase drag handle, move beyond the threshold, record `#view-plan-detail.scrollTop`, send wheel movement, and confirm scrollTop changes while the drag preview remains visible. Cancel with Escape and verify no testcase mutation.

- [ ] **Step 3: Verify neutral targets and real operations**

During pointer drag, hover a middle folder header and a left Plan Folders node. Confirm exactly one target has `tc-drop-target` and computed background `rgb(55, 65, 81)`. Perform one reorder and one folder move in disposable worktree data, verify server results, and restore the original arrangement.

- [ ] **Step 4: Run the complete regression suite**

Run: `python -m pytest web_ui/tests -q`

Run: `node --test web_ui/tests/plan_workspace_interactions.test.js`

Run: inline JavaScript syntax validation and `git diff --check`.

Expected: zero failures and no syntax/diff errors.

- [ ] **Step 5: Commit any verification-discovered fix and report integration choices**

If Task 4 required no code changes, do not create an empty commit. Confirm `git status --short` is empty, keep 5001 available for user verification, and offer merge/PR/keep-branch options.
