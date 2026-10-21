import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as api
import single_case as sc
import plan_state as ps
from models import Base, Project, ProjectPlan, TestCase, Task, TaskTestCase, RepositoryCase

SOURCE = """TEST_CASE = {
    'name': 'Service entry', 'description': 'Read an entry',
    'parameters': {'preset': {'type':'string', 'default':'/redfish/v1/'},
                   'expected': {'type':'integer', 'default':200}}
}
def execute(client, context=None, preset=None):
    client.get(preset)
    assert context['case_settings']['expected'] == 200
"""


class SingleCaseRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engine = create_engine('sqlite:///' + str(self.root / 'test.db'))
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as s:
            s.add_all([Project(id='project', name='Project'),
                       ProjectPlan(id='a', project_id='project', name='Plan A', folders_migrated=True),
                       ProjectPlan(id='b', project_id='project', name='Plan B', folders_migrated=True),
                       Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='task1', plan_id='a', name='Task 1'),
                       Task(environment_config='{"host":"https://example.invalid","username":"test","password":"test"}', id='task2', plan_id='a', name='Task 2')])
            s.commit()
        for name, value in [('DbSession', self.Session), ('MAIN_PROGRAM_DIR', str(self.root)),
                            ('WORKSPACE_DIR', str(self.root))]:
            patcher = patch.object(api, name, value); patcher.start(); self.addCleanup(patcher.stop)
        self.client = api.app.test_client()
        self.repository = self.client.post('/api/repository/testcases', json={'source':SOURCE}).get_json()

    def add_case(self, plan='a'):
        response = self.client.post(f'/api/plans/{plan}/repository/testcases', json={'repository_id':self.repository['id']})
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    def definition(self, tc, plan='a'):
        return self.client.get(f'/api/plans/{plan}/testcases/{tc["id"]}/definition').get_json()

    def update(self, tc, data, plan='a'):
        return self.client.put(f'/api/plans/{plan}/testcases/{tc["id"]}/definition', json=data)

    def test_direct_plan_import_root_move_and_restart(self):
        response=self.client.post('/api/plans/a/testcases/import-python',json={'source':SOURCE,'folder_id':None})
        self.assertEqual(response.status_code,201,response.get_json())
        case=response.get_json()
        self.assertIsNone(case['folder_id'])
        self.assertEqual(self.definition(case)['settings']['expected'],200)
        with self.Session() as session:
            self.assertEqual(session.query(RepositoryCase).count(),1)
            self.assertIsNone(session.get(TestCase,case['id']).repository_id)
        folder=self.client.post('/api/plans/a/folders',json={'name':'Folder'}).get_json()['id']
        for destination in (folder,None):
            response=self.client.post('/api/plans/a/testcases/move',json={'testcase_ids':[case['id']],'folder_id':destination})
            self.assertEqual(response.status_code,200,response.get_json())
        ps.migrate_current_state(self.engine,self.root/'migration.log')
        with self.Session() as session:
            self.assertIsNone(session.get(TestCase,case['id']).folder_id)
        self.assertEqual(self.definition(case)['source'],SOURCE)

    def test_direct_import_folder_validation_and_lock(self):
        folder=self.client.post('/api/plans/a/folders',json={'name':'Folder'}).get_json()['id']
        foreign=self.client.post('/api/plans/b/folders',json={'name':'Other'}).get_json()['id']
        for source,target,status in [('bad syntax !',folder,400),(SOURCE,foreign,400),(SOURCE,folder,201),(SOURCE,folder,409)]:
            response=self.client.post('/api/plans/a/testcases/import-python',json={'source':source,'folder_id':target})
            self.assertEqual(response.status_code,status,response.get_json())
        with self.Session() as session:
            self.assertEqual(session.query(TestCase).count(),1)
            self.assertEqual(session.query(RepositoryCase).count(),1)
            self.assertEqual(session.query(TestCase).one().folder_id,folder)
            session.get(Task,'task1').execution_active=True
            session.commit()
        response=self.client.post('/api/plans/a/testcases/import-python',json={'source':SOURCE.replace('Service entry','Locked')})
        self.assertEqual(response.status_code,409,response.get_json())
        self.assertEqual(len(list(self.root.glob('testcase_database/scripts/*/case.py'))),1)

    def test_source_import_preserves_plan_settings_and_independence(self):
        source=self.add_case('a')
        self.assertEqual(self.update(source,{'settings':{'preset':'/adapted','expected':204},'settings_revision':0}).status_code,200)
        folder=self.client.post('/api/plans/b/folders',json={'name':'Destination'}).get_json()['id']
        payload={'source_type':'plan','source_plan_id':'a','kind':'case','id':source['id'],'target_folder_id':folder}
        response=self.client.post('/api/plans/b/import-cases',json=payload)
        self.assertEqual(response.status_code,201,response.get_json())
        copied=response.get_json()['added'][0]
        self.assertEqual(copied['folder_id'],folder)
        self.assertEqual(self.definition(copied,'b')['settings'],{'preset':'/adapted','expected':204})
        self.assertNotEqual(copied['id'],source['id'])
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0]
        target=conflict['targets'][0]
        self.assertTrue(conflict['same_version'])
        skipped=self.client.post('/api/plans/b/import-cases',json={**payload,'decisions':{source['id']:{'action':'skip','target_id':target['id'],'target_token':target['token']}}})
        self.assertEqual(skipped.get_json()['skipped'],['Service entry'])
        self.assertEqual(self.update(copied,{'settings':{'preset':'/target','expected':205},'settings_revision':0},'b').status_code,200)
        self.assertEqual(self.definition(source)['settings']['expected'],204)
        repo=self.client.post('/api/repository/testcases',json={'source':SOURCE.replace('Service entry','Default case')}).get_json()
        result=self.client.post('/api/plans/b/import-cases',json={'source_type':'repository','kind':'case','id':repo['id']}).get_json()
        self.assertEqual(self.definition(result['added'][0],'b')['settings']['expected'],200)
        self.assertIsNone(result['added'][0]['folder_id'])
        with self.Session() as session:self.assertEqual(session.query(TaskTestCase).count(),0)

    def test_import_nested_folders_reuses_destination_and_rolls_back(self):
        top=self.client.post('/api/plans/a/folders',json={'name':'Top'}).get_json()['id']
        child=self.client.post('/api/plans/a/folders',json={'name':'Child','parent_id':top}).get_json()['id']
        self.client.post('/api/plans/a/folders',json={'name':'Empty','parent_id':child})
        source=self.client.post('/api/plans/a/testcases/import-python',json={'source':SOURCE,'folder_id':child}).get_json()
        payload={'source_type':'plan','source_plan_id':'a','kind':'folder','id':top}
        response=self.client.post('/api/plans/b/import-cases',json=payload)
        self.assertEqual(response.status_code,201,response.get_json())
        folders=self.client.get('/api/plans/b/folders').get_json()
        self.assertEqual(len(folders),3)
        self.assertEqual(self.definition(response.get_json()['added'][0],'b')['source'],SOURCE)
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0]
        target=conflict['targets'][0]
        again=self.client.post('/api/plans/b/import-cases',json={**payload,'decisions':{source['id']:{'action':'skip','target_id':target['id'],'target_token':target['token']}}}).get_json()
        self.assertEqual(len(again['added']),0);self.assertEqual(len(again['skipped']),1)
        self.assertEqual(len(self.client.get('/api/plans/b/folders').get_json()),3)
        # New source subtree fails after a first file was copied; no partial folders/files survive.
        broken=self.client.post('/api/plans/a/folders',json={'name':'Broken'}).get_json()['id']
        for name in ['First valid','Missing file']:
            item=self.client.post('/api/plans/a/testcases/import-python',json={'source':SOURCE.replace('Service entry',name),'folder_id':broken}).get_json()
        with self.Session() as session:sc.script_file(self.root,session.get(TestCase,item['id'])).unlink()
        files=set(self.root.glob('testcase_database/scripts/*/case.py'))
        response=self.client.post('/api/plans/b/import-cases',json={**payload,'id':broken})
        self.assertGreaterEqual(response.status_code,400)
        self.assertEqual(set(self.root.glob('testcase_database/scripts/*/case.py')),files)
        self.assertEqual(len(self.client.get('/api/plans/b/folders').get_json()),3)

    def test_import_conflicts_same_version_overwrite_and_different_version_coexist(self):
        source=self.add_case('a')
        payload={'source_type':'plan','source_plan_id':'a','kind':'case','id':source['id']}
        copied=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['added'][0]
        self.update(source,{'settings':{'preset':'/changed','expected':202},'settings_revision':0})
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0]
        self.assertTrue(conflict['same_version'])
        target=conflict['targets'][0]
        decision={'action':'overwrite','target_id':target['id'],'target_token':target['token']}
        result=self.client.post('/api/plans/b/import-cases',json={**payload,'decisions':{source['id']:decision}})
        self.assertEqual(result.status_code,201,result.get_json())
        self.assertEqual(result.get_json()['updated'][0]['id'],copied['id'])
        self.assertEqual(self.definition(copied,'b')['settings']['expected'],202)
        # A new repository generation of the same name can coexist without renaming.
        repo=self.client.post('/api/repository/testcases',json={'source':SOURCE}).get_json()
        payload={'source_type':'repository','kind':'case','id':repo['id']}
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0]
        self.assertFalse(conflict['same_version']);target=conflict['targets'][0]
        decision={'action':'coexist','target_id':target['id'],'target_token':target['token']}
        result=self.client.post('/api/plans/b/import-cases',json={**payload,'decisions':{repo['id']:decision}})
        self.assertEqual(result.status_code,201,result.get_json())
        twin=result.get_json()['added'][0]
        self.assertEqual(twin['tc_name'],copied['tc_name'])
        self.assertNotEqual(twin['source_version'],copied['source_version'])
        self.assertEqual(self.definition(twin,'b')['settings']['expected'],200)
        # Reimporting this version offers overwrite only, even with another version present.
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0]
        self.assertTrue(conflict['same_version']);self.assertEqual(conflict['targets'][0]['id'],twin['id'])

    def test_import_overwrite_update_keeps_evidence_and_restores_on_commit_failure(self):
        copied=self.add_case('b')
        with self.Session() as session:
            session.add(Task(id='target-task',plan_id='b',name='Target'))
            session.add(TaskTestCase(task_id='target-task',testcase_id=copied['id'],status='Passed',log_text='preserve log'))
            session.commit()
        repo=self.client.post('/api/repository/testcases',json={'source':SOURCE+'\n# newer source'}).get_json()
        payload={'source_type':'repository','kind':'case','id':repo['id']}
        conflict=self.client.post('/api/plans/b/import-cases',json=payload).get_json()['conflicts'][0];target=conflict['targets'][0]
        payload['decisions']={repo['id']:{'action':'overwrite','target_id':target['id'],'target_token':target['token']}}
        with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('simulated failure')):
            self.assertGreaterEqual(self.client.post('/api/plans/b/import-cases',json=payload).status_code,400)
        self.assertEqual(self.definition(copied,'b')['source'],SOURCE)
        result=self.client.post('/api/plans/b/import-cases',json=payload)
        self.assertEqual(result.status_code,201,result.get_json())
        self.assertEqual(result.get_json()['updated'][0]['source_version'],repo['source_version'])
        with self.Session() as session:
            membership=session.query(TaskTestCase).filter_by(testcase_id=copied['id']).one()
            self.assertEqual(membership.log_text,'preserve log');self.assertTrue(membership.needs_retest)
        self.assertEqual(self.client.post('/api/plans/b/import-cases',json=payload).status_code,409)

    def test_folder_import_resolves_versions_within_the_same_batch(self):
        folder=self.client.post('/api/repository/folders',json={'name':'Versions'}).get_json()['id']
        for suffix in ('# one','# two'):
            self.client.post('/api/repository/testcases',json={'source':SOURCE+'\n'+suffix,'folder_id':folder})
        payload={'source_type':'repository','kind':'folder','id':folder}
        response=self.client.post('/api/plans/b/import-cases',json=payload)
        self.assertEqual(response.status_code,409,response.get_json())
        conflict=response.get_json()['conflicts'][0];target=conflict['targets'][0]
        self.assertTrue(target['id'].startswith('incoming:'))
        self.assertEqual(self.client.get('/api/plans/b/folders').get_json(),[])
        result=self.client.post('/api/plans/b/import-cases',json={**payload,'decisions':{conflict['id']:{'action':'coexist','target_id':target['id'],'target_token':target['token']}}})
        self.assertEqual(result.status_code,201,result.get_json())
        self.assertEqual([c['tc_name'] for c in result.get_json()['added']],['Service entry','Service entry'])
        self.assertEqual(len({c['source_version'] for c in result.get_json()['added']}),2)

    def test_import_rejects_foreign_source_destination_self_and_locked(self):
        source=self.add_case('a')
        folder=self.client.post('/api/plans/a/folders',json={'name':'Source'}).get_json()['id']
        base={'source_type':'plan','source_plan_id':'a','kind':'case','id':source['id']}
        for plan,payload in [('a',base),('b',{**base,'source_plan_id':'b'}),('b',{**base,'target_folder_id':folder})]:
            self.assertEqual(self.client.post('/api/plans/'+plan+'/import-cases',json=payload).status_code,400)
        with self.Session() as session:
            session.add(Task(id='busy',plan_id='b',name='Busy',execution_active=True));session.commit()
        self.assertEqual(self.client.post('/api/plans/b/import-cases',json=base).status_code,409)

    def test_independent_source_and_settings_keep_generation(self):
        a, b = self.add_case(), self.add_case('b')
        definition = self.definition(a)
        response = self.update(a, dict(source=SOURCE+'\n# Project adaptation\n', settings={'preset':'/custom','expected':202}, settings_revision=0))
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()['source_version'], self.repository['source_version'])
        self.assertEqual(self.definition(b, 'b')['settings']['preset'], '/redfish/v1/')
        self.assertEqual(self.definition(b, 'b')['source'], SOURCE)
        self.assertEqual(self.definition(a)['settings_revision'], 1)
        with self.Session() as s:
            self.assertEqual(s.get(RepositoryCase,self.repository['id']).source_text, SOURCE)

    def test_plan_change_marks_all_existing_results_preserving_evidence(self):
        tc = self.add_case()
        with self.Session() as s:
            for task_id in ('task1','task2'):
                s.add(TaskTestCase(task_id=task_id,testcase_id=tc['id'],status='Passed',log_text='old log',result_json='{"old":true}',executed_at='earlier'))
            s.commit()
        self.assertEqual(self.update(tc, dict(settings={'preset':'changed','expected':200},settings_revision=0)).status_code, 200)
        for task_id in ('task1','task2'):
            data = self.client.get(f'/api/tasks/{task_id}/summary').get_json()['testcases'][0]
            self.assertTrue(data['needs_retest']); self.assertTrue(data['retest_message'])
            self.assertEqual(data['status'],'Passed'); self.assertEqual(data['log_text'],'old log')
            self.assertEqual(data['result'],{'old':True})

    def test_noop_does_not_require_retest_and_never_run_remains_unrun(self):
        tc = self.add_case()
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='TBD')); s.commit()
        data = dict(settings={'preset':'/redfish/v1/','expected':200}, settings_revision=0)
        self.assertEqual(self.update(tc,data).get_json()['settings_revision'],0)
        data['settings']['preset']='new'
        self.update(tc,data)
        result = self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]
        self.assertFalse(result['needs_retest']); self.assertEqual(result['status'],'TBD')

    def test_running_case_locked_but_other_case_can_be_adapted(self):
        tc = self.add_case()
        repository = self.client.post('/api/repository/testcases', json={'source':SOURCE.replace('Service entry','Other')}).get_json()
        other = self.client.post('/api/plans/a/repository/testcases',json={'repository_id':repository['id']}).get_json()
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='Running'))
            task=s.get(Task,'task1'); task.execution_active=True; task.execution_selection=json.dumps([tc['id']]); s.commit()
        edit=dict(settings={'preset':'new','expected':200},settings_revision=0)
        self.assertEqual(self.update(tc,edit).status_code,409)
        self.assertEqual(self.update(other,edit).status_code,200)
        self.assertEqual(self.definition(tc)['source'],SOURCE)

    def test_conflicting_edit_and_cross_plan_are_rejected(self):
        tc = self.add_case()
        edit=dict(settings={'preset':'new','expected':200},settings_revision=0)
        self.assertEqual(self.update(tc,edit,plan='b').status_code,404)
        self.assertEqual(self.update(tc,edit).status_code,200)
        self.assertEqual(self.update(tc,edit).status_code,409)

    def test_metadata_is_not_executed_and_invalid_schema_rejected(self):
        marker=self.root/'executed'
        response=self.client.post('/api/repository/testcases',json={'source':f"open({str(marker)!r}, 'w').write('executed')\n"+SOURCE})
        self.assertEqual(response.status_code,201); self.assertFalse(marker.exists())
        for source in ('TEST_CASE = make_case()',SOURCE.replace("'type':'integer'","'type':'invalid'"),SOURCE.replace('def execute','async def execute')):
            response=self.client.post('/api/repository/testcases',json={'source':source})
            self.assertEqual(response.status_code,400,response.get_json())

    def test_invalid_settings_cannot_write_source(self):
        tc=self.add_case()
        for value in (None,True,'200'):
            response=self.update(tc,dict(source=SOURCE+'# changed',settings={'preset':'x','expected':value},settings_revision=0))
            self.assertEqual(response.status_code,400,response.get_json())
            self.assertEqual(self.definition(tc)['source'],SOURCE)

    def test_failed_commit_restores_plan_source_and_settings(self):
        tc=self.add_case()
        with patch.object(self.Session.class_, 'commit', side_effect=RuntimeError('write failed')):
            response=self.update(tc,dict(source=SOURCE+'# adaptation',settings={'preset':'new','expected':200},settings_revision=0))
        self.assertEqual(response.status_code,500)
        definition=self.definition(tc)
        self.assertEqual(definition['source'],SOURCE)
        self.assertEqual(definition['settings_revision'],0)
        self.assertEqual(definition['settings']['preset'],'/redfish/v1/')

    def test_copy_and_export_import_preserve_single_contract(self):
        tc=self.add_case()
        response=self.client.post('/api/import_tc',json={'plan_id':'b','tc_name':'Copied','system_id':tc['id']})
        self.assertEqual(response.status_code,201,response.get_json())
        self.assertEqual(self.definition(response.get_json(),'b')['source_version'],self.repository['source_version'])
        response=self.client.post('/api/import_tc',json={'plan_id':'b','tc_name':'Round trip','script_kind':'single',
            'source':SOURCE,'source_version':self.repository['source_version'],'settings':{'preset':'/exported','expected':200}})
        self.assertEqual(response.status_code,201,response.get_json())
        self.assertEqual(self.definition(response.get_json(),'b')['settings']['preset'],'/exported')

    def test_execute_reads_plan_file_each_time(self):
        tc=self.add_case(); paths=[]
        client=SimpleNamespace(get=lambda path: paths.append(path))
        context={'case_settings':{'expected':200}}
        with self.Session() as s:
            case=s.get(TestCase,tc['id']); module=case.script_path+'.case'
        sc.execute_script(str(self.root),module,client,context,'first')
        self.update(tc,dict(source=SOURCE.replace('client.get(preset)',"client.get('adapted')"),settings={'preset':'new','expected':200},settings_revision=0))
        sc.execute_script(str(self.root),module,client,context,'second')
        self.assertEqual(paths,['first','adapted'])

    def test_rerun_clears_retest_only_when_completed(self):
        tc=self.add_case()
        with self.Session() as s:
            s.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='Passed',needs_retest=True))
            s.commit(); ps.begin_write(s); token=ps.start_execution(s,'task1',[tc['id']]); s.commit()
            row=s.query(TaskTestCase).one(); self.assertTrue(row.needs_retest)
            ps.begin_write(s); ps.save_result(s,'task1',{'id':tc['id'],'execution_token':token,'status':'Passed','result':{}})
            s.commit(); self.assertFalse(row.needs_retest)

    def test_task_runner_ignores_submitted_steps_and_settings(self):
        tc=self.add_case()
        self.client.post('/api/tasks/task1/testcases/import',json={'testcases':[tc['id']]})
        token=self.client.post('/api/tasks/task1/execution/start',json={'testcase_ids':[tc['id']]}).get_json()['execution_token']
        (self.root/'config.yaml').write_text('redfish:\n  host: https://example.invalid\n  username: user\n  password: placeholder\n',encoding='utf-8')
        calls=[]
        fake=SimpleNamespace(login=lambda **kwargs:None,logout=lambda:None,get=lambda path,**kwargs:calls.append(path))
        with patch('redfish.redfish_client',return_value=fake):
            response=self.client.post('/api/run',json={'task_id':'task1','testcase_id':tc['id'],'execution_token':token,
                'steps':[{'module_path':'malicious.override','preset':'wrong'}],'settings':{'expected':500}})
            self.assertEqual(response.status_code,200,response.get_json())
            sid=response.get_json()['session_id']; api.run_sessions[sid]['thread'].join(timeout=10)
            self.assertFalse(api.run_sessions[sid]['thread'].is_alive())
        result=self.client.get('/api/tasks/task1/summary').get_json()['testcases'][0]
        self.assertEqual(calls,['/redfish/v1/'])
        self.assertEqual(result['status'],'Passed',result['result'])
        self.assertEqual(result['result']['settings'],{'preset':'/redfish/v1/','expected':200})


if __name__ == '__main__':
    unittest.main()
