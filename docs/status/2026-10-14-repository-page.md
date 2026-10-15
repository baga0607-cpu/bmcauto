# Repository exclusive function page, 2026-10-14

User scope: Add, Remove and View Test Cases. Enter the function on its list, without the left Project list.

Implemented full-width Repository workspace with the Project navigator and its menu toggle hidden only on this function; Projects restores its existing navigator. Entry clears previous source preview. Add accepts .py and assigns the existing timestamped source generation. List has View/Remove per source row; View follows the list and shows description, source version, parameter types/defaults and read-only Python. Existing Plan Add from Repository controls remain unchanged.

DELETE /api/repository/testcases/<id> requires confirm:true. It deletes only RepositoryCase; existing Plan files, settings, source generation, memberships and Task evidence remain. Confirmation identifies the selected version. A pending-dialog guard prevents cancellation/reopen close-event races from resolving an earlier cancellation as confirmation.

Verification: isolated DB/scripts in bmca-runtime/verification/repository-page, Python87 tests (86 pass, 1 historical fixture skipped). Three new tests check confirmation/not-found, retained Plan/Task data and transaction rollback/active Plan independence. Chrome used an actual local .py file, inspected metadata/source, navigated away/back, canceled and confirmed removal, reloaded, and confirmed preserved Plan generation/Task scope. 1440px desktop list and preview screenshots captured; no mobile checks or DUT execution.

Backup: bmca-runtime/backups/repository-page-20261014/source-before.zip and before.db. No schema change. Current local implementation only, no commit/push. Service reload and final integrity results follow below.

Local service reloaded at http://127.0.0.1:5000; root and Repository API HTTP200 confirmed. Integrity/foreign keys pass. Tables different from the initial backup: ["project_plans"]. Current user data retained; no restoration or synthetic imports into production.
