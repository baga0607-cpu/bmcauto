import unittest
import test_single_case_repository as fixtures
from single_case import metadata


class SourceCreatedAtTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    add_case=fixtures.SingleCaseRepositoryTest.add_case
    definition=fixtures.SingleCaseRepositoryTest.definition
    update=fixtures.SingleCaseRepositoryTest.update

    def source(self, stamp):
        return fixtures.SOURCE.replace("'name': 'Service entry'", "'created_at': "+repr(stamp)+", 'name': 'Service entry'")

    def test_birth_time_survives_import_copy_and_adaptation(self):
        response=self.client.post('/api/repository/testcases',json={'source':self.source('2020-01-02T03:04:05.123456+08:00')})
        self.assertEqual(response.status_code,201,response.get_json());self.repository=response.get_json()
        expected='2020-01-01T19:04:05.123456+00:00'
        self.assertEqual(self.repository['source_created_at'],expected)
        self.assertNotEqual(self.repository['modified_at'],expected)
        listing=self.client.get('/api/repository/testcases').get_json()
        self.assertEqual(next(r for r in listing if r['id']==self.repository['id'])['source_created_at'],expected)
        tc=self.add_case();definition=self.definition(tc)
        self.assertEqual(definition['source_created_at'],expected)
        response=self.update(tc,{'source':definition['source']+'\n# Independent Plan comment\n','settings':definition['settings'],'settings_revision':0})
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(response.get_json()['source_created_at'],expected)
        projects=self.client.get('/api/projects').get_json()['projects']
        plan=next(p for project in projects for p in project['plans'] if p['id']=='a')
        self.assertEqual(plan['testcases'][0]['source_created_at'],expected)
        self.client.post('/api/tasks/task1/testcases/import',json={'testcases':[tc['id']]})
        self.assertEqual(self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]['source_created_at'],expected)
        response=self.client.post('/api/plans/b/import-cases',json={'kind':'case','source_type':'plan','source_plan_id':'a','id':tc['id'],'target_folder_id':None})
        self.assertEqual(response.status_code,201,response.get_json())
        copied=response.get_json()['added'][0]
        self.assertEqual(self.definition(copied,'b')['source_created_at'],expected)

    def test_unknown_never_falls_back_to_import_or_copy_time(self):
        self.assertIsNone(self.repository['source_created_at'])
        tc=self.add_case();self.assertIsNone(self.definition(tc)['source_created_at'])
        self.assertIsNone(self.repository['modified_at'])

    def test_modified_time_tracks_source_edits_only(self):
        source = self.source('2020-01-02T00:00:00Z').replace("'name':", "'modified_at': '2021-01-01T08:00:00+08:00', 'name':", 1)
        self.repository = self.client.post('/api/repository/testcases', json={'source':source}).get_json()
        tc = self.add_case()
        original = self.definition(tc)
        self.assertEqual(original['source_modified_at'], '2021-01-01T00:00:00.000000+00:00')
        settings = dict(original['settings'], expected=201)
        unchanged = self.update(tc, {'settings':settings, 'settings_revision':0}).get_json()
        self.assertEqual(unchanged['source_modified_at'], original['source_modified_at'])
        changed = self.update(tc, {'source':original['source']+'\n# revised\n', 'settings_revision':1}).get_json()
        self.assertGreater(changed['source_modified_at'], original['source_modified_at'])
        self.assertEqual(changed['source_created_at'], original['source_created_at'])
        copied = self.client.post('/api/plans/b/import-cases',json={'kind':'case','source_type':'plan','source_plan_id':'a','id':tc['id'],'target_folder_id':None}).get_json()['added'][0]
        self.assertEqual(self.definition(copied,'b')['source_modified_at'], changed['source_modified_at'])

    def test_invalid_naive_non_time_or_non_text_creation_is_rejected(self):
        for value in ('not-time','2020-01-02','2020-01-02T03:04:05',123):
            with self.subTest(value=value):
                response=self.client.post('/api/repository/inspect',json={'source':self.source(value)})
                self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(metadata(self.source('2020-01-02T03:04:05Z'))['created_at'],'2020-01-02T03:04:05.000000+00:00')

    def test_plan_checks_linked_id_and_preserves_subsecond_versions(self):
        first = '2026-01-01T12:00:00.000001+08:00'
        second = '2026-01-01T12:00:00.000002+08:00'
        source = fixtures.SOURCE.replace("'name':", f"'modified_at': '{first}', 'name':")
        repository = '/api/repository/testcases'
        self.repository = self.client.post(repository, json={'source': source}).get_json()
        tc = self.add_case()
        replacement = source.replace(first, second)
        self.client.post(repository, json={'source': replacement})
        def status():
            return self.client.get('/api/plans/a/case-versions').get_json()[0]['status']
        self.assertEqual(status(), 'Up to date')
        target = repository + '/' + self.repository['id']
        payload = {'source': replacement, 'previous_modified_at': tc['modified_at']}
        self.assertEqual(self.client.put(target, json=payload).status_code, 200)
        self.assertEqual(self.client.put(target, json=payload).status_code, 409)
        self.assertEqual(status(), 'Repository update available')
        self.client.delete(target, json={'confirm': True})
        self.assertEqual(status(), 'Not in repository')

    def test_update_requires_confirmation_and_updates_only_checked_copy(self):
        source = fixtures.SOURCE.replace("'name':", "'modified_at': '2026-01-01T00:00:00Z', 'name':")
        self.repository = self.client.post('/api/repository/testcases', json={'source': source}).get_json()
        tc = self.add_case()
        peer = self.add_case('b')
        settings = dict(self.definition(tc)['settings'], expected=204)
        self.update(tc, {'settings': settings, 'settings_revision': 0})
        target = '/api/repository/testcases/' + self.repository['id']
        newer = source.replace('2026-01-01','2026-02-01')
        self.assertEqual(self.client.put(target, json={'source': newer,
            'previous_modified_at': tc['modified_at']}).status_code, 200)
        check = self.client.get('/api/plans/a/case-versions').get_json()[0]
        url = '/api/plans/a/testcases/' + tc['id'] + '/repository-update'
        self.assertEqual(self.client.post(url, json=check).status_code, 400)
        self.assertEqual(self.client.post(url, json=dict(check, confirm=True, repository_modified='stale')).status_code, 409)
        self.assertEqual(self.definition(tc)['source'], source)
        self.assertEqual(self.client.post(url, json=dict(check, confirm=True)).status_code, 200)
        self.assertEqual(self.definition(tc)['source'], newer)
        self.assertEqual(self.definition(tc)['settings'], settings)
        self.assertEqual(self.definition(peer, 'b')['source'], source)
        self.assertEqual(self.client.get('/api/plans/a/case-versions').get_json()[0]['status'], 'Up to date')
        self.assertEqual(self.client.post(url, json=dict(check, confirm=True)).status_code, 409)
