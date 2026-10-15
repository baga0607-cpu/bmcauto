# Test Plan Workspace Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Classic View plan-library, rename, Golden Plan, folder, and ordering capabilities into the new Test Plan Workspace without removing Classic View or regressing existing plan actions.

**Architecture:** Keep `web_ui/static/index.html` as the existing single-page UI entry point, but add small state and rendering helpers for the new Plan Detail workspace. Extend the existing SQLAlchemy entities and migration bootstrap only with the ordering fields that current storage lacks, then reuse existing plan, library, Golden Plan, and folder APIs instead of creating parallel data flows.

**Tech Stack:** Flask, SQLAlchemy, SQLite, vanilla HTML/CSS/JavaScript, Python `unittest`.

## Global Constraints

- Keep Classic View available for comparison throughout this implementation.
- Keep Generate Summary Report, Export Selected, Import Test Case, Delete Plan, selection, Edit, Remove, statistics, Task Summary, locks, confirmations, and errors.
- Remove only the green `+ Create Task` actions from Test Plan Workspace.
- Native categories may be reordered but may not be renamed or deleted.
- Custom subfolders may be created, renamed, deleted, and reordered.
- Default Plan Detail view is `All Test Cases`, with all category groups visible.
- Left tree manages folder structure; the main list manages Test Cases.
- Reuse existing APIs and state unless persistent ordering cannot be represented.

---

### Task 1: Persist plan, folder, and Test Case ordering

**Files:**
- Modify: `web_ui/models.py:39-86`
- Modify: `web_ui/app.py:55-130`
- Modify: `web_ui/app.py:730-850`
- Modify: `web_ui/app.py:1415-1450`
- Test: `web_ui/tests/test_db_lifecycle.py`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Existing `ProjectPlan`, `PlanSubfolder`, `TestCase`, `/api/projects`, and `PATCH /api/plans/<plan_id>`.
- Produces: `ProjectPlan.category_order: Text`, `PlanSubfolder.position: int`, `TestCase.position: int`; JSON fields `category_order`, ordered `custom_subfolders`, and ordered `testcases`.

- [ ] **Step 1: Write failing model and source-contract tests**

```python
def test_plan_ordering_model_contract(self):
    self.assertTrue(hasattr(ProjectPlan, "category_order"))
    self.assertTrue(hasattr(PlanSubfolder, "position"))
    self.assertTrue(hasattr(TestCase, "position"))

def test_plan_patch_accepts_ordering_contract(self):
    source = (WEB_UI_DIR / "app.py").read_text(encoding="utf-8")
    patch_start = source.index("def patch_plan(plan_id):")
    patch_end = source.index("# API CRUD", patch_start)
    block = source[patch_start:patch_end]
    self.assertIn('if "category_order" in data:', block)
    self.assertIn('position=idx', block)
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_ordering_model_contract web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_patch_accepts_ordering_contract -v
```

Expected: FAIL because the three ordering properties and patch handling do not exist.

- [ ] **Step 3: Add minimal columns and idempotent SQLite migration**

```python
class ProjectPlan(Base):
    # existing columns...
    category_order = Column(Text, nullable=True)

class PlanSubfolder(Base):
    # existing columns...
    position = Column(Integer, default=0)

class TestCase(Base):
    # existing columns...
    position = Column(Integer, default=0)
```

Extend the existing `with sqlite3.connect(DB_PATH) as conn:` startup migration block in `web_ui/app.py`, using the same idempotent `ALTER TABLE` pattern already used for `selected` and task result columns:

```python
try: cursor.execute("ALTER TABLE project_plans ADD COLUMN category_order TEXT")
except sqlite3.OperationalError: pass
try: cursor.execute("ALTER TABLE plan_subfolders ADD COLUMN position INTEGER DEFAULT 0")
except sqlite3.OperationalError: pass
try: cursor.execute("ALTER TABLE testcases ADD COLUMN position INTEGER DEFAULT 0")
except sqlite3.OperationalError: pass
```

- [ ] **Step 4: Serialize and patch ordering**

In `/api/projects`, sort Test Cases by `position`, sort subfolders by `position`, and emit:

```python
pl_data["category_order"] = json.loads(plan.category_order or "[]")
pl_data["custom_subfolders"] = [
    folder.subfolder_name
    for folder in sorted(plan.subfolders, key=lambda item: item.position or 0)
]
```

In `patch_plan`, validate string arrays and update:

```python
if "category_order" in data:
    order = [str(name) for name in data["category_order"] if str(name).strip()]
    plan.category_order = json.dumps(order)

if "custom_subfolders" in data:
    for idx, name in enumerate(data["custom_subfolders"]):
        folder = existing_by_name.get(name)
        if folder is None:
            folder = PlanSubfolder(plan_id=plan_id, subfolder_name=name)
            session.add(folder)
        folder.position = idx
```

Extend the existing plan save/import loop so each Test Case receives `position=idx`.

- [ ] **Step 5: Run database and API tests**

Run:

```powershell
python -m unittest web_ui.tests.test_db_lifecycle web_ui.tests.test_task_api_contract -v
```

Expected: PASS with no destructive migration and stable project serialization.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/models.py web_ui/app.py web_ui/tests/test_db_lifecycle.py web_ui/tests/test_task_api_contract.py
git commit -m "feat: persist test plan ordering"
```

---

### Task 2: Add Plan Detail workspace state and preserve header actions

**Files:**
- Modify: `web_ui/static/index.html:1721-1845`
- Modify: `web_ui/static/index.html:3115-3126`
- Modify: `web_ui/static/index.html:5311-5448`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `currentProjId`, `currentPlanId`, `renamePlan(pid)`, `renderPlanDetail()`.
- Produces: `planDetailState`, `setPlanDetailFolderFilter(key)`, `togglePlanDetailTree()`, and `renameCurrentPlan()`.

- [ ] **Step 1: Add failing UI contract test**

```python
def test_plan_detail_workspace_header_and_state_contract(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    self.assertIn("const planDetailState =", html)
    self.assertIn("function renameCurrentPlan()", html)
    self.assertIn("onclick=\"openClassicPlanView()\"", html)
    self.assertIn("Generate Summary Report", html)
    self.assertIn("Export Selected", html)
    self.assertIn("Import Test Case", html)
    self.assertIn("Delete Plan", html)
    detail_start = html.index("function renderPlanDetail()")
    detail_end = html.index("async function openPlanDetail", detail_start)
    self.assertNotIn("+ Create Task", html[detail_start:detail_end])
```

- [ ] **Step 2: Run the contract test and verify failure**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_workspace_header_and_state_contract -v
```

Expected: FAIL because Plan Detail state and inline rename are missing and `+ Create Task` is still rendered.

- [ ] **Step 3: Add Plan Detail state helpers**

Add near other navigation state:

```javascript
const planDetailState = {
  folderFilter: 'all',
  treeCollapsed: false,
  collapsedGroups: new Set(),
  libraryOpen: false,
  libraryQuery: ''
};

function setPlanDetailFolderFilter(key) {
  planDetailState.folderFilter = key || 'all';
  renderPlanDetail();
}

function togglePlanDetailTree() {
  planDetailState.treeCollapsed = !planDetailState.treeCollapsed;
  renderPlanDetail();
}

function renameCurrentPlan() {
  if (!currentPlanId) return;
  return renamePlan(currentPlanId);
}
```

Reset only `folderFilter` and drawer search when opening a different Plan; retain collapsed group preferences during rerenders of the same Plan.

- [ ] **Step 4: Rebuild the Plan Detail header without regressing actions**

Render the Plan title with a rename button:

```javascript
titleEl.innerHTML = `${escapeHtml(plan.name)}
  <button class="btn-text plan-title-rename" onclick="renameCurrentPlan()" title="Rename plan">&#9998;</button>`;
```

Keep the existing report/export/import/delete buttons, remove both Plan Detail `+ Create Task` renderings, and keep:

```html
<button class="btn-text" onclick="openClassicPlanView()">Classic View</button>
```

- [ ] **Step 5: Add responsive CSS shell**

Add focused classes for:

```css
.plan-workbench {}
.plan-folder-tree {}
.plan-case-pane {}
.plan-library-drawer {}
.plan-folder-tree.is-collapsed {}
```

At the existing mobile breakpoint, make the tree an overlay or full-width section and keep the Test Case table horizontally scrollable.

- [ ] **Step 6: Run UI contract and JavaScript syntax checks**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_workspace_header_and_state_contract -v
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');const m=s.match(/<script>([\\s\\S]*)<\\/script>/);new Function(m[1]);console.log('scripts ok')"
```

Expected: PASS and `scripts ok`.

- [ ] **Step 7: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: establish plan workspace shell"
```

---

### Task 3: Render folder tree, grouped All view, and persistent drag ordering

**Files:**
- Modify: `web_ui/static/index.html:5311-5448`
- Modify: `web_ui/static/index.html:6865-7125`
- Modify: `web_ui/app.py:1415-1450`
- Test: `web_ui/tests/test_task_api_contract.py`
- Test: `web_ui/tests/test_db_lifecycle.py`

**Interfaces:**
- Consumes: `planDetailState`, `saveDB()`, `PATCH /api/plans/<plan_id>`, existing folder functions, and existing Test Case patch routes.
- Produces: `getPlanFolderModel(plan)`, `renderPlanFolderTree(plan)`, `renderPlanCaseGroups(plan)`, `movePlanFolder(sourceKey, targetKey)`, and `dropPlanDetailTc(event, target)`.

- [ ] **Step 1: Add failing folder-tree and drag contract tests**

```python
def test_plan_detail_folder_tree_contract(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    for signature in (
        "function getPlanFolderModel(plan)",
        "function renderPlanFolderTree(plan)",
        "function renderPlanCaseGroups(plan)",
        "function movePlanFolder(sourceKey, targetKey)",
        "function dropPlanDetailTc(event, target)",
    ):
        self.assertIn(signature, html)
    self.assertIn("All Test Cases", html)
    self.assertIn("Native categories cannot be renamed", html)
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_folder_tree_contract -v
```

Expected: FAIL because the new folder model and renderers are absent.

- [ ] **Step 3: Build a stable folder view model**

Implement:

```javascript
function getPlanFolderModel(plan) {
  const categories = new Map();
  (plan.testcases || []).forEach((ref, index) => {
    const tc = resolvePlanTestCase(ref);
    const category = tc.category || 'Uncategorized';
    const subfolder = ref.custom_subfolder || tc.custom_subfolder || null;
    // append {ref, tc, realIdx:index} to the matching group
  });
  // apply plan.category_order, then append previously unseen native categories
  // apply plan.custom_subfolders order within Custom
  return {allCount: plan.testcases.length, categories: orderedCategories};
}
```

Extract `resolvePlanTestCase(ref)` from the lookup logic already used by `renderPlanDetailRows` and Classic View so both render paths resolve missing cases consistently.

- [ ] **Step 4: Render the left tree with structure-only controls**

Render:

- `All Test Cases` first.
- Native categories with counts and drag handles, but no rename/delete buttons.
- Custom root and Custom subfolders with Add Folder, Rename, Delete, counts, and drag handles.
- A collapse button that changes only layout state.
- Drop targets on every destination currently allowed by Classic View.

The native context menu must render disabled copy:

```html
<span class="plan-tree-policy" title="Native categories cannot be renamed">System folder</span>
```

- [ ] **Step 5: Render grouped All Test Cases and filtered views**

`renderPlanCaseGroups(plan)` must:

- Render every category when `folderFilter === 'all'`.
- Render one group when filtered.
- Preserve existing selection, Edit, Remove, status, and missing-Test-Case handling.
- Add group collapse controls without changing the folder filter.
- Preserve `realIdx` so existing mutation functions act on the correct Plan Test Case.

- [ ] **Step 6: Reuse and harden drag operations**

Refactor existing `dragTcStart`, `dragTcDrop`, and `dropTcInCustom` into shared data operations used by both views. After a successful move:

```javascript
await savePlanStructure(plan);
renderPlanDetail();
if (currentViewId === 'plan') renderCurrentPlan();
```

`savePlanStructure(plan)` sends:

```javascript
await fetch(`${API}/plans/${plan.id}`, {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    category_order: plan.category_order || [],
    custom_subfolders: plan.custom_subfolders || []
  })
});
await saveDB();
```

On failure, restore a deep copy of `testcases`, `category_order`, and `custom_subfolders`, rerender, and show the API error.

- [ ] **Step 7: Run focused and full Web UI tests**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_folder_tree_contract -v
python -m unittest discover -s web_ui/tests -v
```

Expected: PASS; native category rename/delete is not exposed.

- [ ] **Step 8: Commit**

```powershell
git add web_ui/static/index.html web_ui/app.py web_ui/tests/test_task_api_contract.py web_ui/tests/test_db_lifecycle.py
git commit -m "feat: add plan folder workbench"
```

---

### Task 4: Add the Test Case Library drawer

**Files:**
- Modify: `web_ui/static/index.html:1721-1845`
- Modify: `web_ui/static/index.html:3115-3126`
- Modify: `web_ui/static/index.html:4150-4305`
- Modify: `web_ui/static/index.html:5360-5425`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Existing library fetch/selection data, `renderLibrary()`, and `addSelectedLibraryToPlan()`.
- Produces: `openPlanLibraryDrawer()`, `closePlanLibraryDrawer()`, `renderPlanLibraryDrawer()`, and `addSelectedPlanLibraryCases()`.

- [ ] **Step 1: Add failing Library drawer contract test**

```python
def test_plan_detail_library_drawer_contract(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    self.assertIn("function openPlanLibraryDrawer()", html)
    self.assertIn("function closePlanLibraryDrawer()", html)
    self.assertIn("function renderPlanLibraryDrawer()", html)
    self.assertIn("function addSelectedPlanLibraryCases()", html)
    self.assertIn('id="plan-library-drawer"', html)
    self.assertIn("Add Test Cases", html)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_library_drawer_contract -v
```

Expected: FAIL because the drawer is absent.

- [ ] **Step 3: Extract shared Library data operations**

Keep the existing sidebar Library operational. Separate fetching and selection from its DOM:

```javascript
async function loadLibraryCases() { /* existing fetch and Golden sync */ }
function getFilteredLibraryCases(query) { /* name/id/category match */ }
async function addLibraryCaseIdsToCurrentPlan(ids) { /* existing duplicate checks and save */ }
```

Both `renderLibrary()` and the new drawer call these helpers.

- [ ] **Step 4: Render and operate the drawer**

Add an always-present drawer host inside `view-plan-detail`. Opening it:

- Does not change `currentViewId`.
- Loads the current Library.
- Supports search, item checkboxes, Select All, Refresh, Cancel, and Add Selected.
- Marks cases already in the Plan and prevents duplicate addition.
- Preserves Plan tree filter and scroll position when closed.

After successful add:

```javascript
await addLibraryCaseIdsToCurrentPlan(selectedIds);
planDetailState.libraryOpen = false;
renderPlanDetail();
```

- [ ] **Step 5: Add drawer accessibility and responsive behavior**

Use `role="dialog"`, `aria-modal="true"`, a labelled heading, Escape-to-close, a backdrop, and focus the search input on open. On narrow layouts, drawer width is `min(100vw, 560px)`.

- [ ] **Step 6: Run tests and JavaScript syntax check**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_library_drawer_contract -v
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');const m=s.match(/<script>([\\s\\S]*)<\\/script>/);new Function(m[1]);console.log('scripts ok')"
```

Expected: PASS and `scripts ok`.

- [ ] **Step 7: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: add plan library drawer"
```

---

### Task 5: Expose Golden Plan actions in the new Test Case list

**Files:**
- Modify: `web_ui/static/index.html:5311-5448`
- Modify: `web_ui/static/index.html:6190-6210`
- Modify: `web_ui/static/index.html:6838-6864`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: Existing Golden Plan membership logic and `addSingleTcToGolden(realIdx)`.
- Produces: `getGoldenPlanMembership(tc)`, `renderPlanDetailCaseActions(realIdx, tc)`.

- [ ] **Step 1: Add failing Golden Plan UI contract test**

```python
def test_plan_detail_golden_action_contract(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    self.assertIn("function getGoldenPlanMembership(tc)", html)
    self.assertIn("function renderPlanDetailCaseActions(realIdx, tc)", html)
    self.assertIn("Add to Golden Plan", html)
    self.assertIn("In Golden Plan", html)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_golden_action_contract -v
```

Expected: FAIL because shared membership/action helpers are absent.

- [ ] **Step 3: Extract shared Golden membership and action rendering**

Use the same stable identity check as Classic View:

```javascript
function getGoldenPlanMembership(tc) {
  const golden = findGoldenPlan();
  return Boolean(golden?.testcases?.some(ref => {
    const candidate = resolvePlanTestCase(ref);
    return candidate.id === tc.id || (
      candidate.family_id && tc.family_id &&
      candidate.family_id === tc.family_id
    );
  }));
}
```

Render either a disabled `In Golden Plan` state or an `Add to Golden Plan` action beside Edit and Remove.

- [ ] **Step 4: Make the existing add function refresh both views safely**

Keep its existing confirmation and backend publication. On success:

```javascript
await loadProjects();
await loadLibraryCases();
if (currentViewId === 'plan-detail') renderPlanDetail();
if (currentViewId === 'plan') renderCurrentPlan();
```

On failure, leave the source Plan Test Case untouched and show the server error.

- [ ] **Step 5: Run focused tests and full Web UI suite**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_golden_action_contract -v
python -m unittest discover -s web_ui/tests -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: add golden plan actions to workspace"
```

---

### Task 6: Regression and browser verification

**Files:**
- Modify if verification finds a scoped defect: `web_ui/static/index.html`
- Modify if verification finds a scoped defect: `web_ui/app.py`
- Modify if verification finds a scoped defect: `web_ui/models.py`
- Test: `web_ui/tests/test_task_api_contract.py`
- Test: `web_ui/tests/test_db_lifecycle.py`
- Test: `web_ui/tests/test_test_layout.py`

**Interfaces:**
- Consumes: Completed Tasks 1–5.
- Produces: Verified parity between Plan Detail and Classic View.

- [ ] **Step 1: Run all automated tests**

Run:

```powershell
python -m unittest discover -s web_ui/tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run static syntax and whitespace checks**

Run:

```powershell
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');const m=s.match(/<script>([\\s\\S]*)<\\/script>/);new Function(m[1]);console.log('scripts ok')"
git diff --check
```

Expected: `scripts ok`; `git diff --check` produces no errors.

- [ ] **Step 3: Start the Flask UI and verify the new workspace**

Run:

```powershell
python app.py
```

From `web_ui`, open the local URL printed by Flask. Verify:

1. Plan opens in All Test Cases with every category visible.
2. Folder filter and return to All preserve data.
3. Native category has no Rename/Delete, but drag ordering persists after reload.
4. Custom folder add/rename/delete/reorder persists after reload.
5. Test Case reorder and allowed folder moves persist after reload.
6. Library drawer single-add, multi-add, search, duplicate blocking, and close behavior work.
7. Plan rename appears in Plan Detail, Project Workspace, and Classic View.
8. Add to Golden Plan changes to In Golden Plan and Library refreshes.
9. Report, export, import, delete, selection, Edit, Remove, and Task Summary remain accessible.
10. Plan Detail has no green `+ Create Task`.
11. Classic View still opens and displays the same Plan data.

- [ ] **Step 4: Add a regression test for every defect found**

For each verified defect, add a focused test to `test_task_api_contract.py` or `test_db_lifecycle.py`, run it to observe failure, apply the minimal fix, and rerun it to PASS. Do not expand scope beyond the approved design.

- [ ] **Step 5: Run the final suite**

Run:

```powershell
python -m unittest discover -s web_ui/tests -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit verification fixes, if any**

```powershell
git add web_ui/static/index.html web_ui/app.py web_ui/models.py web_ui/tests
git commit -m "test: verify plan workspace parity"
```

If Step 4 required no changes, do not create an empty commit.
