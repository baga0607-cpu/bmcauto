"""CP/Skip contracts with synthetic responses and disposable databases only."""
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import requests
import pypdf
from sqlalchemy import create_engine
from case_log import CaseLog
from result_policy import validate_method
from report_case import method_table_rows
from plan_state import migrate_block_status, save_result, StateError
import test_report_exports as exports
import test_case_log_integration as integration
from models import TaskTestCase, Task

spec = importlib.util.spec_from_file_location('rf008', Path(__file__).resolve().parents[2]/'test_assets/redfish/rf_01_008_openapi_document_endpoint.py')
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)
MESSAGE = 'The URI /redfish/v1/openapi.yaml was not found.'


def execute(status=404, body=None):
    body = {'error': {'message': MESSAGE}} if body is None else body
    response = type('Response', (), {'status_code': status, 'headers': {},
                    'text': body if isinstance(body, str) else json.dumps(body)})()
    output = io.StringIO()
    log = CaseLog(output, lambda event: None)
    context = {'log': log, 'redfish': {'host': 'https://bmc.invalid'}}
    with patch.object(requests.Session, 'get', return_value=response):
        try:
            case.execute(None, context)
        except (case.CaseFailure, RuntimeError):
            if context.get('case_result', {}).get('status') not in ('Fail', 'Error'):
                raise
    result = dict(context['case_result'], log_records=log.records,
                  report_definition=case.TEST_CASE)
    return result, output.getvalue()


class ConditionalCaseTest(unittest.TestCase):
    def test_absent_404_and_400(self):
        for status, body in [(404, None), (400, {'error': {'@Message.ExtendedInfo': [
                {'MessageId': 'Base.1.16.InvalidURI', 'Message': MESSAGE}]}})]:
            result, log = execute(status, body)
            self.assertEqual(result['status'], 'C-PASS')
            rows = method_table_rows(result, {})
            self.assertEqual([r[4] for r in rows], ['COMPLETED', 'C-PASS'] + ['Skip']*7)
            self.assertIn('Note:', rows[1][3])
            self.assertTrue(all('Reason:' in row[3] for row in rows[2:]))
            self.assertIn('Judgement: C-PASS', log)
            self.assertIn('Result: C-PASS', log)
            self.assertNotIn('Accepted as PASS', log)

    def test_400_must_match_same_entry_and_errors_do_not_pass(self):
        for status, body in [(400, {'error': {'@Message.ExtendedInfo': [
                {'MessageId': 'Base.1.16.InvalidURI'}, {'Message': MESSAGE}]}}),
                (404, {'error': {'message': 'Other URI'}}),
                (404, 'not json'), (500, 'server error')]:
            result, _ = execute(status, body)
            self.assertEqual(result['status'], 'Fail')
            self.assertFalse(result['note'])
            self.assertNotIn('C-PASS', [r[4] for r in method_table_rows(result,{})])

    def test_available_document_and_invalid_document(self):
        good = 'openapi: "3.0.0"\ninfo: {}\npaths: {}'
        result, _ = execute(200, good)
        self.assertEqual(result['status'], 'Pass')
        self.assertEqual([r[4] for r in method_table_rows(result,{})],
                         ['COMPLETED','PASS','COMPLETED','PASS','PASS','COMPLETED','PASS','PASS','PASS'])
        for body in ['[broken', '[]', 'openapi: 3\ninfo: {}\npaths: {}']:
            self.assertEqual(execute(200,body)[0]['status'], 'Fail')

    def test_policy_and_legacy_display(self):
        self.assertEqual(validate_method('Record', {'status':'RECORDED','actual':12})['status'], 'COMPLETED')
        for kind, result in [('Command',{'status':'C-PASS','note':'x'}),
                             ('Record',{'status':'PASS'}),
                             ('Checkpoint',{'status':'C-PASS'}),
                             ('Action',{'status':'Skip'})]:
            with self.assertRaises(ValueError): validate_method(kind,result)
        old = {'log_records':[{'kind':'step','step':'Old step','result':{
            'status':'PASS','checks':[{'label':'Old check','passed':True,'actual':404,'note':'Legacy acceptance'}]}}],
            'note':'Unassociated case note'}
        rows = method_table_rows(old,{})
        self.assertTrue(any('Legacy acceptance' in row[3] for row in rows))
        self.assertFalse(any('Unassociated case note' in row[3] for row in rows))
        self.assertNotIn('C-PASS', [r[4] for r in rows])

    def test_cp_migration_from_block_schema_preserves_evidence(self):
        engine = create_engine('sqlite://')
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE task_testcases(id TEXT PRIMARY KEY, status TEXT, log_text TEXT, CONSTRAINT ck_task_status CHECK(status IN ('TBD','Running','Passed','Failed','Block')))")
            conn.exec_driver_sql('CREATE INDEX evidence_idx ON task_testcases(log_text)')
            conn.exec_driver_sql("INSERT INTO task_testcases VALUES ('a','Passed','original')")
            migrate_block_status(conn); migrate_block_status(conn)
            self.assertEqual(tuple(conn.exec_driver_sql('SELECT * FROM task_testcases').one()),('a','Passed','original'))
            conn.exec_driver_sql("UPDATE task_testcases SET status='C-PASS'")
            self.assertEqual(conn.exec_driver_sql('PRAGMA integrity_check').scalar(),'ok')
            self.assertEqual(list(conn.exec_driver_sql('PRAGMA foreign_key_check')),[])
            self.assertTrue(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='evidence_idx'").scalar())
        engine.dispose()


class ConditionalPipelineTest(unittest.TestCase):
    setUp = integration.CaseLogIntegrationTest.setUp
    add_case = integration.CaseLogIntegrationTest.add_case
    run_source = integration.CaseLogIntegrationTest.run_source

    def test_runner_persists_cp_and_requires_note(self):
        source = """TEST_CASE={'name':'CP fixture','parameters':{}}
def execute(client,context=None,preset=None):
    item={'step_number':1,'type':'Checkpoint','step':'Optional endpoint'}
    result=dict(item,method_index=0,status='C-PASS',note='Optional endpoint absent',actual=404)
    context['log'].method_item(item,result)
    context['log'].finish('C-PASS','Accepted absence',note='Optional endpoint absent')
    context['_tc_status']='C-PASS'
"""
        row = self.run_source(source,{},expected='C-PASS')
        self.assertEqual(row['status'],'C-PASS')
        self.assertIn('Note: Optional endpoint absent',row['log_text'])
        endpoint=f"/api/tasks/task1/testcases/{row['id']}/status"
        self.assertEqual(self.client.patch(endpoint,json={'status':'C-PASS','reason':'  '}).status_code,400)
        manual=self.client.patch(endpoint,json={'status':'C-PASS','reason':'Reviewed conditional acceptance'})
        self.assertEqual(manual.status_code,200)
        self.assertEqual(manual.get_json()['log_text'],row['log_text'])
        token=self.client.post('/api/tasks/task1/execution/start',json={'testcase_ids':[row['id']]}).get_json()['execution_token']
        with self.Session() as session:
            for result in [{}, {'note':'acceptance','log_records':[{'kind':'step','result':{'status':'FAIL'}}]}]:
                with self.assertRaises(StateError):
                    save_result(session,'task1',{'id':row['id'],'execution_token':token,'status':'C-PASS','result':result})
                session.rollback()


class ConditionalReportTest(exports.ReportExportsTest):
    def test_cp_preview_export_and_final_winner(self):
        self.prepare()
        result, log = execute()
        with self.Session() as session:
            row=session.query(TaskTestCase).filter_by(task_id='task1',testcase_id='case-0').one()
            row.status='C-PASS'; row.result_json=json.dumps(result); row.log_text=log
            session.commit()
        response=self.client.get('/api/tasks/task1/testcases/case-0/report-preview')
        self.assertEqual(response.status_code,200)
        preview=response.get_json()['html']
        html_response=self.client.post('/api/projects/project/reports?format=html',json={'plan_ids':['a']})
        import zipfile
        with zipfile.ZipFile(io.BytesIO(html_response.data)) as archive:
            html=archive.read('BMC_Report.html').decode()
        for text in [preview,html]:
            self.assertIn('data-status="C-PASS"',text)
            self.assertNotIn('<dt>Note</dt>',text)
            self.assertIn('Note: DUT returned HTTP 404',text)
            self.assertIn('>Skip</td>',text)
        table=lambda text: re.search(r'<table class="method-table">.*?</table>',text,re.S)[0]
        self.assertEqual(table(preview),table(html))
        pdf=self.export(plan_ids=['a'])
        self.assertEqual(pdf.status_code,200)
        extracted='\n'.join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf.data)).pages)
        self.assertIn('C-PASS',extracted); self.assertIn('Skip',extracted)
        target=os.environ.get('BMC_REPORT_QA_DIR')
        if target:
            Path(target,'cp-preview.html').write_text(preview,encoding='utf-8')
            Path(target,'cp-report.pdf').write_bytes(pdf.data)

    def test_legacy_cp_status_and_manual_note_render_as_c_pass(self):
        self.prepare()
        result, log = execute()
        for record in result['log_records']:
            if record.get('status') == 'C-PASS': record['status'] = 'CP'
            if record.get('result',{}).get('status') == 'C-PASS': record['result']['status'] = 'CP'
        with self.Session() as session:
            row=session.query(TaskTestCase).filter_by(task_id='task1',testcase_id='case-0').one()
            row.status='CP'; row.result_json=json.dumps(result); row.log_text=log
            row.manual_override_json=json.dumps({'status':'CP','reason':'Historical conditional acceptance'})
            session.commit()
        response=self.client.get('/api/tasks/task1/testcases/case-0/report-preview')
        self.assertEqual(response.status_code,200)
        html=response.get_json()['html']
        self.assertIn('data-status="C-PASS"',html)
        self.assertNotIn('>CP<',html)
        self.assertNotIn('Manual result: CP',html)
        with self.Session() as session:
            row=session.query(TaskTestCase).filter_by(task_id='task1',testcase_id='case-0').one()
            self.assertEqual(row.status,'CP')
            self.assertEqual(row.log_text,log)
