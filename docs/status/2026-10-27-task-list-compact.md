# Task List compact layout — 2026-10-27

Task List and My Task now follow Schedule's compact controls and viewport layout. This is a narrow refinement of the existing workbench; ten fixed column ratios, status filters, CRUD and navigation remain.

- Compact 28px tab strip matches Schedule; remove the repeated visible Task List heading. Its accessible heading remains.
- Move the visible/total Task count beside search, preserving live updates after search/filter changes.
- Reduce cell padding to 6px vertically / 12px horizontally, tighten Project/SKU/Plan supporting text, and vertically center cell contents. Rows can expand for long names.
- Table fills remaining viewport with 24px below, updates on resize, and scrolls under sticky 40px headings. Keep 1100px minimum table width and horizontal scrolling for narrower desktop windows.
- Status menu remains scrollable and fits short viewports/empty results. Preserve stable column widths and keyboard focusable table region.
- Correct a remaining workbench date-input handler that still marked the opposite Task date required; both dates remain optional under the approved Not Scheduled rule.

Verification: two JS syntax checks and existing Status filter assertions passed. Isolated desktop checks covered 1440x900, 1920x900, 1440x600 dark, and 1100x700; sticky header, horizontal overflow, empty-menu containment and resize passed. A representative three-line Project/SKU/Plan row reduced from about 101px to 66px.

Formal loopback page was inspected read-only using real nine Tasks. At viewport heights 900/600, table bottoms were 876/576. Populated, empty search, restored data: all ten column widths unchanged. My Task and dark theme passed, no JavaScript page errors. No backend change/restart, formal data mutation, or BMC execution. Existing Python test results are historical, not rerun for this layout change.

Evidence: bmca-runtime/verification/task-list-compact-20261027 (outside published source). Source updates remain local, not published to GitHub.
