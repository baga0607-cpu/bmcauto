import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
from models import Task, TaskTestCase, RepositoryCase

class RepositoryRemovalTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    add_case=fixtures.SingleCaseRepositoryTest.add_case
    definition=fixtures.SingleCaseRepositoryTest.definition

    def test_confirmation_is_required_and_missing_source_is_404(self):
        path='/api/repository/testcases/'+self.repository['id']
        self.assertEqual(self.client.delete(path).status_code,400)
        self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.delete('/api/repository/testcases/missing',json={'confirm':True}).status_code,404)

    def test_remove_preserves_plan_files_parameters_generation_and_task_evidence(self):
        a=self.add_case();b=self.add_case('b')
        before_a=self.definition(a);before_b=self.definition(b,'b')
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=a['id'],status='Passed',result_json='{"kept":true}',log_text='retained',api_log_text='retained API'))
            s.commit()
        path='/api/repository/testcases/'+self.repository['id']
        self.assertEqual(self.client.delete(path,json={'confirm':True}).status_code,200)
        self.assertEqual(self.client.get(path).status_code,404)
        self.assertFalse(self.client.get('/api/repository/testcases').get_json())
        self.assertEqual(self.definition(a),before_a);self.assertEqual(self.definition(b,'b'),before_b)
        with self.Session() as s:
            row=s.query(TaskTestCase).one()
            self.assertEqual(row.status,'Passed');self.assertEqual(row.log_text,'retained')
            self.assertEqual(row.api_log_text,'retained API');self.assertFalse(row.needs_retest)
        self.assertEqual(self.client.post('/api/plans/a/repository/testcases',json={'repository_id':self.repository['id']}).status_code,404)

    def test_removal_rollback_and_independence_from_active_plan(self):
        a=self.add_case()
        with self.Session() as s:s.get(Task,'task1').execution_active=True;s.commit()
        path='/api/repository/testcases/'+self.repository['id']
        with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('commit failed')):
            self.assertEqual(self.client.delete(path,json={'confirm':True}).status_code,500)
        self.assertEqual(self.client.get(path).status_code,200)
        self.assertEqual(self.client.delete(path,json={'confirm':True}).status_code,200)
        self.assertEqual(self.definition(a)['source_version'],self.repository['source_version'])
