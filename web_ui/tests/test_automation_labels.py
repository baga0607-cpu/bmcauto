import unittest
import test_single_case_repository as fixtures
import app as api
from unittest.mock import patch

class AutomationLabelsTest(unittest.TestCase):
 setUp=fixtures.SingleCaseRepositoryTest.setUp
 add_case=fixtures.SingleCaseRepositoryTest.add_case
 definition=fixtures.SingleCaseRepositoryTest.definition

 def source(self,mode):
  return "TEST_CASE="+repr({'name':'Classified '+mode,'automation':mode,'parameters':{}})+"\ndef execute(client,context=None,preset=None): pass\n"

 def test_declared_types_and_legacy_are_read_without_execution(self):
  self.assertEqual(api.sc.metadata(fixtures.SOURCE)['automation'],'unclassified')
  for mode in ['automatic','semi_automatic']:
   result=self.client.post('/api/repository/testcases',json={'source':self.source(mode)})
   self.assertEqual(result.status_code,201)
   data=self.client.get('/api/repository/testcases/'+result.get_json()['id']).get_json()
   self.assertEqual(data['metadata']['automation'],mode)
  for value in ['manual','unclassified',None,True]:
   source="TEST_CASE="+repr({'name':'Invalid','automation':value,'parameters':{}})+"\ndef execute(client,context=None,preset=None): pass\n"
   self.assertEqual(self.client.post('/api/repository/testcases',json={'source':source}).status_code,400)

 def test_plan_and_task_preserve_declaration_after_repository_removal(self):
  for mode in ['automatic','semi_automatic']:
   repo=self.client.post('/api/repository/testcases',json={'source':self.source(mode)}).get_json()
   tc=self.client.post('/api/plans/a/repository/testcases',json={'repository_id':repo['id']}).get_json()
   self.client.post('/api/tasks/task1/testcases/import',json={'testcases':[tc['id']]})
   self.assertEqual(self.definition(tc)['metadata']['automation'],mode)
   case=self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]
   self.assertEqual(case['automation'],mode)
   self.client.delete('/api/repository/testcases/'+repo['id'],json={'confirm':True})
   case=self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]
   self.assertEqual(case['automation'],mode)
   plan=self.client.get('/api/projects').get_json()['projects'][0]['plans'][0]
   self.assertEqual(next(c for c in plan['testcases'] if c['id']==tc['id'])['automation'],mode)

 def test_no_plan_switch_and_no_runtime_behavior_inference(self):
  tc=self.add_case();before=self.definition(tc)
  source=fixtures.SOURCE.replace("'name': 'Service entry'","'automation':'automatic', 'name': 'Service entry'")
  response=self.client.put('/api/plans/a/testcases/'+tc['id']+'/definition',json={'source':source,'settings':before['settings'],'settings_revision':before['settings_revision']})
  self.assertEqual(response.status_code,400)
  self.assertEqual(self.definition(tc),before)
  with patch('builtins.input',side_effect=AssertionError('must not execute')):
   source=self.source('automatic')+"\ninput('No scanning or execution during import')\n"
   self.assertEqual(api.sc.metadata(source)['automation'],'automatic')

 def test_equal_clock_ticks_still_import_distinct_generations(self):
  from datetime import datetime,timezone
  with patch.object(api.sc,'datetime') as clock:
   clock.now.return_value=datetime(2030,1,1,tzinfo=timezone.utc)
   first=self.client.post('/api/repository/testcases',json={'source':self.source('automatic')})
   second=self.client.post('/api/repository/testcases',json={'source':self.source('semi_automatic')})
  self.assertEqual(first.status_code,201);self.assertEqual(second.status_code,201)
  self.assertNotEqual(first.get_json()['source_version'],second.get_json()['source_version'])
