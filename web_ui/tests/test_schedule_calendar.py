import json
import unittest
from datetime import date, timedelta
import test_single_case_repository as fixtures
from models import Task, PlanningTask, ScheduleDayOverride
import schedule_calendar as cal

class ScheduleCalendarTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def patch_day(self, key, value, expected):
        return self.client.patch('/api/schedule/calendar/'+key, json={'is_working':value,'expected_is_working':expected})

    def test_official_years_are_complete_and_include_holidays_and_makeup_work(self):
        for year in cal.OFFICIAL['years']:
            first, last = date(year,1,1), date(year,12,31)
            self.assertEqual(sum(key.startswith(str(year)) for key in cal.OFFICIAL['days']), (last-first).days+1)
        for key in ['2026-01-01','2026-02-16','2026-10-09','2026-10-26','2027-01-01']:
            self.assertFalse(cal.day_info(date.fromisoformat(key),{})['is_working'],key)
        self.assertTrue(cal.day_info(date(2025,2,8),{})['is_working'])
        self.assertTrue(cal.day_info(date(2026,10,22),{})['is_working'])
        self.assertFalse(cal.day_info(date(2026,10,24),{})['is_working'])

    def test_inclusive_counts_weekends_holidays_and_year_boundary(self):
        self.assertEqual(cal.working_days('2026-10-16','2026-10-19',{}),(2,True))
        self.assertEqual(cal.working_days('2026-10-09','2026-10-12',{}),(1,True))
        self.assertEqual(cal.working_days('2026-10-24','2026-10-25',{}),(0,True))
        self.assertEqual(cal.working_days('2026-10-22','2026-10-22',{}),(1,True))
        self.assertEqual(cal.working_days('2026-12-31','2027-01-04',{}),(2,True))
        self.assertEqual(cal.working_days('2025-02-08','2025-02-08',{}),(1,True))

    def test_range_api_defaults_and_manual_setting_survives_sessions(self):
        url='/api/schedule/calendar?start=2026-10-22&end=2026-10-25'
        response=self.client.get(url);self.assertEqual(response.status_code,200)
        self.assertEqual([d['is_working'] for d in response.get_json()['days']],[True,True,False,False])
        self.assertEqual(self.patch_day('2026-10-24',True,False).status_code,200)
        changed=self.client.get(url).get_json()['days'][2]
        self.assertTrue(changed['is_working']);self.assertTrue(changed['overridden'])
        with self.Session() as s:self.assertTrue(s.get(ScheduleDayOverride,'2026-10-24').is_working)
        self.assertEqual(self.patch_day('2026-10-24',None,True).status_code,200)
        self.assertFalse(self.client.get(url).get_json()['days'][2]['is_working'])
        with self.Session() as s:self.assertIsNone(s.get(ScheduleDayOverride,'2026-10-24'))

    def test_calendar_updates_both_task_types_without_changing_metadata_or_evidence(self):
        setup={'start_date':'2026-10-23','end_date':'2026-10-26','notes':'keep me'}
        with self.Session() as s:
            task=s.get(Task,'task1');task.task_metadata=json.dumps(setup)
            original_environment=task.environment_config
            s.add(PlanningTask(id='planning',project_id='project',name='Plan-P-001',task_metadata=json.dumps(setup)))
            s.commit()
        def rows():return {t['id']:t for t in self.client.get('/api/tasks').get_json()['tasks']}
        before=rows()
        for tid in ['task1','planning']:self.assertEqual(before[tid]['working_days'],1)
        self.assertEqual(self.patch_day('2026-10-24',True,False).status_code,200)
        after=rows()
        for tid in ['task1','planning']:
            self.assertEqual(after[tid]['working_days'],2)
            self.assertEqual(after[tid]['setup'],setup)
            self.assertEqual(after[tid]['name'],before[tid]['name'])
        self.assertIsNone(after['task2']['working_days'])
        with self.Session() as s:self.assertEqual(s.get(Task,'task1').environment_config,original_environment)
        self.assertEqual(self.patch_day('2026-10-23',False,True).status_code,200)
        for tid in ['task1','planning']:self.assertEqual(rows()[tid]['working_days'],1)

    def test_stale_or_invalid_edits_do_not_overwrite_a_day(self):
        self.assertEqual(self.patch_day('2026-10-24',True,False).status_code,200)
        self.assertEqual(self.patch_day('2026-10-24',False,False).status_code,409)
        for value in ['true',1,[],{}]:
            self.assertEqual(self.patch_day('2026-10-24',value,True).status_code,400)
        for key in ['2026-02-30','2026-1-01','not-a-day']:
            self.assertEqual(self.patch_day(key,True,False).status_code,400)
        self.assertEqual(self.client.patch('/api/schedule/calendar/2026-10-24',json={'is_working':False}).status_code,400)
        with self.Session() as s:
            self.assertEqual(s.query(ScheduleDayOverride).count(),1)
            self.assertTrue(s.get(ScheduleDayOverride,'2026-10-24').is_working)

    def test_invalid_ranges_and_unsupported_year_are_explicit(self):
        for query in ['','?start=2026-01-01&end=2025-12-31','?start=2026-01-01&end=2028-01-01','?start=2026-02-30&end=2026-03-01']:
            self.assertEqual(self.client.get('/api/schedule/calendar'+query).status_code,400)
        result=self.client.get('/api/schedule/calendar?start=2028-01-01&end=2028-01-03').get_json()
        self.assertTrue(all(not d['covered'] for d in result['days']))
        self.assertEqual([d['is_working'] for d in result['days']],[False,False,True])
        self.assertEqual(cal.working_days('2028-01-01','2028-01-03',{}),(1,False))

    def test_optimized_count_matches_daily_count_with_manual_overrides(self):
        changes={'2025-02-08':False,'2026-10-10':True,'2026-10-22':False,'2027-01-01':True}
        first,last=date(2025,1,1),date(2027,12,31)
        daily=sum(cal.day_info(first+timedelta(days=i),changes)['is_working'] for i in range((last-first).days+1))
        self.assertEqual(cal.working_days(first.isoformat(),last.isoformat(),changes),(daily,True))
