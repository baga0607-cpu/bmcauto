const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
(async()=>{const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});try{
 const page=await browser.newPage(),writes=[],errors=[],cases=[];page.on('pageerror',e=>errors.push(e.message));
 const folders=[{id:'root',name:'BMC',is_root:true,parent_id:null,position:0,folder_path:'BMC'},{id:'target',name:'Target',parent_id:'root',position:0,folder_path:'BMC/Target'}];
 await page.route('http://import.test/**',async route=>{const u=new URL(route.request().url()),p=u.pathname;let data;
 if(p==='/api/projects')data={projects:[]};
 else if(p==='/api/repository/history')data=[];
 else if(p==='/api/repository/inspect')data={metadata:{name:'Replacement',modified_at:'2026-11-24T08:00:00Z'}};
 else if(p==='/api/repository/activity')data={status:'ok'};
 else if(p==='/api/repository/folders')data=folders;
 else if(p==='/api/repository/testcases'){
  if(route.request().method()==='POST'){
   const body=route.request().postDataJSON();writes.push(body);await new Promise(r=>setTimeout(r,100));
   if(body.source==='invalid'){await route.fulfill({status:400,json:{error:'Invalid TEST_CASE declaration'}});return;}
   const c={id:String(cases.length),name:'Case '+cases.length,folder_id:body.folder_id,metadata:{parameters:{}}};cases.push(c);data=c;
  }else data=cases;
 }else{await route.fulfill({body:fs.readFileSync(path.resolve(__dirname,'../static',p==='/'?'index.html':p.slice(1))),contentType:p.endsWith('.js')?'application/javascript':p.endsWith('.css')?'text/css':'text/html'});return;}
 await route.fulfill({json:data});});
 await page.goto('http://import.test/#/repository');await page.locator('[data-folder-node=target]').waitFor();
 async function choose(files){await page.locator('[data-folder-node=target]').click();const chooser=page.waitForEvent('filechooser');await page.locator('[data-action=repo-import]').click();await(await chooser).setFiles(files);}
 const file=(name,text)=>({name,mimeType:'text/x-python',buffer:Buffer.from(text)});
 await choose([file('one.py','first source 中文'),file('bad.py','invalid'),file('three.PY','third source')]);
 await page.locator('#repository-import-results').waitFor();assert.equal(await page.locator('[data-import-close]').isDisabled(),true);await page.keyboard.press('Escape');assert.equal(await page.locator('#repository-import-results').isVisible(),true);
 await page.locator('[data-import-close]:enabled').waitFor();assert.equal(writes.length,3);assert.ok(writes.every(w=>w.folder_id==='target'));assert.deepEqual(writes.map(w=>w.source),['first source 中文','invalid','third source']);assert.equal(cases.length,2);
 assert.match(await page.locator('[data-import-progress]').innerText(),/2 imported, 1 failed, 3 total/);assert.match(await page.locator('#repository-import-results tbody').innerText(),/bad.py[\s\S]*Invalid TEST_CASE declaration/);assert.equal(await page.locator('[data-repository-id]').count(),2);
 await page.locator('[data-import-close]').click();await choose([file('retry.py','corrected source')]);await page.locator('[data-import-close]:enabled').waitFor();assert.equal(cases.length,3);assert.equal(await page.locator('#repository-file-picker').inputValue(),'');assert.equal(await page.locator('#repository-file-picker').getAttribute('multiple'),'');
 await page.locator('[data-import-close]').click();
 const rows=page.locator('tr[data-repository-id]');
 await rows.nth(0).click();await rows.nth(2).click({modifiers:['Shift']});
 assert.equal(await page.locator('.repo-selected').count(),3);
 await rows.nth(1).click({modifiers:['Control']});assert.equal(await page.locator('.repo-selected').count(),2);
 await rows.nth(0).click({button:'right'});assert.equal(await page.locator('.case-context-menu').count(),0);
 assert.equal(await page.locator('#repository-table input[type=checkbox]').count(),0);
 await rows.nth(0).click();await page.locator('[data-action=repo-replace]').click();
 await page.locator('.repo-operation input[type=file]').setInputFiles(file('new.py','next'));
 await page.locator('[data-action=repo-confirm]:enabled').waitFor();
 assert.match(await page.locator('[data-candidate]').innerText(),/Replacement/);
 await page.locator('[data-action=repo-close]').click();
 await page.locator('[data-folder-node=target]').click();await page.locator('[data-action=repo-folder]').click();
 assert.equal(await page.locator('#repository-create-folder-form').getAttribute('data-parent-id'),'target');
 await page.locator('[data-action=cancel-repository-folder]').click();
 await page.locator('[data-action=repo-all]').click();assert.equal(await page.locator('.repo-selected').count(),4);
 await page.locator('[data-action=repo-delete]').click();assert.equal(await page.locator('.repo-operation select').inputValue(),'keep');
 await page.locator('[data-action=repo-close]').click();await page.locator('[data-action=repo-history]').click();
 await page.locator('.repo-operation th').first().waitFor();
 assert.equal(await page.locator('.repo-operation th').allTextContents().then(xs=>xs.length),4);
 assert.deepEqual(errors,[]);console.log('PASS: multi-file selection, destination preservation, UTF-8 source, per-file validation errors, continue after failure, summary/list refresh, busy close protection and subsequent import. Mock APIs only.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
