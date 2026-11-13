# Spec Ref. compact spacing — 2026-11-13

Changed the shared specification_reference presentation adapter to separate citations with one newline instead of two. Report preview, HTML export and PDF export now omit the extra blank line between citations. Citation text, captured report definitions, Checkpoints, Results and execution evidence remain unchanged. No Repository or Plan source synchronization is needed.

Validation: isolated local unittest run (test_report_presentation.DeclarationTest, test_report_html, test_report_preview): 7 passed. Formal service restarted with launch.ps1; no active tasks, all 21 database table fingerprints unchanged, integrity ok and no foreign-key errors. Backup: bmca-runtime/backups/restart-20261113-093047-831. Previously downloaded reports require regeneration to use the new spacing.
