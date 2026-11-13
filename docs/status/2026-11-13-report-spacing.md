# Report spacing refinement — 2026-11-13

Approved scope: Checkpoint Description, table column widths, cell vertical padding, and Test Data/Test Information spacing.

Shared report adapter collapses blank lines only in typed Checkpoint descriptions; saved definitions and observation/Result text remain intact. HTML/preview/PDF columns are 6/13/39/30/12 percent (Step/Type/Description/Result/Judgement). HTML cell vertical padding is 3px (was 4px); print/PDF remains 2pt. HTML section heading padding is 4px, field bottom padding 6px, table bottom margin 8px; PDF subsection spacing is 4pt before/2pt after. No checkpoint aggregation, source synchronization or database changes.

Validation: 17 isolated Python report tests passed; existing Playwright report_methods checks passed (compact spacing, no overflow, disclosure, attachments and print state restoration). Direct adapter check verified blank lines removed from Checkpoint description while Result and input remain unchanged. Formal service restarted; all 21 table fingerprints unchanged, integrity ok, zero foreign-key errors. Backup: bmca-runtime/backups/restart-20261113-135659-288. Generated QA files: bmca-runtime/verification/report-spacing-20261113.
