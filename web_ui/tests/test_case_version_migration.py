import unittest
import sys
from pathlib import Path
from sqlalchemy import create_engine
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from plan_state import migrate_case_versions

class CaseVersionMigrationTest(unittest.TestCase):
    def test_preserves_cases_and_dependent_evidence_and_allows_versions(self):
        engine=create_engine('sqlite://')
        with engine.connect() as conn:
            conn.exec_driver_sql('PRAGMA foreign_keys=OFF');conn.commit()
            conn.exec_driver_sql("CREATE TABLE testcases (system_id TEXT PRIMARY KEY, plan_id TEXT, normalized_name TEXT, source_version TEXT, CONSTRAINT uq_testcases_plan_normalized_name UNIQUE (plan_id, normalized_name))")
            conn.exec_driver_sql('CREATE TABLE evidence (id TEXT, testcase_id TEXT REFERENCES testcases(system_id) ON DELETE CASCADE, log TEXT)')
            conn.exec_driver_sql('CREATE INDEX case_plan_idx ON testcases(plan_id)')
            conn.exec_driver_sql('CREATE UNIQUE INDEX uq_testcases_plan_normalized_name ON testcases(plan_id,normalized_name)')
            conn.exec_driver_sql("INSERT INTO testcases VALUES ('a','p','same','v1')")
            conn.exec_driver_sql("INSERT INTO evidence VALUES ('e','a','keep')")
            migrate_case_versions(conn);migrate_case_versions(conn)
            self.assertEqual(tuple(conn.exec_driver_sql('SELECT * FROM evidence').one()),('e','a','keep'))
            conn.exec_driver_sql("INSERT INTO testcases VALUES ('b','p','same','v2')")
            self.assertTrue(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='case_plan_idx'").scalar())
            self.assertEqual(list(conn.exec_driver_sql('PRAGMA foreign_key_check')),[])
            with self.assertRaises(Exception):conn.exec_driver_sql("INSERT INTO testcases VALUES ('c','p','same','v2')")
            conn.rollback()
        engine.dispose()
