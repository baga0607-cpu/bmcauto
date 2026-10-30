import json
import unittest
import test_task_schedule as schedule
from models import Task, PlanningTask

class TaskReferencePackageTest(unittest.TestCase):
    setUp = schedule.TaskScheduleTest.setUp
    prepare = schedule.TaskScheduleTest.prepare

    def update(self, tid, setup, **expected):
        return self.client.patch('/api/tasks/'+tid,json={'setup':setup,**expected})

    def test_idesign_both_types_roundtrip_and_clear(self):
        self.prepare()
        ref={'request_id':' REQ-123 ','hyperlink':' https://example.invalid/request/123 '}
        canonical={k:v.strip() for k,v in ref.items()}
        for tid,model in [('task1',Task),('planning',PlanningTask)]:
            response=self.update(tid,{'idesign':ref},expected_idesign={})
            self.assertEqual(response.status_code,200,response.get_json())
            with self.Session() as s:self.assertEqual(json.loads(s.get(model,tid).task_metadata)['idesign'],canonical)
            self.assertEqual(self.update(tid,{'idesign':{}},expected_idesign=canonical).status_code,200)

    def test_idesign_invalid_partial_and_unsafe_links_rejected_atomically(self):
        original=self.prepare()
        for ref in [{'request_id':'R'},{'hyperlink':'https://example.invalid'},None,{'request_id':'R','hyperlink':'javascript:alert(1)'},{'request_id':'R','hyperlink':'file:///tmp/x'},{'request_id':'R','hyperlink':'https://example.invalid:bad'},{'request_id':'R','hyperlink':'https://example.invalid/has space'}]:
            self.assertEqual(self.update('task1',{'idesign':ref,'notes':'bad'},expected_idesign={}).status_code,400)
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)

    def test_fw_test_roundtrip_remove_and_other_metadata_preserved(self):
        original=self.prepare()
        package=[{'component':' BMC ','version':' 1.2 '},{'component':'BIOS','version':'3.4'}]
        canonical=[{'component':i['component'].strip(),'version':i['version'].strip()} for i in package]
        response=self.update('task1',{'fw_package':package},expected_fw_package=[])
        self.assertEqual(response.status_code,200,response.get_json())
        rows=self.client.get('/api/tasks').get_json()['tasks']
        self.assertEqual(next(t for t in rows if t['id']=='task1')['setup']['fw_package'],canonical)
        self.assertEqual(self.update('task1',{'notes':'Changed'}).status_code,200)
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata)['fw_package'],canonical)
        self.assertEqual(self.update('task1',{'fw_package':[]},expected_fw_package=canonical).status_code,200)
        self.assertEqual(self.client.get('/api/tasks/task1/history').get_json()['history'],[])

    def test_fw_plan_rejected_on_create_update_and_bulk(self):
        self.prepare()
        package=[{'component':'BMC','version':'1'}]
        self.assertEqual(self.update('planning',{'fw_package':package},expected_fw_package=[]).status_code,400)
        self.assertEqual(self.client.post('/api/tasks',json={'task_type':'Plan','project_id':'project','setup':{'fw_package':package}}).status_code,400)
        response=self.client.post('/api/tasks',json={'task_type':'Test','plan_id':'a','setup':{'fw_package':package}})
        self.assertEqual(response.status_code,200,response.get_json())
        data={'projects':[{'id':'project','plans':[{'id':'a','tasks':[{'id':'task1','setup':{'fw_package':package}}]}]}]}
        self.assertEqual(self.client.post('/api/projects',json=data).status_code,409)

    def test_invalid_fw_rows_duplicate_components_and_oversized_list(self):
        original=self.prepare()
        for package in [{},[{'component':'BMC','version':''}],[{'component':'','version':'1'}],[{'component':'BMC','version':1}],[{'component':'BMC','version':'1'},{'component':'bmc','version':'2'}],[{'component':str(i),'version':'1'} for i in range(101)]]:
            self.assertEqual(self.update('task1',{'fw_package':package},expected_fw_package=[]).status_code,400)
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata),original)

    def test_stale_values_and_combined_invalid_payload_cannot_overwrite(self):
        self.prepare()
        ref={'request_id':'R1','hyperlink':'https://example.invalid/1'}
        package=[{'component':'BMC','version':'1'}]
        self.assertEqual(self.update('task1',{'idesign':ref}).status_code,409)
        self.assertEqual(self.update('task1',{'idesign':ref,'fw_package':package},expected_idesign={},expected_fw_package=[]).status_code,200)
        self.assertEqual(self.update('task1',{'idesign':{}},expected_idesign={}).status_code,409)
        self.assertEqual(self.update('task1',{'fw_package':[]},expected_fw_package=[]).status_code,409)
        self.assertEqual(self.update('task1',{'idesign':{},'fw_package':[{'component':'BMC','version':''}]},expected_idesign=ref,expected_fw_package=package).status_code,400)
        with self.Session() as s:self.assertEqual(json.loads(s.get(Task,'task1').task_metadata)['idesign'],ref)

    def test_active_plan_lock_does_not_lock_independent_plan_task(self):
        self.prepare()
        with self.Session() as s:s.get(Task,'task2').execution_active=True;s.commit()
        ref={'request_id':'R','hyperlink':'http://example.invalid'}
        self.assertEqual(self.update('task1',{'idesign':ref},expected_idesign={}).status_code,409)
        self.assertEqual(self.update('planning',{'idesign':ref},expected_idesign={}).status_code,200)
