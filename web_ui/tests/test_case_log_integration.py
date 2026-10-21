import json
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_single_case_repository as fixtures
import app as api


class CaseLogIntegrationTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp
    add_case = fixtures.SingleCaseRepositoryTest.add_case

    def run_source(self, source, body, expected='Passed', sdk_failure=False, existing=None):
        if existing is None:
            response = self.client.post('/api/repository/testcases', json={'source': source})
            self.assertEqual(response.status_code, 201, response.get_json())
            self.repository = response.get_json()
            tc = self.add_case()
            self.client.post('/api/tasks/task1/testcases/import', json={'testcases': [tc['id']]})
        else:
            tc = existing
        token = self.client.post('/api/tasks/task1/execution/start', json={'testcase_ids': [tc['id']]}).get_json()['execution_token']
        sdk = SimpleNamespace(login=lambda **kwargs: None, logout=lambda: None,
                              get=lambda *args, **kwargs: SimpleNamespace(status=200, dict=body))
        if sdk_failure:
            def login(**kwargs): raise RuntimeError('Synthetic login failure')
            sdk.login = login
        class Session:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def get(self, *args, **kwargs):
                if isinstance(body, Exception): raise body
                return SimpleNamespace(status_code=200, headers={'Set-Cookie': 'secret-cookie'}, text=json.dumps(body))
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline only')), \
             patch('requests.Session', Session), patch('redfish.redfish_client', return_value=sdk):
            response = self.client.post('/api/run', json={'task_id': 'task1', 'testcase_id': tc['id'], 'execution_token': token})
            self.assertEqual(response.status_code, 200, response.get_json())
            sid = response.get_json()['session_id']
            worker = api.run_sessions[sid]['thread']
            worker.join(10)
            self.assertFalse(worker.is_alive())
        row = next(r for r in self.client.get('/api/tasks/task1/summary').get_json()['testcases'] if r['id'] == tc['id'])
        self.assertEqual(row['status'], expected)
        self.assertEqual(row['log_text'].count('Final result'), 1)
        records = row['result']['log_records']
        files = row['result']['log_files']
        self.assertIn('Task 1__', files['test'])
        self.assertEqual(row['api_log_text'], '')
        self.assertEqual(set(files), {'test'})
        # Persisted evidence adds the existing execution summary after the raw log.
        disk_execution = (self.root / 'logs' / files['test']).read_text(encoding='utf-8')
        self.assertEqual(row['log_text'].partition('\n=== Current execution details ===')[0], disk_execution)
        response = self.client.get(f"/api/tasks/task1/testcases/{tc['id']}/logs")
        self.assertEqual(response.status_code, 200)
        current = response.get_json()
        for key in ('log_text', 'api_log_text'):
            self.assertEqual(current[key], row[key])
        self.assertEqual(current['result']['log_files'], files)
        self.assertEqual(records[-1]['kind'], 'finish')
        live = [e['text'] for e in api.run_sessions[sid]['log_history'] if 'log_record' in e]
        for block in live: self.assertIn(block, row['log_text'])
        self.assertNotIn('secret-cookie', row['log_text'])
        self.assertNotIn('secret-cookie', row['api_log_text'])
        self.assertNotIn('secret-cookie', json.dumps(records))
        self.client.post('/api/tasks/task1/execution/finish', json={'execution_token': token})
        api.run_sessions.pop(sid, None)
        return row

    def test_three_rf_cases_persist_sections_http_checks_and_raw_body(self):
        root = Path(__file__).resolve().parents[3] / 'testcases/redfish'
        bodies = [dict(v1='/redfish/v1/'), {'@odata.type': '#ServiceRoot.v1_0_0.ServiceRoot', '@odata.id': '/redfish/v1/'},
                  {'@odata.context': '/redfish/v1/$metadata', 'value': [{'name': 'Systems', 'url': '/redfish/v1/Systems'}]}]
        for number, body in enumerate(bodies, 1):
            with self.subTest(case=number):
                source = next(root.glob(f'rf_01_00{number}_*.py')).read_text(encoding='utf-8')
                row = self.run_source(source, body)
                records = row['result']['log_records']
                self.assertTrue({'section', 'http', 'check', 'finish'} <= {r['kind'] for r in records})
                self.assertEqual(records[-1]['status'], 'Pass')
                self.assertEqual(next(r['body'] for r in records if r['kind'] == 'http'), json.dumps(body))
                self.assertIn('HTTP evidence #1', row['log_text'])
                self.assertIn('\n  "', row['log_text'])
                if number == 3:
                    from report_generator import generate_task_pdf_report
                    from pypdf import PdfReader
                    pdf = self.root / 'log-report.pdf'
                    generate_task_pdf_report('task1', str(pdf), db_path=str(self.root / 'test.db'))
                    attachments = PdfReader(str(pdf)).attachments
                    self.assertIn(row['result']['log_files']['test'], attachments)

    def test_same_task_case_rerun_keeps_previous_disk_evidence(self):
        source = next((Path(__file__).resolve().parents[3] / 'testcases/redfish').glob('rf_01_001_*.py')).read_text(encoding='utf-8')
        first = self.run_source(source, dict(v1='/redfish/v1/'))
        old = {name: (self.root / 'logs' / name).read_bytes() for name in first['result']['log_files'].values()}
        second = self.run_source(source, {}, expected='Failed', existing=first)
        self.assertTrue(set(old).isdisjoint(second['result']['log_files'].values()))
        for name, content in old.items():
            self.assertEqual((self.root / 'logs' / name).read_bytes(), content)
        self.assertEqual(len(list((self.root / 'logs').glob('*.log'))), 2)
        from report_generator import generate_task_pdf_report
        from pypdf import PdfReader
        pdf = self.root / 'rerun-log-report.pdf'
        generate_task_pdf_report('task1', str(pdf), db_path=str(self.root / 'test.db'))
        attachments = PdfReader(str(pdf)).attachments
        self.assertEqual(set(attachments), set(second['result']['log_files'].values()))
        self.assertTrue(set(old).isdisjoint(attachments))
        for kind, key in [('test', 'log_text')]:
            name = second['result']['log_files'][kind]
            self.assertEqual(attachments[name], [second[key].encode('utf-8')])
            embedded = attachments[name][0].decode('utf-8')
            if kind == 'test':
                embedded = embedded.partition('\n=== Current execution details ===')[0]
            self.assertEqual(embedded, (self.root / 'logs' / name).read_text(encoding='utf-8'))

    def test_platform_english_preserves_source_and_device_chinese(self):
        source = "TEST_CASE = {'name': '中文測項', 'parameters': {}}\ndef execute(client, context=None, preset=None):\n    print('測項原文')\n    client.get('/redfish/v1/')\n"
        row = self.run_source(source, {'設備回應': '保留原文'})
        self.assertIn('測項原文', row['log_text'])
        self.assertIn('設備回應', row['log_text'])
        self.assertIn('保留原文', row['log_text'])
        self.assertIn('中文測項', row['log_text'])
        self.assertIn('Final result', row['log_text'])
        from report_generator import generate_task_pdf_report
        from pypdf import PdfReader
        pdf = self.root / 'original-language.pdf'
        generate_task_pdf_report('task1', str(pdf), db_path=str(self.root / 'test.db'))
        attachments = PdfReader(str(pdf)).attachments
        self.assertEqual(attachments[row['result']['log_files']['test']], [row['log_text'].encode('utf-8')])

    def test_sdk_proxy_body_is_in_the_single_test_log(self):
        source = "TEST_CASE = {'name': 'SDK proxy', 'parameters': {}}\ndef execute(client, context=None, preset=None): client.get('/redfish/v1/')\n"
        row = self.run_source(source, {'unique_protocol_body': 'retained'})
        self.assertIn('unique_protocol_body', row['log_text'])
        self.assertIn('retained', row['log_text'])
        self.assertEqual(len(list((self.root / 'logs').glob('*.log'))), 1)

    def test_old_split_evidence_has_one_complete_pdf_attachment(self):
        source = "TEST_CASE = {'name': 'Legacy log', 'parameters': {}}\ndef execute(client, context=None, preset=None): pass\n"
        row = self.run_source(source, {})
        with api.DbSession() as session:
            saved = session.query(api.TaskTestCase).filter_by(task_id='task1', testcase_id=row['id']).one()
            saved.log_text = 'old execution evidence'
            saved.api_log_text = 'old HTTP-only response'
            saved.result_json = json.dumps({'log_files': {'execution': 'old__result.log', 'api': 'old__http.log'}})
            session.commit()
        current = self.client.get(f"/api/tasks/task1/testcases/{row['id']}/logs").get_json()
        self.assertIn('old execution evidence', current['log_text'])
        self.assertIn('old HTTP-only response', current['log_text'])
        self.assertEqual(current['api_log_text'], '')
        from report_generator import generate_task_pdf_report
        from pypdf import PdfReader
        pdf = self.root / 'legacy-log-report.pdf'
        generate_task_pdf_report('task1', str(pdf), db_path=str(self.root / 'test.db'))
        attachments = PdfReader(str(pdf)).attachments
        self.assertEqual(set(attachments), {'old__test.log'})
        self.assertEqual(attachments['old__test.log'], [current['log_text'].encode('utf-8')])

    def test_fail_error_and_login_failure_have_one_final_result(self):
        source = next((Path(__file__).resolve().parents[3] / 'testcases/redfish').glob('rf_01_001_*.py')).read_text(encoding='utf-8')
        for suffix, body, status, sdk_failure in [('bad', {}, 'Fail', False), ('bug', RuntimeError('Synthetic bug'), 'Error', False), ('login', {}, 'Fail', True)]:
            with self.subTest(suffix=suffix):
                row = self.run_source(source.replace('RF-01-001 Version Discovery Endpoint', 'RF-01-001 ' + suffix), body, 'Failed', sdk_failure)
                self.assertEqual(row['result']['log_records'][-1]['status'], status)

    def test_legacy_print_source_has_buffered_output_and_final_result(self):
        source = """TEST_CASE = {'name': 'Legacy print', 'parameters': {}}
def execute(client, context=None, preset=None):
    print('first', end='')
    print(' line')
    print()
    print('  indented')
    print('tail', end='')
"""
        row = self.run_source(source, {})
        self.assertIn('first line\n\n', row['log_text'])
        self.assertIn(' - INFO -   indented\n', row['log_text'])
        self.assertIn('tail', row['log_text'])
