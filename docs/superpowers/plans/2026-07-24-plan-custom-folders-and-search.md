# Plan Custom Folders and Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Custom and its child folders exclusive membership semantics and add a plan-wide testcase search to Test Plan Workspace.

**Architecture:** Keep the existing backend representation because `custom_subfolder` already identifies exclusive folder membership. Centralize the browser-side folder model so tree counts, filters, grouped lists, drag targets, and search all consume the same resolved testcase records.

**Tech Stack:** Vanilla JavaScript and CSS in `web_ui/static/index.html`; Python `unittest` contract tests in `web_ui/tests/test_task_api_contract.py`; Flask/SQLite APIs remain unchanged.

## Global Constraints

- `All Test Cases` is the only aggregate folder.
- `Custom` contains only Custom testcases with no `custom_subfolder`.
- Search spans the current Plan and matches name, ID, category, or Custom folder, but not step/module paths.
- Search must not mutate testcase selection, order, or folder membership.
- Existing valid testcase script directories, including untracked database-owned directories, must not be modified.

---

### Task 1: Exclusive Custom folder model

**Files:**
- Modify: `web_ui/static/index.html:5345-5568`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `resolvePlanTestCases(plan)` records with `category` and `custom_subfolder`.
- Produces: `getPlanFolderModel(plan)` groups whose `cases` represent direct membership and whose `subfolders` represent exclusive child membership.

- [ ] **Step 1: Write the failing contract test**

Add a test asserting that the Custom group exposes direct root cases through
`cases` and that the tree count uses `group.cases.length`:

```python
def test_custom_folder_uses_exclusive_direct_membership(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    start = html.index("function getPlanFolderModel(plan)")
    end = html.index("function setPlanDetailFolderFilter", start)
    block = html[start:end]
    self.assertIn(
        "const directCases = name === 'Custom' ? cases.filter(tc => !tc.custom_subfolder) : cases;",
        block,
    )
    self.assertIn("cases: directCases,", block)
    self.assertNotIn("rootCases:", block)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_custom_folder_uses_exclusive_direct_membership -v
```

Expected: FAIL because the current model stores every Custom testcase in `cases`.

- [ ] **Step 3: Implement exclusive membership**

In `getPlanFolderModel`, retain the raw category list only while building the
model:

```javascript
const directCases = name === 'Custom'
  ? cases.filter(tc => !tc.custom_subfolder)
  : cases;
return { name, cases: directCases, subfolders };
```

Build Custom subfolders from both the saved folder list and testcase
assignments so orphaned assignments remain visible:

```javascript
const folderNames = [...new Set([
  ...(plan.custom_subfolders || []),
  ...cases.map(tc => tc.custom_subfolder).filter(Boolean)
])];
```

Update complete-list rendering to use `group.cases` for the Custom root and
continue rendering each `group.subfolders` collection separately.

- [ ] **Step 4: Run the focused and workspace tests**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_custom_folder_uses_exclusive_direct_membership web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_workspace_parity_contract -v
```

Expected: both PASS.

- [ ] **Step 5: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "fix: make custom folders mutually exclusive"
```

---

### Task 2: Plan-wide testcase search

**Files:**
- Modify: `web_ui/static/index.html:1850-1870,3590-3610,5535-5570,5670-5720`
- Test: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: `resolvePlanTestCases(plan)` and `planDetailState.searchQuery`.
- Produces: `setPlanDetailSearchQuery(value)` and `getPlanSearchResults(plan, query)`.

- [ ] **Step 1: Write the failing search contract test**

```python
def test_plan_detail_has_plan_wide_testcase_search(self):
    html = (WEB_UI_DIR / "static" / "index.html").read_text(encoding="utf-8")
    self.assertIn("searchQuery: ''", html)
    self.assertIn("function setPlanDetailSearchQuery(value)", html)
    self.assertIn("function getPlanSearchResults(plan, query)", html)
    self.assertIn("Search test cases by name, ID, category, or folder...", html)
    self.assertIn("plan-search-results", html)
    self.assertIn("No test cases match this search.", html)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_has_plan_wide_testcase_search -v
```

Expected: FAIL because plan search state and helpers do not exist.

- [ ] **Step 3: Add search state and matching**

Extend `planDetailState` with `searchQuery: ''`. Reset it only when switching
to a different plan. Add:

```javascript
function setPlanDetailSearchQuery(value) {
  planDetailState.searchQuery = value || '';
  renderPlanDetail();
}

function getPlanSearchResults(plan, query) {
  const needle = String(query || '').trim().toLowerCase();
  if (!needle) return [];
  return resolvePlanTestCases(plan).filter(tc => [
    tc.tc_name || tc.testcase || '',
    tc.id || '',
    tc.category || '',
    tc.custom_subfolder || ''
  ].some(value => String(value).toLowerCase().includes(needle)));
}
```

- [ ] **Step 4: Render the search control and flat results**

Place the input inside the Plan Scope card header/body boundary:

```html
<input class="task-setup-input plan-scope-search"
  placeholder="Search test cases by name, ID, category, or folder..."
  value="${escapeHtml(planDetailState.searchQuery)}"
  oninput="setPlanDetailSearchQuery(this.value)">
```

When the trimmed query is non-empty, `renderPlanCaseGroups` must bypass
`folderFilter` and render one flat `plan-search-results` table using
`renderPlanDetailRows(results)`. Use the existing row category cell to show
the full `Custom / folder` path. An empty result renders
`No test cases match this search.`

- [ ] **Step 5: Run focused tests and JavaScript syntax validation**

Run:

```powershell
python -m unittest web_ui.tests.test_task_api_contract.TaskApiContractTest.test_plan_detail_has_plan_wide_testcase_search -v
node -e "const fs=require('fs');const s=fs.readFileSync('web_ui/static/index.html','utf8');[...s.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach(m=>new Function(m[1]));"
```

Expected: test PASS and Node exits 0.

- [ ] **Step 6: Commit**

```powershell
git add web_ui/static/index.html web_ui/tests/test_task_api_contract.py
git commit -m "feat: add plan testcase search"
```

---

### Task 3: Regression and browser verification

**Files:**
- Verify: `web_ui/static/index.html`
- Verify: `web_ui/tests/test_task_api_contract.py`

**Interfaces:**
- Consumes: completed folder and search behavior.
- Produces: verification evidence only.

- [ ] **Step 1: Run the complete relevant test suite**

```powershell
python -m unittest web_ui.tests.test_task_api_contract web_ui.tests.test_test_layout -v
```

Expected: all relevant tests PASS.

- [ ] **Step 2: Verify formatting and syntax**

```powershell
git diff --check
```

Expected: exit 0 with no output.

- [ ] **Step 3: Restart the writable worktree service**

Restart `http://127.0.0.1:5001` from `C:\tmp\rf-plan-ui\web_ui` using the
workspace Python runtime and an unrestricted background process, preserving
the existing database.

- [ ] **Step 4: Verify actual folder counts and filters**

Use a Plan containing Custom root and child-folder testcases. Confirm:

- `Custom` count equals only unassigned Custom testcases;
- selecting `Custom` excludes `000` and `IBM` cases;
- selecting each child folder shows only its assigned cases;
- All Test Cases contains every testcase exactly once.

- [ ] **Step 5: Verify actual search behavior**

From a selected child folder, search for a testcase in another folder.
Confirm it appears once with its full folder path. Clear the input and confirm
the previously selected folder view returns.

- [ ] **Step 6: Confirm repository state**

```powershell
git status --short
git log -5 --oneline
```

Expected: only pre-existing database-owned script directories may remain
untracked; no implementation files are uncommitted.
