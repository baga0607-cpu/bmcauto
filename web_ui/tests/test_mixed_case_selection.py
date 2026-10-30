import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
from models import TestCase, PlanFolder, TaskTestCase

class MixedSelectionTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    def post(self,url,data,status=201):
        response=self.client.post(url,json=data)
        self.assertEqual(response.status_code,status,response.get_json())
        return response.get_json()
    def case(self,name,folder=None):
        return self.post('/api/repository/testcases',{'source':"TEST_CASE={'name':%r}\ndef execute(client, context=None, preset=None): pass\n"%name,'folder_id':folder})['id']
    def folder(self,name,parent=None,plan=None):
        url='/api/plans/'+plan+'/folders' if plan else '/api/repository/folders'
        return self.post(url,{'name':name,'parent_id':parent})['id']
    def test_import_folder_child_case_overlap_is_deduplicated(self):
        parent=self.folder('Parent');child=self.folder('Child',parent)
        one=self.case('One',child);two=self.case('Two')
        result=self.post('/api/plans/a/import-cases',{'source_type':'repository','kind':'selection','folder_ids':[parent,child,parent],'case_ids':[one,two]})
        self.assertEqual(len(result['added']),2)
        with self.Session() as s:
            self.assertEqual(s.query(TestCase).filter_by(plan_id='a').count(),2)
            self.assertEqual(s.query(PlanFolder).filter_by(plan_id='a').count(),2)
        projects=self.client.get('/api/projects').get_json()['projects'];plan=next(p for project in projects for p in project['plans'] if p['id']=='a')
        folders=plan['folders'];source_folder=next(f for f in folders if f['name']=='Parent')['id']
        ids=[c['id'] for c in plan['testcases']]
        result=self.post('/api/plans/b/import-cases',{'source_type':'plan','source_plan_id':'a','kind':'selection','folder_ids':[source_folder],'case_ids':ids})
        self.assertEqual(len(result['added']),2)
    def test_empty_or_root_selection_rejected_and_bad_case_imports_nothing(self):
        parent=self.folder('Parent');self.case('One',parent)
        for payload in ({'folder_ids':[],'case_ids':[]},{'folder_ids':['repository-bmc-root'],'case_ids':[]},{'folder_ids':[parent],'case_ids':['missing']}):
            response=self.client.post('/api/plans/a/import-cases',json={'source_type':'repository','kind':'selection',**payload})
            self.assertGreaterEqual(response.status_code,400)
            with self.Session() as s:
                self.assertEqual(s.query(TestCase).count(),0);self.assertEqual(s.query(PlanFolder).count(),0)
    def test_plan_mixed_move_preserves_evidence_and_deduplicates(self):
        parent=self.folder('Parent',plan='a');child=self.folder('Child',parent,plan='a');dest=self.folder('Destination',plan='a')
        one=self.case('One');two=self.case('Two')
        added=self.post('/api/plans/a/import-cases',{'source_type':'repository','kind':'case','case_ids':[one,two]})['added']
        ids=[c['id'] for c in added]
        self.post('/api/plans/a/testcases/move',{'testcase_ids':[ids[0]],'folder_id':child},200)
        self.post('/api/tasks/task1/testcases/import',{'testcases':ids},200)
        with self.Session() as s:
            member=s.query(TaskTestCase).filter_by(task_id='task1',testcase_id=ids[0]).one();member.status='Passed';member.log_text='retained';s.commit()
        result=self.post('/api/plans/a/items/move',{'folder_ids':[parent,child],'case_ids':ids,'folder_id':dest},200)
        self.assertEqual(result['moved_folders'],1);self.assertEqual(result['moved_cases'],1)
        with self.Session() as s:
            self.assertEqual(s.get(PlanFolder,parent).parent_id,dest)
            self.assertEqual(s.get(PlanFolder,child).parent_id,parent)
            self.assertEqual(s.get(TestCase,ids[0]).folder_id,child)
            self.assertEqual(s.get(TestCase,ids[1]).folder_id,dest)
            member=s.query(TaskTestCase).filter_by(task_id='task1',testcase_id=ids[0]).one();self.assertEqual((member.status,member.log_text),('Passed','retained'))
    def test_plan_mixed_move_cycles_and_commit_failure_roll_back(self):
        parent=self.folder('Parent',plan='a');child=self.folder('Child',parent,plan='a');dest=self.folder('Destination',plan='a')
        self.post('/api/plans/a/items/move',{'folder_ids':[parent],'folder_id':child},409)
        with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('failure')):
            self.post('/api/plans/a/items/move',{'folder_ids':[parent],'folder_id':dest},500)
        with self.Session() as s:self.assertIsNone(s.get(PlanFolder,parent).parent_id)


    def delete_fixture(self):
        parent=self.folder('Parent',plan='a');child=self.folder('Child',parent,plan='a')
        one=self.case('One');two=self.case('Two')
        added=self.post('/api/plans/a/import-cases',{'source_type':'repository','kind':'case','case_ids':[one,two]})['added'];ids=[c['id'] for c in added]
        self.post('/api/plans/a/testcases/move',{'testcase_ids':[ids[0]],'folder_id':child},200)
        self.post('/api/tasks/task1/testcases/import',{'testcases':ids},200)
        return {'folder_ids':[parent,child],'case_ids':ids}
    def test_delete_mixed_overlap_once_preserves_tasks(self):
        selection=self.delete_fixture()
        response=self.client.post('/api/plans/a/items/delete',json=selection);self.assertEqual(response.status_code,400)
        response=self.client.post('/api/plans/a/items/delete',json={**selection,'confirm':True});self.assertEqual(response.status_code,400)
        result=self.post('/api/plans/a/items/delete',{**selection,'confirm':True,'acknowledgement':True},200)
        self.assertEqual(result['impact']['testcase_count'],2);self.assertEqual(result['impact']['task_testcase_count'],2)
        with self.Session() as s:
            self.assertEqual(s.query(TestCase).count(),0);self.assertEqual(s.query(PlanFolder).count(),0);self.assertEqual(s.query(TaskTestCase).count(),0)
        self.assertEqual(len(self.client.get('/api/projects').get_json()['projects'][0]['plans'][0]['tasks']),2)
    def test_delete_failure_restores_all_files_rows_and_memberships(self):
        selection=self.delete_fixture();before={p:p.read_bytes() for p in self.root.rglob('*.py')}
        with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('delete commit failure')):
            self.post('/api/plans/a/items/delete',{**selection,'confirm':True,'acknowledgement':True},500)
        with self.Session() as s:
            self.assertEqual(s.query(TestCase).count(),2);self.assertEqual(s.query(PlanFolder).count(),2);self.assertEqual(s.query(TaskTestCase).count(),2)
        self.assertEqual({p:p.read_bytes() for p in self.root.rglob('*.py')},before)
    def test_delete_empty_folder_case_only_and_foreign_selection(self):
        empty=self.folder('Empty',plan='a');foreign=self.folder('Foreign',plan='b')
        self.post('/api/plans/a/items/delete',{'folder_ids':[empty,foreign],'confirm':True,'acknowledgement':True},400)
        self.post('/api/plans/a/items/delete',{'folder_ids':[empty],'confirm':True,'acknowledgement':True},200)
        rid=self.case('Only');cid=self.post('/api/plans/a/import-cases',{'source_type':'repository','kind':'case','id':rid})['added'][0]['id']
        self.post('/api/plans/a/items/delete',{'case_ids':[cid],'confirm':True},200)

if __name__=='__main__':unittest.main()
