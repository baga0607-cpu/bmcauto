# Multi-keyword search — 2026-10-22

Task List/My Task/Schedule, Plan Test Case trees, Import source, Repository and retained case-search handlers share KeywordSearch.matches. Comma-separated nonempty trimmed keywords must ALL occur, case-insensitive; spaces within a keyword remain literal. Empty query/comma-only query matches all. Sidebar Project picker retains its original single-query behavior.

Repository search now searches rendered descendant cases instead of incorrectly excluding them through the selected-folder ID comparison (rows never had that folder dataset). Existing folder tree remains visible. Schedule search remounts sizing/Today initialization after replacing its table.

Validation: keyword_search.test.cjs runs nine assertions on semantics and actual Task List rendering. Both changed JavaScript files passed syntax checks. Formal browser read-only searches: FWA6084, Plan → two Planning Tasks; RF,001 → one Repository case and one Import source case. No imports, Task edits or DB changes submitted. Screenshot: bmca-runtime/verification/multi-keyword-task-search.png.

This is a local update after commit8389a95; it has not been committed/pushed by this request.
