import time
from pathlib import Path
import unittest

import test_single_case_repository as fixtures
import app as api
from case_process import run_case_worker
from models import TestCase


class CaseStopTest(unittest.TestCase):
    def setUp(self):
        fixtures.SingleCaseRepositoryTest.setUp(self)
        from unittest.mock import patch
        real_worker = patch.object(api, 'run_case_worker', run_case_worker)
        real_worker.start()
        self.addCleanup(real_worker.stop)
        self.first = self.add_case()
        source = fixtures.SOURCE.replace('Service entry', 'Second entry')
        self.repository = self.client.post('/api/repository/testcases', json={'source': source}).get_json()
        self.second = self.add_case()
        self.ids = [self.first['id'], self.second['id']]
        self.client.post('/api/tasks/task1/testcases/import', json={'testcases': self.ids})
        self.token = self.client.post('/api/tasks/task1/execution/start', json={'testcase_ids': self.ids}).get_json()['execution_token']
        self.sessions = []
        # The subprocess imports this SDK from the disposable framework root.
        (self.root / 'redfish.py').write_text(
            'class Client:\n    def login(self, **kw): pass\n    def logout(self): pass\n'
            'def redfish_client(**kw): return Client()\n', encoding='utf-8')
        self.addCleanup(self.cleanup_workers)

    add_case = fixtures.SingleCaseRepositoryTest.add_case

    def cleanup_workers(self):
        for sid in self.sessions:
            run = api.run_sessions.get(sid)
            if run:
                api.ps.request_worker_stop(run)
                run['thread'].join(5)
                api.run_sessions.pop(sid, None)

    def start(self, tc, body='pass'):
        with self.Session() as session:
            module = session.get(TestCase, tc['id']).script_path
        path = self.root.joinpath(*module.split('.'), 'case.py')
        source = path.read_text(encoding='utf-8').split('def execute(')[0]
        source += 'def execute(client, context=None, preset=None):\n'
        path.write_text(source + '\n'.join('    '+line for line in body.splitlines()), encoding='utf-8')
        response = self.client.post('/api/run', json={'task_id': 'task1', 'testcase_id': tc['id'], 'execution_token': self.token})
        self.assertEqual(response.status_code, 200, response.get_json())
        sid = response.get_json()['session_id']
        self.sessions.append(sid)
        return sid

    def waiting(self, tc):
        # No input() or cooperative cancellation. Both Python processes are asleep.
        ready = self.root / (tc['id'] + '.ready')
        helper_done = self.root / (tc['id'] + '.helper-finished')
        helper = f'print("native helper output", flush=True);import time;from pathlib import Path;time.sleep(2);Path({str(helper_done)!r}).touch()'
        sid = self.start(tc, f"""import subprocess, sys, time
from pathlib import Path
subprocess.Popen([sys.executable, '-c', {helper!r}])
print('before interruption')
Path({str(ready)!r}).touch()
time.sleep(60)
raise AssertionError('case ran past stop')""")
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            if api.run_sessions[sid].get('closed'): break
            time.sleep(0.025)
        self.assertTrue(ready.exists(), api.run_sessions[sid]['log_history'])
        return sid

    def join(self, sid):
        api.run_sessions[sid]['thread'].join(5)
        self.assertFalse(api.run_sessions[sid]['thread'].is_alive())

    def stop_case(self, tc, sid, **overrides):
        return self.client.post(f"/api/tasks/task1/testcases/{tc['id']}/execution/stop",
                                json={'session_id': sid, 'execution_token': self.token, **overrides})

    def execution(self):
        return self.client.get('/api/tasks/task1/execution').get_json()

    def test_case_stop_keeps_queue_and_admits_next_case(self):
        sid = self.waiting(self.first)
        response = self.stop_case(self.first, sid)
        self.assertEqual(response.status_code, 200, response.get_json())
        self.join(sid)
        current = self.execution()
        self.assertTrue(current['execution_active'])
        self.assertFalse(current['stop_requested'])
        self.assertEqual(current['execution_token'], self.token)
        self.assertEqual(current['testcase_ids'], self.ids)
        self.assertEqual(current['completed_testcase_ids'], [self.first['id']])
        row = self.client.get(f"/api/tasks/task1/testcases/{self.first['id']}/logs").get_json()
        self.assertEqual(row['status'], 'TBD')
        self.assertIn('Stopped', row['log_text'])
        self.assertIn('before interruption', row['log_text'])
        time.sleep(2.1)
        self.assertFalse((self.root / (self.first['id'] + '.helper-finished')).exists())
        # Task and selection remain locked between cases.
        self.assertEqual(self.client.patch(f"/api/task_testcases/task1/{self.second['id']}", json={'selected': False}).status_code, 409)
        next_sid = self.start(self.second)
        self.join(next_sid)
        row = self.client.get(f"/api/tasks/task1/testcases/{self.second['id']}/logs").get_json()
        self.assertEqual(row['status'], 'Passed')
        self.assertEqual(set(self.execution()['completed_testcase_ids']), set(self.ids))
        self.assertEqual(self.client.post('/api/tasks/task1/execution/finish', json={'execution_token': self.token}).status_code, 200)
        self.assertFalse(self.execution()['execution_active'])
        # A new execution must not inherit completed cases from the old token.
        self.client.post('/api/tasks/task1/execution/start', json={'testcase_ids': self.ids})
        self.assertEqual(self.execution()['completed_testcase_ids'], [])

    def test_input_crosses_process_boundary(self):
        sid = self.start(self.first, "assert input('Confirm test fixture') == 'yes'")
        deadline = time.monotonic() + 10
        while not api.run_sessions[sid].get('input_prompt') and time.monotonic() < deadline:
            time.sleep(0.025)
        self.assertEqual(api.run_sessions[sid].get('input_prompt'), 'Confirm test fixture')
        response = self.client.post('/api/input', json={'session_id': sid, 'value': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.join(sid)
        row = self.client.get(f"/api/tasks/task1/testcases/{self.first['id']}/logs").get_json()
        self.assertEqual(row['status'], 'Passed')

    def test_toolbar_stop_ends_task_and_rejects_remaining_case(self):
        sid = self.waiting(self.first)
        response = self.client.post('/api/tasks/task1/execution/stop', json={'execution_token': self.token})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.join(sid)
        self.assertFalse(self.execution()['execution_active'])
        response = self.client.post('/api/run', json={'task_id': 'task1', 'testcase_id': self.second['id'], 'execution_token': self.token})
        self.assertEqual(response.status_code, 409)

    def test_wrong_case_session_task_or_token_cannot_stop_worker(self):
        sid = self.waiting(self.first)
        self.assertEqual(self.stop_case(self.second, sid).status_code, 409)
        self.assertEqual(self.stop_case(self.first, 'old-session').status_code, 409)
        self.assertEqual(self.stop_case(self.first, sid, execution_token='old-token').status_code, 409)
        response = self.client.post(f"/api/tasks/task2/testcases/{self.first['id']}/execution/stop", json={'session_id': sid, 'execution_token': self.token})
        self.assertIn(response.status_code, (404, 409))
        self.assertFalse(api.run_sessions[sid]['stop_requested'])
        self.assertEqual(self.stop_case(self.first, sid).status_code, 200)
        self.join(sid)
        next_sid = self.waiting(self.second)
        self.assertEqual(self.stop_case(self.first, sid).status_code, 409)
        self.assertFalse(api.run_sessions[next_sid]['stop_requested'])
        self.assertEqual(self.stop_case(self.second, next_sid).status_code, 200)
        self.join(next_sid)

    def test_task_stop_overrides_case_only_stop(self):
        sid = self.waiting(self.first)
        self.assertEqual(self.stop_case(self.first, sid).status_code, 200)
        response = self.client.post('/api/tasks/task1/execution/stop', json={'execution_token': self.token})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.join(sid)
        self.assertFalse(self.execution()['execution_active'])


if __name__ == '__main__':
    unittest.main()
