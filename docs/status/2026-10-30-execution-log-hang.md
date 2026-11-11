# Execution Log renderer hang — 2026-10-30

## Incident and diagnosis
User reported RESULT_CODE_HUNG while executing, and confirmed the Log dialog was open. Read-only checks found HTTP 200, SQLite integrity_check ok, no foreign-key violations. Test-FWA3051-001 remained active with no worker, nine completed cases and RF-01-010/011 pending. RF-01-009 retained 4,598,816 characters / 75,483 lines. Browser-driven queue scheduling explains why no next worker starts when the renderer hangs.

An isolated Playwright replay through the real stream handler and Log dialog exceeded a 15-second watchdog before the fix. Same payload with dialog closed: 3.69 seconds. Disabling translation or synchronous scroll layout individually still exceeded 15 seconds. Batching alone: 9.53 seconds. Batching plus bounded preview: 3.87 seconds. This reproduces the renderer workload consistent with the incident; no original browser crash trace was available.

## Fix
workbench.js coalesces streaming log renders at 100 ms; prompt events and stream completion flush immediately. Preview DOM is limited to the last 65,536 characters, including initially opening a saved log. A notice explains the limit. Full evidence remains in memory/server storage and Export downloads the full current snapshot. Empty input slots no longer emit needless DOM mutations. No service restart or Task mutation was performed.

## Verification
- Before fix: node web_ui/tests/execution_log_performance.test.cjs -> Renderer unresponsive: log replay exceeded 15 seconds.
- After fix: same synthetic 75,483-line regression -> PASS, 4.01 seconds, maximum heartbeat gap 65.6 ms. Checks live/saved preview, complete export, execution completion, switching to another case and no page errors. All APIs simulated; no DUT.
- Original captured payload replay after fix -> 3.86 seconds, 77 heartbeat ticks.
- node web_ui/tests/execution_controls.test.cjs -> PASS (selection, locks, stop scopes, dialogs, export, reconnect, themes).
- node --check web_ui/static/workbench.js -> PASS.
- Formal read-only verification after fix: HTTP 200, active Tasks 1, SQLite integrity ok, foreign-key violations 0.

Captured payload and diagnostic probes are kept only under bmca-runtime/verification/execution-20261030, outside the repository. Regression uses synthetic text, not DUT data. Refresh the browser to load the fix; the interrupted Task has not been resumed or rerun. Long-term resilience would require server-owned queue scheduling; it is outside this frontend performance fix.
