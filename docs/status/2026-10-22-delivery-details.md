# BMCAgent handoff — 2026-10-22

Read [2026-10-21 base handoff](2026-10-21-handoff.md) for environment, architecture and earlier decisions, then this file. Later user instructions take precedence.

## Latest Project spec viewport fit
Project Spec now fills remaining viewport to24px above bottom and recalculates on resize, including edit layout. Old calc(100vh -210px) cap removed. Table scrolls internally beneath sticky column headers. Formal read-only browser measured900→876px and600→576px table bottom; sticky heading retained during600px internal scroll. JS syntax passed; screenshot project-spec-viewport-fit.png. No data edits.

## Latest Schedule viewport fit
Schedule height now fills the available browser viewport below its toolbar, leaving24px below, and recalculates on window resize. Supersedes fixed eight-row limit; internal vertical scroll/native sticky dates retained. Desktop browser measurements:900px viewport → table bottom876px;600px →576px; scroll103.33px retained header offset0.67px. Syntax passed; screenshot schedule-viewport-fit.png. Frontend only.

## Current service and launch authorization
Read [Local/LAN service](2026-10-22-lan-service.md). Current explicitly approved LAN service: http://<LAN_ADDRESS>:5000, same-subnet firewall172.17.16.0/23. IMPORTANT: 啟動BMCAgent always starts local127.0.0.1 using server.py; only explicit 啟動內網服務 starts server-lan.py. Ordinary starts must not reuse the LAN mode. Backup/row/integrity checks passed. Peer connectivity still requires testing from another computer.

## Latest Schedule eight-row viewport
Supersedes content-height/page-pinned header: Schedule max height measures its heading plus first eight Task row heights; extra Tasks scroll internally, native sticky dates top=0. Formal browser confirmed height506px with eighth Task Test-FWAAHP3051-001 aligned to lower edge within1px; internal scroll58.67px retains header offset0.67px. Syntax passed; screenshot schedule-eight-rows.png. Frontend only.

## Earlier date-header verification
Schedule captures document scroll events (including ancestor scrollers) when pinning the date row. At 1280x500 desktop viewport with 9 Tasks and scrollY=229.33px, table top=-116px and header top=0.67px, confirming the dates stay at viewport top while rows move below. Temporary viewport reset afterward. Syntax passed; screenshot schedule-pinned-date-header.png.

## Latest Schedule height
Schedule removes the 62vh cap and grows with Task rows; vertical scrolling belongs to the page, horizontal drag remains. The date header sticky offset follows page scrolling within the table bounds. Formal browser: 9 rows, clientHeight=scrollHeight=565px, max-height none; screenshot schedule-content-height.png. Syntax passed, no formal data mutation.

## Latest navigation icon refinement
Navigation icons now have transparent backgrounds and no border/radius; retain existing 28px alignment boxes, SVG sizes, positions and expand/collapse labels. BMCAgent brand mark retained. Formal browser verified transparent background and dimensions; screenshot navigation-icons-no-background.png.

## Latest Project selector font
Project picker input/options font reduced by 15%: 1.1rem → .935rem (15.4px → 13.09px). Other navigation text remains 15.4px. Formal browser computed styles verified; screenshot project-picker-font-15.png.

## Latest Project picker spacing
Expanded Project link now uses intrinsic width with 4px right padding; picker follows 7px after label (including row gap). Peer entry positions, badge/text sizes and 40px heights remain unchanged. Formal read-only browser and screenshot project-picker-close.png verified. CSS only.

## Latest navigation badges
Nine authored SVG navigation icons use brand-matched 28px square backgrounds with 4px corners. Expanded rail shows icon + label; collapsed rail shows icon only. Text matches BMCAgent 15.4px/700 (supersedes prior 17.5px request), rows remain 40px and single-level. Both states visually checked; browser computed font/badge dimensions match brand, syntax passed. Screenshots: nav-badges-expanded.png and nav-badges-collapsed.png in bmca-runtime/verification. Frontend only; no data changes.

## Latest Schedule default
Schedule initializes at Today, centered in the visible date area using the same helper as the Today button. Initialization runs on each mounted Schedule before the one-time event-binding guard; explicit reschedule/calendar redraw restoration still retains its saved scroll position. JavaScript syntax and formal read-only browser geometry passed (2026-10-22 centered). Screenshot: bmca-runtime/verification/schedule-default-today.png. Frontend only; no formal data mutations.

## Latest Plan import fix
[Plan import drag layout](2026-10-22-plan-import-drag-layout.md): drop indicator pseudo-element moved from tr to td to prevent an anonymous column shrinking names. Browser reproduced 462→231px before fix; nine fixed drag samples retain 462px, import order and source rows verified. CSS only; formal data untouched.

## Latest flat navigation refinement
Sidebar items now share one flat level, no leading icons, and 17.5px text (previously 14px, +25%). Fixed 40px rows retain the existing full rail width; Project picker remains beside its label. Formal browser verified aligned items, no SVG icons, computed font/height/width, and screenshot flat-text-navigation.png. Frontend only, syntax passed, no formal data mutation.

## Earlier navigation refinement
Project List duplicate sidebar entry removed; Dashboard remains and owns the current-page highlight. Existing Dashboard Project table and operations retained. JavaScript syntax and formal read-only browser checks passed; frontend only, no database changes or restart. Screenshot: bmca-runtime/verification/dashboard-only-navigation.png.

## Latest delivery
[Owner History and hover navigation](2026-10-22-owner-history.md) is deployed. Owner changes generate immutable old/new History; date reasons remain required and appear between dates and Owner. Navigation opens on pointer entry, closes on exit, and clicks retain state. 86 tests, isolated/formal browser checks and backup/copy/restart/exact-row verification passed.

## Earlier Edit Task delivery
[Edit Task mandatory History](2026-10-22-edit-task-history.md) is deployed. Any Edit Task date change (including assignment/clearing) requires History and expected old dates, using the same immutable append transaction as Schedule. No date change means no History required/created. Both types and rollback/immutability verified; 79 tests passed, formal backup/restart/exact-row checks passed.

## Earlier immutable History delivery
[Immutable Task History](2026-10-22-task-history.md) is deployed: Schedule rescheduling requires History instead of Note; independent append-only rows and read-only History List in both Task Info types. DB triggers reject UPDATE/DELETE, transactions roll back date changes if History insert fails, and records survive Task deletion. Existing Notes remain unchanged; no fabricated backfill. 73 tests passed; formal backup/copy/restart/row+trigger verification passed.

## Earlier Info/dialog delivery
[Schedule Task Info / reschedule dialog](2026-10-22-schedule-info-dialog.md) is deployed: name opens the correct Task Info for both types, bar opens a modal date editor with mandatory Note. Planning Task gets a stable-ID info view; Test Task selects existing information subtab. JS and isolated/readonly-formal browser checks passed; frontend only, no backend restart or formal data mutation.

## Earlier Owner delivery
[Task Owner](2026-10-22-task-owner.md) is deployed: New/Edit Task dropdown defaults TBD; initial roster TBD/David based on user example (full list still pending). Both Task types store owner in metadata, Schedule shows Owner under name, legacy rows display TBD without migration. 67 tests passed; formal data backup/restart/exact-row verification passed.

## Earlier Schedule editing delivery
[Schedule 改期與日期對話框](2026-10-22-schedule-editing.md) is deployed: persistent date-header bottom border, hidden horizontal scrollbar with drag panning, task-bar schedule edits require a fresh Note and append old/new dates plus reason to existing Notes. Planning/Test both supported with locks and stale-date conflict protection. Date click opens a compact modal with mutually exclusive working/non-working options and Cancel/Save. 62 tests passed; formal backup/restart/exact-row verification passed.

## Earlier compact Schedule delivery
[Schedule 精簡與拖曳](2026-10-22-schedule-compact.md): Today beside search centers the current day, blank-area left-button panning, gray name-only frozen Task column, compact tabs/rows, no date navigation or workday legend. Calendar range now includes all scheduled Tasks plus today; large ranges load in 366-day segments. Frontend only, no service restart or formal mutations. Browser interaction/position checks passed.

## Earlier Schedule delivery
[Schedule 工作日曆](2026-10-22-schedule-calendar.md) is deployed: daily horizontal grid, frozen Task/date axes, official Taiwan 2025–2027 calendar with persistent manual overrides, inclusive working-day counts for both Task types. Outside those years show an explicit coverage warning. 55 tests passed; formal backup/copy/restart verified. Existing records preserved with concurrent user-created Tasks and corresponding counters retained.

## Earlier 10/22 delivery
[Dashboard 與匯入 Skip](2026-10-22-dashboard-import-skip.md) supersedes the preview workflow below: parse → per-SKU Keep/Promote/Skip → confirmation. No spec-review step. Main Project is omitted when no SKU is retained; all Skip creates nothing. Existing records are preserved. 16 import tests passed; formal restarted with backup and exact-row/integrity verification.

## Previous delivery
[Parsed SKU promotion](2026-10-22-project-promotion.md) is deployed locally at http://127.0.0.1:5000 . Automatic Project creation now:
- Parses every SKU and its specifications first, with a per-SKU read-only preview.
- Asks which parsed SKUs should become independent Projects.
- Creates all resulting Projects together after confirmation; conflicts/failures write nothing.
- Displays imported no-SKU Project specs in a single Project column and supports editing them.

The FWA-5084 column in the user's FWA-6084 workbook is an independent Project; this is a human-confirmed promotion rule, not a hardcoded heuristic. New imports can produce multiple Projects. Existing formal records were not retroactively split or modified.

## Verification
13 Project tests + 48 Task tests passed. Real workbook comparison covered all 196 rows. Browser verified isolated two-Project creation and independent specification editing; formal browser only previewed/canceled. Formal existing database rows are exactly preserved, integrity/FKs passed.
Backup: <LOCAL_PATH> (private/local).
Formal launcher: <LOCAL_PATH> Python BMCAgent/.venv/Scripts/python.exe. No active Tasks before the update; re-query live state before future backend restarts. Temporary 5002 promotion preview is stopped.

## Other current invariants
Task codes are globally unique and permanent; newly issued codes start with Plan- or Test- while existing issued codes stay unchanged and source counters continue. All ownership/statistics use stable IDs. See the linked 10/21 Task Type, global-name and prefix status documents before changing this behavior.
