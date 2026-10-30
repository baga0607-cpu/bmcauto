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
        self.assertNotEqual(self.repository['source_version'],expected)
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
        self.assertTrue(self.repository['source_version'])

    def test_invalid_naive_non_time_or_non_text_creation_is_rejected(self):
        for value in ('not-time','2020-01-02','2020-01-02T03:04:05',123):
            with self.subTest(value=value):
                response=self.client.post('/api/repository/inspect',json={'source':self.source(value)})
                self.assertEqual(response.status_code,400,response.get_json())
        self.assertEqual(metadata(self.source('2020-01-02T03:04:05Z'))['created_at'],'2020-01-02T03:04:05.000000+00:00')
