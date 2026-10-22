# Test Plan naming from SKU — 2026-10-21

## Behavior
- New Plan reads saved Project Information before opening the existing dialog.
- Projects with SKUs require an explicit SKU selection; Plan name then defaults to the exact SKU name. Changing the SKU replaces the suggested name. User names are excluded from UI translation.
- Projects without SKUs hide the selector and default Plan name to Project name.
- Names remain editable; confirm accepts the suggestion or the edited value.
- Existing same-Project duplicate-name rules remain: exact matching after trimming. Inline conflict feedback asks the user to change the name, preserves the dialog and focuses the name field. Backend 409 responses also receive that feedback.
- This is naming behavior only; no schema change or persistent SKU relationship was introduced.

## Verification
- Node syntax checks passed for workbench.js and zh.js.
- Browser on isolated port 5001: explicit SKU selection, automatic BMC/GPU naming, direct creation, duplicate rejection, edit-and-resubmit success, no-SKU Project name fallback/direct creation, and cancellation.
- Disposable preview Project: Plan naming no SKU. Preview reference Project received FWA-6084 BMC and FWA-6084 BMC custom Plans. No formal database writes or service restart.
- Screenshot: bmca-runtime/verification/2026-10-21-plan-sku.png (local only).
- Backend and full repository suites were not run; backend behavior is unchanged.
- Impeccable context launcher unavailable: missing 0.1.5 engine and restricted cache installation. Read existing PRODUCT.md, DESIGN.md and craft-floor directly.

Final checks: preview SQLite integrity_check=ok and foreign_key_check returned no rows. Shell HTTP access to localhost was blocked by environment permissions; browser verification on formal port 5000 succeeded: SKU selector and exact SKU-name prefill loaded, then Cancel returned to the unchanged empty Plan list. No formal Plan was created. Screenshot: bmca-runtime/verification/2026-10-21-plan-sku-formal.png (local only).
