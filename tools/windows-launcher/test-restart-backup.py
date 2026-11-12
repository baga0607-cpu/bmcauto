from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('restart_backup', Path(__file__).with_name('restart-backup.py'))
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'fixture.db'
        self.target = self.root / 'backup'
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.executescript("CREATE TABLE tasks(execution_active INTEGER); INSERT INTO tasks VALUES(0);"
                               "CREATE TABLE task_testcases(status TEXT CHECK(status IN ('CP','Failed')),log_text TEXT);"
                               "INSERT INTO task_testcases VALUES('Failed','retained original evidence');")

    def run_backup(self, action):
        with patch('sys.argv', ['restart-backup.py', action, str(self.db), str(self.target)]):
            backup.main()

    def test_snapshot_and_verification_preserve_data(self):
        self.run_backup('before'); self.run_backup('after')
        with closing(sqlite3.connect(self.target / 'testcase_meta-before.db')) as conn, conn:
            self.assertEqual(conn.execute('SELECT * FROM task_testcases').fetchone(), ('Failed','retained original evidence'))
        result = json.loads((self.target / 'after-verification.json').read_text())
        self.assertEqual(result['changed_tables'], [])
        self.assertTrue(result['cp_schema'])
        with self.assertRaises(FileExistsError): self.run_backup('before')

    def test_active_execution_blocks_backup(self):
        with closing(sqlite3.connect(self.db)) as conn, conn: conn.execute('UPDATE tasks SET execution_active=1')
        with self.assertRaises(SystemExit): self.run_backup('before')
        self.assertFalse(self.target.exists())

    def test_changed_evidence_is_detected(self):
        self.run_backup('before')
        with closing(sqlite3.connect(self.db)) as conn, conn: conn.execute("UPDATE task_testcases SET status='CP'")
        with self.assertRaises(SystemExit): self.run_backup('after')


if __name__ == '__main__': unittest.main()
