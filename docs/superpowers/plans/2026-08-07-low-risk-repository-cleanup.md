# Low-Risk Repository Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove confirmed disposable artifacts and align log tracking without touching runtime source, non-empty testcase scripts, legacy skills, documents, XML assets, or Git history.

**Architecture:** Treat generated caches and empty directories as disposable filesystem state. Preserve all authored and runtime data, and remove the nested log ignore rule so the repository-level decision to track logs is effective.

**Tech Stack:** PowerShell, Git, Python bytecode/cache conventions.

## Global Constraints

- Preserve all unrelated working-tree changes.
- Do not remove any non-empty testcase script directory.
- Do not modify `.agent`, XML assets, documents, or `.git` objects.
- Verify every destructive target is inside `D:\Pytest_redfish\v4.0` immediately before removal.

---

### Task 1: Remove generated Python and test caches

**Files:**
- Delete: all `**/*.pyc`
- Delete: all `**/__pycache__/`
- Delete if present: `.pytest_cache/`
- Delete if present: `web_ui/tests/_sandboxes/`

- [x] **Step 1:** Enumerate and count the exact targets.
- [x] **Step 2:** Resolve every target and confirm it is within the repository.
- [x] **Step 3:** Remove only the enumerated cache and sandbox targets.
- [x] **Step 4:** Re-scan and require zero remaining targets.

### Task 2: Remove stale local brainstorming sessions

**Files:**
- Delete: `.superpowers/`

- [x] **Step 1:** Read every recorded `server.pid` and confirm none is a running matching process.
- [x] **Step 2:** Resolve `.superpowers` and confirm it is inside the repository.
- [x] **Step 3:** Remove `.superpowers` and verify it no longer exists.

### Task 3: Remove confirmed empty testcase directories

**Files:**
- Delete: the eight empty UUID directories enumerated during the audit.

- [x] **Step 1:** Re-enumerate UUID directories and select only directories with zero children.
- [x] **Step 2:** Remove only those empty directories.
- [x] **Step 3:** Confirm no empty UUID directory remains and no file was removed.

### Task 4: Align log tracking policy

**Files:**
- Delete: `web_ui/workspace/logs/.gitignore`

- [x] **Step 1:** Confirm the file contains only `*.log`.
- [x] **Step 2:** Remove the nested ignore file.
- [x] **Step 3:** Use `git check-ignore` to verify representative `.log` files are no longer ignored.

### Task 5: Verify scope and report

**Files:**
- Inspect: working-tree status and cleanup targets.

- [x] **Step 1:** Re-run target counts and require zero disposable targets.
- [x] **Step 2:** Confirm the fixture database remains healthy with `PRAGMA integrity_check`.
- [x] **Step 3:** Inspect `git status --short` and distinguish this cleanup from pre-existing changes.
