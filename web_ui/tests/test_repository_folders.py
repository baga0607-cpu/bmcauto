import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
from models import RepositoryFolder,RepositoryFolderCase,TestCase,PlanFolder

class RepositoryFoldersTest(unittest.TestCase):
 setUp=fixtures.SingleCaseRepositoryTest.setUp
 def folder(self,name='Power'):
  r=self.client.post('/api/repository/folders',json={'name':name});self.assertEqual(r.status_code,201,r.get_json());return r.get_json()
 def move(self,repo,folder):
  return self.client.put('/api/repository/testcases/'+repo['id']+'/folder',json={'folder_id':folder['id'] if folder else None})
 def bulk(self,f,plan='a'):
  return self.client.post('/api/plans/'+plan+'/repository/folders/'+f['id'],json={})
 def test_creation_validation_move_and_import(self):
  f=self.folder()
  for name in ['', 'power','A/B','A\\B']:
   self.assertIn(self.client.post('/api/repository/folders',json={'name':name}).status_code,[400,409])
  self.assertEqual(self.move(self.repository,f).status_code,200)
  self.assertEqual(self.client.get('/api/repository/testcases').get_json()[0]['folder_id'],f['id'])
  self.assertEqual(next(r for r in self.client.get('/api/repository/folders').get_json() if r['id']==f['id'])['count'],1)
  self.assertEqual(self.move(self.repository,None).status_code,200)
  self.assertEqual(self.client.get('/api/repository/testcases').get_json()[0]['folder_id'],'repository-bmc-root')
  source=fixtures.SOURCE.replace('Service entry','Other')
  r=self.client.post('/api/repository/testcases',json={'source':source,'folder_id':f['id']})
  self.assertEqual(r.status_code,201)
  self.assertEqual(next(r for r in self.client.get('/api/repository/folders').get_json() if r['id']==f['id'])['count'],1)
 def test_folder_copied_independently_and_repeated_add_skips(self):
  f=self.folder();self.move(self.repository,f)
  r=self.bulk(f);self.assertEqual(r.status_code,201,r.get_json());data=r.get_json();tc=data['added'][0]
  self.assertEqual(tc['folder_path'],'Power')
  self.assertEqual(tc['source_version'],self.repository['source_version'])
  self.move(self.repository,None)
  definition=self.client.get('/api/plans/a/testcases/'+tc['id']+'/definition').get_json()
  self.assertEqual(definition['source'],fixtures.SOURCE)
  self.move(self.repository,f)
  again=self.bulk(f).get_json();self.assertEqual(again['added'],[]);self.assertEqual(len(again['skipped']),1)
  other=self.bulk(f,'b').get_json()['added'][0];self.assertNotEqual(tc['id'],other['id'])
  self.assertNotEqual(tc['folder_id'],other['folder_id'])
 def test_bulk_failure_rolls_back_rows_folder_and_files(self):
  f=self.folder();self.move(self.repository,f)
  other=self.client.post('/api/repository/testcases',json={'source':fixtures.SOURCE.replace('Service entry','Other'),'folder_id':f['id']}).get_json()
  original=api.sc.script_file;calls=[]
  def fail_second(root,tc):
   calls.append(tc.id if hasattr(tc,'id') else tc.system_id)
   if len(calls)==2:raise RuntimeError('Injected failure')
   return original(root,tc)
  with patch.object(api.sc,'script_file',side_effect=fail_second):self.assertEqual(self.bulk(f).status_code,500)
  with self.Session() as s:
   self.assertEqual(s.query(TestCase).count(),0);self.assertEqual(s.query(PlanFolder).count(),0)
  self.assertEqual(list(self.root.glob('testcase_database/scripts/*/case.py')),[])

 def test_running_plan_rejects_folder_add(self):
  from models import Task
  f=self.folder();self.move(self.repository,f)
  with self.Session() as s:
   s.get(Task,'task1').execution_active=True;s.commit()
  self.assertEqual(self.bulk(f).status_code,409)
  with self.Session() as s:self.assertEqual(s.query(TestCase).count(),0)
