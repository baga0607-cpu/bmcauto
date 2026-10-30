const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('C:/Users/david.huang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],writes=[];page.on('pageerror',e=>errors.push(e.message));
 const specs={text:{type:'string',label:'Text',default:''},count:{type:'integer',label:'Count',default:0},enabled:{type:'boolean',label:'Enabled',default:false}};
 const cases=[{id:'a',tc_name:'Case A',automation:'semi_automatic',parameter_count:3,parameters_complete:false},{id:'b',tc_name:'Case B',automation:'automatic',parameter_count:1,parameters_complete:true},{id:'c',tc_name:'Case C',automation:'manual',parameter_count:0,parameters_complete:true},{id:'locked',tc_name:'Locked Case',automation:'semi_automatic',parameter_count:1,parameters_complete:true}].map(c=>({...c,script_kind:'single',folder_id:null}));
 const definitions={a:{id:'a',tc_name:'Case A',source:'TEST_CASE = {"name": "Case A"}\n# source A <safe>\n',metadata:{parameters:specs},settings:{text:'',count:0,enabled:false},settings_revision:0},b:{id:'b',tc_name:'Case B',source:'# source B\n',metadata:{parameters:{text:specs.text}},settings:{text:'B value'},settings_revision:0},c:{id:'c',tc_name:'Case C',source:'# source C\n',metadata:{parameters:{}},settings:{},settings_revision:0},locked:{id:'locked',tc_name:'Locked Case',source:'# locked\n',metadata:{parameters:{text:specs.text}},settings:{text:'locked'},settings_revision:0,editing_locked:true}};
 const project={id:'p',name:'Project',plans:[{id:'plan',name:'Plan',folders:[],testcases:cases,tasks:[]}]};let delayA=false;
 await page.route('http://windows.test/**',async route=>{
  const u=new URL(route.request().url());let data;
  if(u.pathname==='/api/projects')data={projects:[project]};
  else if(/\/definition$/.test(u.pathname)){
   const id=u.pathname.split('/')[5];if(id==='a'&&delayA&&route.request().method()==='GET')await new Promise(r=>setTimeout(r,220));
   if(route.request().method()==='PUT'){const body=route.request().postDataJSON();writes.push({id,body});assert.equal(body.source,definitions[id].source);assert.equal(body.settings_revision,definitions[id].settings_revision);definitions[id]={...definitions[id],settings:body.settings,settings_revision:body.settings_revision+1};cases.find(c=>c.id===id).parameters_complete=Object.values(body.settings).every(v=>typeof v!=='string'||v.trim().length>0);}
   data=definitions[id];
  }else if(u.pathname==='/api/repository/testcases')data=[{id:'repo',name:'Repo Case',folder_id:'root',metadata:{automation:'manual',parameters:{text:specs.text}}}];
  else if(u.pathname==='/api/repository/folders')data=[{id:'root',name:'BMC',parent_id:null,is_root:true,position:0}];
  else if(u.pathname==='/api/repository/testcases/repo')data={id:'repo',name:'Repo Case',source:'# repository source',metadata:{parameters:{text:specs.text}}};
  else if(u.pathname.startsWith('/api/'))throw Error('Unexpected API '+u.pathname);
  else return route.fulfill({body:fs.readFileSync(path.join(__dirname,'../static',u.pathname==='/'?'index.html':u.pathname.slice(1))),contentType:u.pathname.endsWith('.js')?'application/javascript':u.pathname.endsWith('.css')?'text/css':'text/html'});
  await route.fulfill({json:data});
 });
 await page.goto('http://windows.test/#/project/p/plans');await page.locator('[data-plan-case=a]').waitFor();
 const frame=await page.evaluate(()=>{
 const title=document.querySelector('.plan-tabs-heading .page-heading').getBoundingClientRect(),tabs=document.querySelector('.plan-tabs').getBoundingClientRect(),toolbar=document.querySelector('.repository-page-controls').getBoundingClientRect(),list=document.querySelector('#plan-case-list').getBoundingClientRect();
 return {titleBottom:title.bottom,tabsTop:tabs.top,tabsBottom:tabs.bottom,toolbarTop:toolbar.top,toolbarBottom:toolbar.bottom,listTop:list.top,actions:[...document.querySelectorAll('.repository-page-controls button')].map(el=>el.dataset.action)};
 });
 assert.ok(frame.titleBottom<=frame.tabsTop&&frame.tabsBottom<=frame.toolbarTop&&frame.toolbarBottom<=frame.listTop);
 assert.deepEqual(frame.actions,['choose-import-source','plan-list-rename','plan-list-delete']);
 await page.screenshot({path:require('os').tmpdir()+'/bmca-plan-frame.png'});
 await page.locator('[data-plan-case=b] .case-selection-label>strong').click();assert.equal(await page.locator('[data-case-window]').count(),0);
 await page.waitForTimeout(50);
 const listBottom=()=>page.locator('#plan-case-list .repository-scroll').evaluate(el=>el.getBoundingClientRect().bottom);
 assert.ok(Math.abs(await listBottom()-976)<2);
 await page.setViewportSize({width:1440,height:850});await page.waitForTimeout(50);assert.ok(Math.abs(await listBottom()-826)<2);await page.setViewportSize({width:1440,height:1000});
 assert.equal(await page.locator('[data-plan-case=a] [data-action=plan-case-parameters]').evaluate(el=>el.classList.contains('primary')),true);
 assert.equal(await page.locator('[data-plan-case=b] [data-action=plan-case-parameters]').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(255, 255, 255)');
 assert.equal(await page.locator('[data-plan-case=c] .automation-tag').getAttribute('aria-label'),'Fully manual — workflow not yet defined');assert.equal(await page.locator('[data-plan-case=c] .automation-tag circle[cy="7"]').count(),1);
 await page.locator('[data-plan-case=a]').click({button:'right'});await page.locator('.case-context-menu [data-action=plan-case-source]').click();assert.equal(page.context().pages().length,1);await page.locator('[data-case-window=viewer] pre').waitFor();const viewerPage=page,viewer=page.locator('[data-case-window=viewer]');await viewer.locator('pre').waitFor();assert.match(await viewer.locator('pre').innerText(),/source A <safe>/);assert.equal(await viewer.locator('pre safe').count(),0);await page.locator('[data-plan-case=b] .case-selection-label>strong').click();await viewer.getByText('# source B',{exact:false}).waitFor();assert.equal(await page.locator('[data-case-window=parameters]').count(),0);
 await page.locator('[data-plan-case=a] [data-action=plan-case-parameters]').click();await page.locator('[data-case-window=parameters] form').waitFor();const editorPage=page,editor=page.locator('[data-case-window=parameters]');await editor.locator('form').waitFor();assert.equal(await viewer.count(),1);assert.equal(await editor.count(),1);
 assert.equal(page.context().pages().length,1);assert.equal(await page.locator('[data-window-detach]').count(),0);assert.equal(await page.locator('#case-tools-dock [data-case-window]').count(),2);
 await viewer.locator('[data-window-close]').click();await page.locator('[data-plan-case=b] .case-selection-label>strong').click();await page.waitForTimeout(50);assert.equal(await page.locator('[data-case-window=viewer]').count(),0);assert.equal(await editor.getAttribute('data-case-id'),'b');await page.locator('[data-plan-case=a]').click({button:'right'});await page.locator('.case-context-menu [data-action=plan-case-source]').click();
 await editor.locator('[name="p:text"]').fill('   ');await editor.locator('[type=submit]').click();await page.waitForTimeout(80);assert.equal(writes.at(-1).body.settings.count,0);assert.equal(writes.at(-1).body.settings.enabled,false);assert.equal(await page.locator('[data-plan-case=a] [data-action=plan-case-parameters]').evaluate(el=>el.classList.contains('primary')),true);
 await editor.locator('[name="p:text"]').fill('Filled A');await editor.locator('[type=submit]').click();await page.waitForTimeout(80);assert.equal(await page.locator('[data-plan-case=a] [data-action=plan-case-parameters]').evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(255, 255, 255)');
 await editor.locator('[name="p:text"]').fill('unsaved');page.once('dialog',d=>d.dismiss());await page.locator('[data-plan-case=b] .case-selection-label>strong').click();assert.equal(await editor.getAttribute('data-case-id'),'a');assert.equal(await editor.locator('[name="p:text"]').inputValue(),'unsaved');
 page.once('dialog',d=>d.accept());await page.locator('[data-plan-case=b] .case-selection-label>strong').click();await page.waitForTimeout(80);assert.equal(await editor.getAttribute('data-case-id'),'b');assert.equal(await editor.locator('[name="p:text"]').inputValue(),'B value');assert.match(await viewer.locator('pre').innerText(),/source B/);
 delayA=true;await page.locator('[data-plan-case=a] .case-selection-label>strong').click();await page.locator('[data-plan-case=b] .case-selection-label>strong').click();await page.waitForTimeout(300);assert.equal(await editor.getAttribute('data-case-id'),'b');assert.match(await viewer.locator('pre').innerText(),/source B/);
 await page.locator('[data-plan-case=c] .case-selection-label>strong').click();await editor.getByText('No parameters declared for this Test Case.').waitFor();assert.equal(await editor.locator('[type=submit]').count(),0);
 await page.locator('[data-plan-case=locked] .case-selection-label>strong').click();await editor.locator('[name="p:text"]').waitFor();assert.equal(await editor.locator('[name="p:text"]').isDisabled(),true);assert.equal(await editor.locator('[type=submit]').isDisabled(),true);
 await page.evaluate(()=>location.hash='#/repository');await page.locator('[data-repository-id=repo]').waitFor();assert.equal(await page.locator('[data-case-window]').count(),0);await page.locator('[data-action=view-parameters]').click();const repoPage=page;await repoPage.locator('[data-case-window=parameters] form').waitFor();assert.equal(await repoPage.locator('[name="p:text"]').isDisabled(),true);
 assert.equal(writes.length,2);assert.deepEqual(errors,[]);await browser.close();console.log('PASS: automation icons, saved completeness colors, right-side Viewer and Editor, no popup controls, correct saves, draft cancellation, rapid selection races, empty/locked cases and read-only Repository.');
})().catch(e=>{console.error(e);process.exit(1)});