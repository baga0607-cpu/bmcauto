# Task Info drawer and English interface — 2026-11-10

Task names open an independently managed right-side drawer over the existing list. Opening and closing retains list filters and scroll position. Legacy Task Info URLs resolve to Task List and open the corresponding drawer. The My Task page is removed and its legacy URL redirects to Task List. Schedule and My Schedule retain their existing navigation.

Test Tasks have Overview, Scope, Connection, DUT Config and Note. Plan Tasks have Overview and Note only. Fields are immediately editable, with per-page Save changes and Discard changes. Switching pages, selecting another Task, closing or navigating away prompts to save, discard or keep editing. A browser unload warning protects unsaved edits. Server errors retain drafts. Task/Plan execution locks continue to apply through the existing APIs.

Overview reuses existing date, Assignee, status, iDesign and firmware editors and optimistic expected values. Date/status changes require a Note. Assignee-only changes retain automatic records. Note exposes editable Task notes and read-only Note records. History wording inside Task Info is replaced with Note, while existing stored history and API field names remain compatible. DUT Config contains an explicit pending-definition message and no invented fields.

Connection presents seven fields. Console Server IP, user and password map to cs_host, cs_username and cs_password. Console Port maps to dut_connect_cmd as `telnet localhost <port>`. BMC IP/user/password map to host/username/password; a bare BMC address receives an HTTPS scheme. Existing SSH port, protocol, TLS preference, DUT OS settings and other connection values are retained. A legacy custom console command remains intact when Console Port is empty; the UI explains replacement when a port is supplied. Existing case_client and ConsoleClient continue consuming the same normalized context and command. No test-case Python rewrite or new transport implementation is needed for this form mapping. Physical DUT connectivity was not tested.

Task List now has independent Assignee and Status columns immediately after Task. Their double-click and keyboard editors are retained. The language toggle and translation script are no longer loaded; the document language is English even when the old language preference is Chinese. Application-owned Chinese labels and obsolete language-dependent styling were removed. User-entered content and browser-native locale controls are not translated.

## Verification

- JavaScript syntax checks and the updated Task List rendering/calendar regression test passed.
- 36 existing environment, actual-date, owner-history, status and reference/package Python tests passed in isolated workspace/main/temp directories.
- Isolated Chrome exercised five/two tabs, direct date and Assignee saves, required change Note, seven-field connection roundtrip, retained environment settings, Note save, scope removal/addition, discard, save-and-continue, keep-editing, hash navigation cancellation, old Task Info/My Task links, independent list-column editing and English despite a legacy Chinese preference.
- Simulated execution locks verified disabled controls and rejected saves retaining drafts. Light desktop 1440×1000 and dark 1280×720 captures were inspected. No page errors were observed.
- Formal port 5000 returned the updated static files. A separate read-only browser verified Task List and available Test/Plan drawers while blocking non-GET browser API requests. No formal Task data was edited by verification, no DUT was contacted and no GitHub publication was performed.

Runtime verification scripts and screenshots are under `bmca-runtime/verification/task-drawer-*`; the disposable preview used port 5017 and was stopped after verification. The change uses static files, so the running formal service did not require a restart. Existing browser tabs require a reload.
