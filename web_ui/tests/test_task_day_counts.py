import json
import unittest
import test_task_schedule as schedule
from models import Task, PlanningTask, ScheduleDayOverride

class TaskDayCountsTest(unittest.TestCase):
    setUp = schedule.TaskScheduleTest.setUp
    prepare = schedule.TaskScheduleTest.prepare

    def rows(self):
        response=self.client.get('/api/tasks')
        self.assertEqual(response.status_code,200,response.get_json())
        return {t['id']:t for t in response.get_json()['tasks']}

    def test_independent_inclusive_counts_include_holidays_and_manual_days(self):
        self.prepare()
        setup={'start_date':'2026-10-08','end_date':'2026-10-12','actual_start_date':'2026-10-09','actual_end_date':'2026-10-11'}
        with self.Session() as s:
            for model,tid in [(Task,'task1'),(PlanningTask,'planning')]:s.get(model,tid).task_metadata=json.dumps(setup)
            s.commit()
        for tid in ['task1','planning']:
            row=self.rows()[tid]
            self.assertEqual((row['actual_working_days'],row['working_days']),(0,2))
        with self.Session() as s:
            s.add(ScheduleDayOverride(date='2026-10-10',is_working=True));s.commit()
        for tid in ['task1','planning']:
            row=self.rows()[tid]
            self.assertEqual((row['actual_working_days'],row['working_days']),(1,3))
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),setup)

    def test_partial_or_absent_pairs_are_independently_unknown(self):
        self.prepare()
        variants=[({'start_date':'2026-10-22','end_date':'2026-10-22','actual_start_date':'2026-10-22'},(None,1)),({'actual_start_date':'2026-10-22','actual_end_date':'2026-10-22','end_date':'2026-10-22'},(1,None)),({},(None,None))]
        for setup,expected in variants:
            with self.Session() as s:
                s.get(Task,'task1').task_metadata=json.dumps(setup);s.commit()
            row=self.rows()['task1']
            self.assertEqual((row['actual_working_days'],row['working_days']),expected)

    def test_actual_coverage_flag_is_independent_of_plan_coverage(self):
        self.prepare()
        with self.Session() as s:
            s.get(Task,'task1').task_metadata=json.dumps({'start_date':'2026-10-22','end_date':'2026-10-22','actual_start_date':'2028-01-01','actual_end_date':'2028-01-03'});s.commit()
        row=self.rows()['task1']
        self.assertEqual((row['actual_working_days'],row['working_days']),(1,1))
        self.assertFalse(row['actual_calendar_complete']);self.assertTrue(row['calendar_complete'])
