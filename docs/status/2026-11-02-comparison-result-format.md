# Expected / Received result messages — 2026-11-02

Changed RF-01-001 through RF-01-013 comparison messages to `Expected A = X; Received A = Y`. Both sides name the same HTTP status, v1, @odata.type, @odata.id or XML field. No acceptance conditions, Note policy, request settings or report layout changed.

Updated 13 working sources and 6 mirrored test assets (32 occurrences). Python AST parsing and exact reverse-substitution verification passed; 20 working-source formatted messages were evaluated with synthetic values and matching field labels checked. No new tests were added for this wording-only change.

Backed up the formal database and source edits under bmca-runtime/verification/comparison-format-20261102. With no active Task, updated 19 live Plan copies through revision-checked definition APIs and added 13 Repository versions, preserving older versions. Historical status, result JSON, Note, log contents, execution dates and manual overrides matched the backup exactly; SQLite integrity and foreign-key checks passed. Prior results are marked for rerun by the normal Plan update flow. No DUT execution, service restart or report format change.
