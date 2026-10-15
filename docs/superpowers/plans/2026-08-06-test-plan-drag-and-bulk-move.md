# Test Plan Drag and Bulk Move Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Test Plan Workspace dragging easier to control and add a searchable, safe batch workflow for moving selected test cases into plan folders.

**Architecture:** Keep the existing native HTML5 drag system and monolithic Test Plan rendering pattern, but separate drag scrolling, panel sizing, row-menu state, and destination-picker state into named functions with explicit cleanup. Add one transactional plan-scoped batch move API that validates all requested test cases and the destination before updating category/subfolder assignments, then refresh the existing client models after success.

**Tech Stack:** Flask, SQLAlchemy, SQLite, vanilla JavaScript, HTML/CSS, Python `unittest`/pytest, Node.js syntax checks.

## Global Constraints

- A valid test-case drop target uses neutral gray hover feedback only; no purple/blue styling, accent outline, or `Move to <folder>` label.
- Preserve mouse-wheel scrolling while dragging and support proximity-based page/folder-list edge scrolling with complete cleanup.
- Plan Folders has an independently scrolling body, a fixed header, and one browser-local width shared across all Test Plans.
- `In Golden Plan` remains visible in its current row position.
- `Move` may act on selected rows; `Edit` and `Remove` always act on exactly one row.
- Preserve the active folder filter and search query across a successful move.
- Preserve Classic View, Golden Plan membership/version behavior, project selection, folder ordering, locks, and existing test-case data semantics.
- Do not add a drag-and-drop dependency.

---

### Task 1: Transactional Plan Test Case Move API

**Files:**
- Modify: `web_ui/app.py` near the plan testcase reorder endpoints and existing `/api/move_tc` route
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `ProjectPlan`, `TestCase`, `Category`, `PlanSubfolder`, `locked_project_ids`, and `DbSession`.
- Produces: `POST /api/plans/<plan_id>/testcases/move` with JSON `{ "testcase_ids": string[], "target_key": "category:<name>" | "custom:<name>" }`.
- Success response: `{ "status": "ok", "destination": string, "moved_ids": string[], "skipped_ids": string[], "failed_ids": [] }`.
- Validation failures do not commit any assignment changes.

- [ ] **Step 1: Write failing API tests for native and Custom destinations**

Add test setup with one project, one plan, `Resource_Chassis`, `Custom`, a PlanSubfolder named `IBM`, and three test cases. Assert a native move updates `category_id` and clears `subfolder_id`; assert `custom:IBM` sets category to Custom and sets the plan-owned IBM subfolder.

```python
response = client.post(
    "/api/plans/plan_move/testcases/move",
    json={"testcase_ids": ["tc_a", "tc_b"], "target_key": "custom:IBM"},
)
self.assertEqual(response.status_code, 200, response.get_json())
self.assertEqual(response.get_json()["moved_ids"], ["tc_a", "tc_b"])
self.assertEqual(response.get_json()["skipped_ids"], [])
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "batch_move" -q
```

Expected: FAIL because `/api/plans/<plan_id>/testcases/move` does not exist.

- [ ] **Step 3: Write failing validation, skip, lock, and rollback tests**

Cover these exact cases:

- malformed or duplicate `testcase_ids` returns 400;
- missing plan or any testcase outside the plan returns 404 without mutation;
- missing `custom:<name>` destination returns 404 without creating it;
- unknown category destination returns 404;
- a testcase already in the exact category/subfolder is returned in `skipped_ids` while other items move;
- a plan whose `project_id` is in `locked_project_ids` returns 423;
- a forced `session.commit()` exception returns 500 and leaves every row unchanged.

```python
self.assertEqual(payload["moved_ids"], ["tc_a"])
self.assertEqual(payload["skipped_ids"], ["tc_already_there"])
self.assertEqual(payload["failed_ids"], [])
```

- [ ] **Step 4: Implement destination resolution and transactional move**

Add a small helper and route in `web_ui/app.py`:

```python
def _resolve_plan_move_destination(session, plan_id, target_key):
    if target_key.startswith("custom:"):
        folder_name = target_key[7:]
        category = session.query(Category).filter_by(name="Custom").first()
        folder = session.query(PlanSubfolder).filter_by(
            plan_id=plan_id, subfolder_name=folder_name
        ).first()
        if not category or not folder:
            return None
        return category, folder, f"Custom / {folder_name}"
    if target_key.startswith("category:"):
        category_name = target_key[9:]
        category = session.query(Category).filter_by(name=category_name).first()
        if not category:
            return None
        return category, None, category_name
    return None
```

The route must validate the full ID set before changing any ORM object, preserve request order in `moved_ids`/`skipped_ids`, update category and subfolder together, commit once, rollback on every exception, and return useful `error` text.

- [ ] **Step 5: Run focused API tests**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "batch_move" -q
```

Expected: all batch move tests PASS.

- [ ] **Step 6: Commit the API task**

```powershell
git add web_ui/app.py web_ui/tests/test_task_api_contract.py
git commit -m "feat: add transactional plan testcase moves"
```

---

### Task 2: Neutral Drop Feedback and Drag Scroll Controller

**Files:**
- Modify: `web_ui/static/index.html` CSS near `.plan-tree-node.tc-drop-target` and JavaScript near `dragTcStart`, `dragTcEnd`, `showPlanTreeDropFeedback`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `dragSrcIdx`, `.plan-tree-list`, native `drag`, `dragover`, `drop`, `dragend`, `blur`, and `wheel` events.
- Produces: `startPlanDragScrolling(event)`, `updatePlanDragScrolling(event)`, `stopPlanDragScrolling()`, and `planDragScrollFrame` lifecycle state.
- `showPlanTreeDropFeedback(target, targetKey)` adds only `tc-drop-target` for a valid testcase destination and `folder-drop-target` for valid folder sorting.

- [ ] **Step 1: Replace the old feedback contract test with a failing neutral-feedback test**

Assert the HTML/CSS no longer contains `.plan-tree-drop-label`, `Move to ${`, or purple/accent rules for `.tc-drop-target`, and does contain a neutral gray background. Keep the existing invalid folder target and nested `dragleave` assertions.

```python
self.assertNotIn("plan-tree-drop-label", html)
self.assertNotIn("Move to ${", html)
self.assertIn(".plan-tree-node.tc-drop-target { background:#", html)
self.assertNotIn("box-shadow:inset 0 0 0 2px var(--accent)", html)
```

- [ ] **Step 2: Write failing source-contract tests for drag scrolling lifecycle**

Assert:

- `dragTcStart` installs drag-scroll listeners;
- pointer proximity chooses `.plan-tree-list` when the pointer is inside that element, otherwise the page;
- only one `requestAnimationFrame` loop can run;
- speed is derived from distance to the top/bottom threshold;
- wheel events during testcase drag call the applicable scroll container and prevent native drag cancellation;
- `dragTcEnd`, successful/failed drop paths, `window.blur`, and view teardown call `stopPlanDragScrolling()`.

- [ ] **Step 3: Run the focused UI contract tests and verify they fail**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "drag_feedback or drag_scroll" -q
```

Expected: FAIL on old label styling and missing scroll controller.

- [ ] **Step 4: Implement neutral feedback**

Change the testcase target rule to a neutral gray hover treatment, remove `.plan-tree-drop-label`, and simplify `showPlanTreeDropFeedback`:

```javascript
function showPlanTreeDropFeedback(target, targetKey) {
  clearAllPlanTreeDropFeedback();
  if (!target || !targetKey) return false;
  const isTestcaseDrag = dragSrcIdx !== null;
  if (!isTestcaseDrag && !isPlanFolderDropTargetCompatible(planFolderDragKey, targetKey)) return false;
  target.classList.add(isTestcaseDrag ? 'tc-drop-target' : 'folder-drop-target');
  return true;
}
```

- [ ] **Step 5: Implement the drag scroll controller**

Use constants for edge size and maximum speed. Store the active scroll element and signed speed. `requestAnimationFrame` scrolls `document.scrollingElement` or `.plan-tree-list`; it reschedules only while testcase dragging and speed is nonzero. A folder-list edge zone takes priority over the viewport edge zone.

```javascript
const PLAN_DRAG_EDGE_PX = 72;
const PLAN_DRAG_MAX_SCROLL_PX = 18;
let planDragScrollFrame = null;
let planDragScrollTarget = null;
let planDragScrollSpeed = 0;
```

Install one non-passive wheel handler only while `dragSrcIdx !== null`; remove every temporary listener and cancel the frame in `stopPlanDragScrolling()`.

- [ ] **Step 6: Run focused tests and parse inline JavaScript**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "drag_feedback or drag_scroll" -q
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');s.split('<script>').slice(1).map(x=>x.split('</script>')[0]).forEach(x=>new Function(x));console.log('scripts ok')"
```

Expected: focused tests PASS and Node prints `scripts ok`.

- [ ] **Step 7: Commit the drag interaction task**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: improve plan testcase drag scrolling"
```

---

### Task 3: Resizable and Independently Scrollable Plan Folders

**Files:**
- Modify: `web_ui/static/index.html` CSS and `renderPlanFolderTree(plan)`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Pointer Events, `localStorage`, `.plan-folder-tree`, `.plan-tree-list`.
- Produces: `PLAN_FOLDER_WIDTH_KEY = 'testPlanWorkspace.folderWidth'`, `getPlanFolderWidth()`, `applyPlanFolderWidth()`, `startPlanFolderResize(event)`, and `stopPlanFolderResize()`.
- Width is shared across all plans and clamped to the CSS/JS min/max values.

- [ ] **Step 1: Write failing panel layout and persistence tests**

Assert the tree uses a fixed header plus `overflow-y:auto` list, renders a keyboard-inert resize handle with `onpointerdown`, and restores one shared localStorage key. Assert no plan ID is included in the key.

```python
self.assertIn("const PLAN_FOLDER_WIDTH_KEY = 'testPlanWorkspace.folderWidth'", html)
self.assertIn('class="plan-folder-resize-handle"', html)
self.assertIn("localStorage.setItem(PLAN_FOLDER_WIDTH_KEY", html)
self.assertNotIn("PLAN_FOLDER_WIDTH_KEY + currentPlanId", html)
```

- [ ] **Step 2: Run the panel tests and verify they fail**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_folder_resize or independent_scroll" -q
```

Expected: FAIL because the resize handle and persisted width do not exist.

- [ ] **Step 3: Implement panel layout and width restoration**

Make `.plan-folder-tree` a flex column with an explicit shared width custom property, keep `.plan-tree-header` non-scrolling, and set `.plan-tree-list { min-height:0; overflow-y:auto; }`. Render the resize handle only when expanded.

Use fixed numeric bounds in JavaScript and clamp both stored and pointer-derived values:

```javascript
const PLAN_FOLDER_MIN_WIDTH = 220;
const PLAN_FOLDER_MAX_WIDTH = 440;
const PLAN_FOLDER_DEFAULT_WIDTH = 300;
```

Apply the width after every `renderPlanDetail()` and update it continuously during pointer movement. Persist it on pointer release. Ensure pointer listeners are removed on pointerup, pointercancel, blur, and view teardown.

- [ ] **Step 4: Run focused tests and JavaScript syntax check**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_folder_resize or independent_scroll" -q
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');s.split('<script>').slice(1).map(x=>x.split('</script>')[0]).forEach(x=>new Function(x));console.log('scripts ok')"
```

Expected: focused tests PASS and Node prints `scripts ok`.

- [ ] **Step 5: Commit the panel task**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: resize plan folder panel"
```

---

### Task 4: Row Action Menu, Persistent Selection, and Folder Picker

**Files:**
- Modify: `web_ui/static/index.html` state near `planDetailState`, CSS near Plan detail components, rendering near `renderPlanDetailCaseActions`, and move logic near `dropPlanTcIntoFolder`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Task 1 `POST /api/plans/<plan_id>/testcases/move`, `resolvePlanTestCases(plan)`, `getPlanFolderModel(plan)`, current folder filter/search state, existing `openPlanTcEditor(realIdx)` and `deleteTC(realIdx)`.
- Produces: `planDetailState.actionMenuRealIdx`, `planDetailState.moveDialog`, `getSelectedPlanTestCaseIds(plan)`, `openPlanRowActions(event, realIdx)`, `openPlanMoveDialog(realIdx)`, `renderPlanMoveDialog(plan)`, `setPlanMoveDestination(key)`, `submitPlanTestCaseMove()`, and `closePlanMoveDialog()`.

- [ ] **Step 1: Write failing row-menu rendering tests**

Assert every Plan detail row keeps the Golden Plan control visible, replaces the visible Remove button with a vertical-ellipsis button, and conditionally renders the menu. Assert Edit and Remove call only with `realIdx`, while Move derives the selected batch only when the opened row is selected.

```python
self.assertIn("&#8942;", actions_block)
self.assertIn("In Golden Plan", actions_block)
self.assertIn("openPlanTcEditor(realIdx)", menu_block)
self.assertIn("deleteTC(realIdx)", menu_block)
self.assertNotIn("deleteSelected", menu_block)
```

- [ ] **Step 2: Write failing selection persistence tests**

Assert `setPlanDetailFolderFilter` and `setPlanDetailSearchQuery` do not clear `ref.selected`; selected count is calculated from the entire plan, not only visible rows. Assert opening Move on an unselected row produces only that row's ID without altering the existing selected set.

- [ ] **Step 3: Write failing folder-picker and submit tests**

Assert the modal contains:

- affected count in title and confirm button;
- folder search input;
- hierarchical native/Custom/child destinations built from `getPlanFolderModel(plan)`;
- full selected path;
- disabled confirm until a destination is selected;
- cancel/close without state mutation.

Assert submit calls the Task 1 endpoint once, preserves `planDetailState.folderFilter` and `searchQuery`, reloads projects/testcases, clears submitted selections after success, updates counts, and shows moved/skipped details. Assert 404 missing destination and other failures keep selection and useful server error text.

- [ ] **Step 4: Run focused menu and picker tests and verify they fail**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "row_action or move_dialog or selection_persistence" -q
```

Expected: FAIL because the menu, modal, and batch submission do not exist.

- [ ] **Step 5: Implement row menu state and rendering**

Keep Golden membership beside the ellipsis button. Close menus on outside click, Escape, render, and route change. Label Move as `Move selected (N)` only when the opened row belongs to the selected set; Edit and Remove remain single-row.

```javascript
function getPlanMoveIds(plan, realIdx) {
  const row = plan.testcases[realIdx];
  if (!row) return [];
  if (!row.selected) return [row.id];
  return plan.testcases.filter(ref => ref.selected).map(ref => ref.id);
}
```

- [ ] **Step 6: Implement searchable folder picker**

Reuse folder keys (`category:<name>`, `custom:<name>`) and `planTreeHandlerKey()` for safe handlers. Filter folder labels and full paths case-insensitively while retaining parent context for matching children. Do not offer `all` as a destination.

- [ ] **Step 7: Implement batch submit and result handling**

Refresh locks before submit. Post once to the batch endpoint. On success, preserve filter/search values, reload models, clear selection only for IDs included in the submitted result, rerender detail, and report moved/skipped totals plus `destination`. On failure, keep modal/selection state and display `payload.error || HTTP <status>`.

- [ ] **Step 8: Route drag drops through the same batch move client**

Replace the two-request category-plus-subfolder sequence in `dropPlanTcIntoFolder` with the Task 1 plan move endpoint using one testcase ID. This gives drag and modal moves identical validation, lock, destination, refresh, and error semantics without changing folder sorting.

- [ ] **Step 9: Run focused UI tests and syntax check**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "row_action or move_dialog or selection_persistence or generalized_drop" -q
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');s.split('<script>').slice(1).map(x=>x.split('</script>')[0]).forEach(x=>new Function(x));console.log('scripts ok')"
```

Expected: focused tests PASS and Node prints `scripts ok`.

- [ ] **Step 10: Commit the menu and picker task**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: add batch folder move menu"
```

---

### Task 5: Integrated Regression and Browser Verification

**Files:**
- Modify if verification exposes defects: `web_ui/app.py`, `web_ui/static/index.html`, `web_ui/tests/test_task_api_contract.py`
- Verify: all `web_ui/tests`

**Interfaces:**
- Consumes: Tasks 1-4 complete behavior.
- Produces: a verified branch ready for integration, with no runtime artifacts committed.

- [ ] **Step 1: Run the complete automated Web UI suite**

Run:

```powershell
python -m pytest web_ui/tests -q
```

Expected: all tests and subtests PASS; only already-known dependency/collection warnings may remain.

- [ ] **Step 2: Run static checks**

Run:

```powershell
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');s.split('<script>').slice(1).map(x=>x.split('</script>')[0]).forEach(x=>new Function(x));console.log('scripts ok')"
git diff --check main..HEAD
git status --short
```

Expected: JavaScript parses, diff check is empty, and status contains no tracked or untracked runtime artifacts.

- [ ] **Step 3: Start the isolated worktree service and verify drag behavior in a browser**

Using the worktree database and port 5001, verify:

- testcase target highlight is neutral gray with no label;
- dragging near viewport edges scrolls the page smoothly in both directions;
- the wheel scrolls during testcase drag;
- Plan Folders edge scrolling affects only its list;
- drop, Escape/cancel, blur, and leaving the page stop scrolling;
- folder sorting remains distinct and invalid targets remain non-droppable.

- [ ] **Step 4: Verify panel sizing and persistence in a browser**

Resize Plan Folders to its minimum, middle, and maximum widths; reload; open another plan; confirm the shared width persists. Inject an invalid localStorage value through browser devtools and confirm default-width fallback. Confirm long folder names remain usable with independent scrolling.

- [ ] **Step 5: Verify single and batch move workflows in a browser**

Using disposable worktree data:

- move one unselected testcase from its row menu;
- select testcases across two folder filters and a search result, then move from a selected row;
- search the destination tree and choose a Custom child;
- confirm `In Golden Plan` remains visible outside the menu;
- confirm Edit/Remove affect only the opened row;
- include one testcase already in the destination and verify moved/skipped feedback;
- simulate a deleted destination and a locked project and confirm selections remain;
- reload and verify persisted assignments and folder counts.

- [ ] **Step 6: Fix any verified defects with focused regression tests**

For every defect, first add a focused failing test in `web_ui/tests/test_task_api_contract.py`, run it to confirm failure, apply the smallest correction, rerun the focused test, then rerun the complete suite.

- [ ] **Step 7: Commit verification fixes only if files changed**

```powershell
git add web_ui/app.py web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: close plan move verification gaps"
```

- [ ] **Step 8: Record final evidence**

Capture the full test count, Node parse result, browser scenarios completed, current commit SHA, and any remaining tooling limitation. Do not claim an interaction passed unless it was observed or covered by a deterministic automated test.
