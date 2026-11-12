import io
import json
import os
import time
import unittest
from pathlib import Path
import pypdf
from report_case import method_rows, description, firmware, result_summary, execution_date
from case_log import CaseLog
import test_report_exports as export_fixtures


class ReportCaseFieldsTest(unittest.TestCase):
    def test_execution_date_is_readable_taiwan_time(self):
        self.assertEqual(execution_date('2026-10-30T07:27:04.323336+00:00'),'2026/10/30 15:27:04 (UTC+08:00)')
        self.assertEqual(execution_date('2026-10-30T23:59:59Z'),'2026/10/31 07:59:59 (UTC+08:00)')
        self.assertEqual(execution_date('2026-10-30T15:27:04+08:00'),'2026/10/30 15:27:04 (UTC+08:00)')
        self.assertEqual(execution_date(None),'—')
        self.assertIn('timezone not recorded',execution_date('2026-10-30T15:27:04'))
        self.assertEqual(execution_date('unknown'),'unknown')
    def test_explicit_rows_preserve_false_zero_and_missing_fields(self):
        output=io.StringIO();log=CaseLog(output,lambda event:None)
        log.section('Measurements')
        log.step('Read <sensor>', 'Value == 0', 0)
        log.step(None, None, False)
        log.finish('Pass','Done')
        rows=method_rows({'log_records':log.records},{})
        self.assertEqual(rows,[('Read <sensor>','Value == 0','0'),('—','—','False')])
        self.assertNotIn('No check results recorded',output.getvalue())
        before=len(log.records)
        with self.assertRaises(ValueError):log.step('Invalid number','Finite',float('nan'))
        self.assertEqual(len(log.records),before)

    def test_legacy_evidence_uses_its_own_sections_not_static_step_indexes(self):
        result={'log_records':[{'kind':'section','title':'Setup'}, {'kind':'section','title':'Probe'},
                {'kind':'check','label':'Reachable','expected':True,'actual':False,'passed':False}]}
        self.assertEqual(method_rows(result,{'test_method':[{'step':'Different authored method','criteria':'Never guess'}]}),
            [('Setup','—','—'),('Probe','Reachable\nExpected: True','FAIL\nActual: False')])
        self.assertEqual(method_rows({'log_text':'unstructured text'},{}),[('—','—','—')])

    def test_declared_method_and_description_remain_empty_without_observation(self):
        meta={'description':'Current','test_method':[{'step_1':'Inspect','criteria':'Expected state'}]}
        self.assertEqual(method_rows({},meta),[('Inspect','Expected state','—')])
        self.assertEqual(description({'report_definition':{'description':'At execution'}},meta),'At execution')
        self.assertEqual(description({'report_definition':{'description':None}},meta),'—')
        self.assertEqual(firmware({'fw_package':[{'component':'BL','version':'v1'},{'component':'1BMC','version':''}]}),'BL: v1\n1BMC: —')


class WorksheetReportTest(unittest.TestCase):
    setUp=export_fixtures.ReportExportsTest.setUp
    prepare=export_fixtures.ReportExportsTest.prepare
    export=export_fixtures.ReportExportsTest.export
    def test_worksheet_pdf_uses_matrix_winner_context_and_exact_rows(self):
        self.prepare()
        with self.Session() as s:
            from models import Task,TaskTestCase
            s.get(Task,'task1').task_metadata=json.dumps({'owner':'Engineer One','fw_package':[{'component':'1BMC','version':'1.0'}]})
            s.get(Task,'task2').task_metadata=json.dumps({'owner':'Engineer Two','fw_package':[{'component':'1BMC','version':'2.0'}]})
            for task,index,result in [('task1',0,'ZERO observed'),('task2',1,'FAILED observation')]:
                row=s.query(TaskTestCase).filter_by(task_id=task,testcase_id='case-'+str(index)).one()
                row.result_json=json.dumps({'report_definition':{'description':'Description at execution <safe>'},'log_records':[
                    {'kind':'step','step':'Send request <root>','criteria':'Exactly zero & healthy','result':result}, {'kind':'finish','reason':result}]})
            s.commit()
        response=self.export(plan_ids=['a']);self.assertEqual(response.status_code,200,response.get_json(silent=True))
        reader=pypdf.PdfReader(io.BytesIO(response.data));text=' '.join(p.extract_text() or '' for p in reader.pages)
        text=text[text.index('Test Suite :'):]
        first=text[text.index('Case <0>'):text.index('Case <1>')]
        second=text[text.index('Case <1>'):text.index('Case <2>')]
        for label in ['Test Data','Description','Result Summary','Log','Test Information','Task Name','FW Package','DUT Configuration','Tester','Execution Time']:
            self.assertIn(label,text)
        for value in ['Task One','Engineer One','1BMC: 1.0','ZERO observed','Description at execution <safe>']:self.assertIn(value,first)
        for value in ['Task Two','Engineer Two','1BMC: 2.0','FAILED observation']:self.assertIn(value,second)
        self.assertNotIn('Engineer Two',first);self.assertNotIn('Engineer One',second)
        self.assertNotIn('HTTP response code shall',text);self.assertNotIn('Reserved for future',text)
        self.assertNotIn('DUT Model',text)
        self.assertIn('—',text)
        target=os.environ.get('BMC_REPORT_QA_DIR')
        if target:(Path(target)/'worksheet-final.pdf').write_bytes(response.data)

    def test_large_step_results_are_excerpted_with_full_log_attachment(self):
        self.prepare()
        from models import TaskTestCase
        evidence = ('RAW_STEP_EVIDENCE 中文 <&>\n' * 100000) + 'COMPLETE_END'
        with self.Session() as s:
            row=s.query(TaskTestCase).filter_by(task_id='task1',testcase_id='case-0').one()
            row.log_text=evidence
            row.result_json=json.dumps({'report_definition':{'description':'中文說明'},'log_records':[
                {'kind':'step','step':'讀取系統','criteria':'狀態正確','result':evidence},
                {'kind':'finish','reason':'Explicit final reason <&> 中文 '+('x'*2000)}]})
            s.commit()
        start=time.perf_counter()
        response=self.export(task_ids=['task1'])
        self.assertLess(time.perf_counter()-start,10)
        self.assertEqual(response.status_code,200,response.get_json(silent=True))
        reader=pypdf.PdfReader(io.BytesIO(response.data));text=' '.join(p.extract_text() or '' for p in reader.pages)
        self.assertNotIn('Detail Test Method',text)
        self.assertIn('RAW_STEP_EVIDENCE',text)
        self.assertNotIn('COMPLETE_END',text)
        self.assertIn('Test Steps & Results',text)
        self.assertIn('Explicit final reason <&> 中文',text)
        self.assertIn('Excerpt',text)
        self.assertIn('中文說明',text)
        self.assertLess(len(reader.pages),10)
        self.assertEqual(reader.attachments['test_case-0.log'],[evidence.encode('utf-8')])
        target=os.environ.get('BMC_REPORT_QA_DIR')
        if target:(Path(target)/'compact-large.pdf').write_bytes(response.data)

    def test_summary_uses_final_reason_or_manual_reason_without_guessing(self):
        result={'log_records':[{'kind':'step','result':'Not a final reason'},
            {'kind':'finish','reason':'Recorded final reason'}]}
        self.assertEqual(result_summary(result),'Recorded final reason')
        self.assertEqual(result_summary(result,{'reason':'Operator decision'}),'Manual result: Operator decision')
        self.assertIn('No recorded summary',result_summary(result,{'reason':''}))
        self.assertIn('No recorded summary',result_summary({'log_records':[{'kind':'step','result':'No inference'}]}))
        self.assertLessEqual(len(result_summary({'reason':'x'*2000000})),600)
