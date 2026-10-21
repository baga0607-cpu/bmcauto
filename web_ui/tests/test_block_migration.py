import unittest
from sqlalchemy import create_engine
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from plan_state import migrate_block_status

class BlockMigrationTest(unittest.TestCase):
    def test_preserves_rows_indexes_and_is_idempotent(self):
        engine=create_engine('sqlite://')
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE task_testcases (id TEXT PRIMARY KEY, status TEXT, log_text TEXT, CONSTRAINT ck_task_status CHECK (status IN ('TBD','Running','Passed','Failed')))")
            conn.exec_driver_sql('CREATE INDEX evidence_idx ON task_testcases(log_text)')
            conn.exec_driver_sql("INSERT INTO task_testcases VALUES ('a','Failed','retained evidence')")
            migrate_block_status(conn)
            migrate_block_status(conn)
            self.assertEqual(tuple(conn.exec_driver_sql('SELECT * FROM task_testcases').one()),('a','Failed','retained evidence'))
            conn.exec_driver_sql("UPDATE task_testcases SET status='Block'")
            self.assertEqual(conn.exec_driver_sql('SELECT status FROM task_testcases').scalar(),'Block')
            self.assertTrue(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='evidence_idx'").scalar())
            self.assertEqual(list(conn.exec_driver_sql('PRAGMA foreign_key_check')),[])
        engine.dispose()
