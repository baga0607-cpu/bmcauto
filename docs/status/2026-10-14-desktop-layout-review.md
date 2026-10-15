# Desktop layout review, 2026-10-14

User scope: desktop browser only. Mobile support is deferred until requested; no mobile layout work or acceptance checks in this review. Existing responsive CSS was not removed.

Reviewed Plan editing, Task execution/results, Task Connection settings and Repository at 1440x900 and 1920x900. Independent QA server/database; two synthetic Test Cases, two Tasks, no DUT execution and no production-data mutation. Captures and measured dimensions are under bmca-runtime/verification/desktop-layout-20261014.

## Findings

1. Connection settings action is too far below the first viewport. Form height creates a 1612px document at both desktop widths; Save starts at y=1525 in a 900px viewport. Optional Console and DUT groups all expand by default. Recommend a visible fixed/sticky save bar and collapsible optional groups or section navigation, keeping required BMC fields immediately available.
2. The split case list grows unnecessarily on wide desktops. It occupies 401px at 1440 and 574px at 1920 due to a 36% track, while the sample names and statuses need considerably less width. Recommend a roughly 300-360px list or adjustable divider and give remaining width to Python editing and evidence.
3. Task scope and run selection are separate but insufficiently differentiated. The scope count is visible, while the current checked run count is absent. Recommend explicit Run selection / selected-count wording so engineers can distinguish membership from this execution selection without changing ownership or settings rules.

## Keep

Project -> Plan -> Task tree and breadcrumb ownership; Plan parameters separate from Task environment; matched selected row and pane; restrained visual hierarchy; current desktop tabs and English labels. No horizontal page overflow was measured in the eight reviewed captures.

## Scope and limits

This is a review and documentation update, not an implementation of the recommendations. No CSS/JS/backend changes, no service restart needed. Large real-world data sets and long source/log content were not covered by the two-case fixture. Historical mobile support claims are superseded by the new desktop-only scope.
