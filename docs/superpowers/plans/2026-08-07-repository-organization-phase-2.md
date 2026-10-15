# Repository Organization Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale agent layout and misleading root-level documentation with a current, discoverable repository structure.

**Architecture:** Keep the current v4-specific skill as repository-owned agent guidance, remove the obsolete v3 skill from active discovery, group formal TestLink XML assets under test assets, and separate current status documents from archived architecture notes. Update every known pointer in the same change.

**Tech Stack:** Markdown, Codex repository skills, PowerShell, Git.

## Global Constraints

- Preserve all unrelated working-tree changes.
- Keep the 67 non-empty unreferenced testcase script directories unchanged.
- Keep runtime code and Git history unchanged.
- Treat Git history as the recovery path for removed obsolete tracked files.

---

### Task 1: Normalize repository-specific skills

**Files:**
- Move: `.agent/skills/bmc_agent_v4_test_management/` to `.agents/skills/bmc_agent_v4_test_management/`
- Delete: `.agent/skills/redfish_interactive_runner/`
- Modify: `.agents/skills/bmc_agent_v4_test_management/SKILL.md`

- [x] **Step 1:** Confirm the v4 skill describes the current Task model and the runner skill describes obsolete v3/Build behavior.
- [x] **Step 2:** Move the v4 skill into `.agents/skills` and remove the obsolete active skill.
- [x] **Step 3:** Update the v4 skill status-document pointer and remove host-specific regression paths.
- [x] **Step 4:** Validate skill frontmatter and confirm `.agent` no longer exists.

### Task 2: Classify TestLink suite assets

**Files:**
- Move: `01.00.00 IPMI.testsuite-deep (3).xml` to `test_assets/test_suites/01.00.00-IPMI.testsuite.xml`
- Move: `02.00.00 Redfish.testsuite-deep (2).xml` to `test_assets/test_suites/02.00.00-Redfish.testsuite.xml`

- [x] **Step 1:** Confirm neither source filename is referenced.
- [x] **Step 2:** Move and normalize both filenames without changing file hashes.
- [x] **Step 3:** Parse both XML files to verify they remain well formed.

### Task 3: Classify project documentation

**Files:**
- Move: `docs/architecture_v3.1.md` to `docs/archive/architecture_v3.1.md`
- Move: `docs/bmc_agent_v4_next_plan.md` to `docs/status/bmc_agent_v4_next_plan.md`
- Move: `docs/bmc_agent_v4_task_management_status.md` to `docs/status/bmc_agent_v4_task_management_status.md`

- [x] **Step 1:** Move historical architecture and current status documents to their designated folders.
- [x] **Step 2:** Update all repository pointers to the new paths.
- [x] **Step 3:** Confirm the old paths have no remaining references.

### Task 4: Correct repository documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [x] **Step 1:** Replace `.agent` with `.agents/skills` in the documented tree.
- [x] **Step 2:** Document the agreed policy that reviewed config, logs, results, and SQLite databases may be tracked.
- [x] **Step 3:** Add concise pointers for the repository skill, status documents, archived notes, and test assets.

### Task 5: Verify organization and scope

**Files:**
- Inspect: moved assets, Markdown pointers, XML, skill frontmatter, Git status.

- [x] **Step 1:** Verify file hashes and XML parsing.
- [x] **Step 2:** Search for stale `.agent`, v3 path, old document path, and old XML filename references.
- [x] **Step 3:** Confirm excluded testcase scripts and runtime source were not modified by this phase.
