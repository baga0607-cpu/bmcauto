# Globally unique Task names — 2026-10-21

Supersedes the prior Task-Type/Project-scoped name collision rules. The user clarified that Task Name is used as a unique code. The name format remains unchanged; increment the numeric suffix whenever a candidate is already used.

## Cause and correction
The original next_name filtered issued names by Project and Task Type; its old composite uniqueness constraint also allowed Plan and Test to share a display name. Reproduced by creating matching-prefix Plan and Test Tasks and another Project with the same normalized prefix: all three incorrectly received Project-001. Two failing regression tests captured this before the fix.

GlobalTaskName now stores the NFKC/casefold name key as its database primary key. Every supported Task creation reserves this global claim inside the existing BEGIN IMMEDIATE transaction. Candidate selection checks all current Tasks of both types, all older issued reservations, and permanent global claims, regardless of Project. A collision advances the suffix; no type prefix is added. Global claims have no cascading foreign key and survive Task and Project deletion. Existing per-source counters continue monotonically; they do not guarantee an unused name without the global check.

Startup adopts historical names and repairs later duplicates in issued order. The earliest issued Task keeps its name. The later Task takes the next unclaimed suffix. IDs, scope, Plan/Project/SKU ownership, dates, settings, results and logs remain unchanged. This is a one-time conflict repair; user renaming remains disabled.

## Formal repair and verification
- Formal Plan Task 950830b0-f9bc-4a1f-9cec-b2ad0d2cc24d retained FWA6084BMC-001.
- Formal Test Task 877183cd-3fa6-4911-a0e0-8b2bd3a8530a changed from FWA6084BMC-001 to FWA6084BMC-002.
- Formal FWA6084GPU-001 remained unchanged.
- Consistent SQLite backup and row snapshots: bmca-runtime/backups/global-task-names-20261021 (local/private).
- Copied startup verified that only the duplicate Task name, its issued-name row and counter changed, plus the new global claim table. All other records and foreign keys were preserved.
- Formal port 5000 restarted after verifying no active Tasks. The resulting full database exactly matched the verified copy; integrity_check and foreign_key_check passed.
- Browser verified formal Task List shows Plan 001 and Test 002.
- 47 Task tests passed, including global collisions across types/Projects, concurrent Plan/Test creation, deletion without reuse across types and Projects, duplicate repair/idempotency, and previous ownership/rename tests.
- Evidence: bmca-runtime/verification/task-types-tests/global-name-tests.log and verify-global-task-names.py. Full repository suite was not rerun; no DUT was contacted.
