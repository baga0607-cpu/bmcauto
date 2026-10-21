import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
import case_order as co
from models import TestCase, Task, TaskTestCase, CaseListOrder

class CaseOrderingTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    def request(self,method,url,data=None,status=200):
        response=self.client.open(url,method=method,json=data)
        self.assertEqual(response.status_code,status,response.get_json())
        return response.get_json()
    def repo_case(self,name,folder=None):
        source="TEST_CASE = {'name': %r}\ndef execute(client, context=None, preset=None): pass\n" % name
        return self.request('POST','/api/repository/testcases',{'source':source,'folder_id':folder},201)['id']
    def repo_ids(self,folder):
        return [r['id'] for r in self.request('GET','/api/repository/testcases') if r['folder_id']==folder]
    def plan_ids(self,folder=None):
        projects=self.request('GET','/api/projects')['projects']
        plan=next(p for project in projects for p in project['plans'] if p['id']=='a')
        return [c['id'] for c in plan['testcases'] if c['folder_id']==folder]
    def folder(self,name):
        return self.request('POST','/api/repository/folders',{'name':name},201)['id']
    def import_case(self,rid,**extra):
        return self.request('POST','/api/plans/a/import-cases',{'source_type':'repository','kind':'case','id':rid,**extra},201)['added'][0]['id']
    def test_natural_manual_cross_folder_resort_and_restart(self):
        f=self.folder('Numbered');g=self.folder('Destination')
        ten=self.repo_case('RF-01-10 Z',f);two=self.repo_case('RF-01-2 B',f);one=self.repo_case('RF-01-001 A',f)
        self.assertEqual(self.repo_ids(f),[one,two,ten])
        self.request('PUT',f'/api/repository/testcases/{ten}/folder',{'folder_id':f,'relative_to':one,'insertion':'before'})
        self.assertEqual(self.repo_ids(f),[ten,one,two])
        # A new client/session observes the persisted custom order.
        self.client=api.app.test_client();self.assertEqual(self.repo_ids(f),[ten,one,two])
        other=self.repo_case('RF-01-20',g)
        self.request('PUT',f'/api/repository/testcases/{one}/folder',{'folder_id':g,'relative_to':other,'insertion':'after'})
        self.assertEqual(self.repo_ids(f),[ten,two]);self.assertEqual(self.repo_ids(g),[other,one])
        self.request('POST',f'/api/repository/folders/{g}/resort',{})
        self.assertEqual(self.repo_ids(g),[one,other]);self.assertEqual(self.repo_ids(f),[ten,two])
        zero=self.repo_case('RF-01-0',g);self.assertEqual(self.repo_ids(g),[zero,one,other])
    def test_invalid_moves_atomic_and_batch_order(self):
        f=self.folder('Source');g=self.folder('Target')
        ids=[self.repo_case('TC-'+str(n),f) for n in [1,2,10]];foreign=self.repo_case('TC-3',g)
        for data in [{'folder_id':g,'relative_to':ids[1],'insertion':'before'}, {'folder_id':f,'relative_to':ids[0],'insertion':'after'}, {'folder_id':f,'relative_to':ids[1],'insertion':'bad'}]:
            self.request('PUT',f'/api/repository/testcases/{ids[0]}/folder',data,400)
            self.assertEqual(self.repo_ids(f),ids)
        self.request('POST','/api/repository/batch',{'action':'move','folder_id':g,'case_ids':ids[:2],'relative_to':foreign,'insertion':'after'})
        self.assertEqual(self.repo_ids(g),[foreign,*ids[:2]])
        with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('rollback')):
            self.request('PUT',f'/api/repository/testcases/{ids[2]}/folder',{'folder_id':g,'relative_to':foreign,'insertion':'before'},500)
        self.assertEqual(self.repo_ids(f),[ids[2]])
    def test_plan_root_order_task_evidence_locks_and_import_anchor(self):
        r10=self.repo_case('TC-10');r2=self.repo_case('TC-2');r1=self.repo_case('TC-1')
        ten=self.import_case(r10);two=self.import_case(r2);one=self.import_case(r1)
        self.assertEqual(self.plan_ids(),[one,two,ten])
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=two,status='Passed',log_text='keep evidence'));s.commit()
        self.request('POST','/api/plans/a/testcases/move',{'testcase_ids':[ten],'folder_id':None,'relative_to':one,'insertion':'before'})
        self.assertEqual(self.plan_ids(),[ten,one,two])
        with self.Session() as s:
            membership=s.query(TaskTestCase).one();self.assertEqual(membership.status,'Passed');self.assertEqual(membership.log_text,'keep evidence')
            s.get(Task,'task1').execution_active=True;s.commit()
        self.request('POST','/api/plans/a/testcases/resort',{'folder_id':None},409)
        self.assertEqual(self.plan_ids(),[ten,one,two])
        with self.Session() as s:s.get(Task,'task1').execution_active=False;s.commit()
        self.request('POST','/api/plans/a/testcases/resort',{'folder_id':None})
        self.assertEqual(self.plan_ids(),[one,two,ten])
        r20=self.repo_case('TC-20');twenty=self.import_case(r20,target_folder_id=None,relative_to=two,insertion='before')
        self.assertEqual(self.plan_ids(),[one,twenty,two,ten])
        self.request('POST','/api/plans/a/testcases/move',{'testcase_ids':[one],'folder_id':None,'relative_to':one,'insertion':'after'},400)
        self.assertEqual(self.plan_ids(),[one,twenty,two,ten])
    def test_natural_numbers_versions_and_deleted_ids(self):
        with self.Session() as s:
            records=[dict(id=str(i),name=n,folder_id='x',source_version=v) for i,(n,v) in enumerate([('RF-2-10','v1'),('RF-2-2','v2'),('RF-2-2','v1'),('RF-10-1','v1')])]
            self.assertEqual([r['id'] for r in co.arrange(s,'repository',records)],['2','1','0','3'])
            co.save(s,'repository','x',['deleted','3','0'])
            self.assertEqual([r['id'] for r in co.arrange(s,'repository',records)],['3','0','2','1'])

if __name__=='__main__':unittest.main()
