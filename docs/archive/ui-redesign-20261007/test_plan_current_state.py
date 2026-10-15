import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as api
from models import Base, Project, ProjectPlan, TestCase, Task, TaskTestCase

class CurrentStateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = create_engine('sqlite:///' + self.tmp.name + '/test.db')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as s:
            s.add_all([Project(id='project',name='Project'),ProjectPlan(id='p',project_id='project',name='Plan'),ProjectPlan(id='q',project_id='project',name='Other')]); s.commit()
        self.patch = patch.object(api,'DbSession',self.Session); self.patch.start()
        self.client = api.app.test_client()
    def tearDown(self):
        self.patch.stop(); self.engine.dispose(); self.tmp.cleanup()
    def test_delete_then_append_preserves_contiguous_folder_order(self):
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name):
            for mode in ('single','bulk'):
                with self.subTest(mode=mode):
                    cases={}
                    for name in ('A','B','C','D'):
                        response=self.client.post('/api/import_tc',json={'plan_id':'p','tc_name':mode+name,'folder_path':mode,'steps':[]})
                        self.assertEqual(response.status_code,200,response.get_json())
                        cases[name]=response.get_json()['id']
                    untouched=self.client.post('/api/import_tc',json={'plan_id':'q','tc_name':mode+'untouched','folder_path':mode,'steps':[]}).get_json()['id']
                    with self.Session() as session:
                        session.get(TestCase,untouched).position=7;session.commit()
                    if mode=='single':
                        response=self.client.delete('/api/testcases/'+cases['B'],json={'confirm':True})
                        remaining=['A','C','D']
                    else:
                        response=self.client.post('/api/delete_tc',json={'plan_id':'p','tcs':[{'id':cases['B']},{'id':cases['D']}],'confirm':True})
                        remaining=['A','C']
                    self.assertEqual(response.status_code,200,response.get_json())
                    with self.Session() as session:
                        folder_id=session.get(TestCase,cases['A']).folder_id
                        rows=session.query(TestCase).filter_by(folder_id=folder_id).order_by(TestCase.position).all()
                        self.assertEqual([(r.system_id,r.position) for r in rows],[(cases[n],i) for i,n in enumerate(remaining)])
                        self.assertEqual(session.get(TestCase,untouched).position,7)
                    appended=self.client.post('/api/import_tc',json={'plan_id':'p','tc_name':mode+'New','folder_path':mode,'steps':[]})
                    self.assertEqual(appended.status_code,200,appended.get_json())
                    expected=[cases[n] for n in remaining]+[appended.get_json()['id']]
                    with self.Session() as session:
                        rows=session.query(TestCase).filter_by(folder_id=folder_id).order_by(TestCase.position).all()
                        self.assertEqual([(r.system_id,r.position) for r in rows],[(identity,i) for i,identity in enumerate(expected)])

    def test_delete_order_normalization_rolls_back_with_files_on_commit_failure(self):
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name):
            cases=[]
            for name in ('A','B','C'):
                response=self.client.post('/api/import_tc',json={'plan_id':'p','tc_name':name,'folder_path':'Ordered','steps':[]})
                self.assertEqual(response.status_code,200,response.get_json());cases.append(response.get_json()['id'])
            with patch.object(self.Session.class_,'commit',side_effect=RuntimeError('commit failed')):
                response=self.client.delete('/api/testcases/'+cases[1],json={'confirm':True})
                self.assertEqual(response.status_code,500)
            with self.Session() as session:
                rows=session.query(TestCase).filter_by(plan_id='p').order_by(TestCase.position).all()
                self.assertEqual([(r.system_id,r.position) for r in rows],list(zip(cases,range(3))))
            for identity in cases:
                self.assertTrue(Path(self.tmp.name,'testcase_database','scripts',identity,'__testcase__.py').exists())

    def test_runner_persists_current_step_and_connection_errors(self):
        import types
        self.seed_scope()
        class Client:
            def login(self,**kwargs): pass
            def logout(self): pass
        def fail_step(client,context=None):
            raise RuntimeError('Deliberate offline failure')
        def final_step(client,context=None): pass
        modules={
            'redfish':types.SimpleNamespace(redfish_client=lambda **kwargs:Client()),
            'verification.offline_failure':types.SimpleNamespace(execute=fail_step,STEP_NAME='Offline failure'),
            'testcase_database.steps.common.final_judgement':types.SimpleNamespace(execute=final_step),
        }
        Path(self.tmp.name, 'a', '__testcase__.py').write_text("STEPS = [{'module_path':'verification.offline_failure'}]", encoding='utf-8')
        Path(self.tmp.name,'config.yaml').write_text('redfish: {host: sandbox.invalid, username: test, password: test}')
        def execute(session_id):
            token=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a']}).get_json()['execution_token']
            response=self.client.post('/api/run',json={'task_id':'t','testcase_id':'a','execution_token':token,'session_id':session_id,'steps':[{'module_path':'verification.offline_failure'}]})
            self.assertEqual(response.status_code,200,response.get_json())
            api.run_sessions[session_id]['thread'].join(5)
            self.assertFalse(api.run_sessions[session_id]['thread'].is_alive())
            self.client.post('/api/tasks/t/execution/finish',json={'execution_token':token})
            api.run_sessions.pop(session_id,None)
            return next(row for row in self.client.get('/api/tasks/t/summary').get_json()['testcases'] if row['id']=='a')
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name),patch.object(api,'WORKSPACE_DIR',self.tmp.name),patch.dict(sys.modules,modules):
            failed=execute('step-detail')
            self.assertEqual(failed['status'],'Failed')
            self.assertIn('Deliberate offline failure',failed['log_text'])
            self.assertIn('Deliberate offline failure',str(failed['result']))
            def connection_failure(**kwargs): raise RuntimeError('Offline connection failure')
            modules['redfish'].redfish_client=connection_failure
            connection=execute('connection-detail')
            self.assertIn('Offline connection failure',connection['log_text'])
            self.assertIn('Offline connection failure',str(connection['result']))
            self.assertNotIn('Deliberate offline failure',connection['log_text'])

    def test_execution_operational_state_recovers_token_without_summary_exposure(self):
        self.seed_scope()
        self.assertEqual(self.client.get('/api/tasks/missing/execution').status_code,404)
        idle=self.client.get('/api/tasks/t/execution').get_json()
        self.assertFalse(idle['execution_active'])
        self.assertIsNone(idle['execution_token'])
        token=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a']}).get_json()['execution_token']
        active=self.client.get('/api/tasks/t/execution').get_json()
        self.assertTrue(active['execution_active'])
        self.assertEqual(active['execution_token'],token)
        self.assertNotIn('execution_token',self.client.get('/api/tasks/t/summary').get_json())
        self.assertEqual(self.client.post('/api/tasks/t/execution/stop',json={'execution_token':active['execution_token']}).status_code,200)
        self.assertIsNone(self.client.get('/api/tasks/t/execution').get_json()['execution_token'])

    def test_empty_child_subtree_requires_acknowledgement(self):
        root=self.client.post('/api/plans/p/folders',json={'name':'Root'}).get_json()
        self.client.post('/api/plans/p/folders',json={'name':'Child','parent_id':root['id']})
        path='/api/folders/'+root['id']
        impact=self.client.get(path+'/impact').get_json()
        self.assertEqual(impact['descendant_folder_count'],1)
        self.assertEqual(impact['testcase_count'],0)
        self.assertTrue(impact['requires_acknowledgement'])
        self.assertEqual(self.client.delete(path,json={'confirm':True}).status_code,400)
        self.assertEqual(self.client.delete(path,json={'confirm':True,'acknowledgement':True}).status_code,200)

    def test_deleted_final_migrated_folder_stays_deleted_on_restart(self):
        from plan_state import migrate_current_state
        from models import PlanSubfolder
        with self.Session() as session:
            session.get(ProjectPlan,'p').category_order='["Custom"]'
            session.add(PlanSubfolder(id='legacy',plan_id='p',subfolder_name='Empty'));session.commit()
        log=Path(self.tmp.name,'migration.log')
        migrate_current_state(self.engine,log)
        root=next(f for f in self.client.get('/api/plans/p/folders').get_json() if f['parent_id'] is None)
        self.assertEqual(self.client.delete('/api/folders/'+root['id'],json={'confirm':True,'acknowledgement':True}).status_code,200)
        self.assertEqual(self.client.get('/api/plans/p/folders').get_json(),[])
        migrate_current_state(self.engine,log)
        self.assertEqual(self.client.get('/api/plans/p/folders').get_json(),[])

    def test_golden_copy_uses_live_folder_after_rename(self):
        with self.Session() as session:
            session.add(Project(id='golden',name='Golden_Project'));session.flush()
            session.add(ProjectPlan(id='plan_golden',project_id='golden',name='plan_golden'));session.commit()
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name):
            imported=self.client.post('/api/import_tc',json={'plan_id':'plan_golden','tc_name':'Golden Case','folder_path':'Network','steps':[]})
            self.assertEqual(imported.status_code,200,imported.get_json())
            source_id=imported.get_json()['id']
            folder=self.client.get('/api/plans/plan_golden/folders').get_json()[0]
            self.assertEqual(self.client.patch('/api/folders/'+folder['id'],json={'name':'Fabric'}).status_code,200)
            copied=self.client.post('/api/fork_tc',json={'plan_id':'p','category':'Fabric','testcase':'Golden Case'})
            self.assertEqual(copied.status_code,200,copied.get_json())
            by_id=self.client.post('/api/fork_tc',json={'plan_id':'q','source_testcase_id':source_id})
            self.assertEqual(by_id.status_code,200,by_id.get_json())
            invalid=self.client.post('/api/fork_tc',json={'plan_id':'q','source_testcase_id':copied.get_json()['id']})
            self.assertEqual(invalid.status_code,400,invalid.get_json())
        with self.Session() as session:
            copy=session.get(TestCase,copied.get_json()['id'])
            self.assertEqual(copy.folder_obj.path,'Fabric')
            self.assertEqual(copy.family_id,session.get(TestCase,source_id).family_id)

    def test_worker_admission_blocks_finish_before_thread_start(self):
        import threading
        self.seed_scope()
        token=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a','b']}).get_json()['execution_token']
        admitted=threading.Event(); release=threading.Event(); responses=[]
        original_start=threading.Thread.start
        def gated_start(worker):
            admitted.set(); release.wait(5); original_start(worker)
        def request_run():
            responses.append(api.app.test_client().post('/api/run',json={'task_id':'t','testcase_id':'a','execution_token':token,'session_id':'admission-gap','steps':[{'module_path':'unused'}]}))
        request_thread=threading.Thread(target=request_run)
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name), patch.object(threading.Thread,'start',gated_start):
            original_start(request_thread)
            try:
                self.assertTrue(admitted.wait(3))
                self.assertEqual(self.client.post('/api/tasks/t/execution/finish',json={'execution_token':token}).status_code,409)
                stopped=self.client.post('/api/tasks/t/execution/stop',json={'execution_token':token})
                self.assertEqual(stopped.get_json()['status'],'stopping')
                self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'Must remain locked'}).status_code,409)
            finally:
                release.set();request_thread.join(5)
                run=api.run_sessions.get('admission-gap')
                if run and run.get('thread'): run['thread'].join(5)
                api.run_sessions.pop('admission-gap',None)
        self.assertEqual(responses[0].status_code,200)
        self.assertFalse(self.client.get('/api/tasks/t/summary').get_json()['execution_active'])

    def test_second_worker_is_rejected_and_stop_keeps_blocked_worker_locked(self):
        import threading, types
        self.seed_scope()
        token=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a','b']}).get_json()['execution_token']
        entered=threading.Event();release=threading.Event()
        class Client:
            def login(self,**kwargs): entered.set();release.wait(5)
            def logout(self): pass
        Path(self.tmp.name,'config.yaml').write_text('redfish: {host: sandbox.invalid, username: test, password: test}')
        payload={'task_id':'t','execution_token':token,'steps':[{'module_path':'unused'}]}
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name),patch.dict(sys.modules,{'redfish':types.SimpleNamespace(redfish_client=lambda **kwargs:Client())}):
            first=self.client.post('/api/run',json=dict(payload,testcase_id='a',session_id='blocked-worker'))
            try:
                self.assertEqual(first.status_code,200);self.assertTrue(entered.wait(3))
                second=self.client.post('/api/run',json=dict(payload,testcase_id='b',session_id='second-worker'))
                self.assertEqual(second.status_code,409,second.get_json())
                stopped=self.client.post('/api/tasks/t/execution/stop',json={'execution_token':token})
                self.assertEqual(stopped.get_json()['status'],'stopping')
                self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'Still locked'}).status_code,409)
            finally:
                release.set()
                for identity in ('blocked-worker','second-worker'):
                    run=api.run_sessions.get(identity)
                    if run and run.get('thread'):run['thread'].join(5)
                    api.run_sessions.pop(identity,None)
        self.assertFalse(self.client.get('/api/tasks/t/summary').get_json()['execution_active'])

    def test_folder_identity_depth_collision_and_move(self):
        r = self.client.post('/api/plans/p/folders',json={'name':' Network '})
        self.assertEqual(r.status_code,201,r.get_json()); root=r.get_json()
        self.assertEqual(self.client.get('/api/plans/p/folders').get_json()[0]['id'],root['id'])
        self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'NETWORK'}).status_code,409)
        child=self.client.post('/api/plans/p/folders',json={'name':'Ports','parent_id':root['id']}).get_json()
        self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'Third','parent_id':child['id']}).status_code,400)
        self.assertEqual(self.client.patch('/api/folders/'+root['id'],json={'parent_id':child['id']}).status_code,400)
        self.assertEqual(self.client.patch('/api/folders/'+root['id'],json={'name':'Fabric'}).status_code,200)
        moved=self.client.patch('/api/folders/'+child['id'],json={'parent_id':None}).get_json()
        self.assertEqual(moved['id'],child['id']); self.assertIsNone(moved['parent_id'])
    def seed_scope(self):
        # Task execution now resolves definitions from the Plan, not the request.
        for identity in ('a', 'b'):
            folder = Path(self.tmp.name, identity)
            folder.mkdir(exist_ok=True)
            (folder / '__testcase__.py').write_text("STEPS = [{'module_path':'unused'}]", encoding='utf-8')
        with self.Session() as s:
            s.add_all([TestCase(system_id='a',plan_id='p',display_name='A',script_path='a'),TestCase(system_id='b',plan_id='p',display_name='B',script_path='b'),TestCase(system_id='foreign',plan_id='q',display_name='Foreign',script_path='foreign'),Task(id='t',plan_id='p',name='Task')]); s.commit()
        return self.client.post('/api/tasks/t/testcases/import',json={'testcases':[{'id':'a'},{'id':'b'}]})
    def test_scope_validation(self):
        self.seed_scope()
        for ids,code in [(['foreign'],400),(['a','a'],409)]:
            r=self.client.post('/api/tasks/t/testcases/import',json={'testcases':[{'id':x} for x in ids]})
            self.assertEqual(r.status_code,code,r.get_json())
        self.assertEqual(len(self.client.get('/api/tasks/t/summary').get_json()['testcases']),2)
    def test_selected_rerun_lock_and_stop(self):
        self.seed_scope()
        r=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a','b']})
        self.assertEqual(r.status_code,200,r.get_json())
        token=r.get_json()['execution_token']
        self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'Locked'}).status_code,409)
        self.assertEqual(self.client.post('/api/results/save',json={'task_id':'t','execution_token':token,'testcases':[{'id':'b','status':'Passed','log':'old'}]}).status_code,200)
        self.client.post('/api/tasks/t/execution/finish',json={'execution_token':token})
        token=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a']}).get_json()['execution_token']
        self.client.post('/api/tasks/t/execution/stop',json={'execution_token':token})
        cases=self.client.get('/api/tasks/t/summary').get_json()['testcases']
        self.assertEqual({c['id']:c['status'] for c in cases},{'a':'TBD','b':'Passed'})
    def test_live_identity_and_scope_removal(self):
        self.seed_scope()
        self.assertEqual(self.client.patch('/api/testcases/a',json={'tc_name':'Renamed','folder_path':'Network/Ports'}).status_code,200)
        cases=self.client.get('/api/tasks/t/summary').get_json()['testcases']
        self.assertEqual(cases[0]['tc_name'],'Renamed'); self.assertEqual(cases[0]['folder_path'],'Network/Ports')
        self.client.post('/api/tasks/t/testcases/import',json={'testcases':[]})
        self.assertEqual(self.client.get('/api/tasks/t/summary').get_json()['testcases'],[])


    def test_stale_result_and_stop_cannot_modify_new_execution(self):
        self.seed_scope()
        old=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a']}).get_json()['execution_token']
        self.client.post('/api/tasks/t/execution/finish',json={'execution_token':old})
        new=self.client.post('/api/tasks/t/execution/start',json={'selected_testcase_ids':['a']}).get_json()['execution_token']
        self.assertNotEqual(old,new)
        for path,payload in [('result',{'id':'a','status':'Passed'}),('stop',{}),('finish',{})]:
            response=self.client.post('/api/tasks/t/execution/'+path,json=dict(payload,execution_token=old))
            self.assertEqual(response.status_code,409,response.get_json())
        self.assertTrue(self.client.get('/api/tasks/t/summary').get_json()['execution_active'])

    def test_runner_rejects_unscoped_task_execution(self):
        self.seed_scope()
        r=self.client.post('/api/run',json={'task_id':'t','testcase_id':'foreign','steps':[{'module_path':'fake'}]})
        self.assertEqual(r.status_code,400,r.get_json())

    def test_deletion_restores_files_on_commit_and_staging_failure(self):
        import plan_state
        self.seed_scope()
        scripts=Path(self.tmp.name,'testcase_database','scripts'); (scripts/'a').mkdir(parents=True)
        (scripts/'a'/'__testcase__.py').write_text('STEPS=[]')
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name):
            preview=self.client.get('/api/testcases/a/impact').get_json()
            self.assertEqual(preview['affected_task_count'],1)
            for target in ('shutil.move','commit'):
                failure=patch.object(self.Session.class_,'commit',side_effect=RuntimeError('commit failed')) if target=='commit' else patch('plan_state.shutil.move',side_effect=OSError('stage failed'))
                with failure:
                    r=self.client.delete('/api/testcases/a',json={'confirm':True})
                    self.assertEqual(r.status_code,500)
                self.assertTrue((scripts/'a'/'__testcase__.py').exists())
                with self.Session() as db: self.assertIsNotNone(db.get(TestCase,'a'))
            r=self.client.delete('/api/testcases/a',json={'confirm':True})
            self.assertEqual(r.status_code,200,r.get_json())
            self.assertFalse((scripts/'a').exists())
        self.assertEqual(len(self.client.get('/api/tasks/t/summary').get_json()['testcases']),1)

    def test_subtree_confirmation_and_empty_task_retention(self):
        self.seed_scope()
        self.client.patch('/api/testcases/a',json={'folder_path':'Root/Child'})
        self.client.patch('/api/testcases/b',json={'folder_path':'Root'})
        folders=self.client.get('/api/plans/p/folders').get_json()
        root=next(f for f in folders if f['name']=='Root')
        preview=self.client.get('/api/folders/'+root['id']+'/impact').get_json()
        self.assertEqual((preview['descendant_folder_count'],preview['testcase_count'],preview['affected_task_count'],preview['task_testcase_count']),(1,2,1,2))
        self.assertEqual(self.client.delete('/api/folders/'+root['id'],json={'confirm':True}).status_code,400)
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name):
            self.assertEqual(self.client.delete('/api/folders/'+root['id'],json={'confirm':True,'acknowledgement':True}).status_code,200)
        self.assertEqual(self.client.get('/api/tasks/t/summary').get_json()['testcases'],[])
        with self.Session() as db: self.assertIsNotNone(db.get(Task,'t'))

    def test_pdf_uses_current_scope_and_latest_membership_logs(self):
        from report_generator import generate_task_pdf_report
        from pypdf import PdfReader
        self.seed_scope()
        self.client.patch('/api/testcases/a',json={'tc_name':'Current A','folder_path':'Network/Ports'})
        with self.Session() as db:
            row=db.query(TaskTestCase).filter_by(testcase_id='a').one(); row.status='Passed';row.log_text='LATEST ONLY';row.result_json='{"detail":"latest result"}'
            db.get(Task,'t').task_metadata='{"firmware":"current-fw"}'; db.commit()
        out=Path(self.tmp.name,'report.pdf')
        generate_task_pdf_report('t',str(out),db_path=str(Path(self.tmp.name,'test.db')))
        reader=PdfReader(out); text=''.join(p.extract_text() for p in reader.pages)
        self.assertIn('Current A',text);self.assertIn('Network/Ports',text);self.assertIn('current-fw',text)
        self.assertEqual(reader.attachments['result_a.log'],[b'LATEST ONLY'])

    def test_flush_failure_and_restore_failure_preserve_recovery_data(self):
        import plan_state
        self.seed_scope(); scripts=Path(self.tmp.name,'testcase_database','scripts'); (scripts/'a').mkdir(parents=True)
        (scripts/'a'/'__testcase__.py').write_text('STEPS=[]')
        original_flush=self.Session.class_.flush
        def fail_deleted(session,*args,**kwargs):
            if session.deleted: raise RuntimeError('delete flush failed')
            return original_flush(session,*args,**kwargs)
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name), patch.object(self.Session.class_,'flush',fail_deleted):
            response=self.client.delete('/api/testcases/a',json={'confirm':True})
            self.assertEqual(response.status_code,500)
        self.assertTrue((scripts/'a'/'__testcase__.py').exists())
        with self.Session() as db: self.assertIsNotNone(db.get(TestCase,'a'))
        actual_move=plan_state.shutil.move; calls=[]
        def fail_restoration(source,target):
            calls.append(source)
            if len(calls)>1: raise OSError('restore failed')
            return actual_move(source,target)
        with patch.object(api,'MAIN_PROGRAM_DIR',self.tmp.name), patch.object(self.Session.class_,'commit',side_effect=RuntimeError('commit failed')), patch('plan_state.shutil.move',side_effect=fail_restoration):
            response=self.client.delete('/api/testcases/a',json={'confirm':True})
            self.assertEqual(response.status_code,500)
        self.assertTrue((scripts/'a'/'__testcase__.py').exists())

    def test_actual_sqlite_write_reservation_serializes_start(self):
        import threading, time
        import plan_state
        self.seed_scope(); entered=threading.Event(); finished=threading.Event(); errors=[]
        with self.Session() as mutation:
            plan_state.begin_write(mutation)
            plan_state.create_folder(mutation,'p','Concurrent')
            def start():
                entered.set()
                try:
                    with self.Session() as execution:
                        plan_state.begin_write(execution); plan_state.start_execution(execution,'t',['a']); execution.commit()
                except Exception as exc: errors.append(exc)
                finished.set()
            worker=threading.Thread(target=start); worker.start(); entered.wait(2)
            self.assertFalse(finished.wait(.1)); mutation.commit(); worker.join(3)
        self.assertTrue(finished.is_set()); self.assertEqual(errors,[])
        self.assertEqual(self.client.post('/api/plans/p/folders',json={'name':'After start'}).status_code,409)


class MigrationTest(unittest.TestCase):
    def test_production_copy_full_startup_is_stable(self):
        import shutil, subprocess, os, sqlite3
        baseline=Path(__file__).resolve().parents[2]/'verification'/'baseline-workspace'/'testcase_meta.db'
        if not baseline.is_file():
            self.skipTest('Historical 17-case production database is not included in this checkout')
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy2(baseline,Path(tmp)/'testcase_meta.db')
            env=dict(os.environ,BMC_WEB_UI_WORKSPACE_DIR=tmp)
            snapshots=[]
            for _ in range(2):
                run=subprocess.run([sys.executable,'-B','-c','import app'],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                from contextlib import closing
                with closing(sqlite3.connect(Path(tmp)/'testcase_meta.db')) as db:
                    self.assertEqual(db.execute('select count(*) from testcases').fetchone()[0],17)
                    snapshots.append(db.execute('select system_id,folder_id,position from testcases order by system_id').fetchall())
                    self.assertFalse(db.execute("select 1 from sqlite_master where name='task_execution_attempts'").fetchone())
            self.assertEqual(snapshots[0],snapshots[1])

    def test_migration_integrity_failure_rolls_back_placement(self):
        from plan_state import migrate_current_state
        from models import PlanFolder
        with tempfile.TemporaryDirectory() as tmp:
            e=create_engine('sqlite:///'+tmp+'/db'); Base.metadata.create_all(e); S=sessionmaker(bind=e)
            with S() as s:
                s.add_all([Project(id='pr',name='P'),ProjectPlan(id='p',project_id='pr',name='P'),ProjectPlan(id='q',project_id='pr',name='Q')]); s.commit()
                s.add_all([TestCase(system_id='a',plan_id='p',display_name='A',script_path='a'),Task(id='t',plan_id='q',name='Foreign')]); s.commit()
                s.add(TaskTestCase(task_id='t',testcase_id='a'));s.commit()
            with self.assertRaisesRegex(ValueError,'ownership'): migrate_current_state(e,Path(tmp)/'log')
            with S() as s:
                self.assertIsNone(s.get(TestCase,'a').folder_id); self.assertEqual(s.query(PlanFolder).count(),0)
            e.dispose()

    def test_legacy_conversion_and_idempotency(self):
        from plan_state import migrate_current_state
        from models import PlanFolder, Category, PlanSubfolder
        with tempfile.TemporaryDirectory() as tmp:
            e=create_engine('sqlite:///'+tmp+'/db')
            Base.metadata.create_all(e); S=sessionmaker(bind=e)
            with S() as s:
                s.add_all([Project(id='pr',name='P'),ProjectPlan(id='p',project_id='pr',name='P',category_order='["Network", "Custom"]'),Category(id='net',name='Network'),PlanSubfolder(id='empty',plan_id='p',subfolder_name='Empty',position=0)]); s.commit()
                s.add_all([TestCase(system_id='a',plan_id='p',display_name='A',category_id='net',script_path='a'),TestCase(system_id='b',plan_id='p',display_name='B',script_path='b')]); s.commit()
            migrate_current_state(e,Path(tmp)/'migration.log')
            with S() as s:
                before={f.path:f.id for f in s.query(PlanFolder)}
                self.assertEqual(set(before),{'Network','Custom','Custom/Empty'})
                self.assertEqual(s.get(TestCase,'b').folder_obj.path,'Custom')
            migrate_current_state(e,Path(tmp)/'migration.log')
            with S() as s:
                self.assertEqual(before,{f.path:f.id for f in s.query(PlanFolder)})
                self.assertEqual(s.query(TestCase).count(),2)
            self.assertIn('redirected',Path(tmp,'migration.log').read_text())
            e.dispose()

if __name__=='__main__': unittest.main()
