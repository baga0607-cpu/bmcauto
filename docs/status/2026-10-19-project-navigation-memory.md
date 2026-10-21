# Projects return-location memory — 2026-10-19

The top Projects link now restores the last valid Project location (information, Plan list, reports, bugs or individual Plan), saved in browser localStorage. Task detail routes do not overwrite the Projects return location. Missing Plan falls back to the Project Plan list; missing Project falls back to dashboard. Stored routes are validated against known projects/plans and supported sections.

Verified in browser: Plan list -> Tasks -> Task detail -> Tasks -> reload -> top Projects returns to the original Plan list. JavaScript syntax check passed. No database changes or server restart required.

Screenshot: bmca-runtime/verification/projects-return-memory.png
