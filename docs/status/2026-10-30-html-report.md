# HTML-first reports with separate log attachments

## Latest formal-document layout

User selected the Formal Document direction. Case Name is the location/heading and links to its own fragment. PASS/FAIL is aligned at the heading's right edge. Description (why the test exists), Result Summary (observed judgement), and the separate Open Log attachment link are always visible. Only Task, firmware, Tester, Execution Date and the reserved DUT label remain collapsed. The sheet uses serif document titling, quiet section numbering, whitespace and horizontal rules instead of rounded case cards. HTML printing inherits the formal style and expands only the secondary information. The optional legacy server-generated PDF is unchanged.

Verification: two HTML export tests passed, including escaped content/valid fragment targets/full external logs and Final/Reference parity. Chrome standalone regression passed: all descriptions/results visible without opening details, fragment locations valid, logs open separately, print restores collapsed states. Collapsed HTML and first two printed PDF pages inspected. Existing 13-case snapshot generated in 0.741 seconds. Backup formal-layout-predeploy.db retained locally before restart.

Latest user decision supersedes the PDF-only default and any inline HTML log preview proposal. Report composition now defaults to an HTML package (ZIP), containing BMC_Report.html, README.txt and a logs directory. Extract the package before opening the HTML; keep its directory structure. Each case has an Open attachment link to a distinct full .log file. No raw log, encoded log payload, modal or inline log preview is present in the report HTML. The package itself already downloads the log files; a redundant local-file download attribute was removed after Chrome ignored it in the file-origin test.

## Layout and export

- Status/name and the explicit final reason remain visible. Description, Task, Tester, firmware and Execution Date are in a collapsed Test information section. Manual/retest notices remain visible.
- Execution Date uses YYYY/MM/DD HH:MM:SS (UTC+08:00). Missing dates show an em dash; naive legacy dates retain their clock value and identify the missing timezone rather than guessing. Aware offsets convert correctly across day boundaries.
- Print / Save PDF expands test information and restores prior expansion states after printing. Browser-printed PDFs do not embed logs; the report explicitly says to retain the original package.
- The composer also offers optional Download PDF (the existing PDF generator with full embedded attachments) and Download Logs ZIP (same selection/Final/Reference rules). Downloads keep the composer open so all formats remain accessible. Each click takes its own current data snapshot; separately downloaded formats may differ if results change between clicks.
- Existing internal generate_selection defaults to PDF for compatibility; /api/projects/<id>/reports defaults to the HTML ZIP. Explicit ?format=pdf selects the PDF. /reports/logs supplies separate logs ZIP. Direct legacy Task PDF endpoint is unchanged.

## Implementation and safety

report_html.py renders escaped metadata from the same disposable report snapshot and prepared Final memberships as PDF. File names are sanitized, prefixed with group/case numbers, and referenced by encoded relative URLs. Logs preserve exact UTF-8 text; no scripts or test code are executed from metadata. The standalone template contains only local print behavior, needs no network, and cannot contact the BMC. Existing stored evidence is untouched.

## Validation

- Python: test_report_html, test_report_case, test_report_exports, test_case_log_integration: 30 tests passed. Two HTML tests rerun after the final link-only adjustment passed. Tests cover UTC conversion, missing/naive dates, HTML escaping, absent inline log content, complete attachment bytes, valid relative links, missing logs, invalid scope, Final/Reference parity and optional PDF/ZIP.
- report_downloads.test.cjs passed: default HTML package, PDF, ZIP download filenames, identical selections and composer stays open. workbench.js and zh.js syntax checks passed.
- standalone_report.test.cjs passed in Chrome using local file URLs: secondary info collapsed, zero log preview components, independent log opened in another tab, print expands details and restores state, zero page errors or network requests. Initial page load 78 ms in the captured replay.
- Real 13-case snapshot: HTML 23,878 bytes, report ZIP 712,660 bytes, 13 complete .log files, generation ~0.79 seconds. Compression ratio is data-dependent. All 13 log bytes are checked against the source below during deployment verification.
- Desktop collapsed/expanded screenshots and browser-printed PDF reviewed with Poppler. No overlapping/clipped text observed. Artifacts live locally under bmca-runtime/verification/compact-report/html-actual.
- Impeccable context launcher could not install its missing engine in the restricted cache. Existing PRODUCT.md, DESIGN.md and incumbent Report composer styles were used; no product-wide styling changes.

Deployment uses the original server.py service after confirming zero active Tasks and saving pre-html-deploy.db. No migration or DUT test.

Formal deployment completed: default HTML ZIP HTTP 200 in 0.788 seconds (712,573 bytes); optional PDF 0.797 seconds; Logs ZIP 0.802 seconds. All three exports contain exactly the same 13 full log payloads, verified by SHA-256 against stored unified logs. PDF date is verified as 2026/10/30 15:27:04 (UTC+08:00). Stored statuses/results/logs match pre-html-deploy.db; SQLite integrity ok and zero FK violations. Refresh the browser to load the new composer controls.
