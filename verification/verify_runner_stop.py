import json,time
from pathlib import Path
import requests
api='http://127.0.0.1:5127/api'
f=json.loads(Path('verification/browser-fixture.json').read_text())
def post(path,data):
    r=requests.post(api+path,json=data,timeout=15)
    assert r.ok,(path,r.status_code,r.text)
    return r.json()
sibling=post('/create_plan',{'project':f['project_name'],'plan_name':'Editable sibling'})['plan_id']
token=post('/tasks/'+f['task_id']+'/execution/start',{'selected_testcase_ids':[f['cases']['wait']]})['execution_token']
run=post('/run',{'task_id':f['task_id'],'testcase_id':f['cases']['wait'],'execution_token':token,'tc_name':'Offline wait','steps':[{'module_path':'testcase_database.steps.browser_verification','preset':'wait'}]})
stream=requests.get(api+'/stream/'+run['session_id'],stream=True,timeout=15)
lines=stream.iter_lines();started=False
for line in lines:
    if line and line.startswith(b'data: '):
        e=json.loads(line[6:])
        if e.get('type')=='step_start': started=True;break
assert started
locked=requests.post(api+'/plans/'+f['plan_id']+'/folders',json={'name':'Must be blocked'},timeout=10)
assert locked.status_code==409,locked.text
other=requests.post(api+'/plans/'+sibling+'/folders',json={'name':'Allowed'},timeout=10)
assert other.status_code==201,other.text
stopped=post('/tasks/'+f['task_id']+'/execution/stop',{'execution_token':token})
assert stopped['status']=='stopping',stopped
still_locked=requests.post(api+'/plans/'+f['plan_id']+'/folders',json={'name':'Must remain blocked'},timeout=10)
assert still_locked.status_code==409,still_locked.text
for line in lines:
    if line and line.startswith(b'data: ') and json.loads(line[6:]).get('type')=='end':break
stream.close()
summary=requests.get(api+'/tasks/'+f['task_id']+'/summary',timeout=10).json()
assert not summary['execution_active'],summary
assert summary['counts']=={'Passed':1,'Failed':0,'TBD':2},summary
result={'active_plan_mutation':locked.status_code,'sibling_plan_mutation':other.status_code,'stop_response':stopped,'mutation_during_worker_stop':still_locked.status_code,'final_counts':summary['counts'],'execution_active':summary['execution_active']}
Path('verification/runner-stop-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
