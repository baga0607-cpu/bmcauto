# Plan import drag layout — 2026-10-22

Fixed and served locally on port 5000; frontend CSS only, no restart/database changes.

## Reproduction and cause
Isolated port 5002 fixture: drag-preview Project, drag-target Plan with Redfish/System folders, drag-source Plan with three synthetic cases. Native right-to-left case drag initially appeared fine over a folder, but after a case existed the before/after drop frame compressed every first cell from 462px to 231px. The table stayed 566px wide; affected case height grew from 57.9479px to 76.6146px. Repeated native drag captured the same shrink. Temporary tagged dragenter/dragover instrumentation measured actual cell rectangles; evidence saved in bmca-runtime/verification/import-shrink-measurements.json.

The generated ::after box on a table row was counted in table column layout, producing an extra anonymous column. Moving only the generated drop frame into existing td cells eliminated the shrink. Shared top/bottom borders with outside left/right edges retain inside/before/after feedback without changing table structure or dimensions. This also covers the shared Repository/Plan tree styles.

## Verification
Same native right-to-left drag after fix: nine captured drag samples all retained first-cell width 462px and action width 104px, including active before/after states; case heights stayed 57.9479px. Three synthetic cases imported successfully; inserted case appeared in the intended target order. Source rows remained present. JavaScript syntax passed; temporary DEBUG-shrink code removed. Screenshot: bmca-runtime/verification/import-shrink-fixed.png.

This CSS layout regression requires a real browser geometry check; the existing VM-only drag tests cannot assert rendering. The recorded native CUA drag plus per-event cell-geometry assertion is the regression verification seam. No shallow CSS source-string test added. Formal Plan data was never used for mutating verification. Preview service stopped after verification.
