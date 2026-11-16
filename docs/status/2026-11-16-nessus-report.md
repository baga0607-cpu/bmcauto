# Nessus-style report presentation — 2026-11-16

User approved the final RF-01-002/007/008 prototype for production. This supersedes the earlier report typography and badge styling, not report content or verdict rules.

## Approved presentation

- Case Name remains the sole case disclosure. Header: 14px bold white text, 20px line height, 5px vertical padding (30px single-line height), 6px corners. PASS uses blue `#67ace1`, FAIL red `#dd4b50`, C-PASS orange `#f18c43`, matching the reviewed prototype. Other case states retain their explicit text on the base blue header.
- Case judgement is borderless and aligned with the table Judgement column. Table remains Step / Type / Description / Result / Judgement, widths 6/13/39/30/12%.
- Compact 3px HTML cell vertical padding, pale grey header, horizontal rules, dotted section headings. PDF/print retains 2pt cell padding and corresponding compact title sizing.
- FAIL Result and judgement are red and bold. C-PASS judgement and recorded Note are orange and bold, with no highlighted background. Notes in a failed case/row are red. PASS judgement uses muted green; ordinary results remain normal text.
- Note is identified at the recorded field boundary, never inferred by searching Actual for the word "Note:". Legacy checks, note-only rows, manual C-PASS and truncation retain their text and association.
- HTML export starts collapsed; per-case preview starts expanded; print expands cases and restores prior disclosure states. Logs, attachments, original results and case verdicts are unchanged. Case-level note fallback remains removed. Checkpoint aggregation is still unapproved and unimplemented.

## Implementation and verification

Updated `report_case.py`, `report_presentation.py`, `report_html.py`, shared HTML template and ReportLab PDF generator. PDF now loads a real installed CJK bold face when available instead of registering the regular face as bold. Long method tables remain splittable; section headings reserve room for their first content without moving whole tables.

Reference Nessus file was processed only for CSS/tag/class/inline-style structure. Its body text and scripts were not read or reused. Prototype source is retained locally at `bmca-runtime/prototypes/report-emphasis-20261113/build.py`; original test snapshots are local-only.

29 tests passed in both runtime and clean publish checkout using isolated workspace/main/TEMP/TMP: `test_report_emphasis`, `test_report_note_association`, `test_report_case`, `test_report_method_table`, `test_report_html`, `test_report_preview`, `test_conditional_pass.ConditionalCaseTest.test_policy_and_legacy_display`. Includes escaped content, multiline/false Note boundaries, truncation, HTML/PDF export, attachments, preview and original evidence preservation.

Chrome checked an isolated saved-result export: 14px case titles, 30px headers, 3px cell padding, judgement alignment within 0.4px, correct RGB/700 weight for FAIL/Note/C-PASS, no horizontal overflow, collapsed cases and expansion. Production RF-01-008 preview visibly confirmed the new style after deployment. Print-state JavaScript was checked in a Node VM for expand/restore including repeated beforeprint; browser print dialog/PDF-save was not rerun. The existing browser regression font expectation was updated; its headless suite was not executed in this session.

PDF was rendered with Poppler and visually inspected for PASS/FAIL/C-PASS, bold colored evidence, attachments, table continuation and section pagination. Poppler emitted existing optional display-font warnings for Symbol/ArialUnicode; inspected output had no missing text. Evidence: `bmca-runtime/verification/nessus-report-20261116/` (isolated DB, saved-report HTML/PDF, rendered PNGs, test logs). No DUT test was executed.

## Deployment

Runtime: `D:/Codex/bmc_auto_test/BMCAgent`, localhost port 5000. Published from clean `bmca-runtime/publish-handoff-20261111` main; origin verified as `https://github.com/baga0607-cpu/bmcauto.git`. Only named report files and status documentation are included; unrelated runtime edits are preserved.

Restarted with `bmca-runtime/launch.ps1 -Action Restart -Mode Local -NoBrowser`. Final backup: `bmca-runtime/backups/restart-20261116-090053-072`; zero active tasks, 21 table fingerprints unchanged, integrity `ok`, zero foreign-key errors. Earlier same-session backup: `restart-20261116-085759-555`. User already manually synchronized RF-01-011; no Repository/Plan synchronization was performed here.

Next: user review of deployed appearance, then revisit the still-pending Checkpoint summary proposal only when requested.
