import io
import json
import unittest
import zipfile
import test_single_case_repository as fixtures
from models import Project, ProjectInformation


def workbook(broken=False):
    from xml.sax.saxutils import escape
    def sheet(rows):
        return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join('<row r="%s">'%n+''.join('<c r="%s%s" t="inlineStr"><is><t>%s</t></is></c>'%(col,n,escape(value)) for col,value in row.items())+'</row>' for n,row in enumerate(rows,1))+'</sheetData></worksheet>'
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Device" r:id="r1"/><sheet name="SKU 比較" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/a.xml"/><Relationship Id="r2" Target="worksheets/b.xml"/></Relationships>')
        z.writestr('xl/worksheets/a.xml',sheet([{'A':'Product Requirement — Device (Author: User)'},{'A':'Category','B':'Item','D':'Target Specification'},{'A':'Network'},{'B':'Port','C':'Guide','D':'原文\nYes'},{'B':'Port','D':'No'}]))
        z.writestr('xl/worksheets/b.xml',sheet([{'A':'分類','B':'規格項目','C':'不同','D':'BMC','E':'HWM','F':'備註'},{'A':'Network','B':'Missing' if broken else 'Port','D':'Yes','E':'No','F':'備註'},{'A':'Network','B':'Port','D':'N/A','E':''}]))
    return output.getvalue()

class ProjectImportTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    def upload(self,url,name='Imported',payload=None):
        return self.client.post(url,data={'name':name,'file':(io.BytesIO(payload if payload is not None else workbook()),'requirements.xlsx')})
    def test_preview_create_roundtrip_duplicate_and_original_text(self):
        with self.Session() as s:before=s.query(Project).count()
        preview=self.upload('/api/projects/import/preview')
        self.assertEqual(preview.status_code,200,preview.get_json())
        self.assertEqual(preview.get_json()['skus'],2)
        with self.Session() as s:self.assertEqual(s.query(Project).count(),before)
        result=self.upload('/api/projects/import');self.assertEqual(result.status_code,201,result.get_json())
        doc=self.client.get('/api/projects/'+result.get_json()['id']+'/information').get_json()['document']
        items=doc['categories'][0]['items']
        self.assertEqual(items[0]['target'],'原文\nYes')
        self.assertEqual(items[0]['remarks'],'備註')
        self.assertEqual(items[1]['sku_values'],{'D':'N/A','E':''})
        self.assertTrue(doc['source']['imported_at'])
        self.assertEqual(self.upload('/api/projects/import',name='IMPORTED').status_code,409)
        with self.Session() as s:self.assertEqual(s.query(Project).count(),before+1)
    def test_invalid_upload_does_not_create_project(self):
        with self.Session() as s:before=s.query(Project).count()
        for payload in (b'not a workbook',workbook(True)):
            self.assertEqual(self.upload('/api/projects/import',payload=payload).status_code,400)
        with self.Session() as s:
            self.assertEqual(s.query(Project).count(),before)
            self.assertEqual(s.query(ProjectInformation).count(),0)
