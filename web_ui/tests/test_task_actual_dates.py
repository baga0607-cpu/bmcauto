import json
import unittest
from unittest.mock import patch
import test_task_schedule as schedule
from models import Task, PlanningTask, TaskTestCase

class ActualDatesTest(unittest.TestCase):
    setUp = schedule.TaskScheduleTest.setUp
    prepare = schedule.TaskScheduleTest.prepare
    add_case = schedule.TaskScheduleTest.add_case

    def update(self, tid, setup, **extra):
        payload = {'setup':setup,'expected_actual_start_date':'','expected_actual_end_date':'','history':'Actual work confirmed'}
        payload.update(extra)
        return self.client.patch('/api/tasks/'+tid,json=payload)

    def test_both_types_roundtrip_partial_complete_and_clear_with_history(self):
        self.prepare()
        for tid in ['task1','planning']:
            response=self.update(tid,{'actual_start_date':'2026-10-20'})
            self.assertEqual(response.status_code,200,response.get_json())
            response=self.update(tid,{'actual_end_date':'2026-10-24'},expected_actual_start_date='2026-10-20')
            self.assertEqual(response.status_code,200,response.get_json())
            rows=self.client.get('/api/tasks').get_json()['tasks']
            setup=next(row['setup'] for row in rows if row['id']==tid)
            self.assertEqual(setup['actual_start_date'],'2026-10-20')
            self.assertEqual(setup['actual_end_date'],'2026-10-24')
            self.assertEqual(setup['start_date'],'2026-10-19')
            self.assertEqual(setup['task_status'],'New')
            self.assertEqual(setup['firmware'],'keep')
            history=self.client.get('/api/tasks/'+tid+'/history').get_json()['history']
            self.assertEqual(len(history),2)
            self.assertIn('Actual dates: 2026-10-20 ~ — → 2026-10-20 ~ 2026-10-24',history[0]['history'])
            response=self.update(tid,{'actual_start_date':'','actual_end_date':''},expected_actual_start_date='2026-10-20',expected_actual_end_date='2026-10-24')
            self.assertEqual(response.status_code,200,response.get_json())

    def test_invalid_dates_missing_history_and_missing_or_stale_expectations(self):
        self.prepare()
        for tid in ['task1','planning']:
            for setup in [{'actual_start_date':'2026-02-30'},{'actual_end_date':False},{'actual_start_date':'2026-10-24','actual_end_date':'2026-10-20'}]:
                self.assertEqual(self.update(tid,setup).status_code,400)
            self.assertEqual(self.update(tid,{'actual_start_date':'2026-10-20'},history='').status_code,400)
            self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'setup':{'actual_start_date':'2026-10-20'},'history':'Missing expectations'}).status_code,409)
            self.assertEqual(self.update(tid,{'actual_start_date':'2026-10-20'}).status_code,200)
            self.assertEqual(self.update(tid,{'actual_end_date':'2026-10-24'}).status_code,409)
            self.assertEqual(len(self.client.get('/api/tasks/'+tid+'/history').get_json()['history']),1)

    def test_history_failure_rolls_back_combined_changes(self):
        original=self.prepare()
        with patch('task_management.append_actual_history',side_effect=RuntimeError('failed')):
            response=self.update('task1',{'actual_start_date':'2026-10-20','owner':'David','task_status':'Complete'},expected_task_status='New')
        self.assertGreaterEqual(response.status_code,400)
        with self.Session() as s:
            self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)
        self.assertEqual(self.client.get('/api/tasks/task1/history').get_json()['history'],[])

    def test_actual_dates_do_not_schedule_task_or_change_evidence(self):
        self.prepare();tc=self.add_case()
        with self.Session() as s:
            task=s.get(Task,'task1');task.task_metadata='{}'
            s.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='Passed',log_text='keep evidence',result_json='{"keep":true}'))
            environment=task.environment_config;s.commit()
        self.assertEqual(self.update('task1',{'actual_start_date':'2026-10-20','actual_end_date':'2026-10-24'}).status_code,200)
        with self.Session() as s:
            task=s.get(Task,'task1');self.assertEqual(json.loads(task.task_metadata)['task_status'],'Not Scheduled')
            self.assertEqual(task.environment_config,environment)
            row=s.query(TaskTestCase).filter_by(task_id='task1').one()
            self.assertEqual(row.log_text,'keep evidence');self.assertEqual(row.status,'Passed')

    def test_active_plan_lock_and_unrelated_edits_preserve_actual_dates(self):
        self.prepare()
        self.assertEqual(self.update('task1',{'actual_start_date':'2026-10-20'}).status_code,200)
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'setup':{'notes':'Edited'}}).status_code,200)
        with self.Session() as s:
            self.assertEqual(json.loads(s.get(Task,'task1').task_metadata)['actual_start_date'],'2026-10-20')
            s.get(Task,'task2').execution_active=True;s.commit()
        self.assertEqual(self.update('task1',{'actual_end_date':'2026-10-24'},expected_actual_start_date='2026-10-20').status_code,409)
        self.assertEqual(self.update('planning',{'actual_start_date':'2026-10-20'}).status_code,200)

    def test_bulk_cannot_bypass_actual_date_history(self):
        self.prepare()
        data={'projects':[{'id':'project','plans':[{'id':'a','tasks':[{'id':'task1','setup':{'actual_start_date':'2026-10-20'}}]}]}]}
        self.assertEqual(self.client.post('/api/projects',json=data).status_code,409)
        with self.Session() as s:self.assertNotIn('actual_start_date',json.loads(s.get(Task,'task1').task_metadata))
