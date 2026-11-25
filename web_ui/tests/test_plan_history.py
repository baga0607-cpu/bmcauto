import unittest

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

    def test_import_origin_survives_source_plan_rename(self):
        url = '/api/plans/{}/import-cases'
        copied = self.client.post(url.format('b'), json={
            'kind':'case', 'source_type':'repository', 'id':self.repository['id']})
        self.assertEqual(copied.status_code, 201, copied.get_json())
        self.assertEqual(self.history('b')[0]['import_origin'], {'type':'repository'})
        source = dict(kind='case', source_type='plan', source_plan_id='b',
                      id=copied.get_json()['added'][0]['id'])
        self.assertEqual(self.client.post(url.format('a'), json=source).status_code, 201)
        conflict = self.client.post(url.format('a'), json=source).get_json()['conflicts'][0]
        target = conflict['targets'][0]
        decision = dict(target_id=target['id'], target_token=target['token'], action='skip')
        source['decisions'] = {source['id']:decision}
        self.assertEqual(self.client.post(url.format('a'), json=source).status_code, 201)
        self.assertEqual(len(self.history()), 1)
        decision['action'] = 'overwrite'
        self.assertEqual(self.client.post(url.format('a'), json=source).status_code, 201)
        self.assertEqual(self.client.patch('/api/plans/b',json={'name':'Renamed'}).status_code, 200)
        entries = self.history()
        self.assertEqual(len(entries), 2)
        for entry in entries:
            self.assertEqual(entry['import_origin'], {'type':'plan','id':'b','name':'Plan B'})

    def test_batch_parameters_and_folder_policy(self):
        folder = self.client.post('/api/plans/a/folders',json={'name':'Group'}).get_json()['id']
        sources = [self.client.post('/api/repository/testcases', json={
            'source': fixtures.SOURCE.replace('Service entry',name)}).get_json()['id'] for name in ('One','Two')]
        response = self.client.post('/api/plans/a/import-cases',json={
            'kind':'case','source_type':'repository','case_ids':sources,'target_folder_id':folder})
        self.assertEqual(response.status_code,201,response.get_json())
        cases = [item['id'] for item in response.get_json()['added']]
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
            repo = self.client.post('/api/repository/testcases', json={'source':fixtures.SOURCE.replace('Service entry', name)}).get_json()
            case = self.client.post('/api/plans/a/import-cases', json={'source_type':'repository','kind':'case','id':repo['id']})
            ids.append(case.get_json()['added'][0]['id'])
        url = '/api/plans/a/testcases/'
        self.assertEqual(self.client.post(url+'reorder',json={'folder_id':None,'ids':ids[::-1]}).status_code,200)
        reordered = self.history()[0]['changes']
        self.assertEqual({c['item']:c['after']['position'] for c in reordered},{'Case 2':2,'Case 10':1})
        for _ in range(2):
            self.assertEqual(self.client.post(url+'resort',json={}).status_code,200)
        history = self.history()
        self.assertEqual([e['operation'] for e in history[:2]],['Sort Test Cases','Reorder Test Cases'])
        self.assertEqual(len(history),4)
