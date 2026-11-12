const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require(process.env.BMC_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const qa=process.env.BMC_REPORT_QA_DIR;
 assert.ok(qa,'Set BMC_REPORT_QA_DIR to the test_report_preview fixture directory.');
 const conditional=process.env.BMC_CP_REPORT==='1';
 const template=fs.readFileSync(path.join(qa,conditional?'cp-preview.html':'preview.html'),'utf8');
 const browser=await chromium.launch({executablePath:process.env.BMC_CHROME_PATH||'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[],writes=[],previews=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{if(window!==window.top)return;localStorage.setItem('bmc-execution-tabs-v1',JSON.stringify({ids:['a','b'],active:'a'}));window.EventSource=class{close(){}};});
  const cases=[{id:'c0',tc_name:conditional?'RF-01-008 OpenAPI Document Endpoint':'RF-01-002 Service Root',automation:'automatic',script_kind:'single',selected:false,status:conditional?'C-PASS':'Passed'},
               {id:'c1',tc_name:'RF-01-001 Version Discovery',automation:'semi_automatic',script_kind:'single',selected:false,status:'TBD'}];
  const a={id:'a',name:'Test A',plan_id:'pa',testcases:cases,counts:{Passed:conditional?0:1,'C-PASS':conditional?1:0,Failed:0},execution_active:false};
  const b={...a,id:'b',name:'Test B',plan_id:'pb',testcases:[{...cases[0],status:'Running'}],execution_active:true};
  const project={id:'p',name:'Project',plans:[{id:'pa',name:'Plan A',folders:[],testcases:cases,tasks:[a]},{id:'pb',name:'Plan B',folders:[],testcases:b.testcases,tasks:[b]}]};
  let fail=false,hold=false,release;
  await page.route('http://preview.test/**',async route=>{
   const url=new URL(route.request().url()),p=url.pathname,method=route.request().method();
   if(method!=='GET')writes.push(p);
   let data={};const task=p.includes('/b/')?b:a;
   if(p==='/api/projects')data={projects:[project]};
   else if(p==='/api/tasks')data={tasks:[a,b].map(t=>({...t,task_type:'Test',project_id:'p'}))};
   else if(p.endsWith('/summary'))data=task;
   else if(p.endsWith('/report-preview')){
    previews.push(p);const c=task.testcases.find(c=>c.id===p.split('/')[5]);
    if(hold){hold=false;await new Promise(resolve=>release=resolve);}
    if(fail){fail=false;await route.fulfill({status:404,json:{error:'Test Case is not in this Task.'}});return;}
    data={html:template.replaceAll('Case &lt;0&gt; &amp; QA',c.tc_name).replaceAll('Task One',task.name)};
   }else if(!p.startsWith('/api/')){
    await route.fulfill({body:fs.readFileSync(path.resolve(__dirname,'../static',p==='/'?'index.html':p.slice(1))),contentType:p.endsWith('.js')?'application/javascript':p.endsWith('.css')?'text/css':'text/html'});return;
   }
   try{await route.fulfill({json:data});}catch(e){if(!p.endsWith('/report-preview'))throw e;}
  });
  await page.goto('http://preview.test/#/execution');
  await page.locator('[data-action=execution-report-preview], [data-action=select-result]').first().waitFor();
  const local=await page.locator('.execution-case-row').count()>0;
  if(!local)await page.locator('[data-action=select-result][data-id=c0]').click();
  const opener=page.locator('[data-action=execution-report-preview][data-id=c0]');
  await opener.waitFor();
  if(local){
   const actions=await page.locator('[data-execution-case=c0] [data-action]').evaluateAll(bs=>bs.map(b=>b.dataset.action));
   assert.equal(actions[actions.indexOf('execution-log')+1],'execution-report-preview');
  }
  await opener.click();
  const dialog=page.locator('.report-preview-dialog'),frame=page.frameLocator('.report-preview-frame');
  await frame.locator('.method-table').waitFor();
  assert.equal(previews.at(-1),'/api/tasks/a/testcases/c0/report-preview');
  assert.deepEqual(await frame.locator('th').allTextContents(),['Step','Type','Description','Result','Judgement']);
  assert.equal(await frame.locator('details[open]').count(),1);
  assert.equal(await page.locator('.report-preview-frame').getAttribute('sandbox'),'allow-same-origin');
  assert.ok((await frame.locator('body').innerText()).includes(conditional?'Note: DUT returned HTTP 404':'Actual: 1.20.0'));
  assert.ok(!(await frame.locator('body').innerText()).includes('Test B'));
  if(conditional){
   assert.equal(await frame.locator('.status.c-pass').innerText(),'C-PASS');
   assert.deepEqual(await frame.locator('.method-table tbody tr td:last-child').allTextContents(),['COMPLETED','C-PASS',...Array(7).fill('Skip')]);
   assert.equal(await frame.locator('dt').filter({hasText:/^Note$/}).count(),0);
   assert.ok((await page.locator('#app').innerText().catch(()=>page.locator('body').innerText())).includes('C-PASS'));
  }
  for(const theme of ['light','dark']){
   await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
   const box=await dialog.boundingBox();assert.ok(box.x>=0&&box.y>=0&&box.y+box.height<=900);
   assert.equal(await frame.locator('html').evaluate(e=>e.scrollWidth>e.clientWidth),false);
   await page.screenshot({path:path.join(qa,(local?'preview-':'legacy-preview-')+theme+'.png')});
  }
  fail=true;await dialog.locator('[data-preview-refresh]').click();
  await dialog.getByRole('alert').filter({hasText:'Test Case is not in this Task.'}).waitFor();
  assert.equal(await page.locator('.report-preview-frame').isVisible(),false);
  await dialog.locator('[data-preview-refresh]').click();await frame.locator('.method-table').waitFor();
  await frame.locator('.method-table caption').click();
  await page.keyboard.press('Escape');await dialog.waitFor({state:'detached'});
  assert.equal(await opener.evaluate(e=>e===document.activeElement),true);
  // Closing a pending request must never reopen or replace a later Case preview.
  hold=true;await opener.click();await page.getByRole('status').filter({hasText:'Loading report preview'}).waitFor();
  await page.locator('[data-preview-close]').click();
  await page.locator('#execution-tab-b').click();
  if(!local)await page.locator('[data-action=select-result][data-id=c0]').click();
  await page.locator('[data-action=execution-report-preview][data-id=c0]').click();
  await page.frameLocator('.report-preview-frame').getByText('Test B',{exact:true}).waitFor();
  if(release)release();
  assert.equal(previews.at(-1),'/api/tasks/b/testcases/c0/report-preview');
  assert.ok((await page.locator('[data-preview-identity]').textContent()).startsWith('Test B'));
  await page.evaluate(()=>location.hash='#/repository');await page.locator('.report-preview-dialog').waitFor({state:'detached'});
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[]);
  console.log('PASS: preview entry, five report columns, sandbox, refresh/retry, Escape/focus, pending close, Task ownership, route cleanup, light/dark, read-only.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
