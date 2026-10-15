# Isolated verification evidence

See ../docs/status/2026-09-17-plan-folder-current-state-verification.md for verified outcomes and limits. Tests target copied databases and an offline browser fixture, never the active main workspace.

The recorded run used worktree D:/Pytest/_redfish/plan-folder-current-state and localhost:5127. Local baseline/browser/final/migration workspaces, copied script directories, generated fixture IDs, screenshots and PDF are retained but ignored to prevent checking production-format data or copied configuration into Git. Browser fixture IDs are intentionally generated; scripts are ordered scenario probes for this fixture, not a standalone test suite.

Run prepare_browser_workspace.py only on a fresh verification directory; it reads the source database without writing it. browser_server.py explicitly binds copied database and main-program paths. seed_browser_fixture.py requires that server and its documented offline Redfish/step fixture. Browser scripts use installed Chrome through Playwright and must never be pointed at a production server.

Repeat full automated tests with explicit BMC_WEB_UI_WORKSPACE_DIR, BMC_MAIN_PROGRAM_DIR and BMC_LIFECYCLE_SOURCE_DB overrides as shown in the report. verify_migration.py refuses an existing database destination. verify_main_preservation.py compares the local before-run evidence, which is not a generic repository fixture.
