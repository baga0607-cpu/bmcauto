import json
import unittest
import test_single_case_repository as fixtures
from models import Task,PlanningTask,TaskTestCase,TaskScheduleHistory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

class TaskScheduleTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    add_case=fixtures.SingleCaseRepositoryTest.add_case
    def prepare(self):
        setup={'start_date':'2026-10-19','end_date':'2026-10-23','notes':'Original note','firmware':'keep'}
        with self.Session() as s:
            s.get(Task,'task1').task_metadata=json.dumps(setup)
            s.add(PlanningTask(id='planning',project_id='project',name='Plan-P-001',task_metadata=json.dumps(setup)))
            s.commit()
        return setup
    def change(self,tid='task1',**updates):
        data={'start_date':'2026-10-20','end_date':'2026-10-28','history':'Waiting for firmware','expected_start_date':'2026-10-19','expected_end_date':'2026-10-23'}
        data.update(updates)
        return self.client.patch('/api/tasks/'+tid+'/schedule',json=data)
    def test_both_types_append_immutable_history_preserving_notes(self):
        self.prepare()
        for tid in ['task1','planning']:
            response=self.change(tid);self.assertEqual(response.status_code,200,response.get_json())
            setup=response.get_json()['setup']
            self.assertEqual(setup['start_date'],'2026-10-20');self.assertEqual(setup['end_date'],'2026-10-28')
            self.assertEqual(setup['firmware'],'keep')
            self.assertEqual(setup['notes'],'Original note')
            entries=self.client.get('/api/tasks/'+tid+'/history').get_json()['history']
            self.assertEqual(len(entries),1)
            self.assertEqual(entries[0]['history'],'Waiting for firmware')
            self.assertEqual(entries[0]['previous_start_date'],'2026-10-19')
            self.assertEqual(entries[0]['end_date'],'2026-10-28')
        with self.Session() as s:self.assertEqual(s.get(Task,'task1').name,'Task 1')
    def test_missing_blank_or_invalid_history_rejected_without_date_changes(self):
        original=self.prepare()
        for history in [None,'','  \n ',False,123,'x'*4001]:
            self.assertEqual(self.change(history=history).status_code,400)
            with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)
    def test_invalid_dates_and_noop_roll_back(self):
        original=self.prepare()
        for start,end in [('2026-02-30','2026-03-01'),('2026-10-28','2026-10-20'),('',''),('2026-10-19','2026-10-23')]:
            self.assertEqual(self.change(start_date=start,end_date=end).status_code,400)
            with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)
    def test_stale_dates_cannot_overwrite_new_schedule_or_notes(self):
        self.prepare();self.assertEqual(self.change().status_code,200)
        with self.Session() as s:before=s.get(Task,'task1').task_metadata
        self.assertEqual(self.change(history='stale').status_code,409)
        with self.Session() as s:self.assertEqual(s.get(Task,'task1').task_metadata,before)
    def test_active_plan_locks_test_reschedule_but_planning_task_is_independent(self):
        self.prepare()
        with self.Session() as s:s.get(Task,'task2').execution_active=True;s.commit()
        self.assertEqual(self.change().status_code,409)
        self.assertEqual(self.change('planning').status_code,200)
    def test_result_evidence_and_connections_are_untouched(self):
        self.prepare();tc=self.add_case()
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='Passed',result_json='{"preserved":true}',log_text='keep evidence'))
            environment=s.get(Task,'task1').environment_config;s.commit()
        self.assertEqual(self.change().status_code,200)
        with self.Session() as s:
            row=s.query(TaskTestCase).filter_by(task_id='task1').one()
            self.assertEqual(row.status,'Passed');self.assertEqual(row.log_text,'keep evidence');self.assertEqual(row.result_json,'{"preserved":true}')
            self.assertEqual(s.get(Task,'task1').environment_config,environment)
    def test_missing_task_is_404(self):
        self.assertEqual(self.change('missing').status_code,404)

    def test_history_is_read_only_via_api_and_metadata(self):
        self.prepare();self.assertEqual(self.change().status_code,200)
        original=self.client.get('/api/tasks/task1/history').get_json()['history']
        for method in ['POST','PUT','PATCH','DELETE']:
            response=self.client.open('/api/tasks/task1/history',method=method,json={'history':[]})
            self.assertIn(response.status_code,[404,405])
        for data in [{'history':[]},{'setup':{'history':[]}},{'setup':{'history_list':[]}},{'setup':{'schedule_history':[]}}]:
            self.assertEqual(self.client.patch('/api/tasks/task1',json=data).status_code,400)
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'setup':{'notes':'New ordinary note'}}).status_code,200)
        self.assertEqual(self.client.get('/api/tasks/task1/history').get_json()['history'],original)

    def test_database_rejects_update_and_delete_including_bulk_sql(self):
        self.prepare();self.assertEqual(self.change().status_code,200)
        for statement in ["UPDATE task_schedule_history SET history='tampered'",'DELETE FROM task_schedule_history']:
            with self.Session() as s:
                with self.assertRaises(IntegrityError):s.execute(text(statement));s.commit()
                s.rollback()
        with self.Session() as s:
            self.assertEqual(s.query(TaskScheduleHistory).count(),1)
            self.assertEqual(s.query(TaskScheduleHistory).one().history,'Waiting for firmware')

    def test_history_survives_task_removal_for_both_types(self):
        self.prepare()
        for tid in ['task1','planning']:
            self.assertEqual(self.change(tid).status_code,200)
            before=self.client.get('/api/tasks/'+tid+'/history').get_json()['history']
            self.assertEqual(self.client.delete('/api/tasks/'+tid).status_code,200)
            self.assertEqual(self.client.get('/api/tasks/'+tid+'/history').get_json()['history'],before)

    def test_failed_history_insert_rolls_back_schedule_atomically(self):
        original=self.prepare()
        with self.Session() as s:
            s.execute(text("CREATE TRIGGER reject_test_history BEFORE INSERT ON task_schedule_history BEGIN SELECT RAISE(ABORT,'test failure'); END"));s.commit()
        self.assertEqual(self.change().status_code,500)
        with self.Session() as s:
            self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)
            self.assertEqual(s.query(TaskScheduleHistory).count(),0)

    def test_history_is_scoped_and_latest_change_is_first(self):
        self.prepare();self.assertEqual(self.change().status_code,200)
        self.assertEqual(self.change(start_date='2026-10-21',end_date='2026-10-29',expected_start_date='2026-10-20',expected_end_date='2026-10-28',history='Second change').status_code,200)
        entries=self.client.get('/api/tasks/task1/history').get_json()['history']
        self.assertEqual([r['history'] for r in entries],['Second change','Waiting for firmware'])
        self.assertNotEqual(entries[0]['id'],entries[1]['id'])
        self.assertEqual(self.client.get('/api/tasks/task2/history').get_json()['history'],[])
        self.assertEqual(self.client.get('/api/tasks/planning/history').get_json()['history'],[])
        self.assertEqual(self.client.get('/api/tasks/missing/history').status_code,404)

    def test_legacy_note_cannot_substitute_required_history(self):
        self.prepare()
        self.assertEqual(self.change(history=None,note='Old Note').status_code,400)
        with self.Session() as s:self.assertEqual(s.query(TaskScheduleHistory).count(),0)

    def edit_change(self,tid='task1',**updates):
        payload={'setup':{'start_date':'2026-10-20','end_date':'2026-10-28','notes':'Edited Notes'},'history':'Edit Task reschedule','expected_start_date':'2026-10-19','expected_end_date':'2026-10-23'}
        payload.update(updates)
        return self.client.patch('/api/tasks/'+tid,json=payload)

    def test_edit_task_date_change_requires_history_for_both_types(self):
        self.prepare()
        for tid in ['task1','planning']:
            for value in [None,'','   ',False,'x'*4001]:
                self.assertEqual(self.edit_change(tid,history=value).status_code,400)
            self.assertEqual(self.edit_change(tid).status_code,200)
            entries=self.client.get('/api/tasks/'+tid+'/history').get_json()['history']
            self.assertEqual(len(entries),1);self.assertEqual(entries[0]['history'],'Edit Task reschedule')
            self.assertEqual(entries[0]['previous_start_date'],'2026-10-19')
            self.assertEqual(entries[0]['end_date'],'2026-10-28')
            model=Task if tid=='task1' else PlanningTask
            with self.Session() as s:
                setup=json.loads(s.get(model,tid).task_metadata)
                self.assertEqual(setup['notes'],'Edited Notes');self.assertEqual(setup['firmware'],'keep')

    def test_edit_task_unchanged_dates_or_notes_only_need_no_history(self):
        self.prepare()
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'setup':{'start_date':'2026-10-19','end_date':'2026-10-23','notes':'Updated'}}).status_code,200)
        self.assertEqual(self.client.patch('/api/tasks/planning',json={'setup':{'notes':'Updated'}}).status_code,200)
        with self.Session() as s:self.assertEqual(s.query(TaskScheduleHistory).count(),0)

    def test_edit_task_add_and_clear_dates_record_history(self):
        self.prepare()
        self.assertEqual(self.edit_change(setup={'start_date':'','end_date':''},history='Clear dates').status_code,200)
        self.assertEqual(self.edit_change(expected_start_date='',expected_end_date='',history='Set dates again').status_code,200)
        entries=self.client.get('/api/tasks/task1/history').get_json()['history']
        self.assertEqual(len(entries),2)
        self.assertEqual(entries[1]['start_date'],'');self.assertEqual(entries[0]['previous_start_date'],'')

    def test_edit_task_stale_date_rejected_and_history_not_added(self):
        self.prepare();self.assertEqual(self.change().status_code,200)
        self.assertEqual(self.edit_change().status_code,409)
        self.assertEqual(len(self.client.get('/api/tasks/task1/history').get_json()['history']),1)

    def test_edit_task_history_failure_rolls_back_all_fields(self):
        original=self.prepare()
        with self.Session() as s:
            s.execute(text("CREATE TRIGGER reject_edit_history BEFORE INSERT ON task_schedule_history BEGIN SELECT RAISE(ABORT,'test failure'); END"));s.commit()
        self.assertEqual(self.edit_change().status_code,500)
        with self.Session() as s:
            self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)
            self.assertEqual(s.query(TaskScheduleHistory).count(),0)

    def test_edit_task_history_retains_existing_database_immutability(self):
        self.prepare();self.assertEqual(self.edit_change().status_code,200)
        for sql in ["UPDATE task_schedule_history SET history='changed'",'DELETE FROM task_schedule_history']:
            with self.Session() as s:
                with self.assertRaises(IntegrityError):s.execute(text(sql));s.commit()
                s.rollback()
        self.assertEqual(self.client.get('/api/tasks/task1/history').get_json()['history'][0]['history'],'Edit Task reschedule')
