# Report hierarchy — 2026-11-12

The user's latest report structure supersedes nested disclosures and the Result Summary field.

- Case Name is the only disclosure control. Opening it shows all Test Data and Test Information; closing it hides both. Keyboard activation uses native details/summary behavior.
- Test Data contains Description, declared Spec Ref., Log, and Test Steps & Results.
- Test Information contains Task Name, Tester, Execution Time, FW Package, Configuration (renamed from DUT Configuration).
- Result Summary and the separate Note field are omitted from HTML, preview and PDF. CP and historical notes remain in method Result cells; full logs and original persisted results remain unchanged. Manual overrides and rerun notices remain visible.
- Preview starts with the sole Case disclosure open. Formal HTML starts collapsed. Print expands all Cases and restores prior open/closed state afterward.
- PDF uses the same field order and omission; it is static rather than interactive.

Verification: local and publication Python suites each passed 37 tests (report_case, report_html, report_preview, report_method_table, conditional_pass). Chromium verified keyboard/mouse Case disclosure, visible Information without a second click, method table under Test Data, no overflow, attachments, print/restore, and CP preview in light/dark themes. PDF page 4 rendered and inspected.
Artifacts: bmca-runtime/verification/report-hierarchy-20261112.

Formal service restarted via the desktop restart workflow at 16:17 (UTC+08). Backup: bmca-runtime/backups/restart-20261112-161732-635/testcase_meta-before.db. All 21 table fingerprints unchanged; integrity ok, FK errors 0, CP schema retained. Live RF-01-008 report-preview GET returned 200 and confirmed one disclosure, requested hierarchy and removal of both standalone fields. No DUT tests or result rewrites.

Publication: baga0607-cpu/bmcauto main through the independent publication checkout; shared renderer/template changes are identical in local and publication copies.
