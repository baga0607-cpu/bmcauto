# Execution: single Test Case report preview — 2026-11-12

## Delivered behavior

In the local Execution case table, Report preview is the icon immediately to the right of Log and before Parameters. The button is available for completed, not-run, stale and running memberships. It opens a native modal for the selected Task and Case, with the five-column Step / Type / Description / Result / Judgement report, description, summary, Note, Spec Ref. when applicable, and Test Information expanded initially.

The preview directly uses the production HTML renderer and its CSS. It does not export a report, write a temporary report file, run a Case, change annotations or modify Task/Plan data. Log attachment availability is indicated without embedding or downloading the full log; the existing Log viewer remains the access point. The paper content stays white in both application themes to match exported reports.

Refresh reloads currently saved evidence. A running case shows an explicit in-progress notice; this is not a live stream of the worker's unpersisted output. Missing results remain No recorded result. Manual-result explanations and rerun notices are retained. Previewing one Task never applies another Task's Final-report winner.

Close and Escape dismiss the modal and restore focus, including when focus is inside the report. Navigation closes it. Pending fetches are aborted on close or replacement; identity checks prevent late results from overwriting another preview. Errors hide old content and provide a retry through Refresh. Opening an existing Execution dialog (including an operator input prompt) closes the preview first.

## Implementation

- GET /api/tasks/<task_id>/testcases/<case_id>/report-preview returns JSON containing rendered HTML, with no-store caching. Unknown Tasks, absent memberships and wrong-Plan memberships return 404.
- report_html.generate_case_preview calls the production renderer with a single-membership filter. SQLite opens read-only, with one read transaction for consistent Task/evidence reads. Raw log columns are not loaded into Python for previews; SQL only checks availability. Current script metadata is used only under the existing report fallback rules.
- report_preview.js / report_preview.css own the native modal, refresh/error/loading/focus lifecycle and contained report frame. index.html loads them before workbench.js.
- The frame allows same-origin access solely so the parent can relay Escape, but does not allow scripts, forms, popups or top navigation. Preview HTML has a restrictive CSP, no embedded scripts, and the same escaped report fields as exports. Parent code installs the Escape handler; report content cannot execute scripts.
- Existing HTML/PDF exports remain unchanged apart from the shared renderer's read-only transaction.

## Validation

- Local and independent publication checkout: 30 Python tests each passed (preview, HTML, method table, case fields and exports).
- Preview tests compare the five-column table byte-for-byte with the production HTML export; verify one membership, Task context, no DB changes, no export invocation, no raw-log formatting, running/manual/stale states, missing evidence, invalid ownership, escaping and a multi-megabyte omitted log.
- Local and publication browser tests passed: entry point, exact column order, initially expanded information, sandbox, refresh/retry, focus inside report then Escape, delayed response after close, switching Tasks with the same Case ID, route cleanup, no mutation requests, no script errors, desktop light/dark and no horizontal overflow.
- Local execution_controls.test.cjs passed after updating its expected action order and seven table columns. This exercises existing selection/run/stop/resume, parameter locks/conflicts, annotations, Log export, operator prompts, focus/scroll and desktop themes. An initial download cancellation was resolved by running with writable isolated TEMP/TMP; the final run passed.
- Screenshots were inspected at 1440×900. QA fixtures and logs are under bmca-runtime/verification/execution-report-preview-20261112, excluded from Git. Set BMC_REPORT_QA_DIR for Python fixture generation and the browser test, BMC_PLAYWRIGHT_MODULE for Playwright, and isolated TEMP/TMP/workspace/main paths.
- No physical DUT, formal DB mutation or formal service restart. Load the updated backend and reload the browser before using the new endpoint.

## Publication baseline and exact local integration

The independent baga0607-cpu/bmcauto main baseline (49dc750) still has the earlier split Execution/evidence layout, not the local icon-row/dialog redesign. The published adapter adds Report preview to the right of the Test log heading in that older evidence toolbar. It uses the identical modal and backend and was independently browser-tested. The rest of the uncommitted local Execution redesign is not silently bundled into this feature.

The precise integration for the newer local Execution layout, including the row-button placement, dialog interlock and changed regression assertions, is preserved in [the local integration patch](../patches/2026-11-12-execution-report-preview.patch). It is already applied locally; apply it only when integrating the matching newer Execution baseline into the published repository. Do not apply it to the current older remote workbench. This preserves the requested local UI changes in Git without overwriting unrelated work.
