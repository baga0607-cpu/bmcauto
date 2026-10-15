const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const vm=require('node:vm');
const source=fs.readFileSync('web_ui/static/index.html','utf8');
function load(names,extra={}) { const c={...extra}; const code=names.map(name=>{const start=source.search(new RegExp('(?:async )?function '+name+'\\(')); assert.ok(start>=0,name); const end=source.indexOf('\n      function ',start+10); const asyncEnd=source.indexOf('\n      async function ',start+10); return source.slice(start,Math.min(...[end,asyncEnd].filter(x=>x>=0)));}).join('\n'); vm.runInNewContext(code+'\nglobalThis.api={'+names.join(',')+'}',c); return c.api; }
test('persisted empty root and child render independently of testcase placement',()=>{const api=load(['resolvePlanTestCases','getPlanFolderModel'],{allTestcases:[]}); const m=api.getPlanFolderModel({folders:[{id:1,name:'Fabric',parent_id:null,position:0},{id:2,name:'Empty',parent_id:1,position:0}],testcases:[]}); assert.equal(m.categories[0].id,1); assert.equal(m.categories[0].subfolders[0].id,2); assert.equal(m.categories[0].subfolders[0].cases.length,0);});
test('testcase destination request uses stable folder identity',async()=>{let body;const api=load(['requestPlanTestCaseMove'],{API:'/api',currentPlanId:'p',fetch:async(u,o)=>{body=JSON.parse(o.body);return {ok:true,json:async()=>({moved:1})}}});await api.requestPlanTestCaseMove(['a'],'folder:42');assert.deepEqual(body,{testcase_ids:['a'],folder_id:'42'});});
test('live Task identity and placement override stale global catalog',()=>{const api=load(['resolveTaskTestCases'],{allTestcases:[{id:'a',tc_name:'Old',folder_path:'Old'}]});const row=api.resolveTaskTestCases({testcases:[{id:'a',tc_name:'New',folder_id:4,folder_path:'New/Child',status:'Passed'}]})[0];assert.equal(row.tc_name,'New');assert.equal(row.folder_path,'New/Child');});
test('partial template selection sends child path without selecting siblings',()=>{const api=load(['getTemplateSelection']);assert.deepEqual(JSON.parse(JSON.stringify(api.getTemplateSelection([{folder_path:'Root',checked:false},{folder_path:'Root/One',checked:true},{folder_path:'Root/Two',checked:false}]))),['Root/One']);});
test('execution start uses lifecycle endpoint and preserves operational token across reload',async()=>{const stored=new Map();let request;const entity={id:'task',testcases:[]};const api=load(['startTaskExecution'],{API:'/api',sessionStorage:{setItem:(k,v)=>stored.set(k,v)},fetch:async(u,o)=>{request=[u,JSON.parse(o.body)];return{ok:true,json:async()=>({execution_token:'token'})}}});await api.startTaskExecution(entity,[{id:'a'}]);assert.deepEqual(request,['/api/tasks/task/execution/start',{selected_testcase_ids:['a']}]);assert.equal(stored.get('task-execution:task'),'token');});
test('current results are read directly and replace stale Task scope',async()=>{const entity={id:'task',testcases:[{id:'removed'}]};const api=load(['loadTaskResults'],{API:'/api',fetch:async()=>({ok:true,json:async()=>({testcases:[{id:'live',status:'Passed'}],execution_active:false})}),renderMain:()=>{},addLog:()=>{},sessionStorage:{getItem:()=>null},setRunState:()=>{},getCurrentTaskId:()=>null});await api.loadTaskResults(entity);assert.equal(entity.testcases.length,1);assert.equal(entity.testcases[0].id,'live');});
test('pointer folder keys use stable IDs despite renamed folders',()=>{const api=require('../static/plan_workspace_interactions');assert.equal(api.getPlanTestcaseDestinationKey({folder_id:42,category:'Old'}),'folder:42');});
test('Plan locks do not lock siblings',()=>{const api=load(['isPlanLocked'],{currentPlanId:'a',db:{projects:[{plans:[{id:'a',locked:true},{id:'b',locked:false}]}]}});assert.equal(api.isPlanLocked('a'),true);assert.equal(api.isPlanLocked('b'),false);});
test('folder rename keeps stable destination selection and path text',()=>{const api=load(['getPlanMoveFolderOptions','getPlanFolderModel','resolvePlanTestCases'],{allTestcases:[]});const opts=api.getPlanMoveFolderOptions({testcases:[],folders:[{id:3,name:'Renamed',folder_path:'Renamed',parent_id:null,position:0}]});assert.equal(opts[0].key,'folder:3');assert.equal(opts[0].path,'Renamed');});
test('new tab can recover an active execution token without history',async()=>{const stored=new Map();const api=load(['recoverExecutionToken'],{API:'/api',sessionStorage:{setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},fetch:async()=>({ok:true,json:async()=>({execution_active:true,execution_token:'recovered'})})});assert.equal(await api.recoverExecutionToken('task'),'recovered');assert.equal(stored.get('task-execution:task'),'recovered');});
test('all folder origins render identical disabled controls while a Plan is executing',()=>{const api=load(['renderPlanFolderTree','getPlanFolderModel','resolvePlanTestCases','renderPlanSelectionCheckbox'],{allTestcases:[],planDetailState:{folderFilter:'all',collapsedGroups:new Set()},escapeHtml:s=>String(s),planTreeHandlerKey:x=>JSON.stringify(x)});const html=api.renderPlanFolderTree({locked:true,testcases:[],folders:[{id:1,name:'Custom',parent_id:null,position:0},{id:2,name:'Empty',parent_id:1,position:0}]});assert.equal((html.match(/title="Folder actions"/g)||[]).length,2);assert.equal((html.match(/draggable="false"/g)||[]).length,2);assert.ok(html.includes('disabled onclick="editPlanFolder'));assert.ok(!html.includes('System folder'));});
test('destructive folder confirmation cannot submit before required acknowledgement',async()=>{const elements={'#impact-cancel':{},'#impact-delete':{disabled:true},'#impact-ack':{checked:false}};let host;const api=load(['confirmImpact'],{API:'/api',escapeHtml:s=>String(s),fetch:async()=>({ok:true,json:async()=>({name:'Root',names:['Case'],descendant_folder_count:1,testcase_count:1,affected_task_count:2,task_testcase_count:2,requires_acknowledgement:true})}),document:{createElement:()=>host={querySelector:k=>elements[k],remove:()=>{}},body:{append:()=>{}}}});const promise=api.confirmImpact('/folders/1');await new Promise(setImmediate);assert.ok(host.innerHTML.includes('I understand'));assert.ok(host.innerHTML.includes('2 affected Tasks'));assert.equal(elements['#impact-delete'].disabled,true);elements['#impact-ack'].checked=true;elements['#impact-ack'].onchange();assert.equal(elements['#impact-delete'].disabled,false);elements['#impact-delete'].onclick();assert.equal(await promise,true);});
test('cross-parent folder movement is one atomic domain mutation',async()=>{const calls=[];const plan={id:'p',folders:[{id:1,parent_id:10,position:0},{id:2,parent_id:20,position:0}]};const api=load(['movePlanFolder'],{currentProjId:'project',currentPlanId:'p',findProj:()=>({plans:[plan]}),planMutation:async(...args)=>calls.push(args),reloadProjects:async()=>{},renderPlanDetail:()=>{},clearAllPlanTreeDropFeedback:()=>{},alert:e=>{throw Error(e)}});await api.movePlanFolder('folder:1','folder:2');assert.equal(calls.length,1);assert.deepEqual(JSON.parse(JSON.stringify(calls[0])),['/folders/1','PATCH',{parent_id:20,relative_to:2,insertion:'before'}]);});
test('canonical cross-folder testcase drop is atomic and does not compose reorder',async()=>{const api=require('../static/plan_workspace_interactions');const calls=[];const context={projectId:'p',planId:'plan',viewId:'plan-detail'};const identity=api.createPointerCommitIdentity({...context,sourceTestcaseId:'a',targetTestcaseId:'b'});await api.runPlanPointerRowCommit(identity,{refreshLocks:async()=>{},getContext:()=>context,isLocked:()=>false,getTestcases:()=>[{id:'a',folder_id:1},{id:'b',folder_id:2}],moveTestcase:async p=>calls.push(['move',p]),reorderTestcases:async p=>calls.push(['reorder',p]),reload:async()=>{}});assert.equal(calls.length,1);assert.equal(calls[0][0],'move');});
test('viewing active execution between workers makes no mutating request',async()=>{const calls=[];const entity={id:'task'};const api=load(['loadTaskResults'],{API:'/api',executionTaskId:null,getCurrentTaskId:()=> 'task',currentEventSource:null,sessionStorage:{setItem:()=>{},getItem:()=> 'token',removeItem:()=>{}},fetch:async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>url.endsWith('/results')?{execution_active:true,testcases:[]}:{execution_active:true,execution_token:'token',session_id:null}}},renderMain:()=>{},planMutation:async(...args)=>{calls.push(args);throw Error('view mutation');},refreshLockedProjects:async()=>{},addLog:()=>{}});await api.loadTaskResults(entity);assert.equal(calls.length,2);assert.ok(calls.every(call=>!call[1]));});

test('execution loads fresh steps explicitly and stale scope cannot override them',async()=>{let requested,executed;const entity={id:'task',execution_active:true};const api=load(['_executeTCs'],{API:'/api',stopRequested:false,allTestcases:[{id:'a',steps:[]}],taskLogBuffer:[],taskApiLogBuffer:[],fetch:async url=>{requested=url;return{ok:true,json:async()=>[{id:'a',tc_name:'Live',steps:[{module_path:'fresh'}]}]}},renderCompactTaskStatus:()=>{},executeSingleTC:async tc=>executed=tc,loadTaskResults:async()=>{}});await api._executeTCs(entity,[{id:'a',steps:[{module_path:'stale'}]}]);assert.ok(requested?.includes('include_steps=true'));assert.equal(executed.steps[0].module_path,'fresh');});

function definitionFailureHarness({ missing = false, resultWriteFails = false, definitionFetchFails = false } = {}) {
  const entity = { id: 'task', name: 'Task', execution_active: false, testcases: [
    { id: 'broken', tc_name: 'Broken definition', selected: true, status: 'Passed' },
    { id: 'valid', tc_name: 'Valid case', selected: true, status: 'Passed' },
    { id: 'unselected', selected: false, status: 'Passed', log_text: 'retained' },
  ] };
  const writes = [], executed = [], errors = [];
  const context = {
    API: '/api', executionTaskId: null, stopRequested: false,
    taskLogBuffer: [], taskApiLogBuffer: [], allTestcases: [],
    getCurrentEntity: () => entity, getCurrentTaskId: () => entity.id,
    sessionStorage: { getItem: () => 'current-token' },
    startTaskExecution: async (task, selected) => {
      writes.push({ action: 'start' }); task.execution_active = true;
      selected.forEach(tc => { tc.status = 'TBD'; tc.log_text = null; });
    },
    setRunState: () => {}, refreshLockedProjects: async () => {},
    renderCompactTaskStatus: () => {}, renderMain: () => {},
    loadTaskResults: async () => {},
    addLog: (type, message) => { if (type === 'fail') errors.push(message); },
    alert: message => errors.push(message),
    fetch: async (url, options) => {
      if (url.includes('include_steps=true')) {
        return { ok: !definitionFetchFails, status: definitionFetchFails ? 503 : 200,
          json: async () => definitionFetchFails ? { error: 'Definition service unavailable' } : [
            ...(missing ? [] : [{ id: 'broken', steps: [] }]),
            { id: 'valid', steps: [{ module_path: 'valid.step' }] },
          ] };
      }
      assert.equal(url, '/api/tasks/task/execution/result');
      const payload = JSON.parse(options.body); writes.push({ action: 'result', payload });
      if (!resultWriteFails) Object.assign(entity.testcases.find(tc => tc.id === payload.id), payload);
      return { ok: !resultWriteFails, status: resultWriteFails ? 409 : 200,
        json: async () => resultWriteFails ? { error: 'Current result could not be persisted' } : { status: 'ok' } };
    },
    executeSingleTC: async tc => {
      executed.push(tc.id); entity.testcases.find(row => row.id === tc.id).status = 'Passed';
    },
    saveTaskResults: async task => { writes.push({ action: 'finish' }); task.execution_active = false; },
  };
  return { api: load(['runPlan', '_executeTCs'], context), entity, writes, executed, errors };
}

for (const missing of [false, true]) {
  test(`${missing ? 'missing' : 'empty'} executable definition persists Failed after start and continues valid selection`, async () => {
    const h = definitionFailureHarness({ missing });
    await h.api.runPlan();
    const failed = h.entity.testcases[0];
    assert.equal(failed.status, 'Failed');
    assert.match(failed.log_text, missing ? /definition.*missing/i : /no executable steps/i);
    assert.equal(failed.result.status, 'Failed');
    assert.match(failed.result.error, /Broken definition/);
    assert.equal(failed.execution_token, 'current-token');
    assert.ok(failed.executed_at);
    assert.deepEqual(h.executed, ['valid']);
    assert.deepEqual(h.writes.map(w => w.action), ['start', 'result', 'finish']);
    assert.equal(h.entity.testcases[2].log_text, 'retained');
    assert.equal(h.entity.execution_active, false);
    assert.deepEqual(h.errors, []);
  });
}

test('definition failure result-write rejection stops remaining selection and surfaces operational error', async () => {
  const h = definitionFailureHarness({ resultWriteFails: true });
  await h.api.runPlan();
  assert.deepEqual(h.executed, []);
  assert.equal(h.writes.filter(w => w.action === 'result').length, 1);
  assert.ok(h.errors.some(error => error.includes('Current result could not be persisted')));
  assert.equal(h.entity.testcases[0].status, 'TBD');
  assert.equal(h.entity.testcases[1].status, 'TBD');
  assert.equal(h.entity.execution_active, false);
});

test('system-wide definition fetch failure does not fabricate testcase failures', async () => {
  const h = definitionFailureHarness({ definitionFetchFails: true });
  await h.api.runPlan();
  assert.deepEqual(h.executed, []);
  assert.deepEqual(h.writes.map(w => w.action), ['start', 'finish']);
  assert.ok(h.errors.some(error => error.includes('Definition service unavailable')));
  assert.equal(h.entity.testcases[0].status, 'TBD');
});

test('cross-folder row drop forwards atomic before and after insertion',async()=>{const api=require('../static/plan_workspace_interactions');for(const insertion of ['before','after']){const calls=[];const context={projectId:'p',planId:'plan',viewId:'plan-detail'};const identity=api.createPointerCommitIdentity({...context,sourceTestcaseId:'a',targetTestcaseId:'b',insertion});await api.runPlanPointerRowCommit(identity,{refreshLocks:async()=>{},getContext:()=>context,isLocked:()=>false,getTestcases:()=>[{id:'a',folder_id:1},{id:'b',folder_id:2}],moveTestcase:async p=>calls.push(p),reorderTestcases:async()=>assert.fail('must remain atomic'),reload:async()=>{}});assert.equal(calls[0].relativeTo,'b');assert.equal(calls[0].insertion,insertion);}});
test('testcase move sends relative position when provided',async()=>{let body;const api=load(['requestPlanTestCaseMove'],{API:'/api',currentPlanId:'p',fetch:async(u,o)=>{body=JSON.parse(o.body);return {ok:true,json:async()=>({})}}});await api.requestPlanTestCaseMove(['a'],'folder:42','p',{relativeTo:'b',insertion:'after'});assert.deepEqual(body,{testcase_ids:['a'],folder_id:'42',relative_to:'b',insertion:'after'});});
