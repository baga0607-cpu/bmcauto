# Windows desktop launcher

These are the tracked sources for the desktop shortcut's runtime scripts.
Deploy the files together into the existing sibling `bmca-runtime` directory;
do not run them in this source folder. The layout is:

- `<workspace>/BMCAgent/.venv/Scripts/python.exe`
- `<workspace>/BMCAgent/web_ui/workspace/testcase_meta.db`
- `<workspace>/bmca-runtime/launch.ps1`
- `<workspace>/bmca-runtime/python/python.exe` (Windows venv child interpreter)

The existing desktop shortcut invokes `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "<workspace>/bmca-runtime/launch.ps1"`.
It now offers **Open BMCAgent**, **Restart service**, and **Cancel**, with Local / LAN selection defaulting to the current listener mode.

- Open reuses an existing healthy service in the same mode.
- Restart reloads the service even when its mode is unchanged.
- Changing mode through Open still requires confirmation.
- Active or unverifiable execution blocks restart.
- Owned listener and its verified Python launcher ancestors are identified by exact executable and server script paths, with process creation identity rechecked before stopping. PID-file equality is not required; unrelated/reused PIDs are never stop targets.
- Before restart, the SQLite backup API creates a consistent backup under `backups/restart-<timestamp>`. Post-start verification checks all table fingerprints, integrity and foreign keys; it records CP schema availability. A failure is reported, not silently restored over current data.
- Existing saved test judgements are not rewritten. LAN firewall behavior is retained and requires Windows elevation.
- The tool serially checks active runs before backup and immediately before stopping; it does not implement a global maintenance lock. Do not start a new test concurrently with a restart.

Unattended restart (uses the same service workflow):

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<workspace>/bmca-runtime/launch.ps1" -Action Restart -NoBrowser`

Omitting Mode preserves Local / LAN mode. `-Action Open -NoBrowser` opens/starts without a dialog; a mode change requires explicit Restart.

Verification (no DUT requests):
- `powershell.exe -NoProfile -File test-service-control.ps1`: mocked ownership and active-run guards; no live termination.
- `powershell.exe -NoProfile -STA -File test-launcher-dialog.ps1 -OutputPath <png>`: off-screen native button rendering/clicks; no service action.
- `python test-restart-backup.py`: temporary SQLite backup/verification tests. Set TEMP/TMP to a writable directory.

Production deployment details: [2026-11-12 restart handoff](../../docs/status/2026-11-12-desktop-restart-cp.md).
