import io
import json
import os
import re
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from models import Task, TaskTestCase
import test_report_exports as fixtures


class ReportPreviewTest(unittest.TestCase):
    setUp = fixtures.ReportExportsTest.setUp
    prepare = fixtures.ReportExportsTest.prepare

    def get_preview(self, task='task1', case='case-0'):
        return self.client.get(f'/api/tasks/{task}/testcases/{case}/report-preview')

    def seed(self):
        self.prepare()
        from test_rf01_method_items import MethodItemsTest, response, GOOD, CASES
        _, context, log, _ = MethodItemsTest().run_case(1, [response(dict(GOOD[1], RedfishVersion='1.20.0'))])
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            row.log_text = log
            row.result_json = json.dumps({'report_definition': CASES[1].TEST_CASE, 'log_records': context['log'].records})
            session.get(Task, 'task1').task_metadata = json.dumps({'owner': 'Preview tester', 'fw_package': [{'component': 'BMC', 'version': '1.0'}]})
            session.commit()

    def test_preview_matches_export_and_reads_only_selected_membership(self):
        self.seed()
        with self.engine.connect() as conn:
            before = list(conn.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id'))
            tasks_before = list(conn.exec_driver_sql('SELECT * FROM tasks ORDER BY id'))
        with patch('report_exports.generate_selection', side_effect=AssertionError('No export for preview')), \
             patch('report_html.test_log_text', side_effect=AssertionError('Do not load full logs')):
            response = self.get_preview()
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers['Cache-Control'])
        html = response.get_json()['html']
        self.assertEqual(html.count('<article '), 1)
        self.assertEqual(html.count('<details open '), 1)
        self.assertNotIn('<dt>Result Summary</dt>', html)
        self.assertNotIn('<dt>Note</dt>', html)
        self.assertIn('<section class="test-data"><h3>Test Data</h3>', html)
        self.assertIn('<section class="test-information"><h3>Test Information</h3>', html)
        for value in ('Command', 'Judgement', 'Actual: 1.20.0', 'Preview tester', 'BMC: 1.0', 'Case &lt;0&gt;'):
            self.assertIn(value, html)
        for value in ('Case &lt;1&gt;', 'Task Two', 'NEVER-EXPORT-THIS-PASSWORD', '<script', 'href="logs/', 'print-report'):
            self.assertNotIn(value, html)
        export = self.client.post('/api/projects/project/reports?format=html', json={'task_ids': ['task1']})
        self.assertEqual(export.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(export.data)) as archive:
            formal = archive.read('BMC_Report.html').decode()
        table = lambda text: re.search(r'<table class="method-table">.*?</table>', text, re.S)[0]
        self.assertEqual(table(html), table(formal))
        with self.engine.connect() as conn:
            self.assertEqual(before, list(conn.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id')))
            self.assertEqual(tasks_before, list(conn.exec_driver_sql('SELECT * FROM tasks ORDER BY id')))
        target = os.environ.get('BMC_REPORT_QA_DIR')
        if target:
            (Path(target)/'preview.html').write_text(html, encoding='utf-8')

    def test_running_manual_and_stale_results_remain_readable(self):
        self.seed()
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            row.status = 'Running'
            row.needs_retest = True
            row.manual_override_json = json.dumps({'status': 'Block', 'reason': 'Operator explanation'})
            session.get(Task, 'task1').execution_active = True
            session.commit()
        response = self.get_preview()
        self.assertEqual(response.status_code, 200)
        html = response.get_json()['html']
        for text in ('Execution in progress', 'Rerun needed', 'Operator explanation', 'data-status="Running"'):
            self.assertIn(text, html)

    def test_empty_results_and_foreign_or_missing_membership(self):
        self.prepare()
        response = self.get_preview(case='case-3')
        self.assertEqual(response.status_code, 200)
        self.assertIn('No recorded result', response.get_json()['html'])
        for task, case in [('missing', 'case-0'), ('task-b', 'case-0'), ('task1', 'missing'), ('task1', 'case-4')]:
            self.assertEqual(self.get_preview(task, case).status_code, 404)

    def test_preview_escapes_payloads_and_omits_large_logs(self):
        self.prepare()
        with self.Session() as session:
            row = session.query(TaskTestCase).filter_by(task_id='task1', testcase_id='case-0').one()
            row.result_json = json.dumps({'report_definition': {'description': '<script>alert(1)</script><img src=https://bad.invalid>'}})
            row.log_text = 'RAW_LOG_MUST_NOT_BE_EMBEDDED\n' * 200000
            session.commit()
        response = self.get_preview()
        self.assertEqual(response.status_code, 200)
        html = response.get_json()['html']
        self.assertNotIn('<script', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('RAW_LOG_MUST_NOT_BE_EMBEDDED', html)
        self.assertLess(len(html), 30000)
