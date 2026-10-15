# BMCAgent source backup — 2026-10-15

This repository contains a snapshot of the current BMCAgent application, documentation, tests and Python test-case files. It is a source backup, not a complete runtime/database restore.

- Application source is at the repository root (web_ui/, main_program/).
- Plan-owned Python files are included under main_program/testcase_database/scripts/.
- Authoring Python files are under testcases/.
- Standard Repository Python sources exported read-only from the local database are under repository_exports/, with source versions and SHA-256 in manifest.json. These can be imported through the Repository UI.
- Production SQLite databases, Task credentials/settings/results/logs, virtualenvs, caches, temporary sharing credentials, tunnel binaries and local runtime backups are excluded. The legacy SQLite test fixture is also excluded.
- Two archived Session_Service scripts contained hardcoded passwords; only the uploaded copies use <password> instead. Mock credentials in unit-test fixtures are synthetic.
- Existing local Git history/remotes are untouched. This is a fresh snapshot in the user-specified backup repository.
- BACKUP-MANIFEST.json records every other uploaded file and its SHA-256.

External preview sharing is stopped. No tunnel or preview service is started by this backup.
