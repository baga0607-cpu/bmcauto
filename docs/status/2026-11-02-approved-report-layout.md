# Approved report layout — 2026-11-02

User approved the separate three-case prototype and requested applying it to formal HTML/PDF without overwriting concurrent Note work.

## Delivered

- HTML: Case Name uses Bahnschrift 22px/600, #243447, with a disclosure arrow and same-row status. No generated ordinal or separator dot. Original stored case names remain unchanged. Each case has 13px vertical padding and a thin separator.
- Cases default closed. Activating the case heading opens Test Data, leaving Test Information closed. Activating it again closes all child sections. Native summary keyboard activation is supported. Print expands all sections then restores the exact prior state.
- Data uses label/value columns: Description, Result Summary, Note, Spec Ref. for compliance, Log. Information order: Task Name, Tester, Execution Time, FW Package, empty DUT Configuration label. Execution Time retains the existing Taiwan timestamp semantics (not elapsed duration).
- PDF uses the same sections and order, fully expanded; Bahnschrift 600 is embedded at 16.5pt (22 CSS px). Long content can split across pages. Complete logs remain embedded unchanged. HTML ZIP keeps separate logs, with no inline log preview.
- Note rendering only consumes result_json.note. No changes to case_log.py, plan_state.py, models.py, report_exports.py, RF scripts, status interpretation or historical data were made by this work.
- app.py has one narrowly scoped addition to the report_definition metadata capture: spec_ref, test_type, compliance. The execution Note pipeline is unchanged.

## Spec Ref. declaration

Optional TEST_CASE.spec_ref accepts a string or list of references. Authors may also put spec_ref on individual test_method entries. TEST_CASE.test_type='compliance' or compliance=True explicitly identifies compliance. Existing Compliance / Compliance Test / Compliance Tests folder ancestry also displays the field. No reference is inferred from an RF case name.

Saved report_definition is authoritative. When absent, existing literal script metadata fallback remains available. Legacy criteria containing explicit numbered DSP/RFC/ISO/IEEE citations are displayed verbatim; the renderer does not fabricate or rewrite those citations. A declared compliance case without reference shows an em dash. No old execution is backfilled; RF source declarations remain for their owning chat to update.

## Font setup

Additional PDF dependency: web_ui/requirements-report.txt (fonttools). Installed version 4.68.0 in the local project venv. The system Bahnschrift variable font is instantiated at weight 600 in memory and embedded by ReportLab. Unsupported title glyphs use the existing CJK font. If Bahnschrift/fonttools is unavailable, PDF uses the existing font fallback; HTML uses Segoe UI fallback when the viewing computer lacks Bahnschrift. No system font binary is committed.

## Verification and local rollout

- 28 targeted Python tests passed: report presentation, HTML, case fields, exports, existing Note pipeline. New coverage includes real-runner Spec Ref. capture, unchanged Note, source precedence, long/malicious-looking Note, Final winner ownership and byte-identical attachments.
- Browser fixture passed: default collapse, keyboard activation, child reset, field order, separate log opening, print expansion and exact state restore; formal report inspected at desktop widths 1440 and 1920.
- PDF pages rendered with Poppler and inspected, including multiline Chinese Note and real report fields.
- Formal service was backed up and restarted only after confirming no active Task. HTTP 200. Final service exports: 16 PDF pages, 13 log attachments matching HTML attachments byte-for-byte.
- All formal database tables compare equal to the pre-rollout backup; integrity_check=ok and foreign_key_check empty. No DUT execution, no historical PASS conversion, no source imports and no GitHub publication.
- Evidence and backup: bmca-runtime/verification/report-layout-20261102 (formal-before.db, tests.log, verification.json, formal-report.zip/pdf, HTML and rendered screenshots).

This approval supersedes the earlier report-layout-deferred statements; the Note storage contract remains unchanged.
