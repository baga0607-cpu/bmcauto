import json
import sys
import types
import unittest
from unittest.mock import patch
import test_single_case_repository as fixtures
import app as api
import task_environment as te
from models import Task, TaskTestCase

class TaskEnvironmentTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp
    add_case = fixtures.SingleCaseRepositoryTest.add_case

    def save(self, task, **settings):
        return self.client.put('/api/tasks/' + task + '/settings', json=settings)

    def test_independent_roundtrip_and_no_global_fallback(self):
        self.assertEqual(self.save('task1', host='https://one.invalid', password='one', cs_host='console-one').status_code, 200)
        self.assertEqual(self.save('task2', host='https://two.invalid', password='two', cs_host='console-two').status_code, 200)
        for name, host in [('task1', 'https://one.invalid'), ('task2', 'https://two.invalid')]:
            self.assertEqual(self.client.get('/api/tasks/'+name+'/settings').get_json()['host'], host)
        self.assertEqual(self.client.get('/api/settings').status_code, 410)
        self.assertEqual(self.client.post('/api/settings', json={'host':'global'}).status_code, 410)
        self.assertEqual(self.client.get('/api/config').status_code, 410)
        created=self.client.post('/api/tasks', json={'plan_id':'a','name':'Empty'}).get_json()['id']
        self.assertEqual(self.client.get('/api/tasks/'+created+'/settings').get_json()['host'], '')

    def test_missing_environment_rejects_before_clearing_evidence(self):
        tc=self.add_case()
        with self.Session() as session:
            session.get(Task, 'task1').environment_config=None
            session.add(TaskTestCase(task_id='task1',testcase_id=tc['id'],status='Passed',result_json='{"kept":true}',log_text='kept'))
            session.commit()
        (self.root/'config.yaml').write_text('redfish: {host: https://global.invalid}')
        result=self.client.post('/api/tasks/task1/execution/start',json={'testcase_ids':[tc['id']]})
        self.assertEqual(result.status_code,400,result.get_json())
        with self.Session() as session:
            row=session.query(TaskTestCase).filter_by(task_id='task1').one()
            self.assertEqual(row.status,'Passed'); self.assertEqual(row.log_text,'kept')
            self.assertFalse(session.get(Task,'task1').execution_active)

    def test_lock_only_running_task_and_retest_only_owner(self):
        tc=self.add_case()
        with self.Session() as session:
            for tid in ['task1','task2']:
                session.add(TaskTestCase(task_id=tid,testcase_id=tc['id'],status='Passed',result_json='{"kept":true}',log_text='kept'))
            session.get(Task,'task1').execution_active=True;session.commit()
        self.assertEqual(self.save('task1',host='https://locked.invalid').status_code,409)
        self.assertEqual(self.save('task2',host='https://peer.invalid').status_code,200)
        with self.Session() as session:
            rows={r.task_id:r for r in session.query(TaskTestCase).all()}
            self.assertFalse(rows['task1'].needs_retest);self.assertTrue(rows['task2'].needs_retest)
            self.assertEqual(rows['task2'].log_text,'kept')
        self.assertEqual(self.save('task2',cs_port=70000).status_code,400)

    def test_worker_uses_each_tasks_redfish_and_console_environment(self):
        tc=self.add_case();captured=[]
        class Client:
            def login(self,**kwargs): pass
            def logout(self): pass
            def get(self,*args,**kwargs): return types.SimpleNamespace(status=200,dict={})
        def factory(**kwargs): captured.append(kwargs);return Client()
        with patch.dict(sys.modules,{'redfish':types.SimpleNamespace(redfish_client=factory)}):
            for tid,host in [('task1','https://one.invalid'),('task2','https://two.invalid')]:
                self.save(tid,host=host,username=tid,password=tid,cs_host='console-'+tid,verify_ssl=True)
                self.client.post('/api/tasks/'+tid+'/testcases/import',json={'testcases':[tc['id']]})
                token=self.client.post('/api/tasks/'+tid+'/execution/start',json={'testcase_ids':[tc['id']]}).get_json()['execution_token']
                with patch.object(api,'ConsoleClient') as console:
                    def execute(root,module,client,context,preset):
                        self.assertEqual(context['redfish']['host'],host)
                        self.assertEqual(context['console_server']['host'],'console-'+tid)
                        client._get_console_client()
                    with patch.object(api.sc,'execute_script',side_effect=execute):
                        response=self.client.post('/api/run',json={'task_id':tid,'testcase_id':tc['id'],'execution_token':token})
                        self.assertEqual(response.status_code,200,response.get_json())
                        sid=response.get_json()['session_id'];api.run_sessions[sid]['thread'].join(10)
                        self.assertFalse(api.run_sessions[sid]['thread'].is_alive())
                        self.assertEqual(console.call_args.args[0]['redfish']['host'],host)
                        api.run_sessions.pop(sid,None)
                self.client.post('/api/tasks/'+tid+'/execution/finish',json={'execution_token':token})
        self.assertEqual([c['base_url'] for c in captured],['https://one.invalid','https://two.invalid'])
        self.assertTrue(all(c['cafile'] for c in captured))

    def test_nested_environment_can_be_preserved_and_edited(self):
        settings=te.normalize({'redfish':{'host':'https://existing.invalid'},'console_server':{'port':23,'protocol':'telnet'}})
        self.assertEqual(settings['host'],'https://existing.invalid');self.assertEqual(settings['cs_port'],23)
