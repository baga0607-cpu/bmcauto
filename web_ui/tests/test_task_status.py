import json,unittest
from unittest.mock import patch
import test_task_schedule as schedule
from models import Task,PlanningTask
class TaskStatusTest(unittest.TestCase):
 setUp=schedule.TaskScheduleTest.setUp
 prepare=schedule.TaskScheduleTest.prepare
 def update(self,tid,status,reason='Waiting for review',expected='New',schedule=False):
  data={'expected_task_status':expected,'history':reason}
  if schedule:
   data.update(task_status=status,start_date='2026-10-19',end_date='2026-10-23',expected_start_date='2026-10-19',expected_end_date='2026-10-23')
  else:data['setup']={'task_status':status}
  return self.client.patch('/api/tasks/'+tid+('/schedule' if schedule else ''),json=data)
 def test_both_types_both_entry_points_and_all_statuses(self):
  self.prepare()
  for tid in ['task1','planning']:
   old='New'
   for i,status in enumerate(['On-Going','Complete','Cancel','Pending','New']):
    response=self.update(tid,status,expected=old,schedule=bool(i%2));self.assertEqual(response.status_code,200,response.get_json())
    row=self.client.get('/api/tasks/'+tid+'/history').get_json()['history'][0]
    self.assertEqual(row['history'],f'Status: {old} → {status}\nWaiting for review')
    old=status
 def test_missing_reason_invalid_and_stale_rejected(self):
  self.prepare()
  for tid in ['task1','planning']:
   for route in [False,True]:
    self.assertEqual(self.update(tid,'Pending',reason='',schedule=route).status_code,400)
    self.assertEqual(self.update(tid,'Wrong',schedule=route).status_code,400)
    self.assertEqual(self.update(tid,'Pending',expected='Complete',schedule=route).status_code,409)
   self.assertEqual(self.client.get('/api/tasks/'+tid+'/history').get_json()['history'],[])
 def test_unchanged_status_has_no_history(self):
  self.prepare()
  response=self.client.patch('/api/tasks/planning',json={'setup':{'task_status':'New'},'expected_task_status':'New'})
  self.assertEqual(response.status_code,200)
  self.assertEqual(self.client.get('/api/tasks/planning/history').get_json()['history'],[])
 def test_combined_date_status_and_assignee_history(self):
  self.prepare()
  response=self.client.patch('/api/tasks/planning',json={'setup':{'task_status':'Pending','end_date':'2026-10-28','owner':'David'},'expected_task_status':'New','expected_start_date':'2026-10-19','expected_end_date':'2026-10-23','history':'Waiting for firmware'})
  self.assertEqual(response.status_code,200,response.get_json())
  rows=self.client.get('/api/tasks/planning/history').get_json()['history']
  self.assertEqual(len(rows),3)
  self.assertTrue(any(r['history']=='Status: New → Pending\nWaiting for firmware' for r in rows))
 def test_history_failure_rolls_back_status(self):
  self.prepare()
  with patch('task_management.append_status_history',side_effect=RuntimeError('failed')):
   response=self.update('planning','Pending')
  self.assertGreaterEqual(response.status_code,400)
  with self.Session() as s:self.assertNotIn('task_status',json.loads(s.get(PlanningTask,'planning').task_metadata))
 def test_new_task_starts_new(self):
  for kind,fields in [('Plan',{'project_id':'project'}),('Test',{'plan_id':'a'})]:
   response=self.client.post('/api/tasks',json={'task_type':kind,**fields})
   self.assertEqual(response.status_code,200,response.get_json())
   tid=response.get_json()['task_id']
   with self.Session() as s:
    row=s.get(PlanningTask if kind=='Plan' else Task,tid)
    self.assertEqual(json.loads(row.task_metadata)['task_status'],'New')
   self.assertEqual(self.client.post('/api/tasks',json={'task_type':kind,**fields,'setup':{'task_status':'Complete'}}).status_code,400)
