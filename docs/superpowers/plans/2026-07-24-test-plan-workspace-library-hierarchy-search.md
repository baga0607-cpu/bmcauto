# Test Plan Workspace Library, Hierarchy, and Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a folder-aware Golden Plan Library, exact-version duplicate handling, hierarchical All Test Cases rendering, and a compact plan-wide search in the new Test Plan Workspace.

**Architecture:** Keep the existing Flask/SQLAlchemy backend and single-page `index.html` architecture. Make `/api/fork_tc` the authoritative exact-name duplicate guard, then reuse one normalized-name rule in Classic View and the new Library UI. Extend `planDetailState` with Library folder and selection state while reusing the existing plan folder model for consistent native and Custom hierarchy.

**Tech Stack:** Python 3, Flask, SQLAlchemy, vanilla JavaScript, HTML/CSS, pytest/unittest.

## Global Constraints

- Classic View remains available.
- Delete Plan, Export Selected, Generate Summary Report, and other existing plan actions remain.
- Custom contains only directly assigned test cases; child folders are mutually exclusive and All Test Cases is the only aggregate.
- Different versions in one family may coexist; only normalized exact display-name duplicates are blocked.
- Name normalization trims leading/trailing whitespace and compares case-insensitively without removing version suffixes.
- Batch add uses partial success; one skipped or failed item must not cancel other valid items.
- The full existing web UI and lifecycle suite must pass.

---

### Task 1: Backend exact-version duplicate guard

**Files:**
- Modify: `web_ui/app.py:1512-1573`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `POST /api/fork_tc` JSON containing `plan_id`, `category`, and `testcase`.
- Produces: success `{status: "ok", id, family_id}`; duplicate HTTP 409 `{error: "TC already exists", reason: "same_name"}`.

- [ ] **Step 1: Write failing API tests**

Add tests that create Golden test cases named `Indicator_LED_Control_V2` and `Indicator_LED_Control_V3`, then assert:

```python
# The target-plan fixture already contains " indicator_led_control_v2 ".

duplicate = client.post("/api/fork_tc", json={
    "project": project.name,
    "plan_id": plan.id,
    "category": category.name,
    "testcase": "Indicator_LED_Control_V2",
})
assert duplicate.status_code == 409
assert duplicate.get_json()["reason"] == "same_name"

other_version = client.post("/api/fork_tc", json={
    "project": project.name,
    "plan_id": plan.id,
    "category": category.name,
    "testcase": "Indicator_LED_Control_V3",
})
assert other_version.status_code == 200
```

Also assert the forked V2 and V3 rows retain the Golden source `family_id`.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "fork_tc and (duplicate or version)" -v
```

Expected: FAIL because `/api/fork_tc` currently has no target-plan duplicate guard and assigns `src_tc.system_id` as the fork family.

- [ ] **Step 3: Implement normalized duplicate validation**

In `fork_tc()`, normalize names with:

```python
def _normalized_tc_name(value):
    return (value or "").strip().casefold()
```

After resolving `src_tc` and `plan_obj`, query the target plan's test cases and return HTTP 409 when:

```python
duplicate = any(
    _normalized_tc_name(candidate.display_name)
    == _normalized_tc_name(src_tc.display_name)
    for candidate in plan_obj.testcases
)
```

Create the fork only after this validation. Set:

```python
family_id=src_tc.family_id or src_tc.system_id
```

Return the resulting `family_id` with the success response.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "fork_tc and (duplicate or version)" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web_ui/app.py web_ui/tests/test_task_api_contract.py
git commit -m "fix: validate exact testcase versions when forking"
```

---

### Task 2: Unify Classic View duplicate and partial-success behavior

**Files:**
- Modify: `web_ui/static/index.html:4198-4405`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Library records with `tc_name`, `testcase`, `category`, and optional selection state.
- Produces: `normalizeTestCaseName(name)`, `findExactPlanNameConflict(plan, candidate)`, and batch result `{added, skipped, failed}`.

- [ ] **Step 1: Write failing static contract tests**

Add assertions that `index.html` contains:

```python
self.assertIn("function normalizeTestCaseName", html)
self.assertIn("function findExactPlanNameConflict", html)
self.assertIn("same version already in plan", html)
self.assertNotIn("family branches already exist", html)
self.assertNotIn("Batch add cancelled", html)
```

Add a JavaScript behavior harness or extracted-script test that verifies:

```javascript
findExactPlanNameConflict(plan, {tc_name: "TC_A_V2"}) === true
findExactPlanNameConflict(plan, {tc_name: "tc_a_v2"}) === true
findExactPlanNameConflict(plan, {tc_name: "TC_A_V3"}) === false
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "library or classic or duplicate" -v
```

Expected: FAIL because Classic View strips `_Vn` and cancels the entire batch.

- [ ] **Step 3: Replace family-regex checks**

Add:

```javascript
function normalizeTestCaseName(name) {
  return String(name || '').trim().toLocaleLowerCase();
}

function findExactPlanNameConflict(plan, candidate) {
  const wanted = normalizeTestCaseName(candidate.tc_name || candidate.testcase);
  return (plan?.testcases || []).some(ref => {
    const full = allTestcases.find(item => String(item.id) === String(ref.id));
    return normalizeTestCaseName(full?.tc_name || ref.tc_name) === wanted;
  });
}
```

Use this helper for Classic View single-item and batch adds. Remove version-suffix family regex checks.

- [ ] **Step 4: Implement partial-success batch processing**

Process every selected record. Count:

```javascript
const result = {added: 0, skipped: 0, failed: 0};
```

- Pre-known exact conflict: increment `skipped`.
- HTTP 409 with `reason === "same_name"`: increment `skipped`.
- Other non-OK response or exception: increment `failed`.
- Success: increment `added` and append the returned test-case reference.

Show:

```javascript
formatLibraryBatchSummary(result)
// "9 added · 1 skipped (same version already in plan)"
```

Do not cancel the batch because of one conflict.

- [ ] **Step 5: Run focused tests and syntax validation**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "library or classic or duplicate" -v
node -e "const fs=require('fs'); const s=fs.readFileSync('web_ui/static/index.html','utf8'); const m=s.match(/<script>([\\s\\S]*)<\\/script>/); new Function(m[1]); console.log('scripts ok');"
```

Expected: tests PASS and output includes `scripts ok`.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: allow exact testcase versions in library adds"
```

---

### Task 3: Build the folder-aware Golden Plan Library

**Files:**
- Modify: `web_ui/static/index.html:5710-5738`
- Modify: `web_ui/static/index.html` Library CSS near existing `.plan-library-*` rules
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `libraryData`, current plan references, and Golden records' `category`/`custom_subfolder`.
- Produces: `getPlanLibraryFolderModel()`, `getVisiblePlanLibraryItems()`, `setPlanLibraryFolderFilter(key)`, `toggleVisiblePlanLibrarySelection(checked)`, `clearPlanLibrarySelection()`.

- [ ] **Step 1: Write failing Library state and markup tests**

Assert the HTML contains:

```python
for marker in (
    "Add from Golden Plan",
    "Import Test Case",
    "plan-library-folder-tree",
    "Select all in this folder",
    "test cases selected",
    "Clear selection",
    "Add Selected (",
):
    self.assertIn(marker, html)
```

Add behavior tests for:

- Custom root excludes records with `custom_subfolder`.
- IBM contains only `custom_subfolder === "IBM"`.
- All Test Cases contains every Library record.
- Selecting a folder does not change `tc.selected`.
- Select-all affects only eligible visible records.
- Active search select-all affects only eligible matching records.
- Changing folders preserves selection.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_library" -v
```

Expected: FAIL because the current drawer is a flat list with no folder selection model or summary bar.

- [ ] **Step 3: Add the combined Add Test Case menu**

Replace the separate action buttons with one purple action:

```html
<button class="btn btn-primary" onclick="togglePlanAddMenu(event)">+ Add Test Case</button>
```

The menu contains:

```html
<button onclick="openPlanLibraryDrawer()">&#11088; Add from Golden Plan</button>
<button onclick="document.getElementById('import-file').click()">&#128229; Import Test Case</button>
```

Close the menu on outside click, Escape, or after choosing an action. Preserve every other plan action and Classic View.

- [ ] **Step 4: Extend Library state and folder model**

Extend `planDetailState` with:

```javascript
libraryFolderFilter: 'all',
librarySelectionMessage: null,
```

Build groups for native categories, direct Custom, and Custom child folders. Use keys:

```javascript
all
category:Resource_Chassis
category:Custom
custom:IBM
```

Search ignores the active folder and returns a flat result list with folder paths. Clearing search restores `libraryFolderFilter`.

- [ ] **Step 5: Render the wide two-column overlay**

Render:

- Header with search and clear button.
- Folder tree with counts and yellow folder icons.
- Right-side list header and explicit select-all checkbox.
- Disabled duplicate rows labeled `Already in plan`.
- Sticky footer with selected count, Clear selection, Cancel, and `Add Selected (N)`.

Determine duplicates with `findExactPlanNameConflict`; do not compare family IDs or Golden source IDs.

- [ ] **Step 6: Preserve selection and batch outcome**

Keep selection across folder/filter changes. After submission:

- Clear successfully added and skipped duplicate selections.
- Retain failed selections.
- Close only when all selected records were added.
- Otherwise keep the overlay open and display the batch summary.

- [ ] **Step 7: Run focused tests and syntax validation**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_library" -v
node -e "const fs=require('fs'); const s=fs.readFileSync('web_ui/static/index.html','utf8'); const m=s.match(/<script>([\\s\\S]*)<\\/script>/); new Function(m[1]); console.log('scripts ok');"
```

Expected: tests PASS and output includes `scripts ok`.

- [ ] **Step 8: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: organize Golden Plan library by folders"
```

---

### Task 4: Render hierarchical All Test Cases and compact plan search

**Files:**
- Modify: `web_ui/static/index.html:5520-5605`
- Modify: `web_ui/static/index.html:5798-5832`
- Modify: `web_ui/static/index.html` Plan Workspace CSS
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: existing `getPlanFolderModel(plan)`, `planDetailState.folderFilter`, `planDetailState.searchQuery`, and `collapsedGroups`.
- Produces: nested Custom group markup and `clearPlanDetailSearch()`.

- [ ] **Step 1: Write failing hierarchy and search tests**

Assert:

```python
self.assertIn("plan-custom-child-groups", html)
self.assertIn("plan-folder-guide", html)
self.assertIn("clearPlanDetailSearch", html)
self.assertIn("Search test cases in this plan", html)
self.assertNotIn("Drag folders on the left; drag test cases in the list.", html)
```

Add behavior coverage that All Test Cases renders:

- yellow folder icons for every native group;
- direct Custom test cases beneath Custom;
- IBM and 000 as nested groups beneath Custom;
- all groups expanded initially;
- search clear restores the prior folder.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_search or folder or hierarchy" -v
```

Expected: FAIL because All Test Cases currently flattens Custom child folders as peer groups and the search occupies a full row.

- [ ] **Step 3: Render nested Custom hierarchy**

For All Test Cases:

- Render native groups first with yellow folder icons.
- Render one Custom parent group.
- Render direct Custom rows immediately inside it.
- Render child groups under a `.plan-folder-guide` container.
- Indent child headers and their rows.

Keep every group header as a valid drag/drop target and preserve `collapsedGroups`.

- [ ] **Step 4: Move and refine plan search**

Place the search control in the right side of `.plan-detail-card-header`. Add:

```html
<span class="plan-search-icon" aria-hidden="true">&#128269;</span>
<input placeholder="Search test cases in this plan…">
<button class="plan-search-clear" onclick="clearPlanDetailSearch()" aria-label="Clear plan test case search">&#10005;</button>
```

Show the clear button only when `searchQuery` is non-empty. Clear on Escape. Remove the drag instruction. At narrow widths, stack the search beneath the title.

- [ ] **Step 5: Run focused tests and syntax validation**

Run:

```powershell
python -m pytest web_ui/tests/test_task_api_contract.py -k "plan_search or folder or hierarchy" -v
node -e "const fs=require('fs'); const s=fs.readFileSync('web_ui/static/index.html','utf8'); const m=s.match(/<script>([\\s\\S]*)<\\/script>/); new Function(m[1]); console.log('scripts ok');"
```

Expected: tests PASS and output includes `scripts ok`.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: clarify plan hierarchy and search"
```

---

### Task 5: Full regression and visual verification

**Files:**
- Test: `web_ui/tests/`

**Interfaces:**
- Consumes: completed Tasks 1–4.
- Produces: verified Test Plan Workspace behavior ready for integration.

- [ ] **Step 1: Run the complete test suite**

Run:

```powershell
python -m pytest web_ui/tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run JavaScript syntax validation**

Run:

```powershell
node -e "const fs=require('fs'); const s=fs.readFileSync('web_ui/static/index.html','utf8'); const m=s.match(/<script>([\\s\\S]*)<\\/script>/); new Function(m[1]); console.log('scripts ok');"
```

Expected: `scripts ok`.

- [ ] **Step 3: Start the worktree service**

Run:

```powershell
python app.py
```

Use a worktree-only port such as 5001 if 5000 is occupied by the formal main service.

- [ ] **Step 4: Verify the UI in a browser**

Check:

1. `+ Add Test Case` menu exposes Golden Plan and Import.
2. Library folders and Custom children have correct counts.
3. Folder navigation does not select test cases.
4. Select-all, search select-all, cross-folder persistence, selected count, and Clear selection work.
5. Existing exact names are disabled; another version from the same family remains selectable.
6. A batch with one duplicate adds all other valid test cases and shows a summary.
7. All Test Cases shows native yellow folder icons and nested Custom children.
8. Plan search is in the Plan Scope header, clears via × and Escape, and remains usable at narrow width.
9. Classic View uses exact-version duplicate handling and partial success.

- [ ] **Step 5: Run final regression after any visual fixes**

Run:

```powershell
python -m pytest web_ui/tests -v
```

Expected: all tests PASS with no new failures.

- [ ] **Step 6: Record verification evidence**

Record the exact passing test count, JavaScript syntax result, browser scenarios checked, and any remaining hardware-only limitations in the task handoff. Do not create an empty verification commit.
