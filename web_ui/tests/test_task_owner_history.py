import json
import unittest
from unittest.mock import patch
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import test_single_case_repository as fixtures
import test_task_schedule as schedule_tests
from models import Task,PlanningTask,TaskScheduleHistory
import task_management as tm

class TaskOwnerHistoryTest(unittest.TestCase):
    prepare=schedule_tests.TaskScheduleTest.prepare
    def setUp(self):
        fixtures.SingleCaseRepositoryTest.setUp(self)
        path=self.root/'owners.json';path.write_text(json.dumps({'owners':['TBD','David','Alice']}),encoding='utf-8')
        context=patch.object(tm,'OWNER_FILE',path);context.start();self.addCleanup(context.stop)
        self.prepare()
    def edit(self,tid='task1',owner='David',**extra):
        payload={'setup':{'owner':owner},'expected_owner':'TBD'};payload.update(extra)
        return self.client.patch('/api/tasks/'+tid,json=payload)
    def entries(self,tid='task1'):
        return self.client.get('/api/tasks/'+tid+'/history').get_json()['history']
    def test_owner_changes_generate_server_history_for_both_types(self):
        for tid,model in [('task1',Task),('planning',PlanningTask)]:
            self.assertEqual(self.edit(tid).status_code,200)
            entries=self.entries(tid);self.assertEqual(len(entries),1)
            self.assertEqual(entries[0]['history'],'Owner: TBD → David')
            self.assertEqual(entries[0]['previous_start_date'],entries[0]['start_date'])
            with self.Session() as s:
                setup=json.loads(s.get(model,tid).task_metadata)
                self.assertEqual(setup['owner'],'David');self.assertEqual(setup['notes'],'Original note')
    def test_same_owner_adds_nothing_and_reset_records_actual_previous_value(self):
        self.assertEqual(self.edit(owner='TBD').status_code,200);self.assertEqual(self.entries(),[])
        self.assertEqual(self.edit().status_code,200)
        self.assertEqual(self.edit(expected_owner='David').status_code,200);self.assertEqual(len(self.entries()),1)
        self.assertEqual(self.edit(owner='TBD',expected_owner='David').status_code,200)
        self.assertEqual([r['history'] for r in self.entries()],['Owner: David → TBD','Owner: TBD → David'])
    def test_date_and_owner_changes_preserve_manual_reason_and_auto_owner_entry(self):
        result=self.edit(setup={'owner':'David','start_date':'2026-10-20','end_date':'2026-10-28'},history='Waiting for equipment',expected_start_date='2026-10-19',expected_end_date='2026-10-23')
        self.assertEqual(result.status_code,200,result.get_json())
        self.assertEqual({r['history'] for r in self.entries()},{'Waiting for equipment','Owner: TBD → David'})
    def test_stale_owner_cannot_overwrite_new_owner_or_add_history(self):
        self.assertEqual(self.edit().status_code,200)
        self.assertEqual(self.edit(owner='Alice').status_code,409)
        self.assertEqual(len(self.entries()),1)
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata)['owner'],'David')
    def test_failed_history_insert_rolls_back_owner(self):
        with self.Session() as s:
            before=s.get(Task,'task1').task_metadata
            s.execute(text("CREATE TRIGGER reject_owner_history BEFORE INSERT ON task_schedule_history BEGIN SELECT RAISE(ABORT,'test failure'); END"));s.commit()
        self.assertEqual(self.edit().status_code,500)
        with self.Session() as s:
            self.assertEqual(s.get(Task,'task1').task_metadata,before)
            self.assertEqual(s.query(TaskScheduleHistory).count(),0)
    def test_owner_history_cannot_be_modified_or_removed_and_survives_task_deletion(self):
        self.assertEqual(self.edit().status_code,200);before=self.entries()
        for sql in ["UPDATE task_schedule_history SET history='changed'",'DELETE FROM task_schedule_history']:
            with self.Session() as s:
                with self.assertRaises(IntegrityError):s.execute(text(sql));s.commit()
                s.rollback()
        self.assertEqual(self.client.delete('/api/tasks/task1').status_code,200)
        self.assertEqual(self.entries(),before)
    def test_invalid_owner_creates_no_history(self):
        self.assertEqual(self.edit(owner='Unknown').status_code,400)
        self.assertEqual(self.entries(),[])
