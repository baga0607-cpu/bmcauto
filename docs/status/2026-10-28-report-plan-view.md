# Report uses the Plan page — 2026-10-28

User requested replacing the former Report page with the current Plan page presentation. The Project reports route now invokes the same planList(project) renderer as Plan, including summary counts, expandable Task/Case matrix, current Plan/Task links and existing Create control. The separate Plan navigation entry remains.

The former Report heading and per-Plan Task/Scope/Current results/Generate report tables are removed from the Report route. Stored metadata/results and report-generation APIs are unchanged; existing Task execution pages retain Generate report.

Verification: workbench.js syntax passed. Formal read-only browser compared the Plan and Report overview HTML (identical), confirmed Report sidebar selection, removed old Report content, expanded/collapsed the Task matrix, and inspected desktop light and short dark screenshots. No page errors, data edits, backend restart or BMC execution. Evidence: bmca-runtime/verification/report-plan-view-20261028. Applied locally, not published to GitHub.

Follow-up user decision: Report overview is read-only, omitting the Create footer. Shared planList readOnly option suppresses it only on Report; Plan retains Create. JS syntax and formal read-only checks passed for absence of Create/footer on Report, matrix expand/collapse and retained Plan Create. Evidence: bmca-runtime/verification/report-readonly-20261028. No data changes.
