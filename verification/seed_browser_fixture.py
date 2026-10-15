import json,time
from pathlib import Path
import requests
api='http://127.0.0.1:5127/api'
def post(path,data):
    r=requests.post(api+path,json=data,timeout=15)
    assert r.ok,(path,r.status_code,r.text)
    return r.json()
post('/create_project',{'project':'Browser Verification'})
p=post('/create_plan',{'project':'Browser Verification','plan_name':'Offline execution','folder_paths':['Checks','Checks/Child','Empty']})['plan_id']
cases={}
for preset in ['pass','fail','wait']:
    result=post('/import_tc',{'project':'Browser Verification','plan_id':p,'tc_name':'Offline '+preset,'folder_path':'Checks/Child','steps':[{'module_path':'testcase_database.steps.browser_verification','preset':preset}]})
    cases[preset]=result['id']
task=post('/tasks',{'plan_id':p,'name':'Offline verification','setup':{'owner':'Verification','firmware_version':'OFFLINE'}})['id']
post('/tasks/'+task+'/testcases/import',{'testcases':[{'id':v,'selected':True} for v in cases.values()]})
token=post('/tasks/'+task+'/execution/start',{'selected_testcase_ids':[cases['pass']]})['execution_token']
run=post('/run',{'task_id':task,'testcase_id':cases['pass'],'execution_token':token,'tc_name':'Offline pass','steps':[{'module_path':'testcase_database.steps.browser_verification','preset':'pass'}]})
session=run['session_id']
stream=requests.get(api+'/stream/'+session,stream=True,timeout=15)
events=[]
for line in stream.iter_lines():
    if line and line.startswith(b'data: '):
        event=json.loads(line[6:]);events.append(event)
        if event.get('type')=='end':break
stream.close()
post('/tasks/'+task+'/execution/finish',{'execution_token':token})
summary=requests.get(api+'/tasks/'+task+'/summary',timeout=10).json()
assert summary['counts']=={'Passed':1,'Failed':0,'TBD':2},summary
assert not summary['execution_active'],summary
fixture={'project_name':'Browser Verification','plan_id':p,'task_id':task,'cases':cases,'offline_runner_counts':summary['counts'],'runner_events':events}
Path('verification/browser-fixture.json').write_text(json.dumps(fixture,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in fixture.items() if k!='runner_events'},indent=2))
