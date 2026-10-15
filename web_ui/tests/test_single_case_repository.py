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
