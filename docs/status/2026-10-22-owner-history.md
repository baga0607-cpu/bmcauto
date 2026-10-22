# Owner History and hover navigation — 2026-10-22

Deployed locally at http://127.0.0.1:5000.

## Behavior
- Edit Task Owner changes automatically show a read-only History containing old/new Owner, e.g. Owner: TBD → David. Server derives the actual values and appends an immutable History row for both Task types. Unchanged Owner produces no extra row.
- Date edits retain their required manual History reason. History now appears directly after End date and before Owner; Task Name and Notes follow. Combined date/Owner changes show the auto Owner preview and save separate manual/automatic entries in the same transaction.
- expected_owner detects stale forms; history insert failure rolls back metadata. Existing SQLite UPDATE/DELETE protections and survival after Task deletion apply. No schema migration or historical backfill.
- Same-timestamp History sorting uses SQLite insertion rowid as a deterministic secondary key.
- Left navigation expands on pointer entry and collapses on pointer exit. Link/project selection clicks no longer collapse it; focus changes while pointer remains inside do not collapse it. Keyboard Tab/Escape access is retained.

## Verification
86 related Python tests passed (owner-history-tests.log), including both types, unchanged/invalid/stale Owner, combined changes, rollback, immutability and retention after deletion. JavaScript syntax passed. Isolated port 5002 browser verified auto readonly text, required empty manual reason on switching to date changes, persisted separate entries, and form order. Sidebar browser checks confirmed entry/open, link navigation/still open, exit/closed. Formal read-only browser confirmed updated Edit Task and navigation; no formal Task edits were submitted.

Formal backup: <LOCAL_PATH> No active Tasks before restart. Copied startup and formal post-restart exact-row comparisons passed; integrity and foreign keys passed. Formal 5000 remains running. Preview service stopped after verification.

Screenshots: bmca-runtime/verification/owner-history-form-preview.png and sidebar-hover-formal.png (paths relative to workspace parent).
