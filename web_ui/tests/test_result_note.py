import io
import json
from pathlib import Path
import unittest

from case_log import CaseLog, result_note
from models import TaskTestCase
import plan_state as ps
import test_case_log_integration as integration


class NotePipelineTest(unittest.TestCase):
    setUp = integration.CaseLogIntegrationTest.setUp
    add_case = integration.CaseLogIntegrationTest.add_case
    run_source = integration.CaseLogIntegrationTest.run_source

    def test_additive_migration_preserves_old_results(self):
        tc = self.add_case()
        original = json.dumps({'reason': 'Historical failure'})
        with self.Session() as session:
            session.add(TaskTestCase(task_id='task1', testcase_id=tc['id'], status='Failed',
                                     result_json=original, log_text='Historical log'))
            session.commit()
        with self.engine.begin() as conn:
            conn.exec_driver_sql('ALTER TABLE task_testcases DROP COLUMN result_note')
        ps.migrate_current_state(self.engine, self.root/'migration.log')
        ps.migrate_current_state(self.engine, self.root/'migration.log')
        with self.Session() as session:
            row = session.query(TaskTestCase).one()
            self.assertEqual(row.result_json, original)
            self.assertEqual(row.log_text, 'Historical log')
            self.assertEqual(row.status, 'Failed')
            self.assertIsNone(row.result_note)

    def test_note_survives_runner_storage_summary_manual_override_and_clears_on_rerun(self):
        source = '''TEST_CASE = {'name': 'Optional entry', 'parameters': {}}
def execute(client, context=None, preset=None):
    log = context['log']
    log.check('Optional entry', True, expected=200, actual=404, note='Not required; HTTP 404 accepted')
    log.step('Read optional entry', '200 preferred', 'PASS', note='Not required; HTTP 404 accepted')
    log.finish('Pass', 'Optional entry absent', note='Not required; HTTP 404 accepted')
    context['_tc_status'] = 'PASS'
'''
        row = self.run_source(source, {})
        note = 'Not required; HTTP 404 accepted'
        self.assertEqual(row['note'], note)
        self.assertEqual(row['result']['note'], note)
        summary = self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]
        self.assertEqual(summary['note'], note)
        self.assertNotIn('result', summary)
        self.assertIn('Note: '+note, row['log_text'])
        changed = self.client.patch(f"/api/tasks/task1/testcases/{row['id']}/status",
                                    json={'status': 'Block', 'reason': 'Review'}).get_json()
        self.assertEqual(changed['note'], note)
        token = self.client.post('/api/tasks/task1/execution/start',
                                 json={'testcase_ids': [row['id']]}).get_json()['execution_token']
        self.assertEqual(self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]['note'], '')
        with self.Session() as session:
            ps.save_result(session, 'task1', {'id': row['id'], 'execution_token': token,
                           'status': 'Passed', 'result': {'reason': 'Normal pass'}})
            session.commit()
        self.assertEqual(self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]['note'], '')

    def test_legacy_and_explicit_note_extraction(self):
        self.assertEqual(result_note({'reason': 'No inferred notes'}), '')
        self.assertEqual(result_note({'log_records': [{'kind': 'check', 'note': 'A'},
                                                      {'kind': 'step', 'note': 'A'}]}), 'A')
        self.assertEqual(result_note({'note': '', 'log_records': [{'note': 'stale'}]}), '')
        log = CaseLog(io.StringIO(), lambda event: None)
        log.check('Old API', True)
        log.step('Old API', 'yes', 'PASS')
        log.finish('Pass', 'Done')
        self.assertEqual(result_note({'log_records': log.records}), '')
