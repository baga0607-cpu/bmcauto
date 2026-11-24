import io
import json
import os
import time
import unittest
from pathlib import Path
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


    def test_summary_uses_final_reason_or_manual_reason_without_guessing(self):
        result={'log_records':[{'kind':'step','result':'Not a final reason'},
            {'kind':'finish','reason':'Recorded final reason'}]}
        self.assertEqual(result_summary(result),'Recorded final reason')
        self.assertEqual(result_summary(result,{'reason':'Operator decision'}),'Manual result: Operator decision')
        self.assertIn('No recorded summary',result_summary(result,{'reason':''}))
        self.assertIn('No recorded summary',result_summary({'log_records':[{'kind':'step','result':'No inference'}]}))
        self.assertLessEqual(len(result_summary({'reason':'x'*2000000})),600)
