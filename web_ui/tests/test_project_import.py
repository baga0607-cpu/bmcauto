import io
import hashlib
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
    def upload(self,url,name='Imported',payload=None,choices=None,confirmed=True,source_hash=None):
        payload=payload if payload is not None else workbook()
        choices=choices if choices is not None else [{'id':'D','kind':'sku'},{'id':'E','kind':'sku'}]
        return self.client.post(url,data={'name':name,'file':(io.BytesIO(payload),'requirements.xlsx'),
            'classifications':json.dumps(choices),'review_confirmed':str(confirmed).lower(),
            'source_sha256':source_hash if source_hash is not None else hashlib.sha256(payload).hexdigest()})

    def test_preview_create_roundtrip_duplicate_and_original_text(self):
        with self.Session() as s:before=s.query(Project).count()
        preview=self.upload('/api/projects/import/preview')
        self.assertEqual(preview.status_code,200,preview.get_json())
        self.assertEqual(preview.get_json()['skus'],2)
        self.assertEqual(preview.get_json()['columns'],[{'id':'D','name':'BMC'},{'id':'E','name':'HWM'}])
        self.assertEqual(preview.get_json()['specifications'][0]['items'][0]['sku_values'],{'D':'Yes','E':'No'})
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

    def test_split_project_owns_only_its_column_and_no_sku(self):
        choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'project'}]
        response=self.upload('/api/projects/import',choices=choices)
        self.assertEqual(response.status_code,201,response.get_json())
        created=response.get_json()['projects']
        self.assertEqual([(p['name'],p['skus']) for p in created],[('Imported',1),('HWM',0)])
        documents=[self.client.get('/api/projects/'+p['id']+'/information').get_json()['document'] for p in created]
        self.assertEqual(documents[0]['skus'],[{'id':'D','name':'BMC'}])
        self.assertEqual(documents[0]['categories'][0]['items'][0]['sku_values'],{'D':'Yes'})
        independent=documents[1]
        self.assertEqual(independent['skus'],[])
        self.assertEqual(independent['metadata']['product_name'],'HWM')
        items=independent['categories'][0]['items']
        self.assertEqual([i['target'] for i in items],['No',''])
        self.assertTrue(all(i['sku_values']=={} for i in items))
        self.assertEqual(items[0]['remarks'],'備註')
        self.assertTrue(independent['source']['sha256'])
        self.assertEqual(documents[0]['source'],independent['source'])

    def test_all_columns_can_be_independent_projects(self):
        response=self.upload('/api/projects/import',choices=[{'id':'D','kind':'project'},{'id':'E','kind':'project'}])
        self.assertEqual(response.status_code,201,response.get_json())
        self.assertEqual([p['name'] for p in response.get_json()['projects']],['BMC','HWM'])

    def test_unconfirmed_stale_or_incomplete_review_cannot_create(self):
        with self.Session() as session:before=session.query(Project).count()
        invalid=[dict(confirmed=False),dict(source_hash='stale'),
                 dict(choices=[]),dict(choices=[{'id':'D','kind':'sku'}]),
                 dict(choices=[{'id':'D','kind':'sku'},{'id':'D','kind':'project'}]),
                 dict(choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'other'}]),
                 dict(choices=[{'id':'D','kind':'sku'},{'id':'Z','kind':'project'}])]
        for values in invalid:
            with self.subTest(values=values):
                self.assertEqual(self.upload('/api/projects/import',**values).status_code,400)
        with self.Session() as session:
            self.assertEqual(session.query(Project).count(),before)
            self.assertEqual(session.query(ProjectInformation).count(),0)

    def test_existing_independent_project_rejects_whole_batch(self):
        with self.Session() as session:
            session.add(Project(name='hwm'));session.commit()
            before=session.query(Project).count()
        result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'project'}])
        self.assertEqual(result.status_code,409,result.get_json())
        self.assertIn('HWM',result.get_json()['error'])
        with self.Session() as session:
            self.assertEqual(session.query(Project).count(),before)
            self.assertIsNone(session.query(Project).filter_by(name='Imported').first())
            self.assertEqual(session.query(ProjectInformation).count(),0)

    def test_project_names_cannot_collide_within_batch(self):
        result=self.upload('/api/projects/import',name='HWM',choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'project'}])
        self.assertEqual(result.status_code,400,result.get_json())
        with self.Session() as session:self.assertEqual(session.query(ProjectInformation).count(),0)

    def test_failure_writing_second_project_rolls_back_first(self):
        from unittest.mock import patch
        from sqlalchemy.exc import IntegrityError
        real=ProjectInformation
        calls=[]
        def create(**values):
            calls.append(values)
            if len(calls)==2:raise IntegrityError('injected',{},Exception('injected second document failure'))
            return real(**values)
        with self.Session() as session:before=session.query(Project).count()
        with patch('project_information.ProjectInformation',side_effect=create):
            result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'project'}])
        self.assertEqual(result.status_code,409,result.get_json())
        with self.Session() as session:
            self.assertEqual(session.query(Project).count(),before)
            self.assertEqual(session.query(ProjectInformation).count(),0)

    def test_promoted_project_edit_keeps_main_project_specs_independent(self):
        result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'project'}]).get_json()['projects']
        main_id, separate_id=[p['id'] for p in result]
        info=self.client.get('/api/projects/'+separate_id+'/information').get_json()
        info['document']['categories'][0]['items'][0]['target']='Revised independent value'
        response=self.client.put('/api/projects/'+separate_id+'/information',json={'revision':info['revision'],'document':info['document']})
        self.assertEqual(response.status_code,200,response.get_json())
        main=self.client.get('/api/projects/'+main_id+'/information').get_json()['document']
        self.assertEqual(main['categories'][0]['items'][0]['sku_values'],{'D':'Yes'})
        self.assertEqual(main['categories'][0]['items'][0]['target'],'原文\nYes')

    def test_skip_existing_independent_project_preserves_it(self):
        from project_information import blank_information
        with self.Session() as session:
            existing=Project(id='existing-hwm',name='HWM');session.add(existing);session.flush()
            encoded=json.dumps(blank_information())
            session.add(ProjectInformation(project_id=existing.id,document=encoded,revision=5,updated_at='unchanged'))
            session.commit()
        result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'sku'},{'id':'E','kind':'skip'}])
        self.assertEqual(result.status_code,201,result.get_json())
        self.assertEqual([p['name'] for p in result.get_json()['projects']],['Imported'])
        imported=self.client.get('/api/projects/'+result.get_json()['id']+'/information').get_json()['document']
        self.assertEqual(imported['skus'],[{'id':'D','name':'BMC'}])
        self.assertTrue(all(set(i['sku_values'])<= {'D'} for c in imported['categories'] for i in c['items']))
        with self.Session() as session:
            existing=session.get(ProjectInformation,'existing-hwm')
            self.assertEqual((existing.document,existing.revision,existing.updated_at),(encoded,5,'unchanged'))

    def test_skip_main_skus_creates_only_promoted_project_preserving_existing_main(self):
        from project_information import blank_information
        from models import ProjectPlan, Task
        with self.Session() as session:
            session.add(Project(id='existing-main',name='Imported'));session.flush()
            encoded=json.dumps(blank_information())
            session.add(ProjectInformation(project_id='existing-main',document=encoded,revision=7,updated_at='unchanged'))
            session.add(ProjectPlan(id='existing-main-plan',project_id='existing-main',name='Preserved Plan',folders_migrated=True));session.flush()
            session.add(Task(id='existing-main-task',plan_id='existing-main-plan',name='Preserved Task',task_metadata='{"notes":"kept"}'))
            session.commit()
        result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'skip'},{'id':'E','kind':'project'}])
        self.assertEqual(result.status_code,201,result.get_json())
        self.assertEqual([p['name'] for p in result.get_json()['projects']],['HWM'])
        self.assertEqual(result.get_json()['name'],'HWM')
        with self.Session() as session:
            existing=session.get(ProjectInformation,'existing-main')
            self.assertEqual((existing.document,existing.revision,existing.updated_at),(encoded,7,'unchanged'))
            self.assertEqual(session.get(ProjectPlan,'existing-main-plan').project_id,'existing-main')
            self.assertEqual(session.get(Task,'existing-main-task').task_metadata,'{"notes":"kept"}')

    def test_all_skipped_creates_nothing(self):
        with self.Session() as session:before=session.query(Project).count()
        result=self.upload('/api/projects/import',choices=[{'id':'D','kind':'skip'},{'id':'E','kind':'skip'}])
        self.assertEqual(result.status_code,400,result.get_json())
        with self.Session() as session:
            self.assertEqual(session.query(Project).count(),before)
            self.assertEqual(session.query(ProjectInformation).count(),0)
