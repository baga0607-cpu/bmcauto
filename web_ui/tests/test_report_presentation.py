import io
import json
import os
from pathlib import Path
import unittest
import zipfile

from models import TaskTestCase
from report_presentation import note_text, specification_reference
import test_report_exports as fixtures
import test_case_log_integration as integration


class DeclarationTest(unittest.TestCase):
    def test_no_invented_or_current_reference_for_old_evidence(self):
        self.assertIsNone(specification_reference({'report_definition': {}}, {'spec_ref': 'New source'}))
        self.assertEqual(specification_reference({}, {'spec_ref': ['A', 'B']}), 'A\nB')
        self.assertEqual(specification_reference({}, {'test_type': 'compliance'}), '—')
        self.assertEqual(specification_reference({}, {}, 'Compliance Test/Redfish'), '—')
        self.assertIsNone(specification_reference({}, {'name': 'RF-01-008'}))
        self.assertEqual(note_text({}), '—')
        self.assertEqual(note_text({'note': 'accepted <&>'}), 'accepted <&>')


class SpecPersistenceTest(unittest.TestCase):
    setUp = integration.CaseLogIntegrationTest.setUp
    add_case = integration.CaseLogIntegrationTest.add_case
    run_source = integration.CaseLogIntegrationTest.run_source

    def test_runner_preserves_declared_spec_without_changing_note(self):
        source = '''TEST_CASE = {'name': 'Spec reference fixture', 'parameters': {},
    'spec_ref': ['DSP0266 v1.25.0 section 6.7 Table 4'], 'test_type': 'compliance'}
def execute(client, context=None, preset=None):
    context['log'].finish('Pass', 'Accepted', note='Explicit execution note')
    context['_tc_status'] = 'PASS'
'''
        row = self.run_source(source, {})
        self.assertEqual(row['result']['report_definition']['spec_ref'], ['DSP0266 v1.25.0 section 6.7 Table 4'])
        self.assertEqual(row['result']['note'], 'Explicit execution note')


class PresentationExportTest(unittest.TestCase):
    setUp = fixtures.ReportExportsTest.setUp
    prepare = fixtures.ReportExportsTest.prepare

    def test_winner_note_spec_escape_long_note_and_unchanged_data(self):
        self.prepare()
        note = ('Accepted deviation <safe> 中文.\n' * 100) + 'END_OF_NOTE'
        with self.Session() as session:
            winner = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            winner.result_json = json.dumps({'note': note, 'reason': 'Recorded final reason',
                'report_definition': {'description': 'Recorded description', 'spec_ref': 'DSP0266 <recorded>'}})
            ignored = session.query(TaskTestCase).filter_by(task_id='task2', testcase_id='case-0').one()
            ignored.result_json = json.dumps({'note': 'IGNORED_NOTE'})
            session.commit()
        with self.engine.connect() as connection:
            before = list(connection.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id'))
        selection = {'plan_ids': ['a']}
        html_response = self.client.post('/api/projects/project/reports', json=selection)
        with zipfile.ZipFile(io.BytesIO(html_response.data)) as archive:
            html = archive.read('BMC_Report.html').decode()
            self.assertIn('END_OF_NOTE', html)
            self.assertIn('DSP0266 &lt;recorded&gt;', html)
            self.assertNotIn('IGNORED_NOTE', html)
            self.assertNotIn('<details open', html)
            self.assertNotIn('class="case-number"', html)
            target = os.environ.get('BMC_REPORT_QA_DIR')
            if target:
                out = Path(target)/'layout-fixture'
                out.mkdir(exist_ok=True)
                archive.extractall(out)
        with self.engine.connect() as connection:
            self.assertEqual(before, list(connection.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id')))
