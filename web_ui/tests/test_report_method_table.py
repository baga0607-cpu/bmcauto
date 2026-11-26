import io
import json
import os
import re
import unittest
import zipfile
from pathlib import Path

from report_case import method_table_rows
import test_report_exports as fixtures


def item(index, kind, number, text, status=None, **values):
    row = {'kind': 'step', 'method_index': index, 'method_type': kind,
           'step_number': number, 'step': text}
    if status:
        row['result'] = {'method_index': index, 'type': kind, 'step_number': number,
                         'status': status, **values}
    return row


class MethodTableTest(unittest.TestCase):
    def test_revisited_actions_share_rows_and_keep_each_outcome(self):
        from report_html import legacy_method_body

        records = [item(step, 'Action', step, f'Action {step}', 'COMPLETED',
                        actual=f'file-{index}-step-{step}')
                   for index in range(3) for step in (3, 4)]
        body = legacy_method_body({'log_records': records}, {})
        for step in (3, 4):
            self.assertEqual(body.count(f'Step {step} | Action'), 1)
            self.assertEqual(body.count(f'Step {step} | Outcome'), 1)
            for index in range(3):
                self.assertIn(f'file-{index}-step-{step}', body)

    def test_grouped_conditional_judgements_use_conditional_color(self):
        template = Path(__file__).resolve().parents[1] / 'templates' / 'standalone_report.html'
        css = template.read_text(encoding='utf-8')
        for selector in ('.judgement-text[data-judgement="conditional"]',
                         '[data-judgement="conditional"]>.judgement-text'):
            self.assertRegex(css, re.escape(selector) + r'[^{}]*\{color:#f18c43')

    def test_mixed_schema_dialects_show_one_conditional_verdict(self):
        from report_html import snapshot_method_body

        key = 'recommended_json_schema_dialect'
        methods = [{'step_number': 4, 'step': 'Parse schema', 'checkpoints': {
            'schema_document_recognition': {'expected': 'Recognized structure'},
            key: {'expected': 'Check dialect'},
        }}]
        event = {'event': 'checkpoint_result', 'step_number': 4, 'checkpoint_id': key}
        events = [dict(event, judgement='PASS', actual={'uri': '/preferred.json'}),
                  dict(event, judgement='C-PASS', actual={'uri': '/alternate.json'},
                       note='Alternate dialect accepted')]
        row = snapshot_method_body(methods, events).split('Step 4 | Checkpoint B')[1]
        summary, conditional, other = row.split('<details')
        self.assertIn('>C-PASS</div>', summary)
        self.assertIn('Conditional items', conditional)
        self.assertIn('/alternate.json', conditional)
        self.assertIn('Alternate dialect accepted', conditional)
        self.assertIn('Other items', other)
        self.assertIn('/preferred.json', other)
        self.assertNotIn('PASS', conditional + other)

    def test_results_and_judgements_are_separate(self):
        records = [item(0, 'Action', 2, 'Parse JSON.', 'FAILED', reason='Invalid JSON'),
                   item(1, 'Checkpoint', 2, 'Verify JSON.', 'FAIL', expected=True, actual=False),
                   item(2, 'Checkpoint', 2, 'Verify object.', 'NOT_EVALUATED', reason='Parsing failed'),
                   item(3, 'Record', 5, 'Record version.', 'RECORDED', actual=None)]
        rows = method_table_rows({'log_records': records}, {})
        self.assertEqual(rows[0], ('2', 'Action', 'Parse JSON.', 'Reason: Invalid JSON', 'FAILED'))
        self.assertEqual(rows[1], ('', 'Checkpoint', 'Verify JSON.', 'Expected: True\nActual: False', 'FAIL'))
        self.assertEqual(rows[2][4], 'Skip')
        self.assertNotIn('NOT_EVALUATED', rows[2][3])
        self.assertEqual(rows[3], ('', 'Record', 'Record version.', 'Actual: null', 'COMPLETED'))
        for value, rendered in ((0, '0'), (False, 'False'), ('', '""'), ('Not present', 'Not present')):
            records[-1]['result']['actual'] = value
            row = method_table_rows({'log_records': records}, {})[-1]
            self.assertEqual(row[3], 'Actual: '+rendered)
            self.assertEqual(row[4], 'COMPLETED')
        records[-1]['result'].update(status='NOT_RECORDED', actual=None, reason='No response')
        row = method_table_rows({'log_records': records}, {})[-1]
        self.assertEqual(row[3], 'Reason: No response')
        self.assertEqual(row[4], 'Skip')

    def test_saved_definition_orders_partial_results_without_inference(self):
        methods = [{'step_number': 1, 'type': 'Command', 'step': 'Send request'},
                   {'step_number': 1, 'type': 'Checkpoint', 'step': 'Verify response'},
                   {'step_number': 1, 'type': 'Checkpoint', 'step': 'Verify headers'}]
        current = {'test_method': [{'step_number': 99, 'type': 'Action', 'step': 'Changed source'}]}
        result = {'report_definition': {'test_method': methods}, 'log_records': [item(2, 'Checkpoint', 1, 'Verify headers', 'PASS')]}
        rows = method_table_rows(result, current)
        self.assertEqual(rows[0], ('1', 'Command', 'Send request', 'No recorded result', '—'))
        self.assertEqual(rows[1], ('', 'Checkpoint', 'Verify response', 'No recorded result', '—'))
        from report_html import method_row_html
        html_rows = [method_row_html(row) for row in method_table_rows(result, current, number_subitems=True)]
        self.assertIn('<td>1a</td><td>Verify response</td><td class="result-text"></td>', html_rows[1])
        self.assertIn('<td>1b</td>', html_rows[2])
        self.assertEqual(rows[2][4], 'PASS')
        self.assertNotIn('Changed source', str(rows))
        self.assertEqual(method_table_rows({'report_definition': {}}, current)[0][2], 'No test steps recorded')
        result['log_records'].append({'kind': 'step', 'step': 'Legacy', 'result': True})
        self.assertEqual(method_table_rows(result, current)[-1][3], 'True')

    def test_snapshot_matches_by_step_and_id_and_keeps_full_observations(self):
        from report_html import snapshot_method_body
        methods = [{'step_number': 2, 'step': 'Read', 'checkpoints': {
            'missing': {'expected': 'No evidence'}, 'links': {'expected': 'Links are valid'},
            'optional': {'expected': 'Optional'}, 'blocked': {'expected': 'Dependent'}}}]
        events = [
            {'event': 'checkpoint_result', 'step_number': 1, 'checkpoint_id': 'missing', 'judgement': 'PASS'},
            {'event': 'step_observation', 'step_number': 2, 'actual': False},
            {'event': 'step_result', 'step_number': 2, 'status': 'COMPLETED'}]
        for key, status, data in [('links', 'FAIL', {'actual': 'x' * 1500 + '<END>'}),
                                  ('links', 'PASS', {'actual': 0}),
                                  ('optional', 'Skip', {'reason': 'Optional endpoint absent'}),
                                  ('blocked', 'NOT_EVALUATED', {'reason': 'No response'})]:
            events.append(dict(event='checkpoint_result', step_number=2, checkpoint_id=key,
                               judgement=status, **data))
        html = snapshot_method_body(methods, events)
        self.assertEqual(html.count('<td>Step 2 | Checkpoint B</td>'), 1)
        self.assertNotIn('>PASS</span>', html)
        self.assertNotIn('>FAIL</span>', html)
        for text in ('No evidence</td><td class="result-text"></td>', 'Actual: false', 'Actual: 0',
                     'x' * 1500 + '&lt;END&gt;', 'data-judgement="fail">FAIL</div>', 'Fail items: <span>Detail</span>', 'Other items: <span>Detail</span>', '>Skip</span>Reason: Optional',
                     '>Not executed</span>Reason: No response'):
            self.assertIn(text, html)

    def test_old_ids_are_read_without_rewriting_or_displaying_them(self):
        records = [{'kind': 'step', 'method_id': 'S1', 'method_type': 'Step', 'step_id': 'S1',
                    'step': 'S1 | Step | Send request', 'result': {'status': 'COMPLETED'}},
                   {'kind': 'step', 'step': 'R5 | Record | Version',
                    'result': {'id': 'R5', 'type': 'Record', 'step_id': 'S5', 'status': 'RECORDED', 'actual': 0}}]
        before = json.dumps(records)
        rows = method_table_rows({'log_records': records}, {})
        self.assertEqual(rows[0][:3], ('1', 'Action', 'Send request'))
        self.assertEqual(rows[1], ('', 'Record', 'Version', 'Actual: 0', 'COMPLETED'))
        self.assertEqual(json.dumps(records), before)
        rows = method_table_rows({'log_records': [{'kind': 'step', 'step': 'Legacy action', 'criteria': 'Zero', 'result': 0}]}, {})
        self.assertEqual(rows[0], ('1', 'Action', 'Legacy action\nCriteria: Zero', '0', '—'))
        rows = method_table_rows({'log_records': [{'kind': 'section', 'title': 'Probe'},
                {'kind': 'check', 'label': 'Reachable', 'passed': False, 'expected': True, 'actual': False}]}, {})
        self.assertEqual(rows[-1], ('', 'Checkpoint', 'Reachable', 'Expected: True\nActual: False', 'FAIL'))


class MethodExportTest(unittest.TestCase):
    setUp = fixtures.ReportExportsTest.setUp
    prepare = fixtures.ReportExportsTest.prepare

    def test_html_results_long_table_and_escaping(self):
        self.prepare()
        from test_rf01_method_items import MethodItemsTest, response, GOOD, CASES
        _, context, log, _ = MethodItemsTest().run_case(1, [response(dict(GOOD[1], RedfishVersion='1.20.0'))])
        records = context['log'].records
        from models import TaskTestCase
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            row.executed_at = '2026-11-12T00:00:00Z'
            row.log_text = log
            row.result_json = json.dumps({'report_definition': CASES[1].TEST_CASE, 'log_records': records})
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-1').one()
            row.result_json = json.dumps({'log_records': [item(i, 'Checkpoint', 3, 'Check <escaped> & 中文 ' + str(i), 'FAIL', reason='response <script> & mismatch') for i in range(60)]})
            session.commit()
        response = self.client.post('/api/projects/project/reports', json={'task_ids': ['task1']})
        self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            html = archive.read('BMC_Report.html').decode()
            self.assertIn('Test Steps &amp; Results', html)
            self.assertNotIn('<th scope="col">Step</th>', html)
            self.assertNotIn('<th scope="col">Judgement</th>', html)
            self.assertNotIn('<th scope="col">Type</th>', html)
            self.assertIn('<td>Step 1 | Checkpoint A</td>', html)
            self.assertNotIn('Source: S2', html)
            self.assertNotIn('C2a', html)
            self.assertNotIn('RECORDED', html)
            self.assertIn('Actual: &quot;1.20.0&quot;', html)
            self.assertIn('&lt;script&gt;', html)
            self.assertNotIn('response <script>', html)
            target = os.environ.get('BMC_REPORT_QA_DIR')
            if target:
                out = Path(target)/'methods-fixture'; out.mkdir(exist_ok=True)
                archive.extractall(out)
