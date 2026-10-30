import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
from models import TestCase, Task

class BatchCaseImportTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def repository_case(self, name):
        source = "TEST_CASE = {'name': %r}\ndef execute(client, context=None, preset=None): pass\n" % name
        response = self.client.post('/api/repository/testcases', json={'source': source})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['id']

    def request(self, ids, target='a', **extra):
        return self.client.post('/api/plans/'+target+'/import-cases', json={
            'source_type': 'repository', 'kind': 'case', 'case_ids': ids, **extra})

    def test_batch_import_and_insertion_order(self):
        anchor = self.repository_case('Anchor')
        response = self.request([anchor]); self.assertEqual(response.status_code, 201)
        anchor_id = response.get_json()['added'][0]['id']
        first = self.repository_case('First'); second = self.repository_case('Second')
        response = self.request([first, second], relative_to=anchor_id, insertion='before')
        self.assertEqual(response.status_code, 201, response.get_json())
        ids = [row['id'] for row in response.get_json()['added']]+[anchor_id]
        projects = self.client.get('/api/projects').get_json()['projects']
        plan = next(p for project in projects for p in project['plans'] if p['id']=='a')
        self.assertEqual([row['id'] for row in plan['testcases']], ids)

    def test_batch_rejects_invalid_ids_ownership_and_locks_without_partial_data(self):
        first = self.repository_case('First'); second = self.repository_case('Second')
        for ids in ([], [first, first], [first, 'missing'], [first, None], 'invalid'):
            response = self.request(ids)
            self.assertGreaterEqual(response.status_code, 400)
            with self.Session() as session:
                self.assertEqual(session.query(TestCase).count(), 0)
        response = self.request([first]); own_id = response.get_json()['added'][0]['id']
        response = self.request([second], target='b'); foreign_id = response.get_json()['added'][0]['id']
        response = self.request([own_id, foreign_id], source_type='plan', source_plan_id='a', target='b')
        self.assertEqual(response.status_code, 400)
        with self.Session() as session:
            self.assertEqual(session.query(TestCase).count(), 2)
            task = session.get(Task, 'task1'); task.execution_active = True; session.commit()
        self.assertEqual(self.request([second]).status_code, 409)

    def test_batch_from_another_plan(self):
        first = self.repository_case('First'); second = self.repository_case('Second')
        response = self.request([first, second])
        source_ids = [row['id'] for row in response.get_json()['added']]
        response = self.request(source_ids, target='b', source_type='plan', source_plan_id='a')
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(len(response.get_json()['added']), 2)
        with self.Session() as session:
            self.assertEqual(session.query(TestCase).filter_by(plan_id='a').count(), 2)
            self.assertEqual(session.query(TestCase).filter_by(plan_id='b').count(), 2)

    def test_conflict_makes_no_changes_until_resolved(self):
        first = self.repository_case('First'); second = self.repository_case('Second')
        self.assertEqual(self.request([first]).status_code, 201)
        response = self.request([second, first])
        self.assertEqual(response.status_code, 409, response.get_json())
        conflict = response.get_json()['conflicts'][0]; target = conflict['targets'][0]
        with self.Session() as session:
            self.assertEqual(session.query(TestCase).count(), 1)
        response = self.request([second, first], decisions={first: {
            'action': 'skip', 'target_id': target['id'], 'target_token': target['token']}})
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(len(response.get_json()['added']), 1)
        self.assertEqual(len(response.get_json()['skipped']), 1)

    def test_commit_failure_rolls_back_every_copy(self):
        first = self.repository_case('First'); second = self.repository_case('Second')
        before = set(self.root.rglob('*.py'))
        with patch.object(self.Session.class_, 'commit', side_effect=RuntimeError('batch commit failure')):
            response = self.request([first, second])
        self.assertEqual(response.status_code, 500)
        with self.Session() as session:
            self.assertEqual(session.query(TestCase).count(), 0)
        self.assertEqual(set(self.root.rglob('*.py')), before)

if __name__ == '__main__':
    unittest.main()
