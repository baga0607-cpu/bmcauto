# Days (Actual/Plan) values — 2026-10-27

Task List/My Task display actual_working_days / working_days in Days (Actual/Plan). Each side is independently calculated from its complete Actual or Plan date pair, inclusive of both endpoints, using the same Taiwan official calendar and persisted day overrides. Incomplete pairs return null and display — on that side. Preserve genuine zero: 0 / 0. Examples: 3 / 5, — / 5, 3 / —, — / —.

Existing working_days remains the Plan count for Schedule and existing consumers. Add read-only derived actual_working_days and actual_calendar_complete to Task overview. No metadata write or migration. Outside covered years retain weekday/weekend fallback and a calendar coverage tooltip on the table cell.

33 related Python tests passed in 3.430s, including independent counts, official holidays, manual overrides, incomplete pairs, zero days and separate calendar coverage. JS syntax and existing Status filter assertions passed. Formal read-only browser checked all nine Task values on Task List and My Task, plus five isolated renderer combinations. Formal DB backed up, copy startup passed, zero active Tasks confirmed before loopback service restart; all formal table rows unchanged and integrity/FKs passed. No BMC execution. Runtime evidence: bmca-runtime/verification/task-day-counts-20261027. Applied locally, not published.

Follow-up: both Task types now use the same Days (Actual/Plan) label and actual/plan value format in Task Info as well. Formal read-only and five renderer combinations verified; no data change.
