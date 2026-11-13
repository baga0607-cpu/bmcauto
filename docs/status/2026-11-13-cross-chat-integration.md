# Cross-chat integration — 2026-11-13

Integrated the completed changes from the test-error investigation chat with the already-published report spacing work (d26c30d).

- Reports omit Case-level note fallback rows entirely. Step/Checkpoint notes and original saved case notes/logs/attachments remain unchanged. The earlier aggregate-note deduplication proposal is superseded and must not be restored.
- RF-01-011: same-origin resource traversal; allowlisted DMTF schema retrieval over HTTPS with separate credential-free session and TLS verification; redirect validation; exact advertised schema version selection; per-run memory caching only; unversioned schema revalidation request; richer schema failure evidence. External source and tracked test_assets mirrors are synchronized.
- Preserved the RF-01-011 implementation notes and converted its 20 offline checks into portable repository tests. Filesystem birth-time comparison now checks the preserved original creation timestamp because Git copies do not retain filesystem birth times.

Validation on publication checkout: 19 report tests passed (note association, report_case, method_table, legacy conditional-pass policy), including isolated HTML/PDF export checks. RF-01-011: 20 offline tests passed after the portability adjustment. No live DUT testing or browser verification in this integration.

Deployment: no service restart or formal database mutation performed by this integration. Report Note change deployment remains pending. Existing Repository and independent Plan RF-01-011 sources remain unsynchronized; saved settings/results/history unchanged. Previously exported reports are not rewritten.

Pending design: RF-01-012 one-row Checkpoint summary with visible exceptions and expandable full details remains a proposal awaiting user confirmation; no implementation included.
