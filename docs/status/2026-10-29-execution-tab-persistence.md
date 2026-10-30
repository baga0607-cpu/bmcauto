# Execution tab persistence — 2026-10-29

Execution stores ordered Task IDs and active Task ID in browser localStorage (bmc-execution-tabs-v1). Refresh, reopening the page and restarting the service preserve the tabs when using the same browser profile and origin. X updates the saved list immediately; it does not delete Task data. Pending dialog choices are not persisted. Missing/deleted Tasks are pruned against the current API; corrupt saved values are safely ignored. Browser storage failures show an error. Clearing site data or using another browser/profile does not share this preference.

Verification: JavaScript syntax, task_management_list.test.cjs and execution_workspace.test.cjs passed. The browser test now reloads with three cross-Project tabs, closes/reopens the page with the same context, checks Task ownership, and reloads after closing tabs to confirm they stay removed. No formal database changes or DUT execution.
