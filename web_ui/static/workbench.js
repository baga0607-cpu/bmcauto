'use strict';
(() => {
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {eye:'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',plus:'M12 5v14M5 12h14',folder:'M3 7h7l2 2h9v11H3z M3 7V4h7l2 3',plan:'M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7',task:'M8 4h12v17H4V4h4 M8 2h8v4H8z M8 11l2 2 5-5',chevron:'M9 5l7 7-7 7',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',menu:'M4 6h16M4 12h16M4 18h16',sun:'M12 3v2M12 19v2M3 12h2M19 12h2M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2 M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0'};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.plan}"/></svg>`;
const state = {projects:[], repository:[], route:[], tab:'cases', panel:null, caseId:null, definition:null, dirty:false, scope:new Set(), log:'', activeTask:null, generation:0};
let confirmationPending=false;
let notificationTimer, previousHash = location.hash || '#/projects';
const path = (p, plan, task) => `#/project/${encodeURIComponent(p.id)}${plan ? '/plan/'+encodeURIComponent(plan.id) : ''}${task ? '/task/'+encodeURIComponent(task.id) : ''}`;
const button = (label, action, kind='', extra='') => `<button type="button" class="${kind}" data-action="${action}" ${extra}>${label}</button>`;
const status = value => `<span class="status ${escape(String(value).toLowerCase())}">${escape(value === 'TBD' ? 'Not run / pending' : value)}</span>`;
const automation = value => {
 const label=({automatic:'Automatic',semi_automatic:'Semi-automatic'})[value]||'Unclassified';
 const shape=value==='automatic'?'<path d="M9 3h6l.5 3 2.5 1.5 2.8-1 3 5.2-2.3 2v2.6l2.3 2-3 5.2-2.8-1-2.5 1.5-.5 3H9l-.5-3L6 22.5l-2.8 1-3-5.2 2.3-2v-2.6l-2.3-2 3-5.2 2.8 1L8.5 6z" transform="translate(2 0) scale(.83)"/><circle cx="12" cy="12" r="3"/>':value==='semi_automatic'?'<path d="M14.7 6.3a5.5 5.5 0 0 0-7 7L2.8 18.2a2.1 2.1 0 0 0 3 3l4.9-4.9a5.5 5.5 0 0 0 7-7l-3.5 3.5-3-3z"/>':'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5m0 3h.01"/>';
 return `<span class="automation-tag" role="img" aria-label="${label}" title="${label}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${shape}</svg></span>`;
};
const version = value => value ? date(value) + ' · ' + (String(value).match(/\.(\d+)/)?.[1] || '000000') : '—';
const date = value => value ? new Date(value).toLocaleString('en-GB', {year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';
function toast(message, error=false) { clearTimeout(notificationTimer); $('#notifications').innerHTML=`<div class="toast ${error?'error':''}" role="${error?'alert':'status'}">${escape(message)}</div>`; notificationTimer=setTimeout(()=>$('#notifications').replaceChildren(),error?12000:5000); }
async function api(url, method='GET', data) {
  const response = await fetch(url, {method,headers:data ? {'Content-Type':'application/json'} : {},body:data ? JSON.stringify(data) : undefined});
  const result = await response.json().catch(()=>({error:'The service returned an unreadable response.'}));
  if (!response.ok) { const error=new Error(result.error || `Request failed (${response.status}).`); error.status=response.status; throw error; }
  return result;
}
function context() {
  const project = state.projects.find(p=>p.id===state.route[1]);
  const plan = project?.plans.find(p=>p.id===state.route[3]);
  const task = plan?.tasks.find(t=>t.id===state.route[5]);
  return {project,plan,task};
}
function heading(title, description, actions='') { return `<div class="page-heading"><div><h1>${escape(title)}</h1><p>${escape(description)}</p></div><div class="actions">${actions}</div></div>`; }
function empty(title, description, action='') { return `<div class="empty"><h2>${escape(title)}</h2><p>${escape(description)}</p>${action}</div>`; }
function nameForm(type, current='') { return `<form id="name-form" class="inline-form" data-type="${type}"><h2>${type.startsWith('rename')?'Rename':'Create'} ${escape(type.split('-').at(-1))}</h2><label class="field"><span>Name</span><input name="name" required maxlength="100" value="${escape(current)}" autocomplete="off"></label><div class="form-actions"><button class="primary">${type.startsWith('rename')?'Save name':'Create'}</button>${button('Cancel','close-panel')}</div></form>`; }
function breadcrumbs() { const {project,plan,task}=context(); return `<nav class="breadcrumbs" aria-label="Breadcrumb"><a href="#/projects">Projects</a>${project?icon('chevron')+`<a href="${path(project)}">${escape(project.name)}</a>`:''}${plan?icon('chevron')+`<a href="${path(project,plan)}">${escape(plan.name)}</a>`:''}${task?icon('chevron')+`<span aria-current="page">${escape(task.name)}</span>`:''}</nav>`; }
function tabs(items, selected) { return `<div class="tabs" role="tablist" aria-label="Workspace sections">${items.map(([id,label])=>button(label,'tab','',`role="tab" aria-selected="${id===selected}" data-tab="${id}"`)).join('')}</div>`; }
function drawTree() {
  const query=$('#tree-search').value.trim().toLowerCase(); const {project,plan,task}=context();
  $('#tree').innerHTML=state.projects.map(p=> {
    const match=p.name.toLowerCase().includes(query); const plans=p.plans.filter(pl=>match || pl.name.toLowerCase().includes(query) || pl.tasks.some(t=>t.name.toLowerCase().includes(query)));
    if(query && !match && !plans.length) return '';
    const open=project?.id===p.id || Boolean(query);
    return `<div class="tree-group"><a class="${project?.id===p.id&&!plan?'current':''}" href="${path(p)}" ${project?.id===p.id&&!plan?'aria-current="page"':''}>${icon('folder')}<span>${escape(p.name)}</span><span class="count">${p.plans.length}</span></a>${open?plans.map(pl=>`<a class="plan-node ${plan?.id===pl.id&&!task?'current':''}" href="${path(p,pl)}" ${plan?.id===pl.id&&!task?'aria-current="page"':''}>${icon('plan')}<span>${escape(pl.name)}</span></a>${plan?.id===pl.id||query?pl.tasks.map(t=>`<a class="task-node ${task?.id===t.id?'current':''}" href="${path(p,pl,t)}" ${task?.id===t.id?'aria-current="page"':''}>${icon('task')}<span>${escape(t.name)}</span>${t.execution_active?'<span class="count">Running</span>':''}</a>`).join(''):''}`).join(''):''}</div>`;
  }).join('') || `<p class="help">${query?'No matching Projects, Plans or Tasks.':'Create a Project to start preparing a Test Plan.'}</p>`;
}
async function refresh(render=true) { const result=await api('/api/projects'); state.projects=result.projects; drawTree(); if(render) await draw(); }
function projectPage(project) {
  const list=project ? project.plans : state.projects;
  const controls=project ? button('New Plan','new-plan','primary')+button('Rename','rename-project')+button('Delete','delete-project','danger') : button('New Project','new-project','primary');
  return breadcrumbs()+heading(project?.name || 'Projects',project?'Prepare a separate Test Plan for each SKU or test scope.':'Organize your test work by Project, Plan and Task.',controls)+(state.panel?.includes('project')||state.panel?.includes('plan')?nameForm(state.panel, state.panel==='rename-project'?project.name:''):'')+(list.length?`<div class="table-wrap"><table><thead><tr><th>${project?'Test Plan':'Project'}</th><th>${project?'Test Cases':'Plans'}</th><th>Tasks</th><th>Next action</th></tr></thead><tbody>${list.map(item=>`<tr><td><a href="${project?path(project,item):path(item)}">${escape(item.name)}</a><p class="help">${project?'Independent Plan settings':'Project workspace'}</p></td><td>${project?item.testcases.length:item.plans.length}</td><td>${project?item.tasks.length:item.plans.reduce((n,p)=>n+p.tasks.length,0)}</td><td><a href="${project?path(project,item):path(item)}">${project?'Prepare Plan':'Open Project'}</a></td></tr>`).join('')}</tbody></table></div>`:empty(project?'Create your first Test Plan':'Create your first Project',project?'A Plan owns its own Python Test Cases and settings. You can create multiple Plans for different SKUs.':'Start with a Project, then create a Test Plan and load standard Test Cases.',button(project?'New Plan':'New Project',project?'new-plan':'new-project','primary')));
}
function tasksTable(project, plan, report=false) { return plan.tasks.length?`<div class="table-wrap"><table><thead><tr><th>Task</th><th>Scope</th><th>Current results</th><th>${report?'Report':'Action'}</th></tr></thead><tbody>${plan.tasks.map(task=>`<tr><td><a href="${path(project,plan,task)}">${escape(task.name)}</a>${task.execution_active?'<p class="help">Execution active</p>':''}</td><td>${task.testcases.length} Test Cases</td><td>${task.counts.Passed} passed · ${task.counts.Failed} failed${task.testcases.some(c=>c.needs_retest)?'<p class="help">Plan changed — rerun needed</p>':''}</td><td>${report?button('Generate report','report','small-button',`data-id="${escape(task.id)}" ${task.execution_active?'disabled':''}`):`<a href="${path(project,plan,task)}">Open Task</a>`}</td></tr>`).join('')}</tbody></table></div>`:empty('No Tasks yet','When the Plan is ready, create a Task and choose its Test Cases.',button('New Task','new-task','primary',plan.locked?'disabled':'')); }
async function planPage(project, plan) {
  let contents='';
  if(state.tab==='folders') contents=folderPage(plan);
  else if(state.tab==='tasks'||state.tab==='reports') contents=tasksTable(project,plan,state.tab==='reports');
  else if(state.panel==='add-repository') {
    state.repository=await api('/api/repository/testcases');state.repositoryFolders=await api('/api/repository/folders');
    contents=`<div class="toolbar"><h2>Add from Test Case Repository</h2>${button('Back to Plan','close-panel')}</div><p class="help">Each addition creates an independent Python file and settings in this Plan.</p>${repositoryWorkspace(true,plan)}`;
  } else {
    const retired=plan.testcases.filter(c=>c.script_kind!=='single'); const supported=plan.testcases.filter(c=>c.script_kind==='single');
    if(!plan.testcases.some(c=>c.id===state.caseId)) state.caseId=supported[0]?.id||retired[0]?.id;
    contents=(retired.length?`<div class="notice">${retired.length} retired step-based Test Case(s) remain in this Plan for their existing records. Step execution has been removed. Import replacement .py files through the Repository.</div>`:'')+
      (plan.testcases.length?`<div class="toolbar"><span class="help">${supported.length} single-file Test Cases · edits apply to every Task in this Plan</span>${button('New folder','new-folder','',plan.locked?'disabled':'')}</div><div class="split"><div class="case-browser"><label class="search-field"><span class="sr-only">Find Test Case</span><input type="search" id="case-search" placeholder="Find Test Case"></label><label class="sr-only" for="folder-filter">Filter by folder</label><select id="folder-filter"><option value="">All folders</option>${plan.folders.map(f=>`<option value="${escape(f.id)}">${escape(f.folder_path)}</option>`).join('')}</select><div class="case-list" id="case-list">${caseRows(plan)}</div></div><div class="case-editor" id="case-editor">${empty('Select a Test Case','Edit its parameters here. Tasks always use the latest saved Plan definition.')}</div></div>`:empty('Prepare this Plan','Add standard Test Cases from the Repository, then adapt their parameters for this Project.',button('Add from Repository','add-repository','primary',plan.locked?'disabled':'')));
  }
  return breadcrumbs()+heading(plan.name,'Test Plan · '+project.name,button('Add from Repository','add-repository','primary',plan.locked?'disabled':'')+button('New Task','new-task','',plan.locked?'disabled':'')+button('Rename','rename-plan','',plan.locked?'disabled':'')+button('Delete','delete-plan','danger',plan.locked?'disabled':''))+(plan.locked?'<div class="notice info">A Task is running. Plan structure and Task scope are locked. Only the running Test Case’s Python file and parameters are locked.</div>':'')+(state.panel && ['new-task','rename-plan','new-folder'].includes(state.panel)?nameForm(state.panel,state.panel==='rename-plan'?plan.name:''):'')+tabs([['cases','Test Cases'],['folders','Folders'],['tasks','Tasks'],['reports','Reports']],state.tab)+contents+(state.tab==='reports'?'<p class="help section">Reports use each Task’s current scope and retained results. Test Plan documents and Final Report consolidation will follow the agreed report-format design.</p>':'');
}
function folderPage(plan) {
 return `<div class="toolbar"><p class="help">Organize Test Cases in root folders and one level of children.</p>${button('New folder','new-folder','',plan.locked?'disabled':'')}</div>${plan.folders.map(folder=>`<form class="folder-form inline-form" data-id="${escape(folder.id)}"><div class="fields"><label class="field"><span>Folder name</span><input name="name" value="${escape(folder.name)}" required ${plan.locked?'disabled':''}></label><label class="field"><span>Parent folder</span><select name="parent_id" ${plan.locked?'disabled':''}><option value="">Plan root</option>${plan.folders.filter(f=>f.id!==folder.id&&!f.folder_path.startsWith(folder.folder_path+'/')).map(f=>`<option value="${escape(f.id)}" ${folder.parent_id===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('')}</select></label></div><div class="form-actions"><button ${plan.locked?'disabled':''}>Save folder</button>${button('Delete folder','delete-folder','danger',`data-id="${escape(folder.id)}" ${plan.locked?'disabled':''}`)}<span class="help">${plan.testcases.filter(c=>c.folder_id===folder.id).length} direct Test Cases</span></div></form>`).join('')||empty('No folders yet','Create a folder to organize this Plan’s Test Cases.',button('New folder','new-folder','primary'))}`;
}
function caseRows(plan) { return plan.testcases.map(c=>`<button class="case-row" data-action="select-case" data-id="${escape(c.id)}" data-search="${escape(c.tc_name.toLowerCase())}" data-folder="${escape(c.folder_id||'')}" aria-pressed="${c.id===state.caseId}"><strong>${automation(c.automation)}${escape(c.tc_name)}</strong><span class="help">${escape(c.folder_path||'Unfiled')}${c.script_kind!=='single'?' · Retired':''}</span></button>`).join(''); }
function parameterFields(metadata, settings, disabled=false) { return Object.entries(metadata.parameters||{}).map(([key,spec])=>{
  const value=settings[key]; const field=spec.type==='boolean'?`<input type="checkbox" name="p:${escape(key)}" ${value?'checked':''} ${disabled?'disabled':''}>`:`<input name="p:${escape(key)}" type="${['integer','number'].includes(spec.type)?'number':'text'}" ${spec.type==='integer'?'step="1"':spec.type==='number'?'step="any"':''} value="${escape(value)}" ${disabled?'disabled':''} ${spec.type==='string'?'':'required'}>`;
  return `<label class="field"><span>${escape(spec.label||key)}</span>${field}<span class="help">${escape(key)} · ${escape(spec.type)}</span></label>`;
}).join(''); }
async function loadCase() {
  const {plan}=context(); if(!plan||state.route[4]==='task'||state.tab!=='cases'||state.panel==='add-repository') return;
  const tc=plan.testcases.find(c=>c.id===state.caseId); const target=$('#case-editor'); if(!tc||!target) return;
  if(tc.script_kind!=='single') { target.innerHTML=`<h2>${escape(tc.tc_name)}</h2><div class="notice">Step-based editing and execution are retired. Existing Task evidence remains available.</div>${button('Delete retired Test Case','delete-case','danger')}`; return; }
  const requested=tc.id, generation=state.generation; target.innerHTML='<div class="loading">Loading Test Case…</div>';
  const def=await api(`/api/plans/${plan.id}/testcases/${tc.id}/definition`);
  if(state.caseId!==requested||generation!==state.generation||!target.isConnected) return;
  $$('.case-row').forEach(row=>row.setAttribute('aria-pressed',String(row.dataset.id===requested)));
  state.definition=def;
  target.innerHTML=`<header><h2>${automation(def.metadata.automation)}${escape(tc.tc_name)}</h2><p class="help">${escape(def.metadata.description||'Independent Plan Test Case')}</p></header><div class="metadata"><span>Source version <strong>${escape(version(def.source_version))}</strong></span><span>Plan revision <strong>${def.settings_revision}</strong></span></div>${def.editing_locked?'<div class="notice">This Test Case is running. Editing becomes available when it finishes.</div>':''}<form id="case-form"><div class="fields">${parameterFields(def.metadata,def.settings,def.editing_locked)}</div>${!Object.keys(def.metadata.parameters||{}).length?'<p class="help">This Test Case does not declare editable parameters.</p>':''}<details><summary>Project-specific Python adaptation</summary><p class="help">Adapt this Plan’s file without changing its source version. Declare editable fields in TEST_CASE.parameters.</p><div class="field"><label for="plan-source">Python source</label><textarea id="plan-source" class="source-editor code" name="source" spellcheck="false" ${def.editing_locked?'disabled':''}>${escape(def.source)}</textarea></div><div class="form-actions">${button('Read editable fields','inspect-source','',def.editing_locked?'disabled':'')}</div></details><div class="form-actions"><button class="primary" ${def.editing_locked?'disabled':''}>Save Plan Test Case</button><span class="help" id="save-state">Saved · applies to all Tasks</span></div></form><details><summary>Organization and export</summary><form id="case-details"><label class="field"><span>Test Case name</span><input name="name" value="${escape(tc.tc_name)}" required ${plan.locked?'disabled':''}></label><label class="field"><span>Folder</span><select name="folder_id" ${plan.locked?'disabled':''}><option value="">Custom (default)</option>${plan.folders.map(f=>`<option value="${escape(f.id)}" ${tc.folder_id===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('')}</select></label><div class="form-actions"><button ${plan.locked?'disabled':''}>Save organization</button>${button('Export Test Case','export-case')}${button('Delete Test Case','delete-case','danger',plan.locked?'disabled':'')}</div></form></details>`;
}
async function taskPage(project,plan,task) {
  if(!task.testcases.some(c=>c.id===state.caseId)) state.caseId=task.testcases[0]?.id||null;
  const scope=state.tab==='scope'; const needs=task.testcases.filter(c=>c.needs_retest).length;
  const toolbar=button('Generate report','report','',`data-id="${escape(task.id)}" ${task.execution_active?'disabled':''}`)+button('Rename','rename-task','',task.execution_active?'disabled':'')+button('Delete','delete-task','danger',task.execution_active?'disabled':'');
  let content;
  if(state.tab==='settings') content=await settingsPage(task);
  else if(scope) {
    content=`<p>Choose the Plan Test Cases included in this Task. Edit all test parameters in the <a href="${path(project,plan)}">Plan</a>.</p><div class="toolbar"><div class="actions">${button('Select all','scope-all','',plan.locked?'disabled':'')}${button('Clear selection','scope-none','',plan.locked?'disabled':'')}</div><span class="help" id="scope-count">${state.scope.size} selected</span></div><form id="scope-form"><div class="table-wrap"><table><thead><tr><th>Include</th><th>Test Case</th><th>Folder</th><th>Source version</th></tr></thead><tbody>${plan.testcases.map(c=>`<tr><td class="check"><input type="checkbox" data-scope="${escape(c.id)}" aria-label="Include ${escape(c.tc_name)}" ${state.scope.has(c.id)?'checked':''} ${plan.locked||c.script_kind!=='single'?'disabled':''}></td><td>${automation(c.automation)}${escape(c.tc_name)}${c.script_kind!=='single'?'<p class="help">Retired — single .py required</p>':''}</td><td>${escape(c.folder_path||'Unfiled')}</td><td>${escape(version(c.source_version))}</td></tr>`).join('')}</tbody></table></div><div class="form-actions"><button class="primary" ${plan.locked?'disabled':''}>Save Task scope</button><span class="help">Removing a case also removes its current Task result and logs.</span></div></form>`;
  } else if(state.tab==='details') content=`<form id="task-details" class="settings-form"><h2>Task information</h2><p class="help">These fields describe the assignment; Test Case settings belong to the Plan.</p><div class="fields">${['tester','firmware','notes'].map(key=>`<label class="field ${key==='notes'?'full':''}"><span>${key[0].toUpperCase()+key.slice(1)}</span><${key==='notes'?'textarea':'input'} name="${key}" ${key==='notes'?'rows="4"':''} ${task.execution_active?'disabled':''} ${key!=='notes'?`value="${escape(task.setup[key]||'')}"`:''}>${key==='notes'?escape(task.setup[key]||'')+'</textarea>':''}</label>`).join('')}</div><div class="form-actions"><button class="primary" ${task.execution_active?'disabled':''}>Save Task information</button></div></form>`;
  else content=task.testcases.length?`<div class="execution-summary"><span><strong>${task.testcases.length}</strong> in scope</span><span><strong>${task.counts.Passed}</strong> passed</span><span><strong>${task.counts.Failed}</strong> failed</span><span><strong>${needs}</strong> need rerun</span></div><div class="toolbar"><p class="help">Run checked cases using the latest saved Plan settings.</p><div class="actions">${task.execution_active?button('Stop execution','stop','danger')+(!state.activeTask?button('Resume monitoring','resume','primary'):''):button('Run selected cases','run','primary')}</div></div><div class="split"><div class="case-browser"><div class="case-list">${task.testcases.map(c=>`<div class="task-case"><label class="checkbox-field" style="padding:10px 18px 0"><input type="checkbox" data-run="${escape(c.id)}" aria-label="Run ${escape(c.tc_name)}" ${c.selected?'checked':''} ${task.execution_active||c.script_kind!=='single'?'disabled':''}><span class="help">Include in execution</span></label><button class="case-row" data-action="select-result" data-id="${escape(c.id)}" aria-pressed="${state.caseId===c.id}"><strong>${automation(c.automation)}${escape(c.tc_name)}</strong>${status(c.status)} ${c.needs_retest?'<span class="status stale">Rerun needed</span>':''}${c.script_kind!=='single'?'<p class="help">Retired step-based case</p>':''}</button></div>`).join('')}</div></div><div class="case-editor" id="evidence">${evidence(task)}</div></div>`:empty('Set this Task’s scope','Select Test Cases from the Plan before starting an execution.',button('Choose Test Cases','scope','primary',plan.locked?'disabled':''));
  return breadcrumbs()+heading(task.name,'Task · '+plan.name,toolbar)+(state.panel==='rename-task'?nameForm(state.panel,task.name):'')+(needs?`<div class="notice">Plan definitions or Task connection settings changed for ${needs} Test Case(s). Existing results and logs remain available; rerun those cases before using the report.</div>`:'')+(task.execution_active?'<div class="notice info">Execution is active. Scope is locked until execution finishes or stops.</div>':'')+tabs([['execution','Execution & results'],['scope','Task scope'],['settings','Connection settings'],['details','Task information']],state.tab)+content;
}
function evidence(task) {
  const tc=task.testcases.find(c=>c.id===state.caseId); if(!tc)return '';
  return `<h2>${automation(tc.automation)}${escape(tc.tc_name)}</h2><div class="metadata"><span>Latest result ${status(tc.status)}</span><span>Executed <strong>${escape(date(tc.executed_at))}</strong></span></div>${tc.needs_retest?'<div class="notice">Retained evidence predates the current Plan definition or Task connection settings. Rerun needed.</div>':''}${tc.manual_override?`<p class="help">Manual result: ${escape(tc.manual_override.status)} · ${escape(tc.manual_override.reason||'No reason recorded')}</p>`:''}<div class="actions">${button('Execution log','execution-log','small-button')}${button('API log','api-log','small-button')}</div><pre class="log code" id="log-output">${escape(state.activeTask===task.id && tc.status==='Running'?state.log:tc.log_text||'No execution log. Run this Test Case to collect evidence.')}</pre><div id="input-slot">${state.activeTask===task.id&&state.prompt?inputForm(state.prompt.session,state.prompt.text):''}</div><details><summary>Result annotation</summary><form id="annotation-form"><div class="fields"><label class="field"><span>Manual status</span><select name="status" ${task.execution_active?'disabled':''}><option value="TBD">Not run / pending</option><option value="Passed">Passed</option><option value="Failed">Failed</option></select></label><label class="field"><span>Reason</span><input name="reason" ${task.execution_active?'disabled':''}></label><label class="field"><span>Bug ID</span><input name="bug_id" value="${escape(tc.bug_id)}" ${task.execution_active?'disabled':''}></label></div><div class="form-actions"><button ${task.execution_active?'disabled':''}>Save annotation</button></div></form></details>`;
}
function repositoryCheck(kind,id){return state.repositoryBatch?`<input type="checkbox" class="repository-batch-check" data-kind="${kind}" data-id="${escape(id)}" aria-label="Select ${kind}" ${state.repositorySelection?.has(kind+':'+id)?'checked':''}>`:'';}
function repositorySelectionData(){const folders=[],cases=[];for(const value of state.repositorySelection||[]){const [kind,id]=value.split(':');(kind==='folder'?folders:cases).push(id);}return {folder_ids:folders,case_ids:cases};}
function folderAction(label,action,id,kind=''){return button(icon(action==='new-repository-folder'?'plus':'trash'),action,'small-button icon-button '+kind,`data-id="${escape(id)}" aria-label="${label}" title="${label}"`);}
function selectedRepositoryFolder(){return state.repositoryFolders.find(f=>f.id===state.repositoryFolder)||state.repositoryFolders.find(f=>f.is_root);}
function repositoryFolderOptions(selected) {
 return (state.repositoryFolders||[]).map(f=>`<option value="${escape(f.id)}" ${selected===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('');
}
function repositoryTable(add=false,plan=null) {
 const selected=selectedRepositoryFolder();state.repositoryFolder=selected?.id;
 const folderCounts=new Map();
 const folderCount=id=>{if(!folderCounts.has(id))folderCounts.set(id,state.repository.filter(c=>c.folder_id===id).length+state.repositoryFolders.filter(f=>f.parent_id===id).reduce((n,f)=>n+folderCount(f.id),0));return folderCounts.get(id);};
 const caseRow=(c,depth)=>{const exists=plan?.testcases.some(t=>t.tc_name.toLowerCase()===c.name.toLowerCase());
 return `<tr data-repository-id="${escape(c.id)}" ${add?'':'draggable="true"'} data-search="${escape(c.name.toLowerCase())}" style="--depth:${depth}"><td>${repositoryCheck('case',c.id)}<strong>${automation(c.metadata.automation)}${escape(c.name)}</strong><p class="help">${escape(version(c.source_version))}</p></td><td>${add?button(exists?'Already in Plan':'Add to Plan','add-case',exists?'':'primary',`data-id="${escape(c.id)}" ${exists||plan.locked?'disabled':''}`):button(`Parameters (${Object.keys(c.metadata.parameters||{}).length})`,'view-parameters','small-button',`data-id="${escape(c.id)}" aria-label="Parameters for ${escape(c.name)}"`)}</td>${add?'':`<td><div class="actions">${button(icon('eye'),'view-standard','small-button icon-button',`data-id="${escape(c.id)}" title="View" aria-label="View ${escape(c.name)}"`)}${button(icon('trash'),'remove-standard','small-button icon-button danger',`data-id="${escape(c.id)}" title="Remove" aria-label="Remove ${escape(c.name)}"`)}</div></td>`}</tr>`;};
 const children=(parent,depth)=>state.repositoryFolders.filter(f=>f.parent_id===parent).sort((a,b)=>a.position-b.position).map(f=>`<tr class="repository-folder-row" data-folder-node="${escape(f.id)}" data-action="select-repository-folder" data-id="${escape(f.id)}" ${add||f.is_root?'':'draggable="true"'} style="--depth:${depth}"><td><div class="repository-folder-line">${f.is_root?(state.repositoryBatch?'<input type="checkbox" disabled aria-label="BMC">':''):repositoryCheck('folder',f.id)}${button(state.repositoryCollapsed?.has(f.id)?'&#9656;':'&#9662;','toggle-repository-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!state.repositoryCollapsed?.has(f.id)}"`)}<button type="button" class="repository-folder-name" data-action="select-repository-folder" data-id="${escape(f.id)}" aria-pressed="${selected?.id===f.id}" title="${escape(f.folder_path)}">${icon('folder')}<strong>${escape(f.name)}</strong><span class="repository-folder-count">(${folderCount(f.id)})</span></button>${state.repositoryRename===f.id?`<input class="repository-rename" data-id="${escape(f.id)}" aria-label="Folder name" value="${escape(f.name)}" maxlength="100">`:''}</div></td>${add?'':'<td></td>'}<td><div class="actions">${add?button('Add folder to Plan','add-repository-folder','small-button',`data-id="${escape(f.id)}" ${plan.locked?'disabled':''}`):folderAction('New folder','new-repository-folder',f.id)+(f.is_root?'':folderAction('Remove folder','remove-repository-folder',f.id,'danger'))}</div></td></tr>${state.repositoryCollapsed?.has(f.id)?'':children(f.id,depth+1)+state.repository.filter(c=>c.folder_id===f.id).map(c=>caseRow(c,depth+1)).join('')}`).join('');
 return `${add?'<div class="toolbar"><label><span class="sr-only">Find Test Case</span><input id="repository-search" type="search" placeholder="Find Test Case"></label></div>':''}<div class="table-wrap repository-scroll"><table id="repository-table" class="repository-hierarchy"><thead><tr><th>Directory / Test Case</th><th>${add?'Plan action':'Parameters'}</th>${add?'':'<th>Actions</th>'}</tr></thead><tbody>${children(null,0)}</tbody></table></div>`;
}
function repositoryWorkspace(add=false,plan=null){
 const selected=selectedRepositoryFolder();state.repositoryFolder=selected.id;
 return `<div class="repository-layout ${!add&&state.repositoryDefinition?'has-preview':''}" style="--preview-width:${state.repositoryPreviewWidth||45}%"><div class="repository-list">${repositoryTable(add,plan)}</div>${!add&&state.repositoryDefinition?`<div class="repository-resizer" role="separator" tabindex="0" aria-label="Resize details panel" aria-orientation="vertical" aria-controls="repository-preview" aria-valuemin="25" aria-valuemax="70" aria-valuenow="${state.repositoryPreviewWidth||45}"></div>${standardPreview(state.repositoryDefinition)}`:''}</div>`;
}
function standardPreview(def){
 const parameters=Object.entries(def.metadata.parameters||{}),onlyParameters=state.repositoryView==='parameters';
 return `<section id="repository-preview" tabindex="-1" aria-label="Test Case details"><div class="toolbar repository-preview-header"><h2>${escape(def.name)}</h2>${button('Close','close-standard','preview-close')}</div><div class="repository-preview-content"><h3>${onlyParameters?'Editable parameters':'Python source'}</h3>${onlyParameters?(parameters.length?`<div class="table-wrap"><table><thead><tr><th>Parameter</th><th>Type</th><th>Default</th></tr></thead><tbody>${parameters.map(([key,spec])=>`<tr><td>${escape(spec.label||key)}${spec.label&&spec.label!==key?`<p class="help">${escape(key)}</p>`:''}</td><td>${escape(spec.type)}</td><td>${escape(JSON.stringify(spec.default))}</td></tr>`).join('')}</tbody></table></div><p class="help">Edit these values after adding the Test Case to a Plan.</p>`:'<p class="help">No editable parameters declared.</p>'):`<pre class="log code">${escape(def.source)}</pre>`}</div></section>`;
}
async function repositoryPage() {
 state.repository=await api('/api/repository/testcases');state.repositoryFolders=await api('/api/repository/folders');
 const selected=selectedRepositoryFolder(),editing=state.panel==='edit-repository-folder';
 const folderForm=['new-repository-folder','edit-repository-folder'].includes(state.panel)?`<form id="repository-folder-form" class="inline-form" data-id="${editing?escape(selected.id):''}"><h2>${editing?'Edit folder':'New folder'}</h2><p class="help">${escape(editing?selected.folder_path:selected.folder_path+'/')}</p><label class="field"><span>Name</span><input name="name" value="${editing?escape(selected.name):''}" required maxlength="100"></label><div class="form-actions"><button class="primary">${editing?'Save':'Create folder'}</button>${button('Cancel','close-panel')}</div></form>`:'';
 return `<div class="repository-page-controls actions"><label><span class="sr-only">Find Test Case</span><input id="repository-search" type="search" placeholder="Find Test Case"></label>${button('Add Test Case','import-python','primary')}${button(state.repositoryBatch?'Finish batch':'Batch operations','repository-batch-toggle')}${state.repositoryBatch?button('Delete selected','repository-batch-delete','danger',state.repositorySelection?.size?'':'disabled'):''}</div>`+folderForm+(state.panel==='import-python'?`<form id="repository-form" class="inline-form"><h2>Add Test Case</h2><label class="field"><span>Python file</span><input type="file" name="file" accept=".py" required></label><label class="field"><span>Folder</span><select name="folder_id">${repositoryFolderOptions(selected.id)}</select></label><div class="form-actions"><button class="primary">Add to Repository</button>${button('Cancel','close-panel')}</div></form>`:'')+repositoryWorkspace();
}
const settingsGroups=[['BMC connection',[['host','BMC URL'],['username','Username'],['password','Password','password']]],['Console server (optional)',[['cs_host','Host'],['cs_port','Port','number'],['cs_protocol','Protocol'],['cs_username','Username'],['cs_password','Password','password']]],['DUT console commands (optional)',[['dut_connect_cmd','Connect command'],['dut_exit_cmd','Exit command'],['dut_force_connect_cmd','Force connect command']]],['DUT operating system (optional)',[['dut_os_type','OS type'],['dut_os_host_ip','Host IP'],['dut_os_username','Username'],['dut_os_password','Password','password'],['dut_os_prompt_regex','Prompt expression']]]];
async function settingsPage(task) {
  let config={},missing=false; try {config=await api(`/api/tasks/${task.id}/settings`);}catch(e){if(e.status!==404)throw e;missing=true;}
  return '<h2>Connection settings</h2><p>Independent BMC and DUT connection environment for this Task. Other Tasks keep their own settings.</p>'+ (task.execution_active?'<div class="notice">This Task is executing. Connection settings are locked.</div>':'')+(missing?'<div class="notice info">Configure the BMC connection for this Task before execution.</div>':'')+`<form id="settings-form" class="settings-form"><fieldset class="connection-fields" ${task.execution_active?'disabled':''}>${settingsGroups.map(([name,fields],i)=>`<section class="section"><h2>${name}</h2><div class="fields">${fields.map(([key,label,type='text'])=>`<label class="field"><span>${label}</span><input name="${key}" type="${type}" value="${escape(config[key]??'')}" ${key==='host'?'placeholder="https://bmc-host" required':''} autocomplete="${type==='password'?'new-password':'off'}"></label>`).join('')}${i===0?`<label class="checkbox-field"><input type="checkbox" name="verify_ssl" ${config.verify_ssl?'checked':''}>Verify TLS certificate</label>`:''}</div></section>`).join('')}<div class="form-actions"><button class="primary">Save connection settings</button></div></fieldset></form>`;
}
async function taskManagementPage() {
  const result=await api('/api/tasks'); state.managedTasks=result.tasks;
  const plans=state.projects.flatMap(p=>p.plans);
  const editing=state.managedTasks.find(t=>t.id===state.managerTaskId);
  const form=state.panel==='manager-new'?TaskManagement.form(state.projects):state.panel==='manager-edit'&&editing?TaskManagement.form(state.projects,editing):'';
  const search=state.managerSearch||'';
  return heading('Task information','',button('New Task','manager-new','primary',!plans.some(p=>!p.locked)?'disabled':''))+
    (!plans.length?'<div class="notice info">Create a Project and Plan before adding Tasks. <a href="#/projects">Open Projects</a></div>':'')+form+
    `<div class="toolbar"><label><span class="sr-only">Find Task</span><input id="manager-search" type="search" placeholder="Find Task, Project or Plan" value="${escape(search)}"></label></div><div id="task-manager-content">${TaskManagement.content(state.managedTasks,search)}</div>`;
}
async function draw() {
  const generation=++state.generation; const workspace=$('#workspace'); workspace.setAttribute('aria-busy','true');
  const section=state.route[0]||'projects'; document.body.classList.toggle('repository-page',section==='repository'); $$('.global-nav a').forEach(a=>a.toggleAttribute('aria-current',a.dataset.section===(section==='project'?'projects':section))); $$('.global-nav [aria-current]').forEach(a=>a.setAttribute('aria-current','page'));
  const {project,plan,task}=context(); let html;
  if(task) Object.assign(task, await api(`/api/tasks/${task.id}/summary`));
  if(generation!==state.generation)return;
  if(section==='tasks') html=await taskManagementPage(); else if(section==='repository') html=await repositoryPage(); else if(section==='settings') html=empty('Choose a Task','Connection settings belong to each Task. Open a Task and select Connection settings.'); else if(section==='project'&&!project || state.route[2]==='plan'&&!plan || state.route[4]==='task'&&!task) html=empty('Workspace not found','This item may have been deleted. Choose an existing Project from the navigator.','<a href="#/projects">Go to Projects</a>');
  else if(task) html=await taskPage(project,plan,task); else if(plan) html=await planPage(project,plan); else html=projectPage(project);
  if(generation!==state.generation)return; workspace.innerHTML=html; workspace.setAttribute('aria-busy','false'); drawTree();
  if(plan&&!task) await loadCase();
  if(state.panel && $('#name-form input')) $('#name-form input').focus();
}
function discard() { return !state.dirty || window.confirm('Discard unsaved changes?'); }
async function navigate() {
  if(state.restoringHash){state.restoringHash=false;return;}
  if(!discard()){state.restoringHash=true;location.hash=previousHash;return;}
  previousHash=location.hash||'#/projects'; state.route=previousHash.slice(2).split('/').map(decodeURIComponent); state.panel=null;state.dirty=false;state.definition=null;state.caseId=null;state.repositoryDefinition=null;document.body.classList.toggle('repository-page',state.route[0]==='repository');
  $('#workspace').innerHTML='<div class="loading">Loading workspace…</div>';
  $('#workspace').setAttribute('aria-busy','true');
  await refresh(false);
  state.tab=state.route[4]==='task'?'execution':'cases'; const {task}=context(); state.scope=new Set(task?.testcases.map(c=>c.id)||[]);
  state.panel=state.nextPanel||null;state.nextPanel=null;
  document.body.classList.remove('nav-open');$('#nav-toggle').setAttribute('aria-expanded','false');await draw();
}
async function confirmDelete(title,message) {
  if(confirmationPending)return false;confirmationPending=true;
  $('#confirm-title').textContent=title;$('#confirm-message').textContent=message;const dialog=$('#confirm-dialog');dialog.returnValue='';dialog.showModal();
  return new Promise(resolve=>dialog.addEventListener('close',()=>{const answer=dialog.returnValue==='confirm';confirmationPending=false;resolve(answer);},{once:true}));
}
function download(name, content, type='text/plain') { const url=URL.createObjectURL(new Blob([content],{type})); const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000); }
function currentSettings() { const form=$('#case-form'); return Object.fromEntries(Object.entries(state.definition.metadata.parameters||{}).map(([key,spec])=>{const field=form.elements.namedItem('p:'+key);return [key,spec.type==='boolean'?field.checked:['integer','number'].includes(spec.type)?Number(field.value):field.value];})); }
async function doAction(action, element) {
  const {project,plan,task}=context();
  if(action==='manager-new'||action==='manager-edit'){
    if(!discard())return;state.dirty=false;state.panel=action;state.managerTaskId=action==='manager-edit'?element.dataset.id:null;await draw();$('#task-manager-form input')?.focus();
  } else if(action==='manager-delete'){
    const current=state.managedTasks.find(t=>t.id===element.dataset.id);if(!current)return;
    if(!discard())return;
    if(!await confirmDelete(`Delete Task: ${current.name}?`,'This deletes the Task, its scope and current results. Plan Test Cases and other Tasks remain.'))return;
    await api(`/api/tasks/${current.id}`,'DELETE');state.dirty=false;state.panel=null;await refresh();toast('Task deleted.');
  } else if(action==='tab'){if(!discard())return;state.dirty=false;state.tab=element.dataset.tab;state.panel=null;await draw();}
  else if(action==='close-panel'){if(!discard())return;state.dirty=false;state.panel=null;await draw();}
  else if(['new-project','new-plan','new-task','rename-project','rename-plan','rename-task','new-folder','add-repository','import-python'].includes(action)){if(!discard())return;state.dirty=false;if(action==='new-project'&&state.route[0]!=='projects'){state.nextPanel=action;location.hash='#/projects';return;}state.panel=action;state.tab='cases';await draw();}
  else if(action==='select-case'){if(!discard())return;state.generation++;state.dirty=false;state.caseId=element.dataset.id;$$('.case-row').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.id===state.caseId)));await loadCase();}
  else if(action==='select-result'){state.caseId=element.dataset.id;await draw();}
  else if(action==='toggle-repository-folder'){state.repositoryCollapsed??=new Set();state.repositoryCollapsed.has(element.dataset.id)?state.repositoryCollapsed.delete(element.dataset.id):state.repositoryCollapsed.add(element.dataset.id);await draw();}
  else if(action==='repository-batch-toggle'){state.repositoryBatch=!state.repositoryBatch;state.repositorySelection=new Set();await draw();}
  else if(action==='repository-batch-delete'){const selection=repositorySelectionData();if(!await confirmDelete('Delete selected items?',`${selection.folder_ids.length} directories and ${selection.case_ids.length} Test Cases selected. Selected directories and all their contents will be permanently deleted. Plan copies remain independent.`))return;await api('/api/repository/batch','POST',{...selection,action:'delete',confirm:true});state.repositorySelection.clear();state.repositoryDefinition=null;await draw();toast('Selected items deleted.');}
  else if(action==='select-repository-folder'){
    const id=element.dataset.id,folder=state.repositoryFolders.find(f=>f.id===id);
    const rename=state.route[0]==='repository'&&element.classList.contains('repository-folder-name')&&state.repositoryNameClick===id&&state.repositoryFolder===id&&!folder.is_root;
    state.repositoryRename=rename?id:null;state.repositoryFolder=id;state.repositoryDefinition=null;if(state.route[0]==='repository')state.panel=null;await draw();
    if(rename){const input=$('.repository-rename');input.focus();input.select();}
  }
  else if(action==='new-repository-folder'){
    const parent=element.dataset.id||selectedRepositoryFolder().id;
    const folders=await api('/api/repository/folders');
    const names=new Set(folders.filter(f=>f.parent_id===parent).map(f=>f.name.toLowerCase()));
    let name='\u65b0\u8cc7\u6599\u593e',number=2;while(names.has(name.toLowerCase()))name=`\u65b0\u8cc7\u6599\u593e (${number++})`;
    const folder=await api('/api/repository/folders','POST',{name,parent_id:parent});
    state.repositoryFolder=folder.id;state.panel=null;state.dirty=false;await draw();
    $(`[data-folder-node="${folder.id}"]`)?.scrollIntoView({block:'nearest'});toast('Folder created.');
  }
  else if(action==='edit-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;state.panel=action;await draw();}
  else if(action==='remove-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;const selected=selectedRepositoryFolder();if(!await confirmDelete(`Remove folder: ${selected.name}?`,'This permanently deletes the folder, all subfolders and their Test Cases. Existing Plan copies remain independent.'))return;const result=await api(`/api/repository/folders/${selected.id}`,'DELETE',{confirm:true});state.repositoryFolder=result.parent_id;state.repositoryDefinition=null;state.panel=null;await draw();toast('Folder and contents deleted.');}
  else if(action==='add-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;const result=await api(`/api/plans/${plan.id}/repository/folders/${state.repositoryFolder}`,'POST',{});await refresh();toast(`${result.added.length} Test Cases copied into ${result.folder_name}. ${result.skipped.length} existing/duplicate names skipped.`);}
  else if(action==='add-case'){await api(`/api/plans/${plan.id}/repository/testcases`,'POST',{repository_id:element.dataset.id});await refresh();toast('Test Case copied into this Plan.');}
  else if(action==='inspect-source'){const result=await api('/api/repository/inspect','POST',{source:$('#case-form').elements.source.value});const old=currentSettings();state.definition.metadata=result.metadata;const settings=Object.fromEntries(Object.entries(result.metadata.parameters||{}).map(([k,s])=>[k,k in old?old[k]:s.default]));$('#case-form .fields').innerHTML=parameterFields(result.metadata,settings);state.dirty=true;toast('Editable fields refreshed. Save to apply this adaptation.');}
  else if(action==='scope'){state.tab='scope';await draw();}
  else if(action==='scope-all'||action==='scope-none'){state.scope=new Set(action==='scope-all'?plan.testcases.filter(c=>c.script_kind==='single').map(c=>c.id):[]);state.dirty=true;await draw();}
  else if(action==='execution-log'||action==='api-log'){const c=task.testcases.find(c=>c.id===state.caseId);$('#log-output').textContent=(action==='api-log'?c.api_log_text:c.log_text)||'No log collected for this Test Case.';}
  else if(action==='run'){const ids=$$('[data-run]:checked').map(e=>e.dataset.run);if(!ids.length)throw Error('Select at least one Test Case to run.');if(task.testcases.some(c=>ids.includes(c.id)&&c.result)&&!window.confirm('Run selected cases again? Their current results and logs will be replaced.'))return;const config=await api(`/api/tasks/${task.id}/settings`).catch(()=>{throw Error('Configure this Task?s BMC connection in Connection settings before running.');});if(!config.host)throw Error('Set this Task?s BMC URL in Connection settings before running.');const result=await api(`/api/tasks/${task.id}/execution/start`,'POST',{testcase_ids:ids});runTask(task.id,ids,result.execution_token).catch(e=>toast(e.message,true));}
  else if(action==='resume'){const current=await api(`/api/tasks/${task.id}/execution`);runTask(task.id,current.testcase_ids,current.execution_token,current.session_id).catch(e=>toast(e.message,true));}
  else if(action==='stop'){const current=await api(`/api/tasks/${task.id}/execution`);await api(`/api/tasks/${task.id}/execution/stop`,'POST',{execution_token:current.execution_token});toast('Stop requested. Waiting for the running Test Case to finish.');}
  else if(action==='report'){element.disabled=true;try{const response=await fetch(`/api/tasks/${element.dataset.id}/report`);if(!response.ok){const err=await response.json();throw Error(err.error||'Report generation failed.');}const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`BMC_Test_Report_${element.dataset.id}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Task report generated.');}finally{element.disabled=false;}}
  else if(action==='delete-folder'){const impact=await api(`/api/folders/${element.dataset.id}/impact`);if(!await confirmDelete('Delete folder and contents?',`${impact.testcase_count} Test Case(s), ${impact.descendant_folder_count} child folder(s) and evidence in ${impact.affected_task_count} Task(s) will be deleted.`))return;await api(`/api/folders/${element.dataset.id}`,'DELETE',{confirm:true,acknowledgement:true});state.dirty=false;await refresh();toast('Folder and contents deleted.');}
  else if(['view-standard','view-parameters'].includes(action)){state.repositoryView=action==='view-parameters'?'parameters':'source';state.repositoryDefinition=await api('/api/repository/testcases/'+element.dataset.id);await draw();$('#repository-preview')?.focus();}
  else if(action==='remove-standard'){
    if(!discard())return;const current=state.repository.find(c=>c.id===element.dataset.id);if(!current)return;
    if(!await confirmDelete(`Remove Test Case: ${current.name}?`,`Remove source version ${current.source_version} from the Repository. Existing Plan copies, settings and Task evidence remain.`))return;
    await api(`/api/repository/testcases/${current.id}`,'DELETE',{confirm:true});
    if(state.repositoryDefinition?.id===current.id)state.repositoryDefinition=null;
    state.dirty=false;state.panel=null;await draw();toast('Repository Test Case removed.');
  }
  else if(action==='close-standard'){state.repositoryDefinition=null;await draw();}
  else if(action==='export-case'){const c=plan.testcases.find(c=>c.id===state.caseId);download(c.tc_name+'.json',JSON.stringify({script_kind:'single',tc_name:c.tc_name,source:state.definition.source,source_version:c.source_version,settings:state.definition.settings,folder_path:c.folder_path},null,2),'application/json');}
  else if(action.startsWith('delete-')) {
    const type=action.split('-')[1],tc=plan?.testcases.find(c=>c.id===state.caseId);const name=type==='project'?project.name:type==='plan'?plan.name:type==='task'?task.name:tc.tc_name;
    if(!await confirmDelete(`Delete ${type}: ${name}?`,type==='case'?'This deletes the Plan Test Case and its current results and logs from every Task in this Plan.':`This permanently deletes the ${type} and its contained items, including current test evidence.`))return;
    if(type==='project')await api('/api/delete_project','POST',{project_id:project.id,project:project.name,confirm:true});else if(type==='plan')await api('/api/delete_plan','POST',{plan_id:plan.id,confirm:true});else if(type==='task')await api(`/api/tasks/${task.id}`,'DELETE');else await api(`/api/testcases/${tc.id}`,'DELETE',{confirm:true,acknowledgement:true});
    state.dirty=false;await refresh(false);if(type==='project')location.hash='#/projects';else if(type==='plan')location.hash=path(project);else if(type==='task')location.hash=path(project,plan);else await draw();toast('Deleted '+type+'.');
  }
}
async function submit(form) {
 const {project,plan,task}=context();const values=Object.fromEntries(new FormData(form));
 if(form.id==='task-manager-form'){
   const id=form.dataset.taskId;const setup={start_date:values.start_date,end_date:values.end_date,notes:values.notes};
   if(Boolean(setup.start_date)!==Boolean(setup.end_date))throw Error('Supply both start and end dates, or leave both empty.');
   if(setup.start_date&&setup.end_date<setup.start_date)throw Error('End date must be on or after start date.');
   if(id)await api(`/api/tasks/${id}`,'PATCH',{name:values.name,setup});
   else await api('/api/tasks','POST',{name:values.name,plan_id:values.plan_id,setup});
   state.dirty=false;state.panel=null;await refresh();toast(id?'Task updated.':'Task created.');
 }else if(form.id==='name-form'){
   const name=values.name.trim();if(!name)throw Error('Enter a name.');const type=form.dataset.type;
   if(type==='new-project'){await api('/api/create_project','POST',{project:name});await refresh(false);state.dirty=false;state.panel=null;location.hash=path(state.projects.find(p=>p.name===name));}
   else if(type==='new-plan'){const result=await api('/api/create_plan','POST',{project:project.name,plan_name:name});await refresh(false);state.dirty=false;state.panel=null;location.hash=path(project,{id:result.plan_id});}
   else if(type==='new-task'){const result=await api('/api/tasks','POST',{plan_id:plan.id,name});await refresh(false);state.dirty=false;state.panel=null;location.hash=path(project,plan,{id:result.id});}
   else if(type==='new-folder'){await api(`/api/plans/${plan.id}/folders`,'POST',{name});state.dirty=false;state.panel=null;await refresh();}
   else{await api(type==='rename-project'?'/api/rename_project':type==='rename-plan'?`/api/plans/${plan.id}`:`/api/tasks/${task.id}`,type==='rename-project'?'POST':'PATCH',type==='rename-project'?{old_name:project.name,new_name:name}:{name});state.panel=null;state.dirty=false;await refresh();}toast('Saved.');
 }else if(form.classList.contains('folder-form')){
   await api(`/api/folders/${form.dataset.id}`,'PATCH',{name:values.name,parent_id:values.parent_id||null});state.dirty=false;await refresh();toast('Folder saved.');
 }else if(form.id==='case-form'){
   const result=await api(`/api/plans/${plan.id}/testcases/${state.caseId}/definition`,'PUT',{source:values.source,settings:currentSettings(),settings_revision:state.definition.settings_revision});state.definition=result;state.dirty=false;await refresh();toast('Plan Test Case saved. All Tasks use the updated definition.');
 }else if(form.id==='case-details'){
   await api(`/api/testcases/${state.caseId}`,'PATCH',{tc_name:values.name});if(values.folder_id!==undefined)await api(`/api/plans/${plan.id}/testcases/move`,'POST',{testcase_ids:[state.caseId],folder_id:values.folder_id||null});state.dirty=false;await refresh();toast('Test Case organization saved.');
 }else if(form.id==='scope-form'){
   await api(`/api/tasks/${task.id}/testcases/import`,'POST',{testcases:[...state.scope]});state.dirty=false;state.tab='execution';await refresh();toast('Task scope saved.');
 }else if(form.id==='repository-folder-form'){const selected=selectedRepositoryFolder(),id=form.dataset.id;const f=await api('/api/repository/folders'+(id?'/'+id:''),id?'PATCH':'POST',{name:values.name,parent_id:id?selected.parent_id:selected.id});state.repositoryFolder=f.id;state.panel=null;state.dirty=false;await draw();toast(id?'Folder updated.':'Repository folder created.');
 }else if(form.id==='repository-form'){
   const file=form.elements.file.files[0];if(!file||!file.name.toLowerCase().endsWith('.py'))throw Error('Choose a .py file.');await api('/api/repository/testcases','POST',{source:await file.text(),folder_id:values.folder_id||null});state.panel=null;state.dirty=false;await draw();toast('Standard Test Case imported with a new source timestamp.');
 }else if(form.id==='settings-form'){
   values.verify_ssl=form.elements.verify_ssl.checked;await api(`/api/tasks/${task.id}/settings`,'PUT',values);state.dirty=false;await refresh();toast('Task connection settings saved.');
 }else if(form.id==='task-details'){
   await api(`/api/tasks/${task.id}`,'PATCH',{setup:{...task.setup,...values}});state.dirty=false;await refresh();toast('Task information saved.');
 }else if(form.id==='annotation-form'){
   await api(`/api/tasks/${task.id}/testcases/${state.caseId}/status`,'PATCH',{status:values.status,reason:values.reason});await api('/api/task_tc/annotate','POST',{task_id:task.id,testcase_id:state.caseId,bug_id:values.bug_id});state.dirty=false;await refresh();toast('Manual result saved. Execution logs retained.');
 }else if(form.id==='input-form'){
   await api('/api/input','POST',{session_id:form.dataset.session,value:values.value});state.prompt=null;$('#input-slot').replaceChildren();toast('Response submitted.');
 }
}
function inputForm(session,text){return `<form id="input-form" class="input-request" data-session="${escape(session)}"><label for="run-input">${escape(text)}</label><div class="actions"><input id="run-input" name="value" autocomplete="off" required><button class="primary">Submit response</button></div><p class="help">Execution waits here until you respond or stop it.</p></form>`;}
function stream(session,taskId) { return new Promise((resolve,reject)=>{
 const source=new EventSource(`/api/stream/${session}`);let finished=false;
 source.onmessage=event=>{const msg=JSON.parse(event.data);if(msg.type==='end'){finished=true;source.close();resolve();return;}if(msg.type==='heartbeat')return;if(msg.type==='input_resolved'){state.prompt=null;if(context().task?.id===taskId&&$('#input-slot'))$('#input-slot').replaceChildren();}
   if(msg.text||msg.error)state.log+=(msg.text||msg.error)+'\n';if(msg.type==='case_done')state.log+='Test Case: '+msg.result+'\n';
   if(context().task?.id===taskId){const out=$('#log-output');if(out){out.textContent=state.log;out.scrollTop=out.scrollHeight;}if(msg.type==='input_required'){state.prompt={session,text:msg.text};if($('#input-slot'))$('#input-slot').innerHTML=inputForm(session,msg.text);}}
 };
 source.onerror=()=>{if(finished)return; source.close();reject(Error('Live connection interrupted. Use Resume monitoring to reconnect to the active Task.'));};
 }); }
async function runTask(id,ids,token,session=null){
 if(state.activeTask)throw Error('This window is already monitoring an execution.');state.activeTask=id;
 try{
   if(session){state.log='';await stream(session,id);}
   for(const tcId of ids){const current=await api(`/api/tasks/${id}/execution`);if(!current.execution_active||current.stop_requested)break;const summary=await api(`/api/tasks/${id}/summary`);const tc=summary.testcases.find(c=>c.id===tcId);if(!tc||tc.status==='Passed'||tc.status==='Failed')continue;
     const run=await api('/api/run','POST',{task_id:id,testcase_id:tcId,execution_token:token});state.log='';state.caseId=tcId;await refresh();await stream(run.session_id,id);
   }
   const current=await api(`/api/tasks/${id}/execution`);if(current.execution_active&&!current.session_id)await api(`/api/tasks/${id}/execution/finish`,'POST',{execution_token:token});
   toast('Task execution finished. Current results are available.');
 }finally{state.activeTask=null;await refresh();}
}
document.addEventListener('click',event=>{const element=event.target.closest('[data-action]');if(!element||element.disabled)return;doAction(element.dataset.action,element).catch(e=>toast(e.message,true));});
document.addEventListener('submit',event=>{const form=event.target;if(form.closest('dialog'))return;event.preventDefault();const buttons=$$('button[type=submit],button:not([type]):not([data-action])',form);buttons.forEach(b=>b.disabled=true);submit(form).catch(e=>toast(e.message,true)).finally(()=>buttons.forEach(b=>b.disabled=false));});
document.addEventListener('input',event=>{
 const el=event.target;
 if(el.id==='manager-search'){state.managerSearch=el.value;$('#task-manager-content').innerHTML=TaskManagement.content(state.managedTasks,el.value);return;}
 if(el.id==='manager-project'){$('#manager-plan').innerHTML=TaskManagement.planOptions(state.projects.find(p=>p.id===el.value));}
 if(el.closest('#task-manager-form')&&['start_date','end_date'].includes(el.name)){const f=el.form;f.elements.start_date.required=Boolean(f.elements.end_date.value);f.elements.end_date.required=Boolean(f.elements.start_date.value);f.elements.end_date.min=f.elements.start_date.value;}
 if(el.id==='tree-search'){drawTree();return;}if(el.id==='case-search'||el.id==='folder-filter'){const search=($('#case-search')?.value||'').toLowerCase(),folder=$('#folder-filter')?.value;$$('#case-list [data-search]').forEach(row=>row.hidden=!row.dataset.search.includes(search)||(folder&&row.dataset.folder!==folder));return;}
 if(el.id==='repository-search'){const folder=state.repositoryFolder;$$('#repository-table [data-search]').forEach(row=>row.hidden=!row.dataset.search.includes(el.value.toLowerCase())||(folder&&folder!=='all'&&row.dataset.folder!==folder));return;}
 if(el.closest('form')&&!el.closest('#input-form')){state.dirty=true;if($('#save-state'))$('#save-state').textContent='Unsaved changes';}
 if(el.dataset.scope){el.checked?state.scope.add(el.dataset.scope):state.scope.delete(el.dataset.scope);$('#scope-count').textContent=state.scope.size+' selected';state.dirty=true;}
});
document.addEventListener('change',event=>{const el=event.target;if(el.classList.contains('repository-batch-check')){state.repositorySelection??=new Set();const key=el.dataset.kind+':'+el.dataset.id;el.checked?state.repositorySelection.add(key):state.repositorySelection.delete(key);const del=$('[data-action=repository-batch-delete]');if(del)del.disabled=!state.repositorySelection.size;return;}if(el.id==='repository-folder-filter'){state.repositoryFolder=el.value;draw().catch(e=>toast(e.message,true));return;}if(el.classList.contains('repository-move')){api(`/api/repository/testcases/${el.dataset.id}/folder`,'PUT',{folder_id:el.value||null}).then(()=>draw()).catch(e=>toast(e.message,true));return;}if(el.id==='folder-filter')el.dispatchEvent(new Event('input',{bubbles:true}));if(el.dataset.run){const {task}=context();task.testcases.find(c=>c.id===el.dataset.run).selected=el.checked;api(`/api/task_testcases/${task.id}/${el.dataset.run}`,'PATCH',{selected:el.checked}).catch(e=>{el.checked=!el.checked;toast(e.message,true);});}});
document.addEventListener('click',event=>{const name=event.target.closest('.repository-folder-name strong');state.repositoryNameClick=name?.closest('.repository-folder-name').dataset.id||null;},true);
document.addEventListener('click',event=>{if(event.target.classList.contains('repository-rename')||event.target.classList.contains('repository-batch-check'))event.stopPropagation();},true);
document.addEventListener('keydown',async event=>{
 const input=event.target;if(!input.classList.contains('repository-rename'))return;
 if(event.key==='Escape'){event.preventDefault();state.repositoryRename=null;await draw();return;}
 if(event.key!=='Enter')return;event.preventDefault();input.disabled=true;
 try{await api(`/api/repository/folders/${input.dataset.id}`,'PATCH',{name:input.value});state.repositoryRename=null;await draw();toast('Folder renamed.');}
 catch(error){input.disabled=false;input.focus();toast(error.message,true);}
});

function resizeRepositoryPreview(handle, width){
 const value=Math.max(25,Math.min(70,width));
 state.repositoryPreviewWidth=value;
 handle.closest('.repository-layout').style.setProperty('--preview-width',value+'%');
 handle.setAttribute('aria-valuenow',Math.round(value));
}
document.addEventListener('pointerdown',event=>{
 const handle=event.target.closest('.repository-resizer');if(!handle||event.button!==0)return;
 event.preventDefault();handle.focus();handle.setPointerCapture(event.pointerId);
 const layout=handle.closest('.repository-layout'),bounds=layout.getBoundingClientRect();
 const move=e=>resizeRepositoryPreview(handle,(bounds.right-e.clientX)/bounds.width*100);
 const finish=()=>{handle.removeEventListener('pointermove',move);handle.removeEventListener('lostpointercapture',finish);document.body.classList.remove('resizing-repository');};
 handle.addEventListener('pointermove',move);handle.addEventListener('lostpointercapture',finish);
 document.body.classList.add('resizing-repository');
});
document.addEventListener('keydown',event=>{
 const handle=event.target.closest('.repository-resizer');if(!handle)return;
 const width=state.repositoryPreviewWidth||45;
 const next={ArrowLeft:width+2,ArrowRight:width-2,Home:25,End:70}[event.key];
 if(next===undefined)return;event.preventDefault();resizeRepositoryPreview(handle,next);
});

let repositoryDrag=null;
function clearRepositoryDrop(){ $$('[data-folder-node]').forEach(n=>n.removeAttribute('data-drop')); }
document.addEventListener('dragstart',event=>{
 if(state.route[0]!=='repository')return;
 const row=event.target.closest('[data-repository-id]'),node=event.target.closest('[data-folder-node][draggable]');
 if(!row&&!node)return;
 const kind=row?'case':'folder',id=row?.dataset.repositoryId||node.dataset.folderNode;
 repositoryDrag=state.repositoryBatch&&state.repositorySelection?.has(kind+':'+id)?{kind:'batch',...repositorySelectionData()}:{kind,id};
 event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',JSON.stringify(repositoryDrag));
});
document.addEventListener('dragenter',event=>{if(repositoryDrag&&event.target.closest('[data-folder-node]'))event.preventDefault();});
document.addEventListener('dragover',event=>{
 const node=event.target.closest('[data-folder-node]');if(!node||!repositoryDrag)return;
 event.preventDefault();event.dataTransfer.dropEffect='move';clearRepositoryDrop();
 const f=state.repositoryFolders.find(f=>f.id===node.dataset.folderNode),rect=node.getBoundingClientRect(),fraction=(event.clientY-rect.top)/rect.height;
 node.dataset.drop=repositoryDrag.kind==='case'||repositoryDrag.kind==='batch'||f.is_root?'inside':fraction<.25?'before':fraction>.75?'after':'inside';
});
document.addEventListener('drop',async event=>{
 const node=event.target.closest('[data-folder-node]');if(!node||!repositoryDrag)return;
 event.preventDefault();const drag=repositoryDrag,mode=node.dataset.drop||'inside',target=state.repositoryFolders.find(f=>f.id===node.dataset.folderNode);repositoryDrag=null;clearRepositoryDrop();
 try{
  if(drag.kind==='batch'){await api('/api/repository/batch','POST',{...drag,action:'move',folder_id:target.id});state.repositorySelection.clear();}
  else if(drag.kind==='case')await api(`/api/repository/testcases/${drag.id}/folder`,'PUT',{folder_id:target.id});
  else if(drag.id!==target.id)await api(`/api/repository/folders/${drag.id}`,'PATCH',mode==='inside'?{parent_id:target.id}:{parent_id:target.parent_id,relative_to:target.id,insertion:mode});
  await draw();toast(drag.kind==='case'?'Test Case moved.':'Folder moved.');
 }catch(error){toast(error.message,true);}
});
document.addEventListener('dragend',()=>{repositoryDrag=null;clearRepositoryDrop();});
window.addEventListener('hashchange',()=>navigate().catch(e=>toast(e.message,true)));
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});
$('#nav-toggle').innerHTML=icon('menu');$('.nav-heading button').innerHTML=icon('plus');$('#theme-toggle').innerHTML=icon('sun');
function theme(value){document.documentElement.dataset.theme=value;localStorage.setItem('bmc-theme',value);$('#theme-toggle').setAttribute('aria-label',`Switch to ${value==='dark'?'light':'dark'} theme`);}
theme(localStorage.getItem('bmc-theme')||'light');$('#theme-toggle').onclick=()=>theme(document.documentElement.dataset.theme==='dark'?'light':'dark');$('#nav-toggle').onclick=()=>{const open=document.body.classList.toggle('nav-open');$('#nav-toggle').setAttribute('aria-expanded',open);};
refresh(false).then(navigate).catch(e=>{$('#workspace').setAttribute('aria-busy','false');$('#workspace').innerHTML=empty('Unable to load BMC Agent',e.message,button('Retry','retry','primary'));toast(e.message,true);});
document.addEventListener('click',event=>{if(event.target.closest('[data-action=retry]'))refresh(false).then(navigate).catch(e=>toast(e.message,true));});
})();
