# Task List stable column widths — 2026-10-27

Fixed layout with explicit ten-column proportions prevents content-driven reallocation when Status filters yield no Tasks. Stable page scrollbar gutter prevents the available width changing when the page becomes short. Table min-width1100px keeps narrow desktop windows horizontally scrollable; empty-state filter remains accessible.

Formal read-only browser reproduced Task column205.17→72.47px before fix; after fix all ten widths match exactly (maximum difference0px) between populated, empty-filter and restored nine-row states. Sixteen existing search/status JS assertions and syntax passed. Screenshot: bmca-runtime/verification/task-list-stable-empty-widths.png. Frontend only, no database changes/restart, local uncommitted change.
