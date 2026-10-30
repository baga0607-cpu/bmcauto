import unittest
import test_single_case_repository as fixtures
import app as api
from models import TestCase

class ParameterCompletionTest(unittest.TestCase):
    setUp=fixtures.SingleCaseRepositoryTest.setUp
    def create(self):
        meta={'name':'Parameters','automation':'semi_automatic','parameters':{'text':{'type':'string','default':''},'count':{'type':'integer','default':0},'enabled':{'type':'boolean','default':False}}}
        source='TEST_CASE='+repr(meta)+'\ndef execute(client, context=None, preset=None): pass\n'
        repo=self.client.post('/api/repository/testcases',json={'source':source}).get_json()
        response=self.client.post('/api/plans/a/repository/testcases',json={'repository_id':repo['id']})
        self.assertEqual(response.status_code,201,response.get_json());return response.get_json()
    def overview(self,identity):
        return next(c for project in self.client.get('/api/projects').get_json()['projects'] for plan in project['plans'] for c in plan['testcases'] if c['id']==identity)
    def test_empty_whitespace_zero_false_and_saved_completion(self):
        tc=self.create();row=self.overview(tc['id']);self.assertEqual(row['parameter_count'],3);self.assertFalse(row['parameters_complete']);self.assertEqual(row['missing_parameters'],['text'])
        for value,complete in [('   ',False),('filled',True)]:
            url='/api/plans/a/testcases/'+tc['id']+'/definition';definition=self.client.get(url).get_json()
            response=self.client.put(url,json={'source':definition['source'],'settings':{'text':value,'count':0,'enabled':False},'settings_revision':definition['settings_revision']})
            self.assertEqual(response.status_code,200,response.get_json());row=self.overview(tc['id']);self.assertEqual(row['parameters_complete'],complete)
            self.assertNotIn('settings',row)
    def test_missing_fields_do_not_count_as_complete(self):
        tc=self.create()
        with self.Session() as session:
            row=session.get(TestCase,tc['id']);row.settings_json='{}';session.commit()
        row=self.overview(tc['id']);self.assertFalse(row['parameters_complete']);self.assertEqual(set(row['missing_parameters']),{'text','count','enabled'})

if __name__=='__main__':unittest.main()