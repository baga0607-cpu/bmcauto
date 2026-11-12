import io
import json
import os
import unittest
import zipfile
from pathlib import Path

import pypdf
from report_case import method_table_rows
import test_report_exports as fixtures


def item(identity, kind, step, text, status=None, **values):
    row = {'kind': 'step', 'method_id': identity, 'method_type': kind,
           'step_id': step, 'step': f'{identity} | {kind} | {text}'}
    if status:
        row['result'] = {'id': identity, 'type': kind, 'step_id': step,
                         'status': status, **values}
    return row


class MethodTableTest(unittest.TestCase):
    def test_typed_results_preserve_relationship_and_informational_values(self):
        records = [item('S2', 'Step', 'S2', 'Parse JSON.', 'FAILED', reason='Invalid JSON'),
                   item('C2a', 'Checkpoint', 'S2', 'Verify JSON.', 'FAIL', actual=False),
                   item('C2b', 'Checkpoint', 'S2', 'Verify object.', 'NOT_EVALUATED', reason='C2a failed'),
                   item('R5', 'Record', 'S5', 'Record version.', 'RECORDED', actual=None)]
        rows = method_table_rows({'log_records': records}, {})
        self.assertEqual(rows[0][:3], ('S2', 'Step', 'Parse JSON.'))
        self.assertIn('Source: S2', rows[1][2])
        self.assertIn('Actual: False', rows[1][3])
        self.assertIn('NOT_EVALUATED', rows[2][3])
        self.assertEqual(rows[3][3], 'RECORDED\nActual: null')
        for value in (0, False, 'Not present'):
            records[-1]['result']['actual'] = value
            self.assertIn(str(value), method_table_rows({'log_records': records}, {})[-1][3])

    def test_saved_definition_and_missing_observation_never_invent_verdict(self):
        saved = {'test_method': [{'id': 'S1', 'type': 'Step', 'step_id': 'S1', 'step': 'S1 | Step | Saved action'}]}
        current = {'test_method': [{'id': 'S99', 'type': 'Step', 'step': 'Changed source'}]}
        rows = method_table_rows({'report_definition': saved}, current)
        self.assertEqual(rows, [('S1', 'Step', 'Saved action', 'No recorded result')])
        self.assertEqual(method_table_rows({'report_definition': {}}, current)[0][2], 'No test steps recorded')
        result = {'report_definition': saved, 'log_records': [item('C1', 'Checkpoint', 'S1', 'Check', 'PASS')]}
        self.assertEqual(method_table_rows(result, current)[-1], rows[0])

    def test_legacy_values_and_old_logger_adapter(self):
        row = item('R5', 'Record', 'S5', 'Record version.', 'RECORDED', actual=0)
        del row['method_id']; del row['method_type']; del row['step_id']
        self.assertEqual(method_table_rows({'log_records': [row]}, {})[0][0], 'R5')
        rows = method_table_rows({'log_records': [{'kind': 'step', 'step': 'Legacy action', 'criteria': 'Zero', 'result': 0}]}, {})
        self.assertEqual(rows[0], ('—', 'Legacy', 'Legacy action\nCriteria: Zero', '0'))


class MethodExportTest(unittest.TestCase):
    setUp = fixtures.ReportExportsTest.setUp
    prepare = fixtures.ReportExportsTest.prepare

    def test_html_pdf_results_long_table_and_escaping(self):
        self.prepare()
        records = [item('S1', 'Step', 'S1', 'Send GET /redfish/v1/.', 'COMPLETED', actual='HTTP 200'),
                   item('C1', 'Checkpoint', 'S1', 'Verify HTTP status is 200.', 'PASS', expected=200, actual=200),
                   item('S2', 'Step', 'S2', 'Parse the response body as JSON.', 'COMPLETED'),
                   item('C2a', 'Checkpoint', 'S2', 'Verify that the response body can be parsed as JSON.', 'PASS'),
                   item('R5', 'Record', 'S5', 'Record RedfishVersion.', 'RECORDED', actual='1.20.0')]
        from models import TaskTestCase
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            row.executed_at = '2026-11-12T00:00:00Z'
            row.result_json = json.dumps({'report_definition': {'description': 'Verify the Redfish Service Root.'}, 'log_records': records})
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-1').one()
            row.result_json = json.dumps({'log_records': [item(f'C3{i}', 'Checkpoint', 'S3', 'Check <escaped> & 中文 ' + str(i), 'FAIL', reason='response <script> & mismatch') for i in range(60)]})
            session.commit()
        responses = {}
        for fmt in ('html', 'pdf'):
            response = self.client.post('/api/projects/project/reports?format='+fmt, json={'task_ids': ['task1']})
            self.assertEqual(response.status_code, 200, response.get_json(silent=True))
            responses[fmt] = response.data
        with zipfile.ZipFile(io.BytesIO(responses['html'])) as archive:
            html = archive.read('BMC_Report.html').decode()
            self.assertIn('Test Steps &amp; Results', html)
            self.assertIn('Source: S2', html)
            self.assertIn('Actual: 1.20.0', html)
            self.assertIn('&lt;script&gt;', html)
            self.assertNotIn('response <script>', html)
            target = os.environ.get('BMC_REPORT_QA_DIR')
            if target:
                out = Path(target)/'methods-fixture'; out.mkdir(exist_ok=True)
                archive.extractall(out)
        reader = pypdf.PdfReader(io.BytesIO(responses['pdf']))
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        for expected in ('Test Steps & Results', 'C2a', 'Source: S2', 'RECORDED', 'Actual: 1.20.0', 'C359', 'response <script> & mismatch'):
            self.assertIn(expected, text)
        self.assertGreater(text.count('Description\nResult'), 1)
        self.assertNotIn('NEVER-EXPORT-THIS-PASSWORD', text)
        self.assertEqual(reader.attachments['test_case-0.log'], [b'winning-pass'])
        if target:
            (Path(target)/'methods.pdf').write_bytes(responses['pdf'])
