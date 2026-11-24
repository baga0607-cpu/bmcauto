import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
import repository_tree as rt
from models import RepositoryFolder,RepositoryFolderNode,RepositoryFolderCase,TestCase,PlanFolder

class RepositoryTreeTest(unittest.TestCase):
 setUp=fixtures.SingleCaseRepositoryTest.setUp
 def create(self,name,parent=rt.ROOT):
  r=self.client.post('/api/repository/folders',json={'name':name,'parent_id':parent});self.assertEqual(r.status_code,201,r.get_json());return r.get_json()
 def rows(self):return self.client.get('/api/repository/folders').get_json()
 def test_root_migration_and_sibling_names(self):
  root=self.rows()[0];self.assertEqual(root['name'],'BMC');self.assertTrue(root['is_root'])
  a=self.create('A');b=self.create('B');self.create('Same',a['id']);self.create('Same',b['id'])
  self.assertEqual(self.client.post('/api/repository/folders',json={'name':'SAME','parent_id':a['id']}).status_code,409)
  for method,data in [('PATCH',{'name':'Other'}),('DELETE',{'confirm':True})]:
   self.assertEqual(self.client.open('/api/repository/folders/'+rt.ROOT,method=method,json=data).status_code,409)
 def test_reorder_reparent_cycle_and_persist(self):
  a=self.create('A');b=self.create('B');c=self.create('C',a['id'])
  r=self.client.patch('/api/repository/folders/'+b['id'],json={'relative_to':a['id'],'insertion':'before','parent_id':rt.ROOT});self.assertEqual(r.status_code,200,r.get_json())
  self.assertEqual([r['id'] for r in self.rows() if r['parent_id']==rt.ROOT],[b['id'],a['id']])
  self.assertEqual(self.client.patch('/api/repository/folders/'+a['id'],json={'parent_id':c['id']}).status_code,409)
  self.assertEqual(self.client.patch('/api/repository/folders/'+c['id'],json={'parent_id':b['id']}).status_code,200)
  self.assertEqual(next(r for r in self.rows() if r['id']==c['id'])['folder_path'],'BMC/B/C')
 def test_remove_subtree_keeps_sources_in_parent_and_plan_independent(self):
  a=self.create('A');b=self.create('B',a['id']);c=self.create('C',b['id'])
  self.client.put('/api/repository/testcases/'+self.repository['id']+'/folder',json={'folder_id':c['id']})
  r=self.client.post('/api/plans/a/repository/folders/'+a['id'],json={});self.assertEqual(r.status_code,201,r.get_json());tc=r.get_json()['added'][0]
  self.assertEqual(tc['folder_path'],'A/B/C')
  before=self.client.get('/api/plans/a/testcases/'+tc['id']+'/definition').get_json()
  self.assertEqual(self.client.delete('/api/repository/folders/'+b['id'],json={}).status_code,400)
  result=self.client.delete('/api/repository/folders/'+b['id'],json={'confirm':True});self.assertEqual(result.status_code,200,result.get_json());self.assertEqual(result.get_json()['removed_cases'],1)
  self.assertEqual(self.client.get('/api/repository/testcases').get_json(),[])
  self.assertEqual(self.client.get('/api/plans/a/testcases/'+tc['id']+'/definition').get_json(),before)
  self.assertFalse(any(r['id'] in (b['id'],c['id']) for r in self.rows()))
 def test_recursive_plan_delete_counts_all_descendants_and_cleans_files(self):
  a=self.create('A');b=self.create('B',a['id']);c=self.create('C',b['id'])
  self.client.put('/api/repository/testcases/'+self.repository['id']+'/folder',json={'folder_id':c['id']})
  result=self.client.post('/api/plans/a/repository/folders/'+a['id'],json={}).get_json();tc=result['added'][0]
  impact=self.client.get('/api/folders/'+result['folder_id']+'/impact').get_json()
  self.assertEqual(impact['descendant_folder_count'],2);self.assertEqual(impact['testcase_count'],1)
  r=self.client.delete('/api/folders/'+result['folder_id'],json={'confirm':True,'acknowledgement':True});self.assertEqual(r.status_code,200,r.get_json())
  with self.Session() as s:self.assertIsNone(s.get(TestCase,tc['id']));self.assertEqual(s.query(PlanFolder).count(),0)
  self.assertFalse(api.sc.script_file(self.root,type('Case',(),{'script_path':tc['script_path']})()).exists())
 def test_legacy_directory_adoption_idempotent(self):
  with self.Session() as s:
   s.add(RepositoryFolder(id='legacy',name='Legacy',normalized_name='legacy'));s.commit()
  first=self.rows();second=self.rows();self.assertEqual(first,second)
  self.assertEqual(next(r for r in second if r['id']=='legacy')['parent_id'],rt.ROOT)

 def test_batch_move_and_delete_overlap_and_confirm(self):
  a=self.create('A');b=self.create('B',a['id']);target=self.create('Target')
  self.client.put('/api/repository/testcases/'+self.repository['id']+'/folder',json={'folder_id':b['id']})
  data={'folder_ids':[a['id'],b['id']],'case_ids':[self.repository['id']]}
  self.assertEqual(self.client.post('/api/repository/batch',json={**data,'action':'delete'}).status_code,400)
  self.assertEqual(self.client.post('/api/repository/batch',json={**data,'action':'move','folder_id':b['id']}).status_code,409)
  r=self.client.post('/api/repository/batch',json={**data,'action':'move','folder_id':target['id']});self.assertEqual(r.status_code,200,r.get_json());self.assertEqual(r.get_json()['moved_folders'],1)
  r=self.client.post('/api/repository/batch',json={**data,'action':'delete','confirm':True});self.assertEqual(r.status_code,200,r.get_json());self.assertEqual(r.get_json()['removed_cases'],1)
  self.assertEqual(self.client.get('/api/repository/testcases').get_json(),[])
 def test_only_committed_repository_changes_enter_history(self):
  f=self.create('Original')
  history=lambda:self.client.get('/api/repository/history').get_json()
  before=history()
  self.client.post('/api/repository/activity',json={'operation':'Open history'})
  self.client.get('/api/repository/testcases/'+self.repository['id'])
  url='/api/repository/folders/'+f['id']
  self.assertEqual(self.client.patch(url,json={'name':'Original'}).status_code,200)
  self.assertEqual(self.client.patch(url,json={'name':''}).status_code,400)
  self.assertEqual(history(),before)
  self.assertEqual(self.client.patch(url,json={'name':'Renamed'}).status_code,200)
  self.assertEqual(len(history()),len(before)+1)

 def test_identical_replacement_preserves_version_and_history(self):
  url='/api/repository/testcases/'+self.repository['id']
  before=self.client.get(url).get_json()
  history=self.client.get('/api/repository/history').get_json()
  data={'previous_version':before['source_version'],'source':before['source']}
  response=self.client.put(url,json=data)
  self.assertEqual(response.status_code,409)
  self.assertIn('identical',response.get_json()['error'])
  self.assertEqual(self.client.get(url).get_json(),before)
  self.assertEqual(self.client.get('/api/repository/history').get_json(),history)
  self.assertEqual(self.client.put(url,json={**data,'source':data['source']+'\n'}).status_code,200)

 def test_keep_descendant_cases_and_replacement_history(self):
  parent=self.create('Parent');nested=self.create('Child',parent['id'])
  identity=self.repository['id'];url='/api/repository/testcases/'+identity
  self.client.put(url+'/folder',json={'folder_id':nested['id']})
  copied=self.client.post('/api/plans/a/repository/testcases',json={'repository_id':identity}).get_json()['id']
  old=self.client.get(url).get_json()
  data={'source':old['source'].replace('Service entry','Updated entry'),'previous_version':old['source_version']}
  self.assertEqual(self.client.put(url,json=data).status_code,200)
  self.assertEqual(self.client.put(url,json=data).status_code,409)
  result=self.client.post('/api/repository/batch',json={'action':'delete','confirm':True,'keep_cases':True,'folder_ids':[parent['id'],nested['id']]})
  self.assertEqual(result.get_json()['removed_cases'],0)
  case=self.client.get('/api/repository/testcases').get_json()[0]
  self.assertEqual((case['id'],case['folder_id'],case['name']),(identity,rt.ROOT,'Updated entry'))
  plan_case=self.client.get('/api/plans/a/testcases/'+copied+'/definition').get_json()
  self.assertEqual(plan_case['source'],old['source'])
  events=self.client.get('/api/repository/history').get_json()
  replacements=[e for e in events if e['operation']=='replace']
  self.assertEqual(len(replacements),1)
  self.assertIsNone(replacements[0]['operator'])
  self.assertEqual(replacements[0]['changes'][0]['before']['name'],'Service entry')
  self.assertEqual(self.client.delete('/api/repository/history').status_code,405)

 def test_batch_move_collision_rolls_back(self):
  a=self.create('Same');other=self.create('Other');b=self.create('Same',other['id']);target=self.create('Target')
  before=self.rows()
  r=self.client.post('/api/repository/batch',json={'action':'move','folder_ids':[a['id'],b['id']],'folder_id':target['id']})
  self.assertEqual(r.status_code,409);self.assertEqual(self.rows(),before)
