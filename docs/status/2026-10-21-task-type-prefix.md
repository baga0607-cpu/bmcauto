# Task Type name prefix — 2026-10-21

- New Task codes are TaskType-ExistingNamePrefix-NNN, e.g. Plan-FWA6084BMC-001 and Test-FWA6084BMC-001 for fresh independent series.
- Only the naming prefix changes. Per-source counters continue without resetting; full-code global uniqueness, case-normalized reservations, immutability, deletion non-reuse and transactional allocation remain.
- Existing issued codes are preserved because the user identified them as unique codes. Existing IDs/relationships/settings/results are unchanged.
- Prefix length validation includes Task Type so the complete generated code stays within 255 characters.
- Backend resolve_choice supplies the prefix to both name-preview and create, so UI needs no separate naming logic.
- 48 Task tests passed, including prefix formatting, global collision/concurrency coverage, prior series continuation and preservation of an existing unprefixed unique code. Full repository suite was not rerun.
- Consistent backup: bmca-runtime/backups/task-type-prefix-20261021. No active Tasks before restart. Copied startup and formal post-restart checks confirmed all existing database rows/names unchanged, integrity_check ok and no foreign key violations.
- Formal port 5000 updated. Browser preview showed Plan-FWA6084BMC-002 and Test-FWA6084BMC-003 continuing the existing counters; canceled without creating a formal Task.
- Screenshot: bmca-runtime/verification/2026-10-21-task-type-prefix.png; test evidence: verification/task-types-tests/type-prefix-tests.log. Private runtime data remains local.
