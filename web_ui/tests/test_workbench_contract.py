import sys
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import test_single_case_repository as fixtures
import app as api
from models import TestCase, TaskTestCase


class WorkbenchContractTest(fixtures.SingleCaseRepositoryTest):
    # Reuse the isolated fixture, without inheriting its tests a second time.
    def test_retired_routes_and_unscoped_execution_are_unavailable(self):
        for route in ['/builder','/builder.html','/api/steps']:
            self.assertEqual(self.client.get(route).status_code,404,route)
        for route in ['/api/fork_tc','/api/push_to_golden','/api/move_tc']:
            self.assertIn(self.client.post(route,json={}).status_code,(404,405),route)
        self.assertEqual(self.client.post('/api/run',json={'steps':[{'module_path':'danger'}]}).status_code,400)
        response=self.client.post('/api/import_tc',json={'plan_id':'a','tc_name':'Old','steps':[]})
        self.assertEqual(response.status_code,410)

    def test_legacy_records_are_readable_without_importing_their_code(self):
        marker=self.root/'executed.txt'
        folder=self.root/'retired';folder.mkdir()
        (folder/'__testcase__.py').write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()",encoding='utf-8')
        with self.Session() as s:
            s.add(TestCase(system_id='retired',plan_id='a',display_name='Old Case',script_path='retired',script_kind='steps'))
            s.flush()
            s.add(TaskTestCase(task_id='task1',testcase_id='retired',status='Passed',log_text='Historical evidence'));s.commit()
        self.assertEqual(self.client.get('/api/projects').status_code,200)
        self.assertEqual(self.client.get('/api/testcases').status_code,200)
        self.assertFalse(marker.exists())
        self.assertEqual(self.client.get('/api/plans/a/testcases/retired/preview').status_code,410)
        response=self.client.post('/api/tasks/task1/execution/start',json={'testcase_ids':['retired']})
        self.assertEqual(response.status_code,410)
        self.assertEqual(self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]['log_text'],'Historical evidence')
        self.assertFalse(marker.exists())

    def test_operational_state_carries_selected_scope_for_reconnection(self):
        tc=self.add_case();self.client.post('/api/tasks/task1/testcases/import',json={'testcases':[tc['id']]})
        self.client.post('/api/tasks/task1/execution/start',json={'testcase_ids':[tc['id']]})
        state=self.client.get('/api/tasks/task1/execution').get_json()
        self.assertEqual(state['testcase_ids'],[tc['id']]);self.assertFalse(state['stop_requested'])
        self.assertEqual(self.client.post('/api/tasks/task2/execution/start',json={'testcase_ids':[tc['id']]}).status_code,409)

    def test_completed_stream_replays_then_closes(self):
        api.run_sessions['closed-qa']={'listeners':[],'log_history':[{'type':'log','text':'Saved evidence'}],'closed':True}
        try:
            response=self.client.get('/api/stream/closed-qa')
            self.assertIn('Saved evidence',response.text);self.assertIn('"type": "end"',response.text)
        finally:api.run_sessions.pop('closed-qa',None)

    def test_single_preview_returns_metadata_without_executing_source(self):
        tc=self.add_case();response=self.client.get(f'/api/plans/a/testcases/{tc["id"]}/preview')
        self.assertEqual(response.status_code,200);self.assertIn('metadata',response.get_json());self.assertNotIn('steps',response.get_json())


# Borrow fixture methods only: inherited test names are intentionally excluded.
for _name in list(vars(fixtures.SingleCaseRepositoryTest)):
    if _name.startswith('test_'):
        setattr(WorkbenchContractTest,_name,None)
