import json
import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
from models import Task, PlanningTask
import task_management as tm

class TaskOwnerTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    def owners(self):
        path=self.root/'owners.json';path.write_text(json.dumps({'owners':['TBD','David','Alice']}),encoding='utf-8')
        context=patch.object(tm,'OWNER_FILE',path);context.start();self.addCleanup(context.stop)
    def test_options_and_default_for_both_task_types(self):
        self.owners()
        self.assertEqual(self.client.get('/api/tasks/options').get_json()['owners'],['TBD','David','Alice'])
        for data in [{'task_type':'Plan','project_id':'project'},{'task_type':'Test','plan_id':'a'}]:
            response=self.client.post('/api/tasks',json=data);self.assertEqual(response.status_code,200,response.get_json())
            tid=response.get_json()['id']
            row=next(t for t in self.client.get('/api/tasks').get_json()['tasks'] if t['id']==tid)
            self.assertEqual(row['setup']['owner'],'TBD')
    def test_selected_owner_roundtrip_and_unrelated_edits_preserve_it(self):
        self.owners()
        for data in [{'task_type':'Plan','project_id':'project'},{'task_type':'Test','plan_id':'a'}]:
            response=self.client.post('/api/tasks',json={**data,'setup':{'owner':'David','notes':'keep'}})
            self.assertEqual(response.status_code,200,response.get_json());tid=response.get_json()['id']
            self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'setup':{'start_date':'2026-10-22','end_date':'2026-10-23'},'history':'Assign dates','expected_start_date':'','expected_end_date':''}).status_code,200)
            row=next(t for t in self.client.get('/api/tasks').get_json()['tasks'] if t['id']==tid)
            self.assertEqual(row['setup']['owner'],'David');self.assertEqual(row['setup']['notes'],'keep')
            self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'setup':{'owner':'Alice'}}).status_code,200)
            row=next(t for t in self.client.get('/api/tasks').get_json()['tasks'] if t['id']==tid)
            self.assertEqual(row['setup']['owner'],'Alice')
    def test_invalid_owner_rejected_without_changing_task(self):
        self.owners()
        for owner in ['Unknown','',None,123,False]:
            response=self.client.patch('/api/tasks/task1',json={'setup':{'owner':owner}})
            self.assertEqual(response.status_code,400,response.get_json())
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata or '{}'),{})
    def test_legacy_unassigned_rows_are_not_rewritten_by_read(self):
        self.owners()
        self.client.get('/api/tasks');self.client.get('/api/tasks/options')
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata or '{}'),{})
    def test_existing_owner_survives_roster_removal(self):
        self.owners()
        with self.Session() as s:s.get(Task,'task1').task_metadata=json.dumps({'owner':'Former Owner'});s.commit()
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'setup':{'owner':'Former Owner','notes':'kept'}}).status_code,200)
        self.assertEqual(self.client.patch('/api/tasks/task2',json={'setup':{'owner':'Former Owner'}}).status_code,400)
