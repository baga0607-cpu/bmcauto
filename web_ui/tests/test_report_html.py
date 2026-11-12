import io
import json
import os
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote
from html.parser import HTMLParser
import pypdf
from models import TaskTestCase, TestCase
import test_report_exports as fixtures


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.hrefs=[]; self.feed(text)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.append(unquote(dict(attrs)['href']))


class HTMLReportTest(unittest.TestCase):
    setUp=fixtures.ReportExportsTest.setUp
    prepare=fixtures.ReportExportsTest.prepare

    def test_default_html_package_has_separate_full_logs_and_safe_markup(self):
        self.prepare()
        log='RAW_LOG_ONLY </script><script>alert(1)</script> 中文\n'*100000
        with self.Session() as session:
            row=session.query(TaskTestCase).filter_by(task_id='task1',testcase_id='case-0').one()
            row.log_text=log
            row.executed_at='2026-10-30T07:27:04.323336+00:00'
            row.result_json=json.dumps({'report_definition':{'description':'<img src=x onerror=alert(1)>'},'log_records':[{'kind':'finish','reason':'Recorded reason'}]})
            session.get(TestCase,'case-0').display_name='Case </script><script>alert(1)</script>'
            session.commit()
        response=self.client.post('/api/projects/project/reports',json={'task_ids':['task1']})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.mimetype,'application/zip')
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            html=archive.read('BMC_Report.html').decode()
            self.assertIn('Recorded reason',html)
            self.assertIn('2026/10/30 15:27:04 (UTC+08:00)',html)
            self.assertNotIn('RAW_LOG_ONLY',html)
            self.assertNotIn('<img src=x',html)
            self.assertIn('&lt;img src=x',html)
            self.assertNotIn('log-preview',html)
            self.assertNotIn('<details open',html)
            self.assertLess(len(html),40000)
            self.assertIn(log.encode(),[archive.read(n) for n in archive.namelist() if n.endswith('.log')])
            for href in Links(html).hrefs:
                if href.startswith('#'):
                    self.assertIn(f'id="{href[1:]}"', html)
                    continue
                self.assertIn(href,archive.namelist())
                self.assertTrue(href.startswith('logs/'))
                self.assertNotIn('..',Path(href).parts)
            target=os.environ.get('BMC_REPORT_QA_DIR')
            if target:
                out=Path(target)/'html-fixture';out.mkdir(exist_ok=True)
                archive.extractall(out)

    def test_html_final_reference_matches_pdf_attachments_and_validates_scope(self):
        self.prepare()
        selection={'report_area':[{'kind':'plan','id':'a'}], 'reference_area':[{'kind':'task','id':'task-b'}]}
        pdf=self.client.post('/api/projects/project/reports?format=pdf',json=selection)
        response=self.client.post('/api/projects/project/reports',json=selection)
        self.assertEqual(response.status_code,200)
        expected=[v for values in pypdf.PdfReader(io.BytesIO(pdf.data)).attachments.values() for v in values]
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(sorted(archive.read(n) for n in archive.namelist() if n.endswith('.log')),sorted(expected))
            html=archive.read('BMC_Report.html').decode()
            self.assertIn('No Test log available',html)
            self.assertIn('Final Report',html);self.assertIn('Reference',html)
        self.assertEqual(self.client.post('/api/projects/project/reports',json={'task_ids':['missing']}).status_code,400)
        self.assertEqual(self.client.post('/api/projects/project/reports?format=bad',json=selection).status_code,400)
