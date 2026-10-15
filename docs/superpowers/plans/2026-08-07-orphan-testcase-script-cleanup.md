# Orphan Testcase Script Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the 67 tracked UUID script directories that have no current, historical, snapshot, test-asset, scenario, or source reference.

**Architecture:** Use `.scratch/audit_testcase_scripts.py` as a deterministic read-only classifier. A directory is removable only when the classifier marks it `unreferenced`, Git confirms it is tracked and therefore recoverable, and its files compile successfully; active and historical directories remain untouched.

**Tech Stack:** Python standard library, SQLite, PowerShell, Git, unittest.

## Global Constraints

- Preserve all 17 directories referenced by the current `testcase_meta.db`.
- Preserve all 11 directories referenced by the legacy fixture, snapshots, test assets, scenarios, or source.
- Remove exactly the 67 classifier results whose category is `unreferenced`.
- Preserve unrelated working-tree changes and do not commit or push.

---

### Task 1: Freeze the deletion set

**Files:**
- Inspect: `main_program/testcase_database/scripts/<UUID>/`
- Use temporarily: `.scratch/audit_testcase_scripts.py`

- [x] **Step 1:** Run the classifier and require `active=17`, `historical_or_external=11`, `unreferenced=67`, and `syntax_error_directories=0`.
- [x] **Step 2:** Require all 67 unreferenced directories to be tracked by Git.
- [x] **Step 3:** Resolve every selected directory and require it to be inside `main_program/testcase_database/scripts/`.

### Task 2: Remove only confirmed orphan directories

**Files:**
- Delete: the 67 UUID directories emitted as `unreferenced` by the classifier.

- [x] **Step 1:** Re-run classification immediately before deletion.
- [x] **Step 2:** Remove each resolved unreferenced directory without using a wildcard deletion target.
- [x] **Step 3:** Re-run classification and require `unreferenced=0`, `active=17`, and `historical_or_external=11`.

### Task 3: Verify runtime behavior

**Files:**
- Test: `web_ui/tests/`
- Inspect: `web_ui/workspace/testcase_meta.db`

- [x] **Step 1:** Confirm every current DB `script_path` resolves to an existing UUID directory.
- [x] **Step 2:** Run `python -B -m unittest discover -s tests -t ..` from `web_ui/` and require all tests to pass.
- [x] **Step 3:** Parse all frontend script blocks and require zero JavaScript syntax errors.

### Task 4: Remove temporary audit tooling and generated caches

**Files:**
- Delete: `.scratch/audit_testcase_scripts.py`
- Delete: test-generated `.pyc`, `__pycache__`, and `web_ui/tests/_sandboxes/`

- [x] **Step 1:** Remove the temporary classifier after final results are captured.
- [x] **Step 2:** Remove only generated caches and the test sandbox.
- [x] **Step 3:** Confirm the temporary tool and generated artifacts no longer exist.
