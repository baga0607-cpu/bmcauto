import copy
import json
import unittest
import test_single_case_repository as fixtures
from models import Project, ProjectInformation, Task


class ProjectInformationTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def get_info(self, project='project'):
        response=self.client.get(f'/api/projects/{project}/information')
        self.assertEqual(response.status_code,200)
        return response.get_json()

    def save(self, info, project='project'):
        return self.client.put(f'/api/projects/{project}/information',json={'revision':info['revision'],'document':info['document']})

    def test_blank_framework_does_not_seed_reference_product_values(self):
        info=self.get_info()
        self.assertEqual(info['revision'],0)
        self.assertEqual(len(info['document']['categories']),28)
        self.assertEqual(info['document']['skus'],[])
        self.assertTrue(all(not i['target'] for c in info['document']['categories'] for i in c['items']))
        with self.Session() as s:self.assertEqual(s.query(ProjectInformation).count(),0)

    def test_round_trip_sku_values_unicode_and_source_isolation(self):
        info=self.get_info();doc=info['document']
        doc['metadata']['description']='使用者原文 <script>alert(1)</script>'
        doc['skus']=[{'id':'bmc','name':'BMC'},{'id':'hwm','name':'HWM'}]
        item=doc['categories'][0]['items'][0]
        item.update(target='Mixed',remarks='備註',source_ref='FWA-6084!D4')
        item['sku_values']={'bmc':'Yes','hwm':'No'}
        response=self.save(info);self.assertEqual(response.status_code,200,response.get_json())
        self.assertEqual(self.get_info()['document'],doc)
        with self.Session() as s:s.add(Project(id='other',name='Other'));s.commit()
        self.assertEqual(self.get_info('other')['document']['skus'],[])
        self.assertEqual(self.client.get('/api/projects/missing/information').status_code,404)

    def test_stale_writes_rejected_and_invalid_payload_atomic(self):
        original=self.get_info();self.assertEqual(self.save(original).status_code,200)
        self.assertEqual(self.save(original).status_code,409)
        info=self.get_info();before=copy.deepcopy(info)
        info['document']['categories'][0]['items'][0]['sku_values']={'missing':'value'}
        self.assertEqual(self.save(info).status_code,400)
        self.assertEqual(self.get_info()['document'],before['document'])
        self.assertEqual(self.get_info()['revision'],1)
        info=before;info['document']['skus']=[{'id':'one','name':'SKU'},{'id':'two','name':'sku'}]
        self.assertEqual(self.save(info).status_code,400)

    def test_reference_edits_do_not_change_task_execution_and_delete_cascades(self):
        with self.Session() as s:s.get(Task,'task1').execution_active=True;s.commit()
        self.assertEqual(self.save(self.get_info()).status_code,200)
        with self.Session() as s:
            self.assertTrue(s.get(Task,'task1').execution_active)
            s.get(Task,'task1').execution_active=False;s.commit()
        self.assertEqual(self.client.post('/api/delete_project',json={'project':'Project'}).status_code,200)
        with self.Session() as s:self.assertIsNone(s.get(ProjectInformation,'project'))

if __name__=='__main__':unittest.main()
