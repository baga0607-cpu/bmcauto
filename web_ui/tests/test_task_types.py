import json
import unittest
from concurrent.futures import ThreadPoolExecutor
import test_single_case_repository as fixtures
import app as api
from models import Project, ProjectInformation, ProjectPlan, Task, PlanningTask, TaskNameSeries, PlanSKU
from project_information import blank_information


class TaskTypesTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def post(self, **data):
        return self.client.post('/api/tasks', json=data)

    def add_skus(self):
        with self.Session() as session:
            project = session.get(Project, 'project')
            project.name = 'SKY-712V4'
            doc = blank_information()
            doc['skus'] = [{'id':'sata','name':'SATA'}, {'id':'e3s','name':'E3.S'}]
            session.add(ProjectInformation(project_id='project',document=json.dumps(doc),revision=1,updated_at=''))
            session.add(PlanSKU(plan_id='a',sku_id='sata'))
            session.add(PlanSKU(plan_id='b',sku_id='e3s'))
            session.commit()

    def test_project_plan_work_without_existing_plan_and_immutable_name(self):
        with self.Session() as session:
            session.add(Project(id='empty',name='FWA-3051'));session.commit()
        payload=dict(task_type='Plan',project_id='empty',name='User supplied')
        result=self.post(**payload)
        self.assertEqual(result.status_code,200,result.get_json())
        row=result.get_json();self.assertEqual(row['name'],'Plan-FWA3051-001')
        tid=row['id']
        with self.Session() as session:
            self.assertIsNone(session.get(Task,tid))
            self.assertEqual(session.get(PlanningTask,tid).project_id,'empty')
        self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'name':'Changed'}).status_code,400)
        self.assertEqual(self.client.patch('/api/tasks/'+tid,json={'setup':{'start_date':'2026-10-21','end_date':'2026-10-22'},'history':'Assign dates','expected_start_date':'','expected_end_date':''}).status_code,200)
        self.assertEqual(self.client.post('/api/tasks/'+tid+'/execution/start',json={'testcase_ids':[]}).status_code,404)
        self.assertEqual(self.client.delete('/api/tasks/'+tid).status_code,200)
        self.assertEqual(self.post(**payload).get_json()['name'],'Plan-FWA3051-002')

    def test_sku_normalization_and_independent_series(self):
        self.add_skus()
        choices=self.client.get('/api/tasks/options').get_json()['projects'][0]
        self.assertEqual([s['full_name'] for s in choices['skus']],['SKY-712V4 SATA','SKY-712V4 E3.S'])
        base=dict(task_type='Plan',project_id='project')
        self.assertEqual(self.post(**base).status_code,400)
        self.assertEqual(self.post(**base,sku_id='other').status_code,400)
        self.assertEqual(self.post(**base,sku_id='sata').get_json()['name'],'Plan-SKY712V4SATA-001')
        self.assertEqual(self.post(**base,sku_id='e3s').get_json()['name'],'Plan-SKY712V4E3S-001')
        self.assertEqual(self.post(**base,sku_id='sata').get_json()['name'],'Plan-SKY712V4SATA-002')

    def test_test_task_requires_matching_project_sku_plan_and_preserves_plan_scope(self):
        self.add_skus()
        data=dict(task_type='Test',project_id='project',sku_id='sata',plan_id='a')
        self.assertEqual(self.post(**dict(data,plan_id='b')).status_code,400)
        self.assertEqual(self.post(**dict(data,plan_id=None)).status_code,400)
        self.assertEqual(self.post(**dict(data,project_id='missing')).status_code,404)
        first=self.post(**data).get_json()
        self.assertEqual(first['name'],'Test-PlanA-001')
        self.assertEqual(self.post(**data).get_json()['name'],'Test-PlanA-002')
        self.assertEqual(self.post(**dict(data,sku_id='e3s',plan_id='b')).get_json()['name'],'Test-PlanB-001')
        self.assertEqual(self.client.patch('/api/tasks/'+first['id'],json={'sku_id':'e3s'}).status_code,400)
        self.assertEqual(self.client.patch('/api/tasks/'+first['id'],json={'task_type':'Plan'}).status_code,400)

    def test_preview_does_not_allocate_and_invalid_dates_roll_back_number(self):
        query={'task_type':'Plan','project_id':'project'}
        for _ in range(2):
            self.assertEqual(self.client.get('/api/tasks/name-preview',query_string=query).get_json()['name'],'Plan-Project-001')
        response=self.post(**query,setup={'start_date':'2026-10-22','end_date':'2026-10-21'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.post(**query).get_json()['name'],'Plan-Project-001')
        with self.Session() as session:self.assertEqual(session.query(TaskNameSeries).one().last_number,1)

    def test_concurrent_creation_and_deletion_never_recycle_names(self):
        def create(_):
            with api.app.test_client() as client:
                response=client.post('/api/tasks',json={'task_type':'Plan','project_id':'project'})
                self.assertEqual(response.status_code,200,response.get_json())
                return response.get_json()
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows=list(pool.map(create,range(8)))
        self.assertEqual({r['name'] for r in rows},{f'Plan-Project-{n:03d}' for n in range(1,9)})
        for row in rows:
            self.assertEqual(self.client.delete('/api/tasks/'+row['id']).status_code,200)
        self.assertEqual(self.post(task_type='Plan',project_id='project').get_json()['name'],'Plan-Project-009')

    def test_plan_sku_binding_survives_custom_plan_name_and_no_duplicate_prefix(self):
        self.add_skus()
        response=self.client.post('/api/create_plan',json={'project':'SKY-712V4','plan_name':'Custom plan','sku_id':'e3s'})
        self.assertEqual(response.status_code,200,response.get_json())
        pid=response.get_json()['plan_id']
        rows=self.client.get('/api/tasks/options').get_json()['projects'][0]['plans']
        self.assertEqual(next(p for p in rows if p['id']==pid)['sku_id'],'e3s')
        from project_naming import full_sku_name
        self.assertEqual(full_sku_name('FWA-6084','FWA-6084 BMC'),'FWA-6084 BMC')
        self.assertEqual(full_sku_name('FWA-6084','FWA6084 BMC'),'FWA6084 BMC')
        self.assertEqual(self.post(task_type='Test',project_id='project',sku_id='e3s',plan_id=pid).get_json()['name'],'Test-Customplan-001')

    def test_existing_test_names_are_readable_but_cannot_be_renamed_or_bulk_changed(self):
        self.assertEqual(self.client.patch('/api/tasks/task1',json={'name':'Changed'}).status_code,400)
        data={'projects':[{'id':'project','plans':[{'id':'a','tasks':[{'id':'task1','name':'Changed'}]}]}]}
        self.assertEqual(self.client.post('/api/projects',json=data).status_code,400)
        self.assertEqual(next(t for t in self.client.get('/api/tasks').get_json()['tasks'] if t['id']=='task1')['name'],'Task 1')

    def test_lock_and_series_exhaustion(self):
        with self.Session() as session:session.get(Task,'task1').execution_active=True;session.commit()
        self.assertEqual(self.post(task_type='Test',plan_id='a').status_code,409)
        self.assertEqual(self.post(task_type='Plan',project_id='project').status_code,200)
        with self.Session() as session:
            session.query(TaskNameSeries).one().last_number=999;session.commit()
        self.assertEqual(self.post(task_type='Plan',project_id='project').status_code,409)

    def test_renaming_project_sku_and_plan_preserves_links_counts_and_numbering(self):
        self.add_skus()
        planning=self.post(task_type='Plan',project_id='project',sku_id='sata').get_json()
        testing=self.post(task_type='Test',project_id='project',sku_id='sata',plan_id='a').get_json()
        self.assertEqual(self.client.post('/api/rename_project',json={'old_name':'SKY-712V4','new_name':'SKY-712V5'}).status_code,200)
        self.assertEqual(self.client.post('/api/rename_plan',json={'project':'SKY-712V5','old_name':'Plan A','new_name':'Renamed Plan'}).status_code,200)
        with self.Session() as session:
            info=session.get(ProjectInformation,'project')
            document=json.loads(info.document)
            document['skus'][0]['name']='SATA revised'
            info.document=json.dumps(document)
            session.commit()
        rows={t['id']:t for t in self.client.get('/api/tasks').get_json()['tasks']}
        for task in (planning,testing):
            self.assertEqual(rows[task['id']]['name'],task['name'])
            self.assertEqual(rows[task['id']]['project_id'],'project')
            self.assertEqual(rows[task['id']]['sku_id'],'sata')
            self.assertEqual(rows[task['id']]['sku_name'],'SKY-712V5 SATA revised')
        self.assertEqual(rows[testing['id']]['plan_id'],'a')
        self.assertEqual(rows[testing['id']]['plan_name'],'Renamed Plan')
        project=self.client.get('/api/projects').get_json()['projects'][0]
        self.assertEqual(project['planning_task_count'],1)
        self.assertEqual(len(next(p for p in project['plans'] if p['id']=='a')['tasks']),3)
        self.assertEqual(self.post(task_type='Plan',project_id='project',sku_id='sata').get_json()['name'],'Plan-SKY712V5SATArevised-002')
        self.assertEqual(self.post(task_type='Test',project_id='project',sku_id='sata',plan_id='a').get_json()['name'],'Test-RenamedPlan-002')

    def test_names_are_global_across_task_types_and_projects(self):
        with self.Session() as session:
            session.get(ProjectPlan,'a').name='Project'
            session.add(Project(id='peer',name='Project!'))
            session.commit()
        first=self.post(task_type='Plan',project_id='project').get_json()
        second=self.post(task_type='Test',project_id='project',plan_id='a').get_json()
        third=self.post(task_type='Plan',project_id='peer').get_json()
        self.assertEqual([first['name'],second['name'],third['name']],['Plan-Project-001','Test-Project-001','Plan-Project-002'])

    def test_deleted_other_type_keeps_global_name_reserved(self):
        with self.Session() as session:
            session.get(ProjectPlan,'a').name='Project';session.commit()
        first=self.post(task_type='Plan',project_id='project').get_json()
        self.assertEqual(self.client.delete('/api/tasks/'+first['id']).status_code,200)
        self.assertEqual(self.post(task_type='Test',project_id='project',plan_id='a').get_json()['name'],'Test-Project-001')

    def test_repair_duplicate_keeps_first_name_and_all_task_ids_evidence(self):
        from models import GlobalTaskName, TaskNameReservation, TaskTestCase
        from task_management import ensure_global_names
        with self.Session() as session:
            session.get(ProjectPlan,'a').name='Project';session.commit()
        first=self.post(task_type='Plan',project_id='project').get_json()
        later=self.post(task_type='Test',project_id='project',plan_id='a').get_json()
        with self.Session() as session:
            session.query(GlobalTaskName).delete()
            session.get(Task,later['id']).name=first['name']
            session.get(TaskNameReservation,later['id']).name=first['name']
            series=session.get(TaskNameSeries,json.dumps(['Test','project','a']))
            series.last_number=1
            session.commit()
        with self.Session() as session:
            changes=ensure_global_names(session);session.commit()
            self.assertEqual(changes,[dict(task_id=later['id'],task_type='Test',old_name='Plan-Project-001',new_name='Plan-Project-002')])
            self.assertEqual(session.get(PlanningTask,first['id']).name,'Plan-Project-001')
            self.assertEqual(session.get(Task,later['id']).plan_id,'a')
        with self.Session() as session:
            self.assertEqual(ensure_global_names(session),[]);session.commit()

    def test_project_deletion_cannot_free_a_globally_issued_name(self):
        from models import GlobalTaskName
        first=self.post(task_type='Plan',project_id='project').get_json()
        response=self.client.post('/api/delete_project',json={'project_id':'project','project':'Project','confirm':True})
        self.assertEqual(response.status_code,200,response.get_json())
        with self.Session() as session:
            self.assertIsNotNone(session.get(GlobalTaskName,'plan-project-001'))
            session.add(Project(id='replacement',name='Project!'));session.commit()
        self.assertEqual(self.post(task_type='Plan',project_id='replacement').get_json()['name'],'Plan-Project-002')

    def test_concurrent_plan_and_test_creation_share_global_names(self):
        with self.Session() as session:
            session.get(ProjectPlan,'a').name='Project';session.commit()
        def create(index):
            with api.app.test_client() as client:
                data={'task_type':'Test','project_id':'project','plan_id':'a'} if index%2 else {'task_type':'Plan','project_id':'project'}
                response=client.post('/api/tasks',json=data)
                self.assertEqual(response.status_code,200,response.get_json())
                return response.get_json()['name']
        with ThreadPoolExecutor(max_workers=4) as pool:
            names=list(pool.map(create,range(8)))
        self.assertEqual(set(names),{f'{kind}-Project-{n:03d}' for kind in ('Plan','Test') for n in range(1,5)})

    def test_new_prefix_continues_old_series_without_renaming_issued_codes(self):
        from models import TaskNameReservation, GlobalTaskName
        scope=json.dumps(['Plan','project',None])
        with self.Session() as session:
            session.add(PlanningTask(id='prior-plan',project_id='project',name='Project-007',sku_name=''))
            session.add(TaskNameSeries(scope=scope,last_number=7))
            session.add(TaskNameReservation(task_id='prior-plan',project_id='project',task_type='Plan',name='Project-007',sku_name=''))
            session.add(GlobalTaskName(name_key='project-007',name='Project-007',task_id='prior-plan'))
            session.commit()
        query={'task_type':'Plan','project_id':'project'}
        self.assertEqual(self.client.get('/api/tasks/name-preview',query_string=query).get_json()['name'],'Plan-Project-008')
        self.assertEqual(self.post(**query).get_json()['name'],'Plan-Project-008')
        with self.Session() as session:self.assertEqual(session.get(PlanningTask,'prior-plan').name,'Project-007')
