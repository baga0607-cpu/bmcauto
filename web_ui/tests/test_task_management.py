import json
import unittest
import test_single_case_repository as fixtures
from models import Task, TaskTestCase, TestCase

class TaskManagementTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp
    add_case = fixtures.SingleCaseRepositoryTest.add_case

    def rows(self):
        response=self.client.get('/api/tasks')
        self.assertEqual(response.status_code,200)
        return {t['id']:t for t in response.get_json()['tasks']}

    def test_overview_includes_legacy_unscheduled_tasks_without_connection_secrets(self):
        rows=self.rows()
        self.assertEqual(set(rows),{'task1','task2'})
        self.assertEqual(rows['task1']['project_name'],'Project')
        self.assertEqual(rows['task1']['plan_name'],'Plan A')
        self.assertEqual(rows['task1']['scope_count'],0)
        self.assertEqual(rows['task1']['setup'],{})
        self.assertNotIn('environment_config',rows['task1'])
        self.assertNotIn('password',rows['task1'])

    def test_create_edit_and_clear_dates_preserves_environment_and_other_information(self):
        response=self.client.post('/api/tasks',json={'plan_id':'a','name':'Regression','setup':{'start_date':'2026-10-14','end_date':'2026-10-16','tester':'Alice','firmware':'v1'},'environment_config':{'host':'https://task.invalid'}})
        self.assertEqual(response.status_code,200,response.get_json())
        tid=response.get_json()['id']
        self.assertEqual(self.rows()[tid]['setup']['end_date'],'2026-10-16')
        result=self.client.patch('/api/tasks/'+tid,json={'setup':{'start_date':'2026-10-15','end_date':'2026-10-15','notes':'One-day run'},'history':'Adjust duration','expected_start_date':'2026-10-14','expected_end_date':'2026-10-16'})
        self.assertEqual(result.status_code,200,result.get_json())
        setup=self.rows()[tid]['setup']
        self.assertEqual(setup['tester'],'Alice');self.assertEqual(setup['firmware'],'v1')
        self.assertEqual(setup['notes'],'One-day run')
        self.assertEqual(self.client.get('/api/tasks/'+tid+'/settings').get_json()['host'],'https://task.invalid')
        self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'setup':{'start_date':'','end_date':''},'history':'Clear planned dates','expected_start_date':'2026-10-15','expected_end_date':'2026-10-15'}).status_code,200)
        self.assertEqual(self.rows()[tid]['setup']['start_date'],'')

    def test_invalid_dates_and_names_are_rejected_atomically(self):
        values=[{'start_date':'2026-10-14'}, {'end_date':'2026-10-14'},
                {'start_date':'2026-02-30','end_date':'2026-03-02'},
                {'start_date':'2026-10-15','end_date':'2026-10-14'},
                {'start_date':'14/10/2026','end_date':'15/10/2026'},
                {'start_date':False,'end_date':'2026-10-14'}, {'start_date':False,'end_date':False}]
        for setup in values:
            with self.subTest(setup=setup):
                response=self.client.patch('/api/tasks/task1',json={'setup':setup})
                self.assertEqual(response.status_code,400,response.get_json())
                self.assertEqual(self.rows()['task1']['name'],'Task 1')
        self.assertEqual(self.client.post('/api/tasks',json={'task_type':'Other','plan_id':'a'}).status_code,400)
        self.assertEqual(len(self.rows()),2)

    def test_delete_only_task_scope_preserves_plan_cases_and_peer_evidence(self):
        tc=self.add_case()
        with self.Session() as s:
            for tid in ['task1','task2']:
                s.add(TaskTestCase(task_id=tid,testcase_id=tc['id'],status='Passed',result_json='{"kept":true}',log_text='retained peer evidence'))
            s.commit()
        self.assertEqual(self.rows()['task1']['scope_count'],1)
        self.assertEqual(self.client.delete('/api/tasks/task1').status_code,200)
        with self.Session() as s:
            self.assertIsNone(s.get(Task,'task1'));self.assertIsNotNone(s.get(TestCase,tc['id']))
            rows=s.query(TaskTestCase).all();self.assertEqual(len(rows),1)
            self.assertEqual(rows[0].task_id,'task2');self.assertEqual(rows[0].log_text,'retained peer evidence')

    def test_active_plan_locks_management_and_plan_cannot_be_reassigned(self):
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'plan_id':'b'}).status_code,400)
        self.assertEqual(self.rows()['task1']['plan_id'],'a')
        with self.Session() as s:s.get(Task,'task1').execution_active=True;s.commit()
        rows=self.rows();self.assertTrue(rows['task1']['execution_active'])
        self.assertTrue(rows['task1']['locked']);self.assertTrue(rows['task2']['locked'])
        for method,url,data in [('PATCH','/api/tasks/task1',{'name':'Blocked'}),('DELETE','/api/tasks/task1',None),('POST','/api/tasks',{'name':'Blocked','plan_id':'a'}),('PATCH','/api/tasks/task2',{'setup':{'notes':'Blocked'}})]:
            response=self.client.open(url,method=method,json=data)
            self.assertEqual(response.status_code,409,response.get_json())

    def test_bulk_update_cannot_bypass_date_validation(self):
        data={'projects':[{'id':'project','plans':[{'id':'a','tasks':[{'id':'task1','setup':{'start_date':'2026-10-20','end_date':'2026-10-10'}}]}]}]}
        response=self.client.post('/api/projects',json=data)
        self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(self.rows()['task1']['name'],'Task 1')
