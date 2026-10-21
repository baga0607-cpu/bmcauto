import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan_state
from models import Base, Project, ProjectPlan, TestCase, Task, TaskTestCase


class ManualResultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'test.db'
        self.engine = create_engine('sqlite:///' + str(self.db))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as s:
            s.add_all([Project(id='project', name='Project'), ProjectPlan(id='p', project_id='project', name='Plan'), ProjectPlan(id='q', project_id='project', name='Other')])
            s.flush()
            s.add_all([Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='t', plan_id='p', name='Task'), Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='peer', plan_id='p', name='Peer'), TestCase(system_id='a', plan_id='p', display_name='A', script_path='a'), TestCase(system_id='b', plan_id='p', display_name='B', script_path='b'), TestCase(system_id='foreign', plan_id='q', display_name='Foreign', script_path='foreign')])
            s.flush()
            for identity in ('a','b','foreign'):
                s.get(TestCase,identity).script_kind='single'
                directory=Path(self.tmp.name,identity);directory.mkdir()
                (directory/'case.py').write_text("TEST_CASE={'name':'Fixture'}\ndef execute(client, context=None, preset=None): pass\n",encoding='utf-8')
            plan_state.replace_scope(s, 't', ['a', 'b'])
            s.commit()
        app = Flask(__name__)
        plan_state.install_routes(app, {'DbSession': self.Session, 'MAIN_PROGRAM_DIR': self.tmp.name, 'run_sessions': {}})
        self.client = app.test_client()

    def tearDown(self):
        self.engine.dispose()
        self.tmp.cleanup()

    def change(self, identity='a', status='Passed', reason='Reviewed by QA'):
        return self.client.patch(f'/api/tasks/t/testcases/{identity}/status', json={'status': status, 'reason': reason})

    def test_never_executed_manual_result_has_no_fabricated_evidence(self):
        for status in ('Passed', 'Failed', 'Block', 'TBD'):
            response = self.change(status=status)
            self.assertEqual(response.status_code, 200, response.get_json())
            case = response.get_json()
            self.assertEqual(case['status'], status)
            self.assertIsNone(case['executed_at'])
            self.assertIsNone(case['result'])
            self.assertEqual((case['log_text'], case['api_log_text']), ('', ''))
            self.assertEqual(case['manual_override']['reason'], 'Reviewed by QA')
            self.assertEqual(case['manual_override']['status'], status)
            self.assertIsNotNone(datetime.fromisoformat(case['manual_override']['modified_at']).tzinfo)
            current = self.client.get('/api/tasks/t/summary').get_json()
            self.assertEqual(current['testcases'][0]['manual_override'], case['manual_override'])
            self.assertEqual(current['counts'][status], 2 if status == 'TBD' else 1)

    def test_manual_change_preserves_execution_and_logs_endpoint(self):
        with self.Session() as s:
            row = s.query(TaskTestCase).filter_by(task_id='t', testcase_id='a').one()
            row.status = 'Failed'
            row.result_json = json.dumps({'steps': [{'error': 'original failure'}]})
            row.log_text = 'console evidence'
            row.api_log_text = 'HTTP evidence'
            row.executed_at = '2026-09-01T10:00:00Z'
            s.commit()
        response = self.change()
        self.assertEqual(response.status_code, 200)
        logs = self.client.get('/api/tasks/t/testcases/a/logs')
        self.assertEqual(logs.status_code, 200)
        case = logs.get_json()
        self.assertEqual(case['status'], 'Passed')
        self.assertEqual(case['executed_at'], '2026-09-01T10:00:00Z')
        self.assertEqual(case['result'], {'steps': [{'error': 'original failure'}]})
        self.assertEqual((case['log_text'], case['api_log_text']), ('console evidence', 'HTTP evidence'))

    def test_status_validation_and_plan_lock(self):
        for status in ('Running', 'pass', 'unknown', '', None, ['Passed']):
            self.assertEqual(self.change(status=status).status_code, 400)
        self.assertEqual(self.change(reason={'invalid': 'type'}).status_code, 400)
        with self.Session() as s:
            s.get(Task, 'peer').execution_active = True
            s.commit()
        self.assertEqual(self.change().status_code, 409)
        with self.Session() as s:
            row = s.query(TaskTestCase).filter_by(task_id='t', testcase_id='a').one()
            self.assertEqual(row.status, 'TBD')

    def test_live_membership_is_required_for_read_and_write(self):
        for identity in ('missing', 'foreign'):
            self.assertEqual(self.change(identity=identity).status_code, 404)
            self.assertEqual(self.client.get(f'/api/tasks/t/testcases/{identity}/logs').status_code, 404)
        with self.Session() as s:
            s.get(TestCase, 'a').plan_id = 'q'
            s.commit()
        self.assertEqual(self.change().status_code, 404)
        self.assertEqual(self.client.get('/api/tasks/t/testcases/a/logs').status_code, 404)

    def test_rerun_clears_only_selected_manual_marker(self):
        self.assertEqual(self.change().status_code, 200)
        self.assertEqual(self.change(identity='b', status='Failed').status_code, 200)
        response = self.client.post('/api/tasks/t/execution/start', json={'selected_testcase_ids': ['a']})
        self.assertEqual(response.status_code, 200)
        cases = self.client.get('/api/tasks/t/summary').get_json()['testcases']
        self.assertIsNone(cases[0]['manual_override'])
        self.assertEqual(cases[0]['status'], 'TBD')
        self.assertEqual(cases[1]['manual_override']['reason'], 'Reviewed by QA')
        self.assertEqual(cases[1]['status'], 'Failed')

    def test_pdf_exposes_manual_marker_reason_and_time_without_execution(self):
        from report_generator import generate_task_pdf_report
        from pypdf import PdfReader
        self.assertEqual(self.change(status='Block', reason='QA acceptance <confirmed>').status_code, 200)
        marker = self.client.get('/api/tasks/t/summary').get_json()['testcases'][0]['manual_override']
        pdf = Path(self.tmp.name) / 'report.pdf'
        generate_task_pdf_report('t', str(pdf), db_path=str(self.db))
        reader = PdfReader(str(pdf))
        content = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn('BLOCK', content)
        self.assertIn('Manual status', content)
        self.assertIn('QA acceptance <confirmed>', content)
        self.assertIn(marker['modified_at'], content)
        self.assertEqual(list(reader.attachments), [])

    def test_projects_reload_preserves_manual_marker_without_loading_logs(self):
        import app as api
        from unittest.mock import patch
        self.assertEqual(self.change().status_code, 200)
        expected = self.client.get('/api/tasks/t/testcases/a/logs').get_json()['manual_override']
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='t', testcase_id='a').one()
            row.log_text = 'large console evidence'
            row.api_log_text = 'large API evidence'
            session.commit()
        with patch.object(api, 'DbSession', self.Session):
            response = api.app.test_client().get('/api/projects')
        self.assertEqual(response.status_code, 200, response.get_json())
        plans = response.get_json()['projects'][0]['plans']
        task = next(task for plan in plans for task in plan['tasks'] if task['id'] == 't')
        case = next(case for case in task['testcases'] if case['id'] == 'a')
        self.assertEqual(case.get('manual_override'), expected)
        self.assertEqual(case['status'], 'Passed')
        self.assertNotIn('log_text', case)
        self.assertNotIn('api_log_text', case)

    def folders(self, plan='p'):
        return self.client.get(f'/api/plans/{plan}/folders').get_json()

    def folder(self, name, parent=None, plan='p'):
        response = self.client.post(f'/api/plans/{plan}/folders', json={'name': name, 'parent_id': parent})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['id']

    def assert_folder_order(self, parent, identities):
        rows = sorted((row for row in self.folders() if row['parent_id'] == parent), key=lambda row: row['position'])
        self.assertEqual([(row['id'], row['position']) for row in rows], list(zip(identities, range(len(identities)))))

    def test_relative_folder_drop_inserts_cross_parent_and_same_parent(self):
        root = self.folder('Root')
        other = self.folder('Other')
        left = self.folder('Left', root)
        moving = self.folder('Moving', root)
        right = self.folder('Right', root)
        target = self.folder('Target', other)
        tail = self.folder('Tail', other)
        response = self.client.patch('/api/folders/' + moving, json={'parent_id': other, 'relative_to': target, 'insertion': 'before'})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assert_folder_order(root, [left, right])
        self.assert_folder_order(other, [moving, target, tail])
        response = self.client.patch('/api/folders/' + moving, json={'relative_to': target, 'insertion': 'after'})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assert_folder_order(other, [target, moving, tail])
        response = self.client.patch('/api/folders/' + moving, json={'parent_id': None, 'relative_to': root, 'insertion': 'before'})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assert_folder_order(None, [moving, root, other])
        self.assert_folder_order(other, [target, tail])

    def test_invalid_relative_folder_drop_rolls_back_rename_and_membership(self):
        root = self.folder('Root')
        other = self.folder('Other')
        moving = self.folder('Moving', root)
        target = self.folder('Target', other)
        foreign = self.folder('Foreign', plan='q')
        initial = self.folders()
        cases = [
            ({'relative_to': target, 'insertion': 'before'}, 400),
            ({'relative_to': moving, 'insertion': 'before'}, 400),
            ({'parent_id': None, 'relative_to': foreign, 'insertion': 'after'}, 400),
            ({'parent_id': other, 'relative_to': target, 'insertion': 'invalid'}, 400),
            ({'parent_id': other, 'relative_to': target}, 400),
            ({'parent_id': other, 'insertion': 'before'}, 400),
            ({'parent_id': other, 'relative_to': 'missing', 'insertion': 'before'}, 404),
        ]
        for data, status in cases:
            with self.subTest(data=data):
                response = self.client.patch('/api/folders/' + moving, json=dict(data, name='Renamed'))
                self.assertEqual(response.status_code, status, response.get_json())
                self.assertEqual(self.folders(), initial)

    def case_placements(self):
        with self.Session() as session:
            return {row.system_id: (row.folder_id, row.position) for row in session.query(TestCase)}

    def seed_testcase_folders(self):
        source = self.folder('Source')
        destination = self.folder('Destination')
        with self.Session() as session:
            session.get(TestCase, 'a').folder_id = source
            session.get(TestCase, 'a').position = 0
            session.get(TestCase, 'b').folder_id = source
            session.get(TestCase, 'b').position = 1
            session.add_all([
                TestCase(system_id='target', plan_id='p', display_name='Target', script_path='target', folder_id=destination, position=0),
                TestCase(system_id='tail', plan_id='p', display_name='Tail', script_path='tail', folder_id=destination, position=1),
            ])
            session.commit()
        return source, destination

    def test_relative_testcase_move_preserves_target_position_and_source_order(self):
        source, destination = self.seed_testcase_folders()
        url = '/api/plans/p/testcases/move'
        response = self.client.post(url, json={'testcase_ids': ['a'], 'folder_id': destination, 'relative_to': 'target', 'insertion': 'before'})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.case_placements(), {'a': (destination, 0), 'b': (source, 0), 'target': (destination, 1), 'tail': (destination, 2), 'foreign': (None, 0)})
        response = self.client.post(url, json={'testcase_ids': ['b', 'a'], 'folder_id': destination, 'relative_to': 'target', 'insertion': 'after'})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(self.case_placements(), {'a': (destination, 2), 'b': (destination, 1), 'target': (destination, 0), 'tail': (destination, 3), 'foreign': (None, 0)})

    def test_invalid_relative_testcase_move_is_atomic_and_plan_locked(self):
        source, destination = self.seed_testcase_folders()
        initial = self.case_placements()
        url = '/api/plans/p/testcases/move'
        for data, status in [
            ({'relative_to': 'a', 'insertion': 'before'}, 400),
            ({'relative_to': 'b', 'insertion': 'after'}, 400),
            ({'relative_to': 'foreign', 'insertion': 'after'}, 400),
            ({'relative_to': 'target'}, 400),
            ({'insertion': 'before'}, 400),
            ({'relative_to': 'target', 'insertion': 'invalid'}, 400),
            ({'relative_to': 'missing', 'insertion': 'before'}, 404),
        ]:
            with self.subTest(data=data):
                response = self.client.post(url, json=dict(data, testcase_ids=['a'], folder_id=destination))
                self.assertEqual(response.status_code, status, response.get_json())
                self.assertEqual(self.case_placements(), initial)
        with self.Session() as session:
            session.get(Task, 'peer').execution_active = True
            session.commit()
        response = self.client.post(url, json={'testcase_ids': ['a'], 'folder_id': destination, 'relative_to': 'target', 'insertion': 'before'})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.case_placements(), initial)

    def test_migration_adds_optional_column_once_and_preserves_manual_data(self):
        with self.engine.begin() as connection:
            columns = [r[1] for r in connection.exec_driver_sql('PRAGMA table_info(task_testcases)')]
            if 'manual_override_json' in columns:
                connection.exec_driver_sql('ALTER TABLE task_testcases DROP COLUMN manual_override_json')
        plan_state.migrate_current_state(self.engine, Path(self.tmp.name) / 'migration.log')
        self.assertEqual(self.change().status_code, 200)
        first = self.client.get('/api/tasks/t/summary').get_json()
        plan_state.migrate_current_state(self.engine, Path(self.tmp.name) / 'migration.log')
        self.assertEqual(self.client.get('/api/tasks/t/summary').get_json(), first)


if __name__ == '__main__':
    unittest.main()
