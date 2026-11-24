const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('C:/Users/david.huang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
try{
const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[],writes=[];
page.on('pageerror',e=>{errors.push(e.message);console.log('PAGE ERROR',e.message);});
await page.addInitScript(()=>{localStorage.setItem('bmc-execution-tabs-v1',JSON.stringify({ids:['a','b'],active:'a'}));window.streams=[];window.EventSource=class{constructor(){window.streams.push(this);}close(){}};});
const cases=Array.from({length:50},(_,i)=>({id:'c'+i,tc_name:'RF-01-'+String(i+1).padStart(3,'0'),automation:i===1?'semi_automatic':i===2?'manual':i===3?null:'automatic',script_kind:'single',selected:false,status:'TBD',parameter_count:1,log_text:'Evidence '+i}));
const a={id:'a',name:'Test A',plan_id:'plan-a',testcases:cases,counts:{Passed:0,Failed:0},execution_active:false},b={...a,id:'b',name:'Test B',plan_id:'plan-b',testcases:[{...cases[0],automation:'semi_automatic',log_text:'Other Task evidence'}]};
const project={id:'p',name:'Project',plans:[{id:'plan-a',name:'Plan A',testcases:cases,folders:[],tasks:[a]},{id:'plan-b',name:'Plan B',testcases:b.testcases,folders:[],tasks:[b]}]};
let selection=[],stopped=false,session=null,conflict=false,completed=[];
await page.route('http://controls.test/**',async route=>{
 const u=new URL(route.request().url()),pathname=u.pathname,method=route.request().method(),body=method==='GET'?null:route.request().postDataJSON();if(body)writes.push({path:pathname,body});let data={};
 const task=pathname.includes('/b/')?b:a;
 if(pathname==='/api/projects')data={projects:[project]};
 else if(pathname==='/api/tasks')data={tasks:[a,b].map(t=>({...t,task_type:'Test',project_id:'p'}))};
 else if(pathname.endsWith('/summary'))data=task;
 else if(pathname.endsWith('/logs'))data={log_text:task.testcases.find(c=>c.id===pathname.split('/')[5]).log_text};
 else if(pathname.endsWith('/settings'))data={host:'https://fixture.invalid',username:'fixture'};
 else if(pathname.endsWith('/definition')){if(method==='PUT'&&conflict){await route.fulfill({status:409,json:{error:'Parameters changed in another window.'}});return;}data={source:'TEST_CASE = {}',metadata:{parameters:{timeout:{type:'integer',default:5},enabled:{type:'boolean',default:false}}},settings:{timeout:5,enabled:false},settings_revision:12};}
 else if(pathname.startsWith('/api/task_testcases/')){task.testcases.find(c=>c.id===pathname.split('/').at(-1)).selected=body.selected;}
 else if(pathname.endsWith('/execution/start')){selection=body.testcase_ids;task.execution_active=true;stopped=false;completed=[];for(const c of task.testcases)if(selection.includes(c.id))c.status='TBD';data={execution_token:'token'};}
 else if(pathname==='/api/run'){a.testcases.find(c=>c.id===body.testcase_id).status='Running';session='session';data={session_id:session};}
 else if(pathname.includes('/testcases/')&&pathname.endsWith('/execution/stop')){const row=a.testcases.find(c=>c.id===pathname.split('/')[5]);assert.equal(body.session_id,session);assert.equal(row.status,'Running');row.status='TBD';completed.push(row.id);session=null;}
 else if(pathname.endsWith('/execution/stop')){stopped=true;session=null;a.testcases.find(c=>c.status==='Running').status='Block';}
 else if(pathname.endsWith('/execution/finish')){a.execution_active=false;}
 else if(pathname.endsWith('/execution'))data={execution_active:task.execution_active,testcase_ids:selection,execution_token:'token',session_id:session,stop_requested:stopped,completed_testcase_ids:completed};
 else if(pathname.startsWith('/api/'))data={};
 else{await route.fulfill({body:fs.readFileSync(path.resolve(__dirname,'../static',pathname==='/'?'index.html':pathname.slice(1))),contentType:pathname.endsWith('.js')?'application/javascript':pathname.endsWith('.css')?'text/css':'text/html'});return;}
 await route.fulfill({json:pathname.endsWith('/logs')?data:JSON.parse(JSON.stringify(data,(key,value)=>['log_text','result'].includes(key)?undefined:value))});
});
await page.goto('http://controls.test/#/execution');await page.locator('.execution-case-row').first().waitFor();
assert.equal(await page.locator('.execution-toolbar [data-action=run],.execution-toolbar [data-action=stop]').count(),1);assert.equal(await page.locator('.execution-case-row').first().locator('[data-action=execution-run-one],[data-action=execution-stop-one]').count(),1);assert.deepEqual(await page.locator('[data-execution-case=c1] button').evaluateAll(buttons=>buttons.map(b=>b.dataset.action)),['execution-annotation','execution-run-one','execution-log','execution-report-preview','execution-parameters']);assert.equal(await page.locator('.execution-case-table thead').count(),0);assert.equal(await page.locator('.execution-case-row').first().locator('td').count(),7);assert.equal(await page.locator('.execution-toolbar .execution-icon-button').count(),5);assert.ok(await page.locator('.execution-icon-button').evaluateAll(items=>items.every(b=>b.querySelector('svg')&&b.getAttribute('aria-label')&&b.title&&!b.textContent.trim())));
assert.equal(await page.getByRole('link',{name:'Test Plans',exact:true}).count(),0);assert.equal(await page.getByRole('link',{name:'Task Info',exact:true}).count(),0);assert.equal(await page.locator('.execution-summary,.case-editor').count(),0);
// Saving a row dialog redraws the same Task. Keep the operator's place in the list.
const scroller=page.locator('.execution-case-scroll');
const annotation=page.locator('[data-execution-case=c33] [data-action=execution-annotation]');
await annotation.scrollIntoViewIfNeeded();
const beforeSave=await scroller.evaluate(el=>el.scrollTop);
assert.ok(beforeSave>0);
await annotation.click();
await page.locator('.execution-dialog [name=reason]').fill('Scroll regression');
await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/projects')),page.locator('.execution-dialog [type=submit]').click()]);
await page.waitForFunction(()=>document.querySelector('#workspace').getAttribute('aria-busy')==='false');
assert.equal(await scroller.evaluate(el=>el.scrollTop),beforeSave);
await page.locator('#execution-filter').selectOption('operator');assert.equal(await page.locator('.execution-case-row').count(),2);
await page.locator('[data-action=execution-select-all]').click();await page.waitForFunction(()=>document.querySelectorAll('[data-run]:checked').length===2).catch(async e=>{console.log({writes,selected:cases.filter(c=>c.selected).map(c=>c.id),toast:await page.locator('#notifications').innerText(),ui:await page.locator('#workspace').innerText()});throw e;});
assert.deepEqual(writes.slice(-2).map(w=>w.path),['/api/task_testcases/a/c1','/api/task_testcases/a/c2']);
await page.locator('[data-action=execution-select-none]').click();await page.waitForFunction(()=>document.querySelectorAll('[data-run]:checked').length===0);
await page.locator('#execution-filter').selectOption('automatic');assert.equal(await page.locator('.execution-case-row').count(),47);
await page.locator('[data-action=execution-select-all]').click();await page.waitForFunction(()=>document.querySelectorAll('[data-run]:checked').length===47);
const top=await page.locator('.execution-toolbar').evaluate(e=>e.getBoundingClientRect().top);await page.locator('.execution-case-scroll').evaluate(e=>e.scrollTop=1500);assert.equal(await page.locator('.execution-toolbar').evaluate(e=>e.getBoundingClientRect().top),top);
await page.locator('.execution-case-scroll').evaluate(e=>e.scrollTop=0);
assert.equal(await page.locator('[data-action=execution-parameters]').count(),0);await page.locator('#execution-filter').selectOption('operator');assert.equal(await page.locator('[data-action=execution-parameters]').count(),2);await page.locator('[data-action=execution-parameters]').first().click();await page.locator('[name="p:timeout"]').fill('9');
page.once('dialog',dialog=>dialog.dismiss());await page.keyboard.press('Escape');assert.equal(await page.locator('.execution-dialog').count(),1);
conflict=true;await page.locator('.execution-dialog [type=submit]').click();await page.getByText('Parameters changed in another window.').waitFor();assert.equal(await page.locator('[name="p:timeout"]').inputValue(),'9');conflict=false;
await page.locator('.execution-dialog [type=submit]').click();await page.locator('.execution-dialog').waitFor({state:'detached'});assert.equal(writes.at(-1).path,'/api/plans/plan-a/testcases/c1/definition');assert.equal(writes.at(-1).body.settings_revision,12);assert.equal(writes.at(-1).body.settings.timeout,9);
await page.locator('#execution-filter').selectOption('automatic');await page.locator('[data-action=execution-annotation]').first().click();await page.locator('.execution-dialog [name=status]').selectOption('Block');await page.locator('.execution-dialog [name=reason]').fill('Fixture annotation');await page.locator('.execution-dialog [type=submit]').click();await page.locator('.execution-dialog').waitFor({state:'detached'});assert.equal(writes.at(-2).path,'/api/tasks/a/testcases/c0/status');assert.equal(writes.at(-1).body.task_id,'a');
await page.locator('[data-action=execution-scope]').click();
const scopeGaps=await page.locator('.execution-dialog[data-kind=scope]').evaluate(d=>{const box=e=>e.getBoundingClientRect(),dialog=box(d),title=box(d.querySelector('h2')),name=box(d.querySelector('.execution-dialog-header .help')),close=box(d.querySelector('[data-execution-close]')),select=box(d.querySelector('[data-action=dialog-scope-all]')),list=box(d.querySelector('.table-wrap')),save=box(d.querySelector('[type=submit]'));return {top:title.top-dialog.top,close:close.top-title.top,nameToSelect:select.top-name.bottom,selectToList:list.top-select.bottom,listToSave:save.top-list.bottom,bottom:dialog.bottom-save.bottom};});
for(const key of ['top','nameToSelect','listToSave','bottom'])assert.ok(Math.abs(scopeGaps[key]-18)<1,JSON.stringify(scopeGaps));assert.ok(Math.abs(scopeGaps.close)<1,JSON.stringify(scopeGaps));assert.ok(Math.abs(scopeGaps.selectToList-12)<1,JSON.stringify(scopeGaps));
await page.locator('.execution-dialog [type=submit]').click();await page.locator('.execution-dialog').waitFor({state:'detached'});assert.equal(writes.at(-1).path,'/api/tasks/a/testcases/import');assert.equal(writes.at(-1).body.testcases.length,50);
await page.locator('#execution-tab-b').click();await page.locator('[data-execution-task-id=b]').waitFor();await page.locator('[data-action=execution-connection]').click();await page.locator('.execution-dialog [name=host]').fill('https://other-fixture.invalid');await page.locator('.execution-dialog button:not([type])').click();await page.locator('.execution-dialog').waitFor({state:'detached'});assert.equal(writes.at(-1).path,'/api/tasks/b/settings');
await page.locator('[data-action=execution-log]').click();await page.waitForFunction(()=>document.querySelector('[data-execution-log]')?.textContent==='Other Task evidence');
const exportBox=await page.locator('[data-execution-export]').boundingBox(),closeBox=await page.locator('[data-execution-close]').boundingBox();assert.ok(exportBox.x+exportBox.width<=closeBox.x);
const [logDownload]=await Promise.all([page.waitForEvent('download'),page.locator('[data-execution-export]').click()]);assert.equal(logDownload.suggestedFilename(),'Test B__RF-01-001__test.log');assert.equal(fs.readFileSync(await logDownload.path(),'utf8'),'Other Task evidence');await page.keyboard.press('Escape');
await page.locator('[data-action=execution-parameters]').click();await page.locator('.execution-dialog fieldset').waitFor();
a.execution_active=true;await page.waitForFunction(()=>document.querySelector('[data-run]').disabled);assert.equal(await page.locator('[data-action=run]').isDisabled(),true);assert.equal(await page.locator('[data-action=execution-parameters]:not(:disabled)').count(),0);assert.equal(await page.locator('.execution-dialog [name="p:timeout"]').isDisabled(),true);a.execution_active=false;await page.waitForFunction(()=>!document.querySelector('[data-run]').disabled).catch(async e=>{console.log({active:a.execution_active,stopped,session,last:writes.slice(-6),ui:await page.locator('#workspace').innerText()});throw e;});
await page.locator('.execution-dialog [name="p:timeout"]:enabled').waitFor();await page.keyboard.press('Escape');
await page.locator('#execution-tab-a').click();await page.locator('[data-execution-task-id=a]').waitFor();
await page.locator('[data-action=run]').click();await page.waitForFunction(()=>window.streams.length===1);assert.equal(selection.length,47);assert.equal(await page.locator('.execution-toolbar [data-action=run]').count(),0);assert.equal(await page.locator('.execution-toolbar [data-action=stop]').count(),1);assert.equal(await page.locator('[data-execution-case=c0] [data-action=execution-run-one]').count(),0);assert.equal(await page.locator('[data-execution-case=c0] [data-action=execution-stop-one]').count(),1);assert.equal(await page.locator('[data-run]:not(:disabled)').count(),0);assert.equal(await page.locator('[data-action=execution-parameters]:not(:disabled)').count(),0);
const runningStatus=page.locator('[data-execution-case=c0] button.status');
assert.equal(await runningStatus.textContent(),'Running');
await page.waitForFunction(()=>document.querySelector('[data-execution-case=c0] button.status')?.textContent.startsWith('IDLE: '));
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'heartbeat'})}));
await page.waitForTimeout(1100);
assert.ok(Number((await runningStatus.textContent()).match(/^IDLE: (\d+)s$/)?.[1])>=4);
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'log',text:'Fixture activity'})}));
await page.waitForFunction(()=>document.querySelector('[data-execution-case=c0] button.status')?.textContent==='Running');
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'input_required',text:'Confirm fixture step'})}));await page.locator('[data-execution-input] input').waitFor();await page.locator('[data-execution-input] input').fill('yes');await page.locator('[data-execution-input] button').click();await page.locator('[data-execution-input] form').waitFor({state:'detached'});assert.equal(writes.at(-1).path,'/api/input');await page.keyboard.press('Escape');await page.locator('.execution-dialog').waitFor({state:'detached'});
await Promise.all([page.waitForResponse(r=>r.url().endsWith('/testcases/c0/execution/stop')),page.locator('[data-action=execution-stop-one]:not(:disabled)').click()]);
assert.equal(a.execution_active,true);assert.equal(stopped,false);
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'end'})}));
await page.waitForFunction(()=>window.streams.length===2);
assert.equal(writes.filter(w=>w.path==='/api/run').at(-1).body.testcase_id,'c4');
assert.equal(await page.locator('[data-run]:not(:disabled)').count(),0);
// Reconnect while the second worker is live, then stop it. Completed NR cases must not rerun.
await page.evaluate(()=>window.streams.at(-1).onerror());await page.locator('[data-action=resume]').waitFor();await page.locator('[data-action=resume]').click();await page.waitForFunction(()=>window.streams.length===3);
await Promise.all([page.waitForResponse(r=>r.url().endsWith('/testcases/c4/execution/stop')),page.locator('[data-action=execution-stop-one]:not(:disabled)').click()]);
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'end'})}));await page.waitForFunction(()=>window.streams.length===4);
assert.deepEqual(writes.filter(w=>w.path==='/api/run').map(w=>w.body.testcase_id),['c0','c4','c5']);
await Promise.all([page.waitForResponse(r=>r.url().endsWith('/tasks/a/execution/stop')),page.locator('[data-action=stop]').click()]);
await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'end'})}));await page.waitForFunction(()=>!document.querySelector('[data-run]').disabled);
assert.equal(writes.filter(w=>w.path==='/api/run').length,3);const statusStyles=await page.locator('.execution-case-table button.status').evaluateAll(buttons=>buttons.map(b=>{const s=getComputedStyle(b);return {width:b.getBoundingClientRect().width,weight:s.fontWeight,align:s.alignItems,justify:s.justifyContent};}));assert.ok(statusStyles.every(s=>s.width===80&&s.weight==='700'&&s.align==='center'&&s.justify==='center'));
await page.locator('[data-action=execution-run-one]').first().click();await page.waitForFunction(()=>window.streams.length===5);assert.deepEqual(selection,['c0']);
await Promise.all([page.waitForResponse(r=>r.url().endsWith('/tasks/a/execution/stop')),page.locator('[data-action=stop]').click()]);await page.evaluate(()=>window.streams.at(-1).onmessage({data:JSON.stringify({type:'end'})}));await page.waitForFunction(()=>!document.querySelector('[data-run]').disabled);
const output=path.resolve(__dirname,'../../.impeccable/execution-20261030');fs.mkdirSync(output,{recursive:true});
for(const width of [1440,1920]){await page.setViewportSize({width,height:900});for(const theme of ['light','dark']){await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);await page.waitForTimeout(200);await page.screenshot({path:path.join(output,width+'-'+theme+'.png')});const bounds=await page.locator('.execution-case-scroll').boundingBox();assert.ok(Math.abs(bounds.y+bounds.height-876)<2);}}
assert.deepEqual(errors,[]);console.log('PASS: filters, visible selection/run scope, global lock/unlock, single/batch start, case stop continues, Task stop cancels queue, reconnect skips stopped cases, input prompt, stable ownership, revision conflict, dirty cancel, dialogs, sticky controls, desktop light/dark. All APIs simulated; no DUT.');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
