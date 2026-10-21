# Current handoff

Read [2026-10-21 handoff](2026-10-21-handoff.md) first. This supersedes older navigation and publication instructions.

# Latest update

2026-10-21: See [Project view/edit and workbook import](2026-10-21-project-import.md). New Project workbook import is now implemented; this supersedes earlier notes describing it as future work.

# BMC Agent next steps

Last updated: 2026-10-21

Project Information framework: [delivery and future import mapping](2026-10-21-project-information.md). Workbook upload/automatic Project creation remains future work.

Latest navigation update: [persistent sidebar](2026-10-20-sidebar-layout.md), superseding earlier navigation and sidebar visibility rules.

Start here: [latest handoff](2026-10-16-handoff.md). Its current UI and import rules supersede older descriptions below.

The current local checkout implements the single-file Repository and English file navigator workbench. The user approved complete removal of step/block editing and execution, replacing the earlier compatibility decision.

- Current UI and verification: [workbench delivery](2026-10-07-workbench-ui.md).
- Ownership and single-file contract: [approved design](../superpowers/specs/2026-10-07-single-file-case-design.md).
- Prior facet evidence: [single-file delivery](2026-10-07-single-file-case-delivery.md).

Continue case by case with environment injection and the agreed result states. Test Plan documents, report formats and Final Report aggregation remain pending discussion. Do not add placeholder controls for undecided functions.

This change is local; it has not been committed or pushed. Historical 2026-09-30 deployment/publishing permissions and counts belong to that earlier delivery and do not describe the current checkout. Preserve current work and use disposable databases/scripts for verification. The offline checks do not validate real BMC behavior.

Task-owned connection environment delivered locally: [Task connection settings](2026-10-14-task-connection-settings.md).

Desktop-only UI scope and current layout findings: [desktop layout review](2026-10-14-desktop-layout-review.md). Mobile support is deferred.

Task management first increment delivered locally: [Task information, CRUD and Gantt](2026-10-14-task-management.md). Further task management features remain for separate decisions.

Repository function page add/view/remove and exclusive workspace: [Repository page](2026-10-14-repository-page.md).

Automation declaration and badges delivered locally: [classification delivery](2026-10-14-automation-labels.md).

Repository folders and whole-folder Plan copies: [delivery](2026-10-14-repository-folders.md).

Current Repository BMC tree, recursive directories and drag/drop: [delivery](2026-10-14-repository-tree.md). Supersedes the prior flat Repository folder UI and two-level Plan depth constraint for subtree preservation.

Latest handoff (2026-10-15): [complete current decisions, paths and verification](2026-10-15-handoff.md). Read this before resuming in a new conversation.

RF-01-001 integration audit (2026-10-15): [current local records, isolated runner verification and remaining gaps](2026-10-15-rf01-integration-audit.md). Repository and Plan already contain the exact current case; no Task exists in the audited live database. Next proposed increment is method metadata validation and Plan presentation.


2026-10-16: Plan Case operations now use the fixed BMC root, direct Python import, folder inline rename and drag/drop. Verified and deployed locally; see [Plan Case operations](2026-10-16-plan-case-operations.md).

## Latest status pointer — 2026-10-16 Plan source import

Read docs/status/2026-10-16-plan-source-import.md before continuing. The implemented toolbar/dual-tree workflow and version-aware conflict rules supersede earlier Plan .py picker and folder Add Case plans. Tests, copied-database startup checks and formal port 5000 deployment passed. All existing rows remain unchanged, integrity/FK checks passed, and the version-aware index and import endpoint are loaded. Preserve before-deploy.db and deploy-rows.json in the backup directory.
Test Case ordering (2026-10-19): all case-list views use folder-local natural numeric name ordering by default. A manual before/after drag stores a folder-specific custom order; folder Actions > Resorting restores automatic numbering for direct cases. Repository case-only batches and Plan case/source-case insertion support before/after anchors. Dashed allowed-area frames and active inside/upper/lower-half boxes show placement; self/cycle/locked/reverse-source targets are rejected. Source panes remain read-only. Persistent overrides are additive case_list_orders records, independent of definitions and Task evidence. See docs/status/2026-10-19-case-ordering.md.

Unified logs (2026-10-19): `context['log']` supplies section/http/check/finish; RF-01-001–003 use it. Platform-owned filenames include Task and case names. Formal service and six matching Plan copies updated with prior evidence preserved. See [Log interface, verification and deployment](2026-10-19-structured-case-logs.md), including the independently reproduced existing ordering-test failure.

Log filenames (2026-10-19): per-execution timestamp/Task/Case ID/type plus UUID; exclusive creation retains all prior disk logs. Supersedes fixed overwrite naming. See [delivery and validation](2026-10-19-log-naming.md).

2026-10-19: Task Log viewing and new-name PDF attachments verified with nine passing isolated tests; see `2026-10-19-task-log-attachments.md`.

2026-10-19: Single Test log deployed; supersedes split API/Execution logs. 54 tests (53 passed, one historical skip); see `2026-10-19-unified-test-log.md`.

2026-10-19: Platform-owned Test log / PDF messages now English; user, test source and device text retained. See `2026-10-19-english-test-log.md`.
2026-10-19: Test log checks now render inside their section, with explicit no-check notices and clear HTTP/final-result boundaries. See `2026-10-19-grouped-test-log.md`.
