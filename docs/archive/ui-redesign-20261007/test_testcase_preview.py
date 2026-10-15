import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as app_module
from models import Base, Project, ProjectPlan, TestCase


class TestCasePreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.main = Path(self.temp.name)
        self.engine = create_engine('sqlite:///:memory:')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as session:
            session.add_all([
                Project(id='project', name='Project'),
                ProjectPlan(id='plan', project_id='project', name='Plan', folders_migrated=True),
                ProjectPlan(id='other', project_id='project', name='Other', folders_migrated=True),
                TestCase(system_id='tc', family_id='family', display_name='Preview TC', plan_id='plan', script_path='testcase_database.scripts.tc'),
            ])
            session.commit()
        for name, value in [('DbSession', self.Session), ('MAIN_PROGRAM_DIR', str(self.main))]:
            patcher = patch.object(app_module, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def write(self, module, source):
        path = self.main.joinpath(*module.split('.')).with_suffix('.py')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding='utf-8')
        return path

    def preview(self, plan='plan', tc='tc'):
        return self.client.get(f'/api/plans/{plan}/testcases/{tc}/preview')

    def test_ordered_formats_and_metadata_without_executing_modules(self):
        marker = self.main / 'executed'
        side_effect = f'open({str(marker)!r}, "w").write("executed")\n'
        testcase = self.write('testcase_database.scripts.tc.__testcase__', side_effect + "STEPS = [{'module_path':'steps.one','preset':'Lit'}, ('steps.two', 'Off'), 'steps.one']\n")
        original = testcase.read_bytes()
        self.write('steps.one', side_effect + "STEP_NAME = '第一步'\nSTEP_DESCRIPTION = 'Read state'\nSTEP_METADATA = {'inputs': ['state']}\n")
        self.write('steps.two', "STEP_NAME = 'Second'\nSTEP_DESCRIPTION = 'Verify'\nSTEP_METADATA = {}\n")
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual((data['id'], data['plan_id'], data['tc_name'], data['folder_path']), ('tc', 'plan', 'Preview TC', ''))
        self.assertEqual([(s['module_path'], s['preset']) for s in data['steps']], [('steps.one', 'Lit'), ('steps.two', 'Off'), ('steps.one', '')])
        self.assertEqual(data['steps'][0]['step_name'], '第一步')
        self.assertEqual(data['steps'][0]['step_description'], 'Read state')
        self.assertEqual(data['steps'][0]['metadata'], {'inputs': ['state']})
        self.assertFalse(marker.exists())
        self.assertEqual(testcase.read_bytes(), original)

    def test_empty_steps_are_success(self):
        self.write('testcase_database.scripts.tc.__testcase__', 'STEPS = []')
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['steps'], [])

    def test_missing_and_cross_plan_are_not_found(self):
        for plan, tc in [('missing', 'tc'), ('plan', 'missing'), ('other', 'tc')]:
            with self.subTest(plan=plan, tc=tc):
                self.assertEqual(self.preview(plan, tc).status_code, 404)

    def test_unreadable_or_unsupported_steps_are_errors_not_empty(self):
        sources = [None, 'OTHER = []', 'STEPS = make_steps()', 'STEPS = [', 'STEPS = 7', 'STEPS = [12]', "STEPS = []\nSTEPS.append('steps.one')"]
        for source in sources:
            with self.subTest(source=source):
                if source is not None:
                    self.write('testcase_database.scripts.tc.__testcase__', source)
                response = self.preview()
                self.assertEqual(response.status_code, 422)
                self.assertTrue(response.get_json()['error'])
                self.assertNotIn('steps', response.get_json())

    def test_missing_or_dynamic_metadata_keeps_steps_with_warning(self):
        self.write('testcase_database.scripts.tc.__testcase__', "STEPS = ['steps.missing', 'steps.dynamic']")
        self.write('steps.dynamic', "STEP_NAME = make_name()\nSTEP_METADATA = {}")
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        steps = response.get_json()['steps']
        self.assertEqual([s['step_name'] for s in steps], ['missing', 'dynamic'])
        for step in steps:
            self.assertEqual(step['step_description'], '')
            self.assertEqual(step['metadata'], {})
            self.assertTrue(step['step_error'])

    def test_public_read_errors_hide_host_paths(self):
        missing_script = self.preview()
        self.assertEqual(missing_script.status_code, 422)
        self.assertNotIn(self.main.name, missing_script.get_json()['error'])
        self.assertIn('not found', missing_script.get_json()['error'].lower())
        self.write('testcase_database.scripts.tc.__testcase__', "STEPS = ['steps.missing']")
        missing_step = self.preview().get_json()['steps'][0]
        self.assertEqual(missing_step['module_path'], 'steps.missing')
        self.assertNotIn(self.main.name, missing_step['step_error'])
        self.assertIn('not found', missing_step['step_error'].lower())

    def test_script_path_cannot_escape_main_program(self):
        for path in ['../outside', 'C:\\outside', 'testcase_database..outside']:
            with self.subTest(path=path):
                with self.Session() as session:
                    session.get(TestCase, 'tc').script_path = path
                    session.commit()
                self.assertEqual(self.preview().status_code, 422)


if __name__ == '__main__':
    unittest.main()
