# Task metadata interaction refinement — 2026-10-27

User decision supersedes pencil metadata editors: remove pencil buttons from Task Info and Task List/My Task. Task Info metadata is read-only until entering the existing Edit Task mode. Table iDesign ID and Test-only FW Package use double-click editing like other editable cells, with keyboard access retained.

Request ID remains a link. Table single-click opens its URL; a brief delayed mouse-click dispatch lets double-click open the editor without also opening the link. Task Info links retain ordinary navigation. Modifier/key navigation remains available.

Firmware editors include default BL, 1BMC and BMConf rows, plus existing custom components. Default rows without versions are optional placeholders and are omitted on save; custom rows still require Component/Version. Existing stored data is not renamed or backfilled. Task List/My Task show only 1BMC and BMConf versions (— when unknown); the native hover title and accessible label contain the complete package including BL and custom components. Task Info shows the full package. Plan Tasks remain firmware read-only in UI and backend.

Validation: JS syntax and existing Status-filter assertions passed. Isolated browser verified both types double-clicking iDesign without pencils, link double-click without popup and single-click navigation, three defaults, two-row summary/full tooltip, Task Info read-only and full edit, clearing optional default versions, removing custom rows, My Task behavior, Plan restriction and creating a Test Task with unknown BL version. Short dark and desktop screenshots inspected, no page errors. Existing backend tests are historical, not rerun for this frontend-only refinement.

Formal browser only opened/cancelled metadata editors and checked both list pages, default rows, summary/full tooltip and Task Info read-only. All formal rows unchanged; integrity/FKs passed. No backend restart, formal edits or BMC execution. Preview stopped. Evidence: bmca-runtime/verification/task-meta-interaction-20261027. Local updates not yet published.
