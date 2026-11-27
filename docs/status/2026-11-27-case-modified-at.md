# Test Case revision checks

Plan → Manage → Check Version compares each independent Plan source with its linked Repository ID. The authored modification time is normalized to UTC for comparisons at microsecond precision. Both columns display Taipei time to seconds. A missing source date produces Unavailable. Removing a Repository entry leaves the Plan copy intact.

The startup migration reads modification times from each original Python source and uses NULL for unknown dates. Repository IDs, Plan case IDs and saved execution evidence are preserved. New execution records and exports include modified_at.

Verification on an isolated workspace database copy retained 13 Repository cases, 39 Plan cases and 26 Task memberships across two startups. SQLite integrity and foreign-key checks passed. The ten related unittest modules passed all 60 tests, including matching by ID, parameter-only changes, subsecond replacements, stale writes and copying between Plans. The workbench JavaScript passed syntax validation.
