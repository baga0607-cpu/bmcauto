# Compact report with test steps and results — 2026-11-12

## Delivered

The HTML ZIP, browser print and server-generated PDF now include a Test Steps & Results table inside Test Data: ID / Type / Description / Result. This supersedes the earlier decision to omit method tables from reports. Cases remain collapsed initially; opening a case opens Test Data, while Test Information stays closed. Printing expands all content and restores the previous disclosure state afterwards.

- Step, Checkpoint and Record use the existing S/C/R identities. Complete readable descriptions remain visible without duplicating the ID/type prefix. Checkpoints and Records show their source Step.
- Results use saved log_records, including status, Expected, Actual and Reason when recorded. Record displays RECORDED and its informational value, never an inferred Pass/Fail. Null, false, zero and absent-version text remain distinct.
- A captured report_definition is authoritative. Missing observed entries in that definition are appended with No recorded result; current source is not joined to historical observations. With no structured execution evidence, declared methods may be shown without a verdict. No test steps recorded is explicit when neither exists.
- Older step/criteria/result and section/check logs remain readable as Legacy rows. No new IDs or inferred alignment are assigned to those records.
- Result text longer than 1,200 characters is explicitly excerpted (1,100 characters plus a notice). Full saved execution evidence and existing full log attachments are unchanged. Descriptions are not abbreviated. Existing manual/retest notices, Note, Spec Ref., Final/Reference selection and winner context remain intact.

## Compact layout

HTML field row gaps: 16px → 6px; case vertical padding: 13px → 7px; section summary padding: 14px → 6px. Table cells have 4px vertical padding and readable 12px text. The existing 22px Bahnschrift case heading is retained.

PDF field padding: top/bottom 4pt/8pt → 2pt/3pt; table cells 2pt vertical padding. The complete case is no longer forced into a KeepTogether block. Tables repeat their header across pages and can split long rows. Browser print uses matching compact spacing. Full logs stay separate in the HTML package and embedded in server PDFs.

## Validation

- Local Python suite: 29 tests passed: test_report_method_table, test_report_case, test_report_html, test_report_exports, test_report_presentation.
- Independent publication checkout: 39 tests passed: test_report_method_table, test_report_case, test_report_html, test_report_exports, test_rf01_method_items.
- New tests cover typed results, associations, null/false/zero, missing results, captured definition precedence, old logger adapter, legacy records, HTML escaping, a 60-row multi-page table, final-report ownership, full log preservation and bounded large-result rendering.
- Offline Chrome passed keyboard disclosure, compact spacing, no horizontal overflow, attachment file/tab, print expansion/restoration and no external requests/script errors. PDF and browser-print table pages were rendered with Poppler and visually inspected for wrapping, repeated headers, Chinese text and clipping.
- Fixtures and screenshots are under bmca-runtime/verification/report-methods-20261112 (not committed). BMC_REPORT_QA_DIR writes export fixtures; BMC_HTML_REPORT_QA selects methods-fixture for web_ui/tests/report_methods.test.cjs. BMC_PLAYWRIGHT_MODULE can point to an installed Playwright module; BMC_CHROME_PATH overrides Chrome's Windows path.
- All tests use isolated TEMP/TMP, BMC_WEB_UI_WORKSPACE_DIR, BMC_MAIN_PROGRAM_DIR and PYTHONPATH. No formal DB mutation, DUT execution or service restart was performed. Existing downloaded reports remain unchanged; regenerate reports after loading the updated backend.

## Publication boundary

Published from the isolated bmcauto main checkout based on b882cac. The remote baseline lacked local HTML report support, so this delivery includes report_html, the standalone template, report_fonts, report_presentation, and narrowly scoped report API/export integration. Existing HTML default ZIP, optional ?format=pdf and selected log ZIP support are thereby reproducible remotely. This does not publish the unrelated local Task soft-delete or Task Info implementation. Local soft-delete filtering remains in place and is not removed.

The product checkout retains unrelated pre-existing changes. No blanket staging/reset was used. The correct repository is baga0607-cpu/bmcauto; the retired original origin must not be used. RF case source and the live Repository/Plan copies are unchanged in this report-only increment.
