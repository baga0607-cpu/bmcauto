# Plan source import — 2026-10-16

Toolbar Import Test Case replaces folder Add Case icons and the previous Plan .py picker. Source selection is Repository or Project/Plan. The target tree is left and the read-only source tree right. Drag a case or folder subtree, including empty children, right-to-left only; reverse drops are explicitly rejected. Repository imports inherit defaults; Plan imports inherit saved parameters and code. Both lists display versions.

POST /api/plans/<id>/import-cases preflights conflicts and commits atomically. Matching name/source metadata identity and version offers overwrite or skip; the same Case with a different version offers overwrite/update, coexist or skip. Cancel writes nothing. Coexist retains the name. Overwrite retains target identity/placement and Task evidence, increments revision and marks results for retest. The source is untouched.

Database uniqueness is now Plan/name/coalesce(source_version,''). Migration handles both the previous name-only table constraint and standalone index; startup normalization is version-aware. This extends current-case identity without introducing execution history.

Verification supplied by the implementation pass:

- Single-case tests: 20 passed; migration: 1 passed; Plan current-state tests: 21 passed, 1 historical fixture skipped.
- plan-source-import-check.py passed source selectors/dialog, case and folder nesting, defaults/settings inheritance, reverse-drop rejection, cancellation, same-version overwrite, different-version coexist/update, unchanged names, version columns and 1440/1920 desktop checks.
- Full application startup against formal and preview database copies ran twice and preserved all rows; SQLite integrity and foreign-key checks passed, including coexist names. Independent review: Ship.
- Backup: D:/Codex/bmc_auto_test/bmca-runtime/backups/plan-source-import-20261016/before.db and rows.json.

Formal deployment completed on local port 5000 after confirming no active execution. All pre-deployment rows are unchanged, integrity/FK checks passed, and the new import endpoint and version index are loaded. Final deployment backup: before-deploy.db and deploy-rows.json in the same directory. The disposable preview and QA browser are closed. No Git push or tunnel publication. PRODUCT.md, CONTEXT.md, DESIGN.md and the sidecar record the new behavior; tokens are unchanged.

## Import workspace refinement
Latest UI: the whole right workspace, including headings/search, splits into equal target/source panes by default. The full-height divider drags from 25 to 75 percent and supports arrow/Home/End keys. Import trees show only names with source versions beneath; Parameters and Actions are omitted. Source list sizing permits scrolling and wrapping without clipping at either resize limit. The normal Plan table caps at 900px with adjacent parameter/action columns.

Case Conflicts now shows a case-name label and direct action buttons, one conflict at a time. Same version offers Overwrite/Skip; different versions offer Overwrite and update/Keep both/Skip. Only multiple existing versions require a target-version selector. Choices remain buffered until all conflicts are resolved; Cancel imports nothing. No backend behavior changed.

plan-import-layout-check.py passed equal initial pane widths, full-height divider, native pointer resizing, keyboard limits, source overflow checks, hidden action columns, both conflict variants, cancellation and imports. Formal read-only 5000 checks verified the served static UI. Screenshots under bmca-runtime/verification/plan-tree: normal-compact-columns.png, import-equal-workspaces.png, import-1440.png (75/25 stress), import-conflicts.png. No formal data mutation or service restart was needed.


## Unified case-tree styling
Repository is the visual baseline for Plan and import source trees: Case name 14px/700, folder name 15.05px/900, folder SVG 17.5px, case SVG 18px inside 20px tags, versions 11.2px/400 with 1.35 line height, matching header and row spacing. Shared CSS rules prevent source-pane drift; source Case names now use the same strong markup. All trees indent by 1ch per level, with a root collapse spacer for virtual Plan BMC. Formal read-only case-tree-style-check.py compared computed font/weight/line/icon metrics across Repository, Plan and source trees, checked 1ch indentation and no viewport overflow. Screenshot: plan-tree/unified-case-trees.png. No backend changes or data mutation.

## Latest: current Actions during import
The left current Plan tree now retains Actions (folder New/Remove and Case View/Remove) during import; Parameters alone stays hidden. The right source remains read-only. Import Actions reserves 96px. import-actions-check.py passed read-only formal checks for 3 normal/2 import columns, buttons, hidden parameters, source read-only and no viewport overflow. This supersedes the earlier hidden-Actions description.
