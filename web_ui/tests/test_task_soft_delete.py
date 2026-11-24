import json
import unittest
from sqlalchemy import text
import test_single_case_repository as fixtures
from models import Task, PlanningTask


class TaskSoftDeleteTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def test_deletion_rejected_and_historical_deleted_tasks_preserved(self):
        with self.Session() as session:
            session.add(PlanningTask(id='planning', project_id='project', name='Planning'))
            session.commit()
        for tid, model in [('task1', Task), ('planning', PlanningTask)]:
            url = '/api/tasks/' + tid
            self.assertEqual(self.client.delete(url, json={'reason':'Superseded'}).status_code, 405)
            self.assertEqual(self.client.patch(url, json={'setup':{'task_status':'Deleted'}}).status_code, 400)
            self.assertIn(tid, [t['id'] for t in self.client.get('/api/tasks').get_json()['tasks']])
            self.assertEqual(self.client.get(url+'/history').get_json()['history'], [])
            # Existing Deleted records retain their historical visibility.
            with self.Session() as session:
                row = session.get(model, tid)
                row.task_metadata = json.dumps({'task_status':'Deleted'})
                session.commit()
            self.assertNotIn(tid, [t['id'] for t in self.client.get('/api/tasks').get_json()['tasks']])
            deleted = self.client.get('/api/tasks?status=Deleted').get_json()['tasks']
            self.assertIn(tid, [t['id'] for t in deleted])
            self.assertTrue(all(t['setup']['task_status']=='Deleted' for t in deleted))
            self.assertEqual(self.client.patch(url, json={'setup': {'notes':'edit'}}).status_code, 409)
            self.assertEqual(self.client.patch(url+'/schedule', json={}).status_code, 409)
            with self.Session() as session:
                self.assertEqual(json.loads(session.get(model,tid).task_metadata)['task_status'], 'Deleted')
                self.assertEqual(session.execute(text('PRAGMA integrity_check')).scalar(), 'ok')
                self.assertEqual(session.execute(text('PRAGMA foreign_key_check')).all(), [])
        self.assertEqual(self.client.put('/api/tasks/task1/settings', json={'host':'test'}).status_code,409)
        self.assertEqual(self.client.post('/api/tasks/task1/testcases/import', json={'testcases':[]}).status_code,409)
        self.assertEqual(self.client.post('/api/tasks/task1/execution/start', json={'testcase_ids':['missing']}).status_code,409)
        projects = self.client.get('/api/projects').get_json()
        self.assertNotIn('"Task 1"', json.dumps(projects))

