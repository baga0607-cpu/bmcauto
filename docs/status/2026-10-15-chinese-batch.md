# Chinese Repository and batch operations

2026-10-15 Chinese/batch update supersedes prior retained-case directory deletion: deleting a Repository directory deletes its subtree and standard cases, while independent Plan copies remain. Every UI deletion requires confirmation; confirm is left of cancel. Repository uses Chinese UI labels, no duplicate page heading, collapsible folders and mixed batch checkboxes (BMC root disabled). Selected items drag together to directories or delete as one atomic transaction. Overlapping selections are deduplicated; cycles and sibling collisions roll back.

Verification: isolated suite 102 tests, 101 passed and 1 skipped. New batch overlap, cyclic target and collision rollback coverage; prior deletion tests updated to the approved recursive deletion contract. Browser verified Chinese labels, collapsed descendants, mixed directory/case drag, recursive batch deletion, cancel preservation and confirmation button order. JavaScript syntax passed. Production DB backed up before deployment; no real DUT execution or commit/push.

Language toggle: top-bar English/Chinese switch restores original English text/attributes and remembers bmc-language in localStorage. Newly rendered UI follows the selected language. Browser verified round trips, dynamic redraw, placeholder restoration and reload persistence; syntax compilation passed.

Compact layout: one toolbar ordered Search, Add Test Case, Batch operations; total count removed. Repository folder rows measure 25px and column headings 23px, approximately half the former spacing. Case list owns viewport-bounded scroll area; table headings stick within it. Detail panel scrolls independently. Browser verified toolbar order, no count, measured density, stable header position during internal scrolling, no page scroll and right detail bounds at 1440/1920.

Borderless list: remove outer/row/header borders while retaining drop-position feedback. Folder names show recursive Test Case counts in parentheses. Browser checked computed border widths, root count against Repository API and fixed header/desktop bounds.

Typography update: header text 0.8rem to 1rem, folder name 0.86rem to 1.075rem and folder glyph 14px to 17.5px. Preserve 28px header/30px directory rows. Rename requires the selected directory name strong element; repeated icon clicks select only. Browser verified icon exclusion, name-triggered save/cancel and unchanged row heights.
