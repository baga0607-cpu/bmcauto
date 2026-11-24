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
const reads=[];let selection=[],stopped=false,session=null,conflict=false,completed=[];
await page.route('http://controls.test/**',async route=>{
 const u=new URL(route.request().url()),pathname=u.pathname,method=route.request().method(),body=method==='GET'?null:route.request().postDataJSON();if(body)writes.push({path:pathname,body});let data={};
 if(method==='GET')reads.push(pathname);
 const task=pathname.includes('/b/')?b:a;
 if(pathname==='/api/projects/p/reports'||pathname==='/api/projects/p/reports/logs'){await route.fulfill({body:'ZIP fixture',headers:{'Content-Type':'application/zip','Content-Disposition':'attachment; filename=fixture.zip'}});return;}
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


await page.goto('http://controls.test/#/project/p/reports');
await page.locator('[data-action=report-select]').click();
await page.locator('[data-report-select=plan]').first().check();
await page.locator('[data-action=report-generate]').click();
await page.locator('#report-compose-dialog').waitFor({state:'visible'});
for(const [id,ext] of [['report-compose-generate','zip'],['report-compose-logs','zip']]){
 const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#'+id).click()]);
 assert.equal(download.suggestedFilename(),'fixture.'+ext);
 await page.locator('#report-compose-generate:not([disabled])').waitFor();
 assert.equal(await page.locator('#report-compose-dialog').isVisible(),true);
}
const sent=writes.filter(w=>w.path.includes('/reports'));
assert.equal(sent.length,2);assert.deepEqual(sent[0].body,sent[1].body);
await page.screenshot({path:path.resolve(__dirname,'../../../bmca-runtime/verification/compact-report/download-dialog.png')});
assert.deepEqual(errors,[]);console.log('PASS: HTML and Logs ZIP buttons, same selection, dialog stays open, downloads and no page errors');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
