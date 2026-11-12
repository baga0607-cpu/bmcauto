import io
import json
import os
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import pypdf
import test_single_case_repository as fixtures
from models import Project, ProjectPlan, Task, TestCase, TaskTestCase, PlanFolder
from report_exports import selected_tasks, final_memberships, report_groups
from plan_state import StateError

class ReportExportsTest(unittest.TestCase):
    setUp = fixtures.SingleCaseRepositoryTest.setUp

    def test_logs_zip_matches_selected_pdf_attachments(self):
        self.prepare()
        selection={'report_area':[{'kind':'plan','id':'a'}], 'reference_area':[{'kind':'task','id':'task-b'}]}
        pdf=self.export(**selection)
        response=self.client.post('/api/projects/project/reports/logs',json=selection)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.mimetype,'application/zip')
        expected=[item for items in pypdf.PdfReader(io.BytesIO(pdf.data)).attachments.values() for item in items]
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(sorted(archive.read(name) for name in archive.namelist()),sorted(expected))
            self.assertTrue(all('/' not in name and '\\' not in name for name in archive.namelist()))
        self.assertEqual(self.client.post('/api/projects/project/reports/logs',json={'task_ids':['task-b']}).status_code,404)
        self.assertEqual(self.client.post('/api/projects/project/reports/logs',json={'task_ids':['missing']}).status_code,400)

    def prepare(self):
        with self.Session() as s:
            s.get(ProjectPlan,'a').name='Plan <A> & QA'
            s.get(Task,'task1').name='Task One'
            s.get(Task,'task2').name='Task Two'
            s.add(PlanFolder(id='report-folder',plan_id='a',name='Suite <A> & QA',normalized_name='suite <a> & qa'));s.flush()
            for index in range(5):
                s.add(TestCase(system_id='case-'+str(index),plan_id='a',display_name='Case <'+str(index)+'> & QA',folder_id='report-folder',script_path='example.py',script_kind='single',position=index))
            s.flush()
            def result(tid,index,status,time,log='',manual=None):
                s.add(TaskTestCase(task_id=tid,testcase_id='case-'+str(index),position=index,status=status,executed_at=time,log_text=log,manual_override_json=json.dumps(manual) if manual else None))
            result('task1',0,'Passed','2026-10-20T00:00:00Z','winning-pass')
            result('task2',0,'Running','2026-10-22T00:00:00Z','ignored-running')
            result('task1',1,'Passed','2026-10-20T00:00:00Z','older-tie')
            result('task2',1,'Failed','2026-10-20T00:00:00Z','winning-fail')
            result('task1',2,'Failed','2026-10-21T00:00:00Z','older-fail')
            result('task2',2,'Block','2026-10-19T00:00:00Z','winning-block',{'status':'Block','modified_at':'2026-10-23T00:00:00Z','reason':'Manual <blocked>'})
            result('task1',3,'TBD',None,'ignored-tbd')
            s.add(Task(id='task-b',plan_id='b',name='Task B'))
            s.get(Task,'task1').environment_config=json.dumps({'host':'https://example.invalid','password':'NEVER-EXPORT-THIS-PASSWORD'})
            s.commit()

    def export(self, **selection):
        return self.client.post('/api/projects/project/reports?format=pdf',json=selection)

    def test_grouping_order_final_and_single_task(self):
        self.prepare()
        with self.Session() as s:
            plan,tasks,final=selected_tasks(s,'project',{'task_ids':['task2','task1']})
            self.assertTrue(final);self.assertEqual([t.id for t in tasks],['task1','task2'])
            plan,tasks,final=selected_tasks(s,'project',{'task_ids':['task1']})
            self.assertFalse(final)
            plan,tasks,final=selected_tasks(s,'project',{'plan_ids':['a'],'task_ids':['task1']})
            self.assertTrue(final);self.assertEqual(len(tasks),2)

    def test_final_matches_matrix_eligible_latest_and_missing_memberships(self):
        self.prepare()
        with self.Session() as s:
            plan,tasks,_=selected_tasks(s,'project',{'plan_ids':['a']})
            rows=final_memberships(s,plan,tasks)
            self.assertEqual([(r.status if r else 'TBD',t.id if t else None) for tc,r,t in rows],[('Passed','task1'),('Failed','task2'),('Block','task2'),('TBD',None),('TBD',None)])
            rows=final_memberships(s,plan,[tasks[0]])
            self.assertEqual([r.status if r else 'TBD' for tc,r,t in rows],['Passed','Passed','Failed','TBD','TBD'])

    def test_empty_invalid_cross_plan_cross_project_and_missing_ids_rejected(self):
        self.prepare()
        for selection in [{},{'task_ids':['task1','task-b']},{'plan_ids':['a','b']},{'plan_ids':['a'],'task_ids':['task-b']},{'task_ids':['missing']},{'task_ids':['task1','task1']},{'task_ids':'task1'},{'plan_ids':['missing']}]:
            self.assertEqual(self.export(**selection).status_code,400,selection)
        with self.Session() as s:
            s.add(Project(id='other',name='Other'));s.add(ProjectPlan(id='outside',project_id='other',name='Other'));s.flush();s.add(Task(id='outside-task',plan_id='outside',name='Outside'));s.commit()
        self.assertEqual(self.export(task_ids=['outside-task']).status_code,400)

    def test_active_tasks_rejected_only_if_in_selected_scope(self):
        self.prepare()
        with self.Session() as s:s.get(Task,'task1').execution_active=True;s.commit()
        self.assertEqual(self.export(plan_ids=['a']).status_code,409)
        self.assertEqual(self.export(task_ids=['task1']).status_code,409)
        self.assertEqual(self.export(task_ids=['task-b']).status_code,200)

    def test_pdf_single_task_and_final_evidence_and_live_data_unchanged(self):
        self.prepare()
        with self.engine.connect() as c:
            before=list(c.exec_driver_sql('SELECT * FROM tasks ORDER BY id'))
            before_cases=list(c.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id'))
        for kind,selection in [('task',{'task_ids':['task1']}),('final',{'task_ids':['task1','task2']})]:
            response=self.export(**selection)
            self.assertEqual(response.status_code,200,response.get_json(silent=True))
            self.assertEqual(response.mimetype,'application/pdf')
            reader=pypdf.PdfReader(io.BytesIO(response.data))
            text=' '.join(page.extract_text() or '' for page in reader.pages)
            self.assertNotIn('NEVER-EXPORT-THIS-PASSWORD',text)
            self.assertIn('Case <0> & QA',text)
            self.assertIn('BMC Final Report' if kind=='final' else 'BMC Test Report',text)
            if kind=='final':
                self.assertIn('Task Name',text);self.assertIn('Task Two',text)
                attachments=b''.join(content for items in reader.attachments.values() for content in items)
                self.assertIn(b'winning-pass',attachments);self.assertIn(b'winning-fail',attachments);self.assertIn(b'winning-block',attachments)
                self.assertNotIn(b'ignored-running',attachments);self.assertNotIn(b'ignored-tbd',attachments)
            target=os.environ.get('BMC_REPORT_QA_DIR')
            if target:
                Path(target).mkdir(parents=True,exist_ok=True);(Path(target)/(kind+'.pdf')).write_bytes(response.data)
        with self.engine.connect() as c:
            self.assertEqual(list(c.exec_driver_sql('SELECT * FROM tasks ORDER BY id')),before)
            self.assertEqual(list(c.exec_driver_sql('SELECT * FROM task_testcases ORDER BY id')),before_cases)

    def test_plan_without_tasks_generates_nr_final_and_failed_generation_is_read_only(self):
        self.prepare()
        with self.Session() as s:
            s.add(ProjectPlan(id='empty',project_id='project',name='Empty Plan'));s.commit()
        self.assertEqual(self.export(plan_ids=['empty']).status_code,200)
        with patch('report_generator.generate_task_pdf_report',side_effect=RuntimeError('render failed')):
            self.assertEqual(self.export(plan_ids=['a']).status_code,500)
        with self.Session() as s:self.assertEqual(s.query(Task).count(),3)

    def item(self, kind, identity):
        return {'kind':kind, 'id':identity}

    def test_areas_group_by_plan_in_first_occurrence_order_with_matrix_task_order(self):
        self.prepare()
        with self.Session() as s:
            groups=report_groups(s,'project',{'report_area':[self.item('task','task2'),self.item('task','task-b'),self.item('task','task1')]})
            self.assertEqual([(area,p.id,[t.id for t in tasks],final) for area,p,tasks,final in groups],
                [('report','a',['task1','task2'],True),('report','b',['task-b'],False)])
            rows=final_memberships(s,groups[0][1],groups[0][2])
            self.assertEqual(rows[1][2].id,'task2')  # Drag order must not change timestamp ties.
            groups=report_groups(s,'project',{'report_area':[self.item('plan','b')], 'reference_area':[self.item('task','task2'),self.item('task','task1')]})
            self.assertEqual([(area,p.id,final) for area,p,tasks,final in groups],[('report','b',True),('reference','a',True)])

    def test_area_validation_overlap_ownership_and_active_tasks(self):
        self.prepare()
        task=self.item('task','task1');plan=self.item('plan','a')
        invalid=[{'report_area':[],'reference_area':[task]}, {'report_area':None},
            {'report_area':[task],'reference_area':'bad'}, {'report_area':[task,task]},
            {'report_area':[task],'reference_area':[task]}, {'report_area':[plan],'reference_area':[task]},
            {'report_area':[task],'reference_area':[plan]}, {'report_area':[{'kind':'other','id':'a'}]},
            {'report_area':[self.item('plan','missing')]}, {'report_area':[self.item('task','missing')]},
            {'report_area':[{'kind':'task','id':[]}]}, {'report_area':[task],'task_ids':['task1']}]
        for payload in invalid:self.assertEqual(self.export(**payload).status_code,400,payload)
        with self.Session() as s:
            s.add(Project(id='other',name='Other'));s.flush();s.add(ProjectPlan(id='outside',project_id='other',name='Other'));s.flush();s.add(Task(id='outside-task',plan_id='outside',name='Outside'));s.get(Task,'task2').execution_active=True;s.commit()
        self.assertEqual(self.export(report_area=[self.item('task','outside-task')]).status_code,400)
        self.assertEqual(self.export(report_area=[self.item('plan','b')],reference_area=[plan]).status_code,409)
        self.assertEqual(self.export(report_area=[task],reference_area=[self.item('task','task-b')]).status_code,200)

    def test_plan_selection_includes_all_tasks_and_deduplicates_children(self):
        self.prepare()
        with self.Session() as s:
            groups=report_groups(s,'project',{'report_area':[self.item('task','task2'),self.item('plan','a'),self.item('task','task1')]})
            self.assertEqual(len(groups),1);self.assertTrue(groups[0][3]);self.assertEqual([t.id for t in groups[0][2]],['task1','task2'])

    def test_merged_pdf_orders_formal_then_reference_and_preserves_colliding_logs(self):
        self.prepare()
        with self.engine.connect() as c:
            before={table:list(c.exec_driver_sql('SELECT * FROM '+table+' ORDER BY 1')) for table in ['tasks','task_testcases']}
        response=self.export(report_area=[self.item('task','task-b'),self.item('task','task1')], reference_area=[self.item('task','task2')])
        self.assertEqual(response.status_code,200,response.get_json(silent=True))
        reader=pypdf.PdfReader(io.BytesIO(response.data))
        text=' '.join(p.extract_text() or '' for p in reader.pages)
        self.assertLess(text.index('Task B'),text.index('Task One'))
        self.assertLess(text.index('Task One'),text.index('Reference Reports'))
        self.assertLess(text.index('Reference Reports'),text.index('Task Two'))
        attachments=b''.join(content for items in reader.attachments.values() for content in items)
        self.assertIn(b'winning-pass',attachments);self.assertIn(b'ignored-running',attachments)
        names=list(reader.attachments.keys())
        self.assertTrue(any(n.startswith('02_Task_One') for n in names))
        self.assertTrue(any(n.startswith('03_Task_Two') for n in names))
        roots=[i['/Title'] for i in reader.outline if isinstance(i,dict)]
        self.assertEqual(roots,['Report Area','Reference Reports'])
        with self.engine.connect() as c:
            for table,rows in before.items():self.assertEqual(list(c.exec_driver_sql('SELECT * FROM '+table+' ORDER BY 1')),rows)
        target=os.environ.get('BMC_REPORT_QA_DIR')
        if target:(Path(target)/'reference.pdf').write_bytes(response.data)

    def test_multi_plan_pdf_aggregates_reference_tasks_by_matrix(self):
        self.prepare()
        response=self.export(report_area=[self.item('plan','b')],reference_area=[self.item('task','task2'),self.item('task','task1')])
        self.assertEqual(response.status_code,200,response.get_json(silent=True))
        reader=pypdf.PdfReader(io.BytesIO(response.data));text=' '.join(p.extract_text() or '' for p in reader.pages)
        self.assertEqual(text.count('BMC Final Report'),2)
        attachments=b''.join(content for items in reader.attachments.values() for content in items)
        self.assertIn(b'winning-pass',attachments);self.assertIn(b'winning-fail',attachments);self.assertIn(b'winning-block',attachments)
        self.assertNotIn(b'ignored-running',attachments);self.assertNotIn(b'older-tie',attachments)
        target=os.environ.get('BMC_REPORT_QA_DIR')
        if target:(Path(target)/'reference-final.pdf').write_bytes(response.data)

    def test_split_same_plan_keeps_each_area_results_separate(self):
        self.prepare()
        with self.Session() as s:
            s.add(Task(id='task3',plan_id='a',name='Task Three'));s.commit()
        groups=None
        with self.Session() as s:
            groups=report_groups(s,'project',{'report_area':[self.item('task','task1'),self.item('task','task3')], 'reference_area':[self.item('task','task2')]})
            self.assertEqual(len(groups),2)
            self.assertEqual(final_memberships(s,groups[0][1],groups[0][2])[1][1].status,'Passed')
            self.assertEqual(final_memberships(s,groups[1][1],groups[1][2])[1][1].status,'Failed')
        response=self.export(report_area=[self.item('task','task1'),self.item('task','task3')],reference_area=[self.item('task','task2')])
        self.assertEqual(response.status_code,200,response.get_json(silent=True))
        text=' '.join(p.extract_text() or '' for p in pypdf.PdfReader(io.BytesIO(response.data)).pages)
        formal,reference=text.split('Reference Reports',1)
        self.assertIn('Task Name\nTask One',formal);self.assertNotIn('Task Name\nTask Two',formal)
        self.assertIn('Task Two',reference)
