import unittest
from uuid import uuid4

import test_single_case_repository as fixtures


class PlanHistoryTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def history(self, plan='a'):
        response = self.client.get(f'/api/plans/{plan}/history')
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_plan_identity_and_noop_rename(self):
        response = self.client.post('/api/create_plan', json={'project': 'Project', 'plan_name': 'New'},
                                    environ_overrides={'REMOTE_USER': 'QA'})
        plan = response.get_json()['plan_id']
        created, = self.history(plan)
        self.assertEqual(created['operator'], 'QA')
        self.assertEqual(created['changes'][0]['after'], {'name': 'New'})
        for name in ['Renamed', 'Renamed']:
            self.assertEqual(self.client.patch('/api/plans/'+plan,json={'name':name}).status_code, 200)
        renamed, original = self.history(plan)
        self.assertEqual(original, created)
        self.assertEqual(renamed['changes'][0]['before'], {'name':'New'})
        self.assertEqual(self.history('b'), [])

    def test_batch_parameters_and_folder_policy(self):
        folder = self.client.post('/api/plans/a/folders',json={'name':'Group'}).get_json()['id']
        batch = str(uuid4())
        cases = []
        for name in ['One', 'Two', 'Two']:
            response = self.client.post('/api/plans/a/testcases/import-python',json={
                'folder_id': folder, 'source': fixtures.SOURCE.replace('Service entry',name), 'history_batch':batch})
            if response.status_code == 201:
                cases.append(response.get_json()['id'])
            else:
                self.assertEqual(response.status_code,409)
        imported, created = self.history()
        self.assertEqual({c['item'] for c in imported['changes']},{'One','Two'})
        url = '/api/plans/a/testcases/'+cases[0]+'/definition'
        definition = self.client.get(url).get_json()
        definition['settings']['expected'] = 201
        self.assertEqual(self.client.put(url,json=definition).status_code,200)
        self.assertEqual(self.client.put(url,json=definition).status_code,409)
        self.assertEqual(self.client.put(url,json=self.client.get(url).get_json()).status_code,200)
        edited, old_import, old_create = self.history()
        self.assertEqual(edited['changes'][0]['before'],{'parameters':{'expected':200}})
        self.assertEqual(edited['changes'][0]['after'],{'parameters':{'expected':201}})
        self.assertEqual((old_import,old_create),(imported,created))
        payload = dict(folder_ids=[folder],case_ids=[],keep_cases=True,confirm=True,acknowledgement=True)
        self.assertEqual(self.client.post('/api/plans/a/items/remove',json=payload).status_code,200)
        moved = [c for c in self.history()[0]['changes'] if c['kind']=='Test Case']
        self.assertEqual(len(moved),2)
        self.assertTrue(all(c['before']=={'folder':'BMC/Group'} and c['after']=={'folder':'BMC'} for c in moved))

    def test_sort_records_displayed_order_only_when_changed(self):
        ids = []
        for name in ['Case 2', 'Case 10']:
            case = self.client.post('/api/plans/a/testcases/import-python',
                json={'source':fixtures.SOURCE.replace('Service entry', name)})
            ids.append(case.get_json()['id'])
        url = '/api/plans/a/testcases/'
        self.assertEqual(self.client.post(url+'reorder',json={'folder_id':None,'ids':ids[::-1]}).status_code,200)
        reordered = self.history()[0]['changes']
        self.assertEqual({c['item']:c['after']['position'] for c in reordered},{'Case 2':2,'Case 10':1})
        for _ in range(2):
            self.assertEqual(self.client.post(url+'resort',json={}).status_code,200)
        history = self.history()
        self.assertEqual([e['operation'] for e in history[:2]],['Sort Test Cases','Reorder Test Cases'])
        self.assertEqual(len(history),4)
