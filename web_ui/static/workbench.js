'use strict';
(() => {
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {sort:'M4 4v16m-3-3 3 3 3-3M10 5h4M10 11h7M10 17h10',folderPlus:'M3 7h7l2 2h9v11H3z M3 7V4h7l2 3 M12 12v6 M9 15h6',eye:'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',plus:'M12 5v14M5 12h14',folder:'M3 7h7l2 2h9v11H3z M3 7V4h7l2 3',plan:'M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7',task:'M8 4h12v17H4V4h4 M8 2h8v4H8z M8 11l2 2 5-5',chevron:'M9 5l7 7-7 7',trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',menu:'M4 6h16M4 12h16M4 18h16',sun:'M12 3v2M12 19v2M3 12h2M19 12h2M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2 M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0'};
const icon = name => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name] || icons.plan}"/></svg>`;
const state = {projects:[], repository:[], route:[], tab:'cases', panel:null, caseId:null, definition:null, dirty:false, scope:new Set(), log:'', activeTask:null, generation:0};
let confirmationPending=false;
let notificationTimer, previousHash = location.hash || '#/dashboard';
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
  if (!response.ok) { const error=new Error(result.error || `Request failed (${response.status}).`); error.status=response.status;error.details=result; throw error; }
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
function nameForm(type, current='') { if(type==='new-project')return projectCreateForm(); return `<form id="name-form" class="inline-form" data-type="${type}"><h2>${type.startsWith('rename')?'Rename':'Create'} ${escape(type.split('-').at(-1))}</h2><label class="field"><span>Name</span><input name="name" required maxlength="100" value="${escape(current)}" autocomplete="off"></label><div class="form-actions"><button class="primary">${type.startsWith('rename')?'Save name':'Create'}</button>${button('Cancel','close-panel')}</div></form>`; }
function projectCreateForm(){
 const mode=state.projectCreateMode;
 if(!mode)return `<section class="inline-form"><h2>New Project</h2><p>Choose how to create your Project.</p><div class="project-create-options"><button type="button" data-action="project-create-mode" data-mode="auto"><strong>Automatic creation</strong><span>Import a requirements workbook to create the Project and SKU specifications.</span></button><button type="button" data-action="project-create-mode" data-mode="manual"><strong>Manual creation</strong><span>Enter a Project name, then edit its information in the workspace.</span></button></div><div class="form-actions">${button('Cancel','close-panel')}</div></section>`;
 const automatic=mode==='auto';
 return `<form id="project-create-form" class="inline-form" data-mode="${mode}"><h2>${automatic?'Automatic creation':'Manual creation'}</h2>${automatic?'<label class="field"><span>Requirements document</span><input id="project-document" type="file" accept=".xlsx" required></label><p class="help">Import a requirements workbook to create the Project and SKU specifications.</p><div id="project-import-preview" aria-live="polite"></div>':'<p>Enter a Project name, then edit its information in the workspace.</p>'}${automatic?'':`<label class="field"><span>Name</span><input name="name" required maxlength="100" autocomplete="off"></label>`}<div class="form-actions"><button type="submit" class="primary" ${automatic?'disabled':''}>${automatic?'Create Projects':'Create and edit'}</button>${button('Back','project-create-back')}${button('Cancel','close-panel')}</div></form>`;
}
function breadcrumbs() { return ''; }
function tabs(items, selected) { return `<div class="tabs" role="tablist" aria-label="Workspace sections">${items.map(([id,label])=>button(label,'tab','',`role="tab" aria-selected="${id===selected}" data-tab="${id}"`)).join('')}</div>`; }
function projectEntryRoute() {
  const saved=localStorage.getItem('bmc-last-project');
  const project=state.projects.find(p=>p.id===saved);
  if(!project)return '#/dashboard';
  const base=path(project),savedRoute=localStorage.getItem('bmc-last-project-route');
  if([base,...['info','plans','reports','bugs'].map(section=>base+'/'+section)].includes(savedRoute))return savedRoute;
  if(project.plans.some(plan=>path(project,plan)===savedRoute))return savedRoute;
  // A removed Plan should return to the surviving Project's Plan list.
  return savedRoute?.startsWith(base+'/plan/')?base+'/plans':base;
}
function drawTree() {
  const {project,plan,task}=context();
  if(project){
    localStorage.setItem('bmc-last-project',project.id);
    if(!task)localStorage.setItem('bmc-last-project-route',plan?path(project,plan):path(project)+'/'+(state.route[2]||'info'));
  }
  const selected=project||state.projects.find(p=>p.id===localStorage.getItem('bmc-last-project'))||state.projects[0];
  const section=task?'execution':plan?'plans':state.route[2]||'info';
  const navigationIcons={"Dashboard":"M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z","Schedule":"M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4 M8 14h3 M14 17h3","Task":"M8 4h12v17H4V4h4 M8 2h8v4H8z M8 12l2 2 5-5","Project:":"M3 7h7l2 2h9v11H3z M3 7V4h7l2 3 M7 13h4 M7 16h8","Plan":"M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h5","Execution":"M6 3v18l14-9z","Report":"M4 3h16v18H4z M8 17v-4 M12 17V9 M16 17v-7","bug":"M8 8h8v8a4 4 0 0 1-8 0z M9 8V5h6v3 M4 10h4 M16 10h4 M3 15h5 M16 15h5 M5 21l4-3 M19 21l-4-3","Case Repository":"M3 4h18v4H3z M5 8v13h14V8 M9 12h6 M9 16h6"};
  const navLink=(href,label,current=false)=>`<a href="${href}" aria-label="${escape(label)}" title="${escape(label)}" ${current?'aria-current="page"':''}><span class="sidebar-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${navigationIcons[label]}"/></svg></span><span class="sidebar-label">${label}</span></a>`;
  const projectLinks=selected?`<div class="sidebar-project-heading">${navLink(path(selected)+'/info','Project:',Boolean(project&&section==='info'))}<div class="project-picker"><input id="project-search" type="text" role="combobox" aria-expanded="false" aria-controls="project-options" aria-autocomplete="list" value="${escape(selected.name)}" data-selected-name="${escape(selected.name)}" placeholder="Search Projects" aria-label="Search Projects" autocomplete="off"><div class="project-picker-menu" hidden><div id="project-options" class="project-options" role="listbox">${state.projects.map(p=>button(escape(p.name),'choose-project','',`data-project-id="${escape(p.id)}" data-project-name="${escape(p.name.toLowerCase())}" data-no-translate role="option" aria-selected="${p.id===selected.id}"`)).join('')}</div><p id="project-search-empty" class="help" hidden>No matching Projects</p></div></div></div>${[['plans','Plan'],['execution','Execution'],['reports','Report'],['bugs','bug']].map(([id,label])=>navLink(path(selected)+'/'+id,label,Boolean(project&&section===id))).join('')}`:'<p class="help">Create a Project to get started.</p>';
  $('#navigation-content').innerHTML=`<nav class="sidebar-navigation" aria-label="Workspace navigation">${navLink('#/dashboard','Dashboard',state.route[0]==='dashboard')}${navLink('#/tasks','Schedule',state.route[0]==='tasks'&&['schedule','my-schedule'].includes(state.managerTab))}${navLink('#/tasks/list','Task',state.route[0]==='tasks'&&['list','my-task','info'].includes(state.managerTab))}${projectLinks}${navLink('#/repository','Case Repository',state.route[0]==='repository')}</nav>`;
}
function openProjectPicker() {
  const input=$('#project-search');if(!input)return;
  input.setAttribute('aria-expanded','true');$('.project-picker-menu').hidden=false;
}
function closeProjectPicker() {
  const input=$('#project-search');if(!input)return;
  input.value=input.dataset.selectedName;input.setAttribute('aria-expanded','false');
  $('.project-picker-menu').hidden=true;
  $$('[data-project-name]').forEach(option=>option.hidden=false);$('#project-search-empty').hidden=true;
}
// Pointer position controls the rail; navigation clicks retain its current state.
let sidebarKeyboard=false,sidebarPointerInside=false;
function collapseSidebar(){
 $('#navigator').classList.remove('sidebar-open');closeProjectPicker();
 if($('#navigator').contains(document.activeElement))$('#workspace').focus({preventScroll:true});
}
document.addEventListener('keydown',event=>{if(event.key==='Tab')sidebarKeyboard=true;},true);
document.addEventListener('pointerdown',()=>{sidebarKeyboard=false;},true);
$('#navigator').addEventListener('pointerenter',()=>{sidebarPointerInside=true;$('#navigator').classList.add('sidebar-open');});
$('#navigator').addEventListener('pointerleave',()=>{sidebarPointerInside=false;collapseSidebar();});
$('#navigator').addEventListener('focusin',()=>{if(sidebarKeyboard)$('#navigator').classList.add('sidebar-open');});
$('#navigator').addEventListener('focusout',event=>{if(!sidebarPointerInside&&(!event.relatedTarget||!$('#navigator').contains(event.relatedTarget)))$('#navigator').classList.remove('sidebar-open');});
$('#navigator').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();collapseSidebar();}});
document.addEventListener('focusin',event=>{if(event.target.id==='project-search'){openProjectPicker();event.target.select();}});
document.addEventListener('click',event=>{if(event.target.id==='project-search')openProjectPicker();else if(!event.target.closest('.project-picker'))closeProjectPicker();});
document.addEventListener('focusout',event=>{if(event.target.closest('.project-picker')&&!event.relatedTarget?.closest('.project-picker'))closeProjectPicker();});
document.addEventListener('keydown',event=>{
  const picker=event.target.closest('.project-picker');if(!picker)return;
  const options=$$('[data-project-name]').filter(option=>!option.hidden);
  if(event.key==='Escape'){event.preventDefault();$('#project-search').focus();closeProjectPicker();}
  else if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();openProjectPicker();const current=options.indexOf(document.activeElement);options[(current+(event.key==='ArrowDown'?1:-1)+options.length)%options.length]?.focus();}
  else if(event.key==='Enter'&&event.target.id==='project-search'){event.preventDefault();options[0]?.click();}
});
function sizeGlobalNavigation() {
  const nav=$('.global-nav'),link=nav?.querySelector('a');if(!link)return;
  const style=getComputedStyle(link),measure=document.createElement('canvas').getContext('2d');
  measure.font=`600 ${style.fontSize} ${style.fontFamily}`;
  const labels=['Projects','Tasks','Test Case Repository','專案','任務','測項資料庫'];
  const width=Math.ceil(Math.max(...labels.map(label=>measure.measureText(label).width))+parseFloat(style.paddingLeft)+parseFloat(style.paddingRight))+2;
  nav.style.setProperty('--global-entry-width',width+'px');
}
function sizeProjectNavigation() {
  const nav=$('.project-sections'),item=nav?.querySelector('a');
  if(!item)return;
  const style=getComputedStyle(item),measure=document.createElement('canvas').getContext('2d');
  // Reserve the selected font weight for every entry, in both languages.
  measure.font=`600 ${style.fontSize} ${style.fontFamily}`;
  const labels=['Project information','Test Plan','Test Report','Bug List','專案資訊'];
  const width=Math.ceil(Math.max(...labels.map(label=>measure.measureText(label).width))+parseFloat(style.paddingLeft)+parseFloat(style.paddingRight))+2;
  nav.style.setProperty('--project-entry-width',width+'px');
}
async function projectSectionPage(project) {
  if(!state.route[2]||state.route[2]==='info'){
    if(state.projectInformation?.project_id!==project.id)state.projectInformation=await api(`/api/projects/${project.id}/information`);
    if(state.editCreatedProject===project.id){state.editCreatedProject=null;state.infoEditing=true;state.infoOriginal=structuredClone(state.projectInformation);}
    return ProjectInformationUI.render(state.projectInformation,state.infoEditing,state.infoCollapsed,state.infoSection||'spec');
  }
  const title={info:'Project information',reports:'Test Report',bugs:'Bug List'}[state.route[2]||'info'];
  return breadcrumbs()+heading(title,project.name)+empty('To be designed','This section will be designed in a later phase.');
}
async function refresh(render=true) { const result=await api('/api/projects'); state.projects=result.projects; drawTree(); if(render) await draw(); }
function matrixStatus(value) {
  if(value===null)return '<span class="help" title="Not in Task scope">—</span>';
  const style={PASS:'passed',FAIL:'failed',Block:'blocked',NR:'tbd',Running:'running'}[value];
  return `<span class="status ${style}">${value}</span>`;
}
function sizePlanColumns() {
  const table=$('.plan-overview'),cell=table?.querySelector('thead th:nth-child(2)');
  if(!cell)return;
  const style=getComputedStyle(cell),canvas=document.createElement('canvas'),measure=canvas.getContext('2d');
  measure.font=`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
  const labels=['Total Cases','Completion','PASS','FAIL','Block','Not Run','Task','測項總數','完成度'];
  const width=Math.ceil(Math.max(...labels.map(label=>measure.measureText(label).width))+parseFloat(style.paddingLeft)+parseFloat(style.paddingRight))+2;
  table.style.setProperty('--summary-column-width',width+'px');
  const create=$('.plan-list-footer button');
  if(create){
    const buttonStyle=getComputedStyle(create);
    measure.font=`${buttonStyle.fontWeight} ${buttonStyle.fontSize} ${buttonStyle.fontFamily}`;
    const buttonWidth=Math.ceil(Math.max(...['Create','新增'].map(label=>measure.measureText(label).width))+parseFloat(buttonStyle.paddingLeft)+parseFloat(buttonStyle.paddingRight)+parseFloat(buttonStyle.borderLeftWidth)+parseFloat(buttonStyle.borderRightWidth))+2;
    create.style.width=buttonWidth+'px';
  }

}
function planList(project) {
  const rows=project.plans.map(plan=>{
    const summary=PlanMatrix.summarize(plan),expanded=state.expandedPlans?.has(plan.id),matrixId='matrix-'+plan.id;
    const matrix=`<div class="table-wrap plan-matrix" id="${escape(matrixId)}"><table aria-label="${escape(plan.name)} Matrix"><thead><tr><th scope="col">Case</th>${plan.tasks.map(task=>`<th scope="col"><a href="${path(project,plan,task)}">${escape(task.name)}</a></th>`).join('')}<th scope="col">Final</th></tr></thead><tbody>${summary.rows.map(row=>`<tr><th scope="row">${escape(row.name)}</th>${row.cells.map(cell=>`<td>${matrixStatus(cell)}</td>`).join('')}<td>${matrixStatus(row.final)}</td></tr>`).join('')||`<tr><td colspan="${plan.tasks.length+2}">No Test Cases</td></tr>`}</tbody></table></div>`;
    return `<tr><td><a href="${path(project,plan)}">${escape(plan.name)}</a></td><td>${summary.total}</td><td>${summary.completed}/${summary.total}</td><td>${summary.counts.PASS}</td><td>${summary.counts.FAIL}</td><td>${summary.counts.Block}</td><td>${summary.counts.NR}</td><td>${button(String(plan.tasks.length),'toggle-plan-matrix','small-button matrix-toggle',`data-id="${escape(plan.id)}" aria-label="${escape(plan.name)} Task Matrix" aria-expanded="${Boolean(expanded)}" aria-controls="${escape(matrixId)}"`)}</td></tr><tr ${expanded?'':'hidden'} class="matrix-row"><td colspan="8">${matrix}</td></tr>`;
  }).join('');
  return `<div class="table-wrap plan-overview"><table><thead><tr><th>Plan</th><th>Total Cases</th><th>Completion</th><th>PASS</th><th>FAIL</th><th>Block</th><th>Not Run</th><th data-no-translate>Task</th></tr></thead><tbody>${rows}${!rows?'<tr><td colspan="8">No Test Plans</td></tr>':''}</tbody></table></div><div class="plan-list-footer">${button('Create','new-plan','primary')}</div>`;
}
function projectImportResultPanel(){
 const projects=state.projectImportResult;
 return projects?.length?`<section class="notice info" aria-label="Projects created"><div class="toolbar"><h2>Projects created</h2>${button('Close','dismiss-import-result')}</div><ul>${projects.map(p=>`<li><a href="${path(p)}/info" data-no-translate>${escape(p.name)}</a></li>`).join('')}</ul></section>`:'';
}
function projectPage(project) {
  if(project)return planList(project);
  const controls=button('New Project','new-project','primary');
  return `<div class="page-heading"><h1>Dashboard</h1><div class="actions">${controls}</div></div>`+projectImportResultPanel()+
    (state.panel?.includes('project')||state.panel?.includes('plan')?nameForm(state.panel):'')+
    (state.projects.length?`<div class="table-wrap"><table><thead><tr><th>Project</th><th>Plans</th><th>Tasks</th></tr></thead><tbody>${state.projects.map(item=>`<tr><td><a href="${path(item)}">${escape(item.name)}</a></td><td>${item.plans.length}</td><td>${item.plans.reduce((n,p)=>n+p.tasks.length,0)+(item.planning_task_count||0)}</td></tr>`).join('')}</tbody></table></div>`:empty('Create your first Project','Start with a Project, then create a Test Plan and load standard Test Cases.',button('New Project','new-project','primary')));
}
function tasksTable(project, plan, report=false) { return plan.tasks.length?`<div class="table-wrap"><table><thead><tr><th>Task</th><th>Scope</th><th>Current results</th><th>${report?'Report':'Action'}</th></tr></thead><tbody>${plan.tasks.map(task=>`<tr><td><a href="${path(project,plan,task)}">${escape(task.name)}</a>${task.execution_active?'<p class="help">Execution active</p>':''}</td><td>${task.testcases.length} Test Cases</td><td>${task.counts.Passed} passed · ${task.counts.Failed} failed${task.testcases.some(c=>c.needs_retest)?'<p class="help">Plan changed — rerun needed</p>':''}</td><td>${report?button('Generate report','report','small-button',`data-id="${escape(task.id)}" ${task.execution_active?'disabled':''}`):`<a href="${path(project,plan,task)}">Open Task</a>`}</td></tr>`).join('')}</tbody></table></div>`:empty('No Tasks yet','When the Plan is ready, create a Task and choose its Test Cases.',report?'':button('New Task','new-task','primary',plan.locked?'disabled':'')); }
function planCaseTable(plan) {
  const importing=Boolean(state.importSource);
  const query=(state.planSearch||'').trim().toLowerCase(),collapsed=state.planCollapsed||new Set();
  const action=(label,type,id,shape,disabled=false)=>button(icon(shape),type,'small-button icon-button'+(shape==='trash'?' danger':''),`data-id="${escape(id||'')}" title="${label}" aria-label="${label}" ${disabled?'disabled':''}`);
  const cases=(folder,depth,match)=>plan.testcases.filter(c=>(c.folder_id||null)===folder&&(match||!query||c.tc_name.toLowerCase().includes(query))).map(c=>`<tr data-plan-case="${escape(c.id)}" draggable="${!plan.locked}" style="--depth:${depth}"><td><strong>${automation(c.automation)}${escape(c.tc_name)}</strong><p class="help case-source-version" data-no-translate>${escape(version(c.source_version))}</p></td>${importing?'':`<td>${c.parameter_count>0?button('Parameters','plan-case-parameters','small-button',`data-id="${escape(c.id)}"`):''}</td>`}<td><div class="actions">${action('View','plan-case-source',c.id,'eye',c.script_kind!=='single')}${action('Remove','plan-remove-case',c.id,'trash',plan.locked)}</div></td></tr>`).join('');
  const children=(parent,depth,ancestorMatch=false)=>plan.folders.filter(f=>(f.parent_id||null)===parent).sort((a,b)=>a.position-b.position).map(f=>{
    const match=ancestorMatch||Boolean(query&&f.name.toLowerCase().includes(query)),descendants=children(f.id,depth+1,match)+cases(f.id,depth+1,match);
    if(query&&!match&&!descendants)return '';
    return `<tr class="repository-folder-row" data-plan-folder="${escape(f.id)}" draggable="${!plan.locked}" style="--depth:${depth}"><td><div class="repository-folder-line">${button(collapsed.has(f.id)&&!query?'&#9656;':'&#9662;','toggle-plan-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!collapsed.has(f.id)||Boolean(query)}"`)}<button class="repository-folder-name" data-action="select-plan-folder" data-id="${escape(f.id)}" aria-pressed="${state.planFolder===f.id}">${icon('folder')}<strong>${escape(f.name)}</strong></button>${state.planRename===f.id?`<input class="plan-folder-rename repository-rename" data-id="${escape(f.id)}" aria-label="Folder name" maxlength="100" value="${escape(f.name)}">`:''}</div></td>${importing?'':'<td></td>'}<td><div class="actions">${action('New folder','new-plan-folder',f.id,'folderPlus',plan.locked)}${action('Resorting','resort-plan-folder',f.id,'sort',plan.locked)}${action('Remove folder','delete-folder',f.id,'trash',plan.locked)}</div></td></tr>${collapsed.has(f.id)&&!query?'':descendants}`;
  }).join('');
  const rows=children(null,1)+cases(null,1,false);
  return `<div class="table-wrap repository-scroll"><table id="repository-table" class="repository-hierarchy"><thead><tr><th>Directory / Test Case</th>${importing?'':'<th>Parameters</th>'}<th>Actions</th></tr></thead><tbody><tr class="repository-folder-row" data-plan-folder=""><td><div class="repository-folder-line"><span class="folder-collapse-spacer" aria-hidden="true"></span><span class="repository-folder-name">${icon('folder')}<strong>BMC</strong><span class="repository-folder-count">(${plan.testcases.length})</span></span></div></td>${importing?'':'<td></td>'}<td><div class="actions">${action('New folder','new-plan-folder','','folderPlus',plan.locked)}${action('Resorting','resort-plan-folder','','sort',plan.locked)}</div></td></tr>${rows||`<tr><td colspan="${importing?2:3}">No Test Cases</td></tr>`}</tbody></table></div>`;
}
function importSourceTable(){
  const source=state.importSource,collapsed=state.importCollapsed||new Set();
  const query=(state.importSearch||'').toLowerCase().trim();
  const cases=(parent,depth,match)=>source.cases.filter(c=>(c.folder_id||null)===parent&&(match||!query||c.name.toLowerCase().includes(query))).map(c=>`<tr data-import-kind="case" data-import-id="${escape(c.id)}" draggable="true" style="--depth:${depth}"><td><strong>${automation(c.automation)}${escape(c.name)}</strong><p class="help case-source-version" data-no-translate>${escape(version(c.source_version))}</p></td></tr>`).join('');
  const folders=(parent,depth,match=false)=>source.folders.filter(f=>(f.parent_id||null)===parent).sort((a,b)=>a.position-b.position).map(f=>{
    const matches=match||Boolean(query&&f.name.toLowerCase().includes(query)),contents=folders(f.id,depth+1,matches)+cases(f.id,depth+1,matches);
    if(query&&!matches&&!contents)return '';
    return `<tr class="repository-folder-row" data-import-kind="folder" data-import-id="${escape(f.id)}" draggable="${!f.is_root}" style="--depth:${depth}"><td><div class="repository-folder-line">${button(collapsed.has(f.id)&&!query?'&#9656;':'&#9662;','toggle-import-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!collapsed.has(f.id)||Boolean(query)}"`)}<span class="repository-folder-name">${icon('folder')}<strong>${escape(f.name)}</strong></span></div></td></tr>${collapsed.has(f.id)&&!query?'':contents}`;
  }).join('');
  return `<div class="table-wrap repository-scroll"><table class="repository-hierarchy import-source-table"><thead><tr><th>Directory / Test Case</th></tr></thead><tbody>${source.type==='plan'?'<tr class="repository-folder-row"><td><div class="repository-folder-line"><span class="folder-collapse-spacer" aria-hidden="true"></span><span class="repository-folder-name">'+icon('folder')+'<strong>BMC</strong></span></div></td></tr>':''}${folders(null,source.type==='plan'?1:0)+cases(null,1,false)||'<tr><td colspan="1">No Test Cases</td></tr>'}</tbody></table></div>`;
}
function importSourcePane(){
 const source=state.importSource;
 return `<section class="import-source-pane" aria-label="Import source"><header class="import-pane-heading"><h2 data-no-translate>${escape(source.label)}</h2>${button('Close','close-import-source','preview-close')}</header><div class="import-pane-controls"><label><span class="sr-only">Find source Test Case</span><input id="import-source-search" type="search" placeholder="Find source Test Case" value="${escape(state.importSearch||'')}"></label></div><div id="import-source-list">${importSourceTable()}</div></section>`;
}
async function planPage(project, plan) {
  if(!plan.testcases.some(c=>c.id===state.caseId))state.caseId=null;
  const header=heading('Test Plan: '+plan.name,'',button('Rename','rename-plan','',plan.locked?'disabled':'')+button('Delete','delete-plan','danger',plan.locked?'disabled':''));
  let contents;
  if(state.panel==='add-repository'){
    state.repository=await api('/api/repository/testcases');state.repositoryFolders=await api('/api/repository/folders');
    contents=`<div class="toolbar"><h2>Add from Test Case Repository</h2>${button('Back to Plan','close-panel')}</div>${repositoryWorkspace(true,plan)}`;
  }else{
    contents=`<div class="repository-page-controls actions"><label><span class="sr-only">Find Test Case</span><input id="plan-search" type="search" placeholder="Find Test Case" value="${escape(state.planSearch||'')}"></label>${button('Import Test Case','choose-import-source','',plan.locked?'disabled':'')}</div><div class="repository-layout ${state.caseId?'has-preview':''}" style="--preview-width:${state.repositoryPreviewWidth||45}%"><div class="repository-list" id="plan-case-list">${planCaseTable(plan)}</div>${state.caseId?`<div class="repository-resizer" role="separator" tabindex="0" aria-label="Resize details panel" aria-orientation="vertical" aria-controls="case-editor" aria-valuemin="25" aria-valuemax="70" aria-valuenow="${state.repositoryPreviewWidth||45}"></div><section class="plan-case-details" aria-label="Test Case details"><div class="toolbar repository-preview-header"><h2>${escape(plan.testcases.find(c=>c.id===state.caseId)?.tc_name||'')}</h2>${button('Close','close-plan-case','preview-close')}</div><div class="repository-preview-content" id="case-editor"></div></section>`:''}</div>`;
  }
  if(state.importSource){
    const ratio=state.importSplit??50;
    return `<div class="plan-import-layout" style="--import-left:${ratio}fr;--import-right:${100-ratio}fr"><section class="import-target-pane"><header class="import-pane-heading"><h1 data-no-translate>Test Plan: ${escape(plan.name)}</h1></header><div class="import-pane-controls"><label><span class="sr-only">Find Test Case</span><input id="plan-search" type="search" placeholder="Find Test Case" value="${escape(state.planSearch||'')}"></label>${button('Import Test Case','choose-import-source','',plan.locked?'disabled':'')}</div><div class="repository-list" id="plan-case-list">${planCaseTable(plan)}</div></section><div class="import-resizer" role="separator" tabindex="0" aria-label="Resize import workspaces" aria-orientation="vertical" aria-valuemin="25" aria-valuemax="75" aria-valuenow="${ratio}"></div>${importSourcePane()}</div>`;
  }

  return header+(plan.locked?'<div class="notice info">A Task is running. Plan structure and Task scope are locked. Only the running Test Case’s Python file and parameters are locked.</div>':'')+(state.panel==='rename-plan'?nameForm('rename-plan',plan.name):'')+contents;
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
  const onlyParameters=state.planCaseView!=='source';
  if(!onlyParameters){target.innerHTML=`<h3>Python source</h3><pre class="log code">${escape(def.source)}</pre>`;return;}
  target.innerHTML=`${def.editing_locked?'<div class="notice">This Test Case is running. Editing becomes available when it finishes.</div>':''}<h3>Editable parameters</h3><form id="case-form"><div class="fields">${parameterFields(def.metadata,def.settings,def.editing_locked)}</div>${!Object.keys(def.metadata.parameters||{}).length?'<p class="help">No editable parameters declared.</p>':''}<div class="form-actions"><button class="primary" ${def.editing_locked?'disabled':''}>Save Plan</button><span class="help" id="save-state">Saved · applies to all Tasks</span></div></form>`;
}
async function taskPage(project,plan,task) {
  if(!task.testcases.some(c=>c.id===state.caseId)) state.caseId=task.testcases[0]?.id||null;
  const scope=state.tab==='scope'; const needs=task.testcases.filter(c=>c.needs_retest).length;
  const toolbar=button('Generate report','report','',`data-id="${escape(task.id)}" ${task.execution_active?'disabled':''}`)+button('Delete','delete-task','danger',task.execution_active?'disabled':'');
  let content;
  if(state.tab==='settings') content=await settingsPage(task);
  else if(scope) {
    content=`<p>Choose the Plan Test Cases included in this Task. Edit all test parameters in the <a href="${path(project,plan)}">Plan</a>.</p><div class="toolbar"><div class="actions">${button('Select all','scope-all','',plan.locked?'disabled':'')}${button('Clear selection','scope-none','',plan.locked?'disabled':'')}</div><span class="help" id="scope-count">${state.scope.size} selected</span></div><form id="scope-form"><div class="table-wrap"><table><thead><tr><th>Include</th><th>Test Case</th><th>Folder</th><th>Source version</th></tr></thead><tbody>${plan.testcases.map(c=>`<tr><td class="check"><input type="checkbox" data-scope="${escape(c.id)}" aria-label="Include ${escape(c.tc_name)}" ${state.scope.has(c.id)?'checked':''} ${plan.locked||c.script_kind!=='single'?'disabled':''}></td><td>${automation(c.automation)}${escape(c.tc_name)}${c.script_kind!=='single'?'<p class="help">Retired — single .py required</p>':''}</td><td>${escape(c.folder_path||'Unfiled')}</td><td>${escape(version(c.source_version))}</td></tr>`).join('')}</tbody></table></div><div class="form-actions"><button class="primary" ${plan.locked?'disabled':''}>Save Task scope</button><span class="help">Removing a case also removes its current Task result and logs.</span></div></form>`;
  } else if(state.tab==='details') content=`<form id="task-details" class="settings-form"><h2>Task information</h2><p class="help">These fields describe the assignment; Test Case settings belong to the Plan.</p><div class="fields">${['tester','firmware','notes'].map(key=>`<label class="field ${key==='notes'?'full':''}"><span>${key[0].toUpperCase()+key.slice(1)}</span><${key==='notes'?'textarea':'input'} name="${key}" ${key==='notes'?'rows="4"':''} ${task.execution_active?'disabled':''} ${key!=='notes'?`value="${escape(task.setup[key]||'')}"`:''}>${key==='notes'?escape(task.setup[key]||'')+'</textarea>':''}</label>`).join('')}</div><div class="form-actions"><button class="primary" ${task.execution_active?'disabled':''}>Save Task information</button></div></form>`;
  else content=task.testcases.length?`<div class="execution-summary"><span><strong>${task.testcases.length}</strong> in scope</span><span><strong>${task.counts.Passed}</strong> passed</span><span><strong>${task.counts.Failed}</strong> failed</span><span><strong>${needs}</strong> need rerun</span></div><div class="toolbar"><p class="help">Run checked cases using the latest saved Plan settings.</p><div class="actions">${task.execution_active?button('Stop execution','stop','danger')+(!state.activeTask?button('Resume monitoring','resume','primary'):''):button('Run selected cases','run','primary')}</div></div><div class="split"><div class="case-browser"><div class="case-list">${task.testcases.map(c=>`<div class="task-case"><label class="checkbox-field" style="padding:10px 18px 0"><input type="checkbox" data-run="${escape(c.id)}" aria-label="Run ${escape(c.tc_name)}" ${c.selected?'checked':''} ${task.execution_active||c.script_kind!=='single'?'disabled':''}><span class="help">Include in execution</span></label><button class="case-row" data-action="select-result" data-id="${escape(c.id)}" aria-pressed="${state.caseId===c.id}"><strong>${automation(c.automation)}${escape(c.tc_name)}</strong>${status(c.status)} ${c.needs_retest?'<span class="status stale">Rerun needed</span>':''}${c.script_kind!=='single'?'<p class="help">Retired step-based case</p>':''}</button></div>`).join('')}</div></div><div class="case-editor" id="evidence">${evidence(task)}</div></div>`:empty('Set this Task’s scope','Select Test Cases from the Plan before starting an execution.',button('Choose Test Cases','scope','primary',plan.locked?'disabled':''));
  if(state.tab==='details')content+=TaskManagement.historyList((await api('/api/tasks/'+encodeURIComponent(task.id)+'/history')).history);
  return breadcrumbs()+heading(task.name,'Task · '+plan.name,toolbar)+(state.panel==='rename-task'?nameForm(state.panel,task.name):'')+(needs?`<div class="notice">Plan definitions or Task connection settings changed for ${needs} Test Case(s). Existing results and logs remain available; rerun those cases before using the report.</div>`:'')+(task.execution_active?'<div class="notice info">Execution is active. Scope is locked until execution finishes or stops.</div>':'')+tabs([['settings','Connection settings'],['scope','Task scope'],['details','Task information'],['execution','Execution & results']],state.tab)+content;
}
function evidence(task) {
  const tc=task.testcases.find(c=>c.id===state.caseId); if(!tc)return '';
  return `<h2>${automation(tc.automation)}${escape(tc.tc_name)}</h2><div class="metadata"><span>Latest result ${status(tc.status)}</span><span>Executed <strong>${escape(date(tc.executed_at))}</strong></span></div>${tc.needs_retest?'<div class="notice">Retained evidence predates the current Plan definition or Task connection settings. Rerun needed.</div>':''}${tc.manual_override?`<p class="help">Manual result: ${escape(tc.manual_override.status)} · ${escape(tc.manual_override.reason||'No reason recorded')}</p>`:''}<div class="actions"><strong>Test log</strong></div><pre class="log code" id="log-output">${escape(state.activeTask===task.id && tc.status==='Running'?state.log:tc.log_text||'No test log. Run this Test Case to collect evidence.')}</pre><div id="input-slot">${state.activeTask===task.id&&state.prompt?inputForm(state.prompt.session,state.prompt.text):''}</div><details><summary>Result annotation</summary><form id="annotation-form"><div class="fields"><label class="field"><span>Manual status</span><select name="status" ${task.execution_active?'disabled':''}><option value="TBD">Not run / pending</option><option value="Passed">Passed</option><option value="Failed">Failed</option><option value="Block">Block</option></select></label><label class="field"><span>Reason</span><input name="reason" ${task.execution_active?'disabled':''}></label><label class="field"><span>Bug ID</span><input name="bug_id" value="${escape(tc.bug_id)}" ${task.execution_active?'disabled':''}></label></div><div class="form-actions"><button ${task.execution_active?'disabled':''}>Save annotation</button></div></form></details>`;
}
function repositoryCheck(kind,id){return state.repositoryBatch?`<input type="checkbox" class="repository-batch-check" data-kind="${kind}" data-id="${escape(id)}" aria-label="Select ${kind}" ${state.repositorySelection?.has(kind+':'+id)?'checked':''}>`:'';}
function repositorySelectionData(){const folders=[],cases=[];for(const value of state.repositorySelection||[]){const [kind,id]=value.split(':');(kind==='folder'?folders:cases).push(id);}return {folder_ids:folders,case_ids:cases};}
function folderAction(label,action,id,kind=''){return button(icon(action==='new-repository-case'?'plus':action==='new-repository-folder'?'folderPlus':action==='resort-repository-folder'?'sort':'trash'),action,'small-button icon-button '+kind,`data-id="${escape(id)}" aria-label="${label}" title="${label}"`);}
function selectedRepositoryFolder(){return state.repositoryFolders.find(f=>f.id===state.repositoryFolder)||state.repositoryFolders.find(f=>f.is_root);}
function repositoryFolderOptions(selected) {
 return (state.repositoryFolders||[]).map(f=>`<option value="${escape(f.id)}" ${selected===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('');
}
function repositoryTable(add=false,plan=null) {
 const selected=selectedRepositoryFolder();state.repositoryFolder=selected?.id;
 const folderCounts=new Map();
 const folderCount=id=>{if(!folderCounts.has(id))folderCounts.set(id,state.repository.filter(c=>c.folder_id===id).length+state.repositoryFolders.filter(f=>f.parent_id===id).reduce((n,f)=>n+folderCount(f.id),0));return folderCounts.get(id);};
 const caseRow=(c,depth)=>{const exists=plan?.testcases.some(t=>t.tc_name.toLowerCase()===c.name.toLowerCase());
 return `<tr data-repository-id="${escape(c.id)}" ${add?'':'draggable="true"'} data-search="${escape(c.name.toLowerCase())}" style="--depth:${depth}"><td>${repositoryCheck('case',c.id)}<strong>${automation(c.metadata.automation)}${escape(c.name)}</strong><p class="help">${escape(version(c.source_version))}</p></td><td>${add?button(exists?'Already in Plan':'Add to Plan','add-case',exists?'':'primary',`data-id="${escape(c.id)}" ${exists||plan.locked?'disabled':''}`):Object.keys(c.metadata.parameters||{}).length?button(`Parameters (${Object.keys(c.metadata.parameters||{}).length})`,'view-parameters','small-button',`data-id="${escape(c.id)}" aria-label="Parameters for ${escape(c.name)}"`):''}</td>${add?'':`<td><div class="actions">${button(icon('eye'),'view-standard','small-button icon-button',`data-id="${escape(c.id)}" title="View" aria-label="View ${escape(c.name)}"`)}${button(icon('trash'),'remove-standard','small-button icon-button danger',`data-id="${escape(c.id)}" title="Remove" aria-label="Remove ${escape(c.name)}"`)}</div></td>`}</tr>`;};
 const children=(parent,depth)=>state.repositoryFolders.filter(f=>f.parent_id===parent).sort((a,b)=>a.position-b.position).map(f=>`<tr class="repository-folder-row" data-folder-node="${escape(f.id)}" data-action="select-repository-folder" data-id="${escape(f.id)}" ${add||f.is_root?'':'draggable="true"'} style="--depth:${depth}"><td><div class="repository-folder-line">${f.is_root?(state.repositoryBatch?'<input type="checkbox" disabled aria-label="BMC">':''):repositoryCheck('folder',f.id)}${button(state.repositoryCollapsed?.has(f.id)?'&#9656;':'&#9662;','toggle-repository-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!state.repositoryCollapsed?.has(f.id)}"`)}<button type="button" class="repository-folder-name" data-action="select-repository-folder" data-id="${escape(f.id)}" aria-pressed="${selected?.id===f.id}" title="${escape(f.folder_path)}">${icon('folder')}<strong>${escape(f.name)}</strong><span class="repository-folder-count">(${folderCount(f.id)})</span></button>${state.repositoryRename===f.id?`<input class="repository-rename" data-id="${escape(f.id)}" aria-label="Folder name" value="${escape(f.name)}" maxlength="100">`:''}</div></td>${add?'':'<td></td>'}<td><div class="actions">${add?button('Add folder to Plan','add-repository-folder','small-button',`data-id="${escape(f.id)}" ${plan.locked?'disabled':''}`):folderAction('Add Test Case','new-repository-case',f.id)+folderAction('New folder','new-repository-folder',f.id)+folderAction('Resorting','resort-repository-folder',f.id)+(f.is_root?'':folderAction('Remove folder','remove-repository-folder',f.id,'danger'))}</div></td></tr>${state.repositoryCollapsed?.has(f.id)?'':children(f.id,depth+1)+state.repository.filter(c=>c.folder_id===f.id).map(c=>caseRow(c,depth+1)).join('')}`).join('');
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
 return `<div class="repository-page-controls actions"><label><span class="sr-only">Find Test Case</span><input id="repository-search" type="search" placeholder="Find Test Case"></label>${button(state.repositoryBatch?'Finish batch':'Batch operations','repository-batch-toggle')}${state.repositoryBatch?button('Delete selected','repository-batch-delete','danger',state.repositorySelection?.size?'':'disabled'):''}</div>`+folderForm+(state.panel==='import-python'?`<form id="repository-form" class="inline-form"><h2>Add Test Case</h2><label class="field"><span>Python file</span><input type="file" name="file" accept=".py" required></label><label class="field"><span>Folder</span><select name="folder_id">${repositoryFolderOptions(selected.id)}</select></label><div class="form-actions"><button class="primary">Add to Repository</button>${button('Cancel','close-panel')}</div></form>`:'')+repositoryWorkspace();
}
const settingsGroups=[['BMC connection',[['host','BMC URL'],['username','Username'],['password','Password','password']]],['Console server (optional)',[['cs_host','Host'],['cs_port','Port','number'],['cs_protocol','Protocol'],['cs_username','Username'],['cs_password','Password','password']]],['DUT console commands (optional)',[['dut_connect_cmd','Connect command'],['dut_exit_cmd','Exit command'],['dut_force_connect_cmd','Force connect command']]],['DUT operating system (optional)',[['dut_os_type','OS type'],['dut_os_host_ip','Host IP'],['dut_os_username','Username'],['dut_os_password','Password','password'],['dut_os_prompt_regex','Prompt expression']]]];
async function settingsPage(task) {
  let config={},missing=false; try {config=await api(`/api/tasks/${task.id}/settings`);}catch(e){if(e.status!==404)throw e;missing=true;}
  return '<h2>Connection settings</h2><p>Independent BMC and DUT connection environment for this Task. Other Tasks keep their own settings.</p>'+ (task.execution_active?'<div class="notice">This Task is executing. Connection settings are locked.</div>':'')+(missing?'<div class="notice info">Configure the BMC connection for this Task before execution.</div>':'')+`<form id="settings-form" class="settings-form"><fieldset class="connection-fields" ${task.execution_active?'disabled':''}>${settingsGroups.map(([name,fields],i)=>`<section class="section"><h2>${name}</h2><div class="fields">${fields.map(([key,label,type='text'])=>`<label class="field"><span>${label}</span><input name="${key}" type="${type}" value="${escape(config[key]??'')}" ${key==='host'?'placeholder="https://bmc-host" required':''} autocomplete="${type==='password'?'new-password':'off'}"></label>`).join('')}${i===0?`<label class="checkbox-field"><input type="checkbox" name="verify_ssl" ${config.verify_ssl?'checked':''}>Verify TLS certificate</label>`:''}</div></section>`).join('')}<div class="form-actions"><button class="primary">Save connection settings</button></div></fieldset></form>`;
}
async function taskManagementPage() {
  const result=await api('/api/tasks'); const project=context().project; state.managedTasks=project?result.tasks.filter(t=>t.project_id===project.id):result.tasks;
  const plans=project?project.plans:state.projects.flatMap(p=>p.plans);
  const editing=state.managedTasks.find(t=>t.id===state.managerTaskId);
  if(['manager-new','manager-edit'].includes(state.panel)){const options=await api('/api/tasks/options');state.taskOptions=options.projects;state.taskOwners=options.owners||['TBD'];}
  const form=state.panel==='manager-new'?TaskManagement.form(state.taskOptions,null,state.taskOwners):state.panel==='manager-edit'&&editing?TaskManagement.form(state.taskOptions,editing,state.taskOwners):'';
  const search=state.managerSearch||'';
  const selected=project?'my-task':state.managerTab||'schedule';
  if(['schedule','my-schedule'].includes(selected)){
    const range=TaskManagement.calendarRange(state.managedTasks),first=Date.parse(range.start+'T00:00:00Z')/86400000,last=Date.parse(range.end+'T00:00:00Z')/86400000;
    const requests=[];
    for(let value=first;value<=last;value+=366){const segment={start:new Date(value*86400000).toISOString().slice(0,10),end:new Date(Math.min(value+365,last)*86400000).toISOString().slice(0,10)};requests.push(api('/api/schedule/calendar?'+new URLSearchParams(segment)));}
    const calendars=await Promise.all(requests);
    TaskManagement.setCalendar({...calendars[0],...range,days:calendars.flatMap(item=>item.days)});
  }
  if(selected==='info'){
    const identity=state.route[0]==='tasks'&&state.route[1]==='info'?state.route[2]:null;
    const current=state.managedTasks.find(item=>item.id===identity&&item.task_type==='Plan');
    if(current)state.taskInfoPath=TaskManagement.infoLink(current);
    const info=current?((form||TaskManagement.planningInfo(current))+TaskManagement.historyList((await api('/api/tasks/'+encodeURIComponent(current.id)+'/history')).history)):empty(identity?'Task not found.':'Select a Task',identity?'This Task may have been deleted.':'Choose a Task from Task List or My Task to configure its connection settings, scope and information.');
    return taskWorkspaceTabs(selected)+`<div id="task-manager-content" role="tabpanel" aria-labelledby="manager-tab-info">${info}</div>`;
  }
  return (project?heading('Execution',project.name):taskWorkspaceTabs(selected))+
    (!state.projects.length?'<div class="notice info">Create a Project before adding Tasks. <a href="#/dashboard">Open Projects</a></div>':'')+form+
    `<div class="toolbar"><div class="actions"><label><span class="sr-only">Find Task</span><input id="manager-search" type="search" placeholder="Find Task, Project or Plan" value="${escape(search)}"></label>${['schedule','my-schedule'].includes(selected)?'<button type="button" data-schedule-action="today">Today</button>':''}</div>${button('New Task','manager-new','primary',!state.projects.length?'disabled':'')}</div><div id="task-manager-content" ${project?'role="region" aria-label="Project Tasks"':`role="tabpanel" aria-labelledby="manager-tab-${selected}"`}>${TaskManagement.content(state.managedTasks,search,selected)}</div>`;
}
function taskWorkspaceTabs(selected) {
  const tabs=['schedule','my-schedule'].includes(selected)?[['schedule','Schedule'],['my-schedule','My Schedule']]:[['list','Task List'],['my-task','My Task'],['info','Task Info']];
  return `<div class="tabs ${['schedule','my-schedule'].includes(selected)?'schedule-tabs':''}" role="tablist" aria-label="Task workspace">${tabs.map(([id,label])=>button(label,'manager-tab','',`id="manager-tab-${id}" role="tab" aria-selected="${selected===id}" aria-controls="task-manager-content" data-manager-tab="${id}" data-no-translate`)).join('')}</div>`;
}
function missingWorkspaceParent() {
  if(state.route[0]!=='project')return null;
  const {project,plan,task}=context();
  if(!project)return '#/dashboard';
  if(state.route[2]==='plan'&&!plan)return path(project)+'/plans';
  if(state.route[4]==='task'&&!task)return path(project,plan);
  return null;
}
async function draw() {
  const parent=missingWorkspaceParent();
  if(parent){location.replace(parent);return;}

  const generation=++state.generation; const workspace=$('#workspace'); workspace.setAttribute('aria-busy','true');
  const section=state.route[0]||'dashboard'; document.body.classList.toggle('repository-page',section==='repository'); $$('.global-nav a').forEach(a=>a.toggleAttribute('aria-current',a.dataset.section===(context().task?'tasks':section==='project'?'projects':section))); $$('.global-nav [aria-current]').forEach(a=>a.setAttribute('aria-current','page'));

  const {project,plan,task}=context(); document.body.classList.toggle('plan-workspace',Boolean(plan&&!task));let html;
  if(task) Object.assign(task, await api(`/api/tasks/${task.id}/summary`));
  if(generation!==state.generation)return;
  if(section==='tasks') html=await taskManagementPage(); else if(section==='repository') html=await repositoryPage(); else if(section==='settings') html=empty('Choose a Task','Connection settings belong to each Task. Open a Task and select Connection settings.'); else if(section==='project'&&!project || state.route[2]==='plan'&&!plan || state.route[4]==='task'&&!task) html=empty('Workspace not found','This item may have been deleted. Choose an existing Project from the navigator.','<a href="#/dashboard">Go to Projects</a>');
  else if(project&&state.route[2]==='execution') html=await taskManagementPage();
  else if(project&&state.route[2]==='reports') html=heading('Report',project.name)+(!project.plans.length?empty('No Tasks yet','Create a Plan and Task to generate reports.'):project.plans.map(p=>'<section class="section"><h2>'+escape(p.name)+'</h2>'+tasksTable(project,p,true)+'</section>').join(''));
  else if(project&&(!state.route[2]||['info','reports','bugs'].includes(state.route[2]))) html=await projectSectionPage(project); else if(task) html=await taskPage(project,plan,task); else if(plan) html=await planPage(project,plan); else html=projectPage(project);
  if(task){state.taskInfoPath=path(project,plan,task)+(state.route[6]==='info'?'/info':'');html=taskWorkspaceTabs('info')+`<div id="task-manager-content" role="tabpanel" aria-labelledby="manager-tab-info">${html}</div>`;}
  if(generation!==state.generation)return; workspace.innerHTML=html; sizePlanColumns(); workspace.setAttribute('aria-busy','false'); drawTree();
  TaskManagement.bindForm(state.taskOptions||[],api);
  TaskManagement.bindSchedule(api,draw,toast);
  ProjectInformationUI.bind();
  if(plan&&!task) await loadCase();
  if(state.panel && $('#name-form input')) $('#name-form input').focus();
}
function discard() { return !state.dirty || window.confirm('Discard unsaved changes?'); }
async function navigate() {
  if(state.restoringHash){state.restoringHash=false;return;}
  if(!discard()){state.restoringHash=true;location.hash=previousHash;return;}
  state.managerTab=state.nextManagerTab||(location.hash==='#/tasks/list'?'list':location.hash==='#/tasks/my-task'?'my-task':location.hash==='#/tasks/my-schedule'?'my-schedule':location.hash.startsWith('#/tasks/info/')?'info':'schedule');state.nextManagerTab=null;
  state.infoEditing=false;state.projectImport=null;state.projectInformation=null;state.infoCollapsed=new Set();state.infoSection='spec';
  previousHash=location.hash||'#/dashboard'; state.route=previousHash.slice(2).split('/').map(decodeURIComponent); state.panel=null;state.dirty=false;state.definition=null;state.caseId=null;state.planSearch='';state.planCollapsed=new Set();state.planFolder=null;state.planRename=null;state.planTargetFolder=null;state.importSource=null;state.repositoryDefinition=null;document.body.classList.toggle('repository-page',state.route[0]==='repository');
  $('#workspace').innerHTML='<div class="loading">Loading workspace…</div>';
  $('#workspace').setAttribute('aria-busy','true');
  await refresh(false);
  if(state.route[0]==='projects'){location.replace(projectEntryRoute());return;}
  state.tab=state.route[4]==='task'?(state.route[6]==='info'?'details':'settings'):'cases'; const {task}=context(); state.scope=new Set(task?.testcases.map(c=>c.id)||[]);
  state.panel=state.nextPanel||null;state.nextPanel=null;
  document.body.classList.remove('nav-open');await draw();
}
async function confirmDelete(title,message,itemName) {
  if(confirmationPending)return false;confirmationPending=true;
  $('#confirm-title').textContent=title;$('#confirm-message').textContent=message;if(itemName){const name=document.createElement('strong');name.dataset.noTranslate='';name.textContent=itemName;$('#confirm-message').prepend(name,document.createElement('br'));}const dialog=$('#confirm-dialog');dialog.returnValue='';dialog.showModal();
  return new Promise(resolve=>dialog.addEventListener('close',()=>{const answer=dialog.returnValue==='confirm';confirmationPending=false;resolve(answer);},{once:true}));
}
function download(name, content, type='text/plain') { const url=URL.createObjectURL(new Blob([content],{type})); const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000); }
function currentSettings() { const form=$('#case-form'); return Object.fromEntries(Object.entries(state.definition.metadata.parameters||{}).map(([key,spec])=>{const field=form.elements.namedItem('p:'+key);return [key,spec.type==='boolean'?field.checked:['integer','number'].includes(spec.type)?Number(field.value):field.value];})); }
async function doAction(action, element) {
  const {project,plan,task}=context();
  if(action==='dismiss-import-result'){state.projectImportResult=null;await draw();return;}
  if(action==='project-create-mode'||action==='project-create-back'){if(!discard())return;state.dirty=false;state.projectImport=null;state.projectCreateMode=action==='project-create-back'?null:element.dataset.mode;await draw();return;}
  if(action==='info-section'){ProjectInformationUI.capture(state.projectInformation.document);state.infoSection=element.dataset.section;await draw();if(state.dirty&&$('#save-state'))$('#save-state').textContent='Unsaved changes';return;}
  if(action==='info-toggle-category'){const group=document.getElementById(element.getAttribute('aria-controls'));state.infoCollapsed??=new Set();const closed=!group.hidden;group.hidden=closed;element.setAttribute('aria-expanded',String(!closed));element.querySelector('.info-chevron').textContent=closed?'▸':'▾';closed?state.infoCollapsed.add(element.dataset.id):state.infoCollapsed.delete(element.dataset.id);return;}
  if(action==='info-edit'){state.infoEditing=true;state.infoOriginal=structuredClone(state.projectInformation);await draw();return;}
  if(action==='info-cancel'){if(!discard())return;state.projectInformation=state.infoOriginal;state.infoEditing=false;state.dirty=false;await draw();return;}
  if(action==='info-add-sku'||action==='info-remove-sku'){
    if(!state.infoEditing)return;
    const record=state.projectInformation;ProjectInformationUI.capture(record.document);
    if(action==='info-add-sku'){
      if(record.document.skus.length>=32){toast('At most 32 SKUs are supported.',true);return;}
      let number=record.document.skus.length+1;while(record.document.skus.some(s=>s.name===`SKU ${number}`))number++;
      record.document.skus.push({id:crypto.randomUUID(),name:`SKU ${number}`});state.dirty=true;
    }else{
      const sku=record.document.skus.find(s=>s.id===element.dataset.id);if(!sku)return;
      if(!await confirmDelete('Remove SKU?','Remove this SKU and its specification values from project information?',sku.name))return;
      record.document.skus=record.document.skus.filter(s=>s.id!==sku.id);record.document.categories.forEach(c=>c.items.forEach(i=>delete i.sku_values[sku.id]));state.dirty=true;
    }
    await draw();if(state.dirty)$('#save-state').textContent='Unsaved changes';
  } else if(action==='choose-project'){
    const selected=state.projects.find(p=>p.id===element.dataset.projectId);if(!selected)return;
    const section=['info','plans','execution','reports','bugs'].includes(state.route[2])?state.route[2]:'plans';
    closeProjectPicker();
    location.hash=path(selected)+'/'+section;
  } else if(action==='manager-tab'){
    if(!discard())return;
    state.dirty=false;state.panel=null;state.managerTab=element.dataset.managerTab;
    if(state.managerTab==='info'&&state.taskInfoPath&&!task){location.hash=state.taskInfoPath;return;}
    if(state.managerTab!=='info'){const target=state.managerTab==='list'?'#/tasks/list':state.managerTab==='my-task'?'#/tasks/my-task':state.managerTab==='my-schedule'?'#/tasks/my-schedule':'#/tasks';if(location.hash!==target){location.hash=target;return;}}
    await draw();
    $(`#manager-tab-${state.managerTab}`)?.focus();
  } else if(action==='resort-plan-folder'||action==='resort-repository-folder'){
    if(!discard())return;
    element.disabled=true;
    try{
      if(action==='resort-plan-folder')await api(`/api/plans/${plan.id}/testcases/resort`,'POST',{folder_id:element.dataset.id||null});
      else await api(`/api/repository/folders/${element.dataset.id}/resort`,'POST',{});
      state.dirty=false;await refresh();toast('Test Cases sorted by number.');
    }finally{element.disabled=false;}
  } else if(action==='new-task'){
    if(!discard())return;state.nextPanel='manager-new';state.dirty=false;location.hash='#/tasks/list';
  } else if(action==='manager-new'||action==='manager-edit'){
    if(!discard())return;state.dirty=false;state.panel=action;state.managerTaskId=action==='manager-edit'?element.dataset.id:null;await draw();$('#manager-type')?.focus();
  } else if(action==='manager-delete'){
    const current=state.managedTasks.find(t=>t.id===element.dataset.id);if(!current)return;
    if(!discard())return;
    if(!await confirmDelete(`Delete Task: ${current.name}?`,'This deletes the Task, its scope and current results. Plan Test Cases and other Tasks remain.'))return;
    await api(`/api/tasks/${current.id}`,'DELETE');state.dirty=false;state.panel=null;await refresh();toast('Task deleted.');
  } else if(action==='tab'){if(!discard())return;state.dirty=false;state.tab=element.dataset.tab;state.panel=null;await draw();}
  else if(action==='close-panel'){if(!discard())return;state.dirty=false;state.panel=null;await draw();}
  else if(action==='new-plan'){
    if(!discard())return;state.dirty=false;
    element.disabled=true;
    try{
      const options=(await api('/api/tasks/options')).projects.find(p=>p.id===project.id);
      const information={project_name:options.name},skus=options.skus,form=$('#plan-create-form');
      form.reset();form.dataset.projectId=project.id;
      const selector=$('#plan-create-sku'),name=$('#plan-create-name');
      selector.replaceChildren(new Option('Choose a SKU',''),...skus.map(sku=>{const option=new Option(sku.full_name,sku.id);option.setAttribute('data-no-translate','');return option;}));
      $('#plan-create-sku-field').hidden=!skus.length;selector.required=Boolean(skus.length);selector.disabled=!skus.length;
      name.value=skus.length?'':information.project_name;name.disabled=Boolean(skus.length);
      $('#plan-create-error').textContent='';$('#plan-create-dialog').showModal();
      (skus.length?selector:name).focus();
    }finally{element.disabled=false;}
  }
  else if(action==='cancel-create-plan'){if(!state.creatingPlan){$('#plan-create-dialog').close();state.dirty=false;}}
  else if(action==='delete-project'){
    if(!discard())return;
    const selected=state.projects.find(p=>p.id===element.dataset.id);if(!selected)return;
    if(!await confirmDelete('Delete Project?','This permanently deletes the Project and all its Plans, Test Cases, Tasks and current results. Repository Test Cases are kept.',selected.name))return;
    element.disabled=true;
    try{
      await api('/api/delete_project','POST',{project:selected.name});
      if(localStorage.getItem('bmc-last-project')===selected.id){localStorage.removeItem('bmc-last-project');localStorage.removeItem('bmc-last-project-route');}
      if(state.taskInfoPath?.startsWith(path(selected)+'/'))state.taskInfoPath=null;
      state.dirty=false;state.panel=null;await refresh();toast('Project deleted.');
    }finally{element.disabled=false;}
  }
  else if(['new-project','new-plan','new-task','rename-project','rename-plan','rename-task','new-folder','add-repository','import-python'].includes(action)){if(!discard())return;state.dirty=false;if(action==='new-project'){state.projectCreateMode=null;state.projectImport=null;state.projectImportResult=null;}if(action==='new-project'&&state.route[0]!=='dashboard'){state.nextPanel=action;location.hash='#/dashboard';return;}state.panel=action;state.tab='cases';await draw();}
  else if(action==='select-case'){if(!discard())return;state.generation++;state.dirty=false;state.caseId=element.dataset.id;$$('.case-row').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.id===state.caseId)));await loadCase();}
  else if(action==='select-result'){state.caseId=element.dataset.id;await draw();}
  else if(action==='toggle-plan-matrix'){state.expandedPlans??=new Set();const id=element.dataset.id;state.expandedPlans.has(id)?state.expandedPlans.delete(id):state.expandedPlans.add(id);const expanded=state.expandedPlans.has(id);element.setAttribute('aria-expanded',String(expanded));element.closest('tr').nextElementSibling.hidden=!expanded;}
  else if(action==='toggle-repository-folder'){state.repositoryCollapsed??=new Set();state.repositoryCollapsed.has(element.dataset.id)?state.repositoryCollapsed.delete(element.dataset.id):state.repositoryCollapsed.add(element.dataset.id);await draw();}
  else if(action==='repository-batch-toggle'){state.repositoryBatch=!state.repositoryBatch;state.repositorySelection=new Set();await draw();}
  else if(action==='repository-batch-delete'){const selection=repositorySelectionData();if(!await confirmDelete('Delete selected items?',`${selection.folder_ids.length} directories and ${selection.case_ids.length} Test Cases selected. Selected directories and all their contents will be permanently deleted. Plan copies remain independent.`))return;await api('/api/repository/batch','POST',{...selection,action:'delete',confirm:true});state.repositorySelection.clear();state.repositoryDefinition=null;await draw();toast('Selected items deleted.');}
  else if(action==='select-repository-folder'){
    const id=element.dataset.id,folder=state.repositoryFolders.find(f=>f.id===id);
    const rename=state.route[0]==='repository'&&element.classList.contains('repository-folder-name')&&state.repositoryNameClick===id&&state.repositoryFolder===id&&!folder.is_root;
    state.repositoryRename=rename?id:null;state.repositoryFolder=id;state.repositoryDefinition=null;if(state.route[0]==='repository')state.panel=null;await draw();
    if(rename){const input=$('.repository-rename');input.focus();input.select();}
  }
  else if(action==='select-plan-folder'){
    if(!discard())return;state.dirty=false;
    const id=element.dataset.id,rename=state.planFolder===id&&state.repositoryNameClick===id&&!plan.locked;
    state.planFolder=id;state.planRename=rename?id:null;$('#plan-case-list').innerHTML=planCaseTable(plan);
    const input=$('.plan-folder-rename');if(input){input.focus();input.select();}
  }
  else if(action==='plan-import-case'){
    if(state.repositoryImporting||plan.locked||!discard())return;
    state.dirty=false;const picker=$('#repository-file-picker');picker.dataset.planId=plan.id;picker.dataset.folderId=element.dataset.id||'';picker.value='';picker.click();
  }
  else if(action==='toggle-plan-folder'){state.planCollapsed??=new Set();const id=element.dataset.id;state.planCollapsed.has(id)?state.planCollapsed.delete(id):state.planCollapsed.add(id);$('#plan-case-list').innerHTML=planCaseTable(plan);}
  else if(['plan-case-parameters','plan-case-source'].includes(action)){if(!discard())return;state.dirty=false;state.importSource=null;state.caseId=element.dataset.id;state.planCaseView=action==='plan-case-source'?'source':'parameters';await draw();}
  else if(action==='close-plan-case'){if(!discard())return;state.dirty=false;state.caseId=null;await draw();}
  else if(action==='plan-remove-case'){
    if(!discard())return;const current=plan.testcases.find(c=>c.id===element.dataset.id);if(!current)return;
    if(!await confirmDelete(`Delete Test Case: ${current.tc_name}?`,'This deletes the Plan Test Case and its current results and logs from every Task in this Plan.'))return;
    await api(`/api/testcases/${current.id}`,'DELETE',{confirm:true,acknowledgement:true});state.dirty=false;await refresh();toast('Deleted Test Case.');
  }
  else if(action==='choose-import-source'){
    if(plan.locked||!discard())return;state.dirty=false;
    $('#plan-import-source').innerHTML='<option value="repository">Test Case Repository</option>'+state.projects.map(p=>`<optgroup label="${escape(p.name)}">${p.plans.filter(x=>x.id!==plan.id).map(x=>`<option value="plan:${escape(x.id)}">${escape(p.name)} / ${escape(x.name)}</option>`).join('')}</optgroup>`).join('');
    $('#plan-import-error').textContent='';$('#plan-import-dialog').showModal();$('#plan-import-source').focus();
  }
  else if(action==='cancel-import-conflicts')$('#import-conflict-dialog').close();
  else if(action==='cancel-import-source')$('#plan-import-dialog').close();
  else if(action==='close-import-source'){state.importSource=null;await draw();}
  else if(action==='toggle-import-folder'){state.importCollapsed??=new Set();const id=element.dataset.id;state.importCollapsed.has(id)?state.importCollapsed.delete(id):state.importCollapsed.add(id);$('#import-source-list').innerHTML=importSourceTable();}
  else if(action==='plan-add-cases'){if(!discard())return;state.dirty=false;state.planTargetFolder=element.dataset.id||null;state.panel='add-repository';await draw();}
  else if(action==='new-plan-folder'){
    if(!discard())return;state.dirty=false;
    const form=$('#repository-create-folder-form');form.reset();form.dataset.parentId=element.dataset.id||'';form.dataset.planId=plan.id;
    $('#repository-create-folder-error').textContent='';$('#repository-create-folder-dialog').showModal();$('#repository-create-folder-name').focus();
  }
  else if(action==='new-repository-case'){
    if(state.repositoryImporting)return;
    const picker=$('#repository-file-picker');delete picker.dataset.planId;picker.dataset.folderId=element.dataset.id;picker.value='';picker.click();
  }
  else if(action==='new-repository-folder'){
    const form=$('#repository-create-folder-form');form.reset();delete form.dataset.planId;form.dataset.parentId=element.dataset.id;
    $('#repository-create-folder-error').textContent='';$('#repository-create-folder-dialog').showModal();$('#repository-create-folder-name').focus();
  }
  else if(action==='cancel-repository-folder'){if(!state.repositoryCreatingFolder){$('#repository-create-folder-dialog').close();state.dirty=false;}}
  else if(action==='edit-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;state.panel=action;await draw();}
  else if(action==='remove-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;const selected=selectedRepositoryFolder();if(!await confirmDelete(`Remove folder: ${selected.name}?`,'This permanently deletes the folder, all subfolders and their Test Cases. Existing Plan copies remain independent.'))return;const result=await api(`/api/repository/folders/${selected.id}`,'DELETE',{confirm:true});state.repositoryFolder=result.parent_id;state.repositoryDefinition=null;state.panel=null;await draw();toast('Folder and contents deleted.');}
  else if(action==='add-repository-folder'){if(element.dataset.id)state.repositoryFolder=element.dataset.id;const result=await api(`/api/plans/${plan.id}/repository/folders/${state.repositoryFolder}`,'POST',{});await refresh();toast(`${result.added.length} Test Cases copied into ${result.folder_name}. ${result.skipped.length} existing/duplicate names skipped.`);}
  else if(action==='add-case'){await api(`/api/plans/${plan.id}/repository/testcases`,'POST',{repository_id:element.dataset.id,...(state.planTargetFolder?{folder_id:state.planTargetFolder}:{})});await refresh();toast('Test Case copied into this Plan.');}
  else if(action==='inspect-source'){const result=await api('/api/repository/inspect','POST',{source:$('#case-form').elements.source.value});const old=currentSettings();state.definition.metadata=result.metadata;const settings=Object.fromEntries(Object.entries(result.metadata.parameters||{}).map(([k,s])=>[k,k in old?old[k]:s.default]));$('#case-form .fields').innerHTML=parameterFields(result.metadata,settings);state.dirty=true;toast('Editable fields refreshed. Save to apply this adaptation.');}
  else if(action==='scope'){state.tab='scope';await draw();}
  else if(action==='scope-all'||action==='scope-none'){state.scope=new Set(action==='scope-all'?plan.testcases.filter(c=>c.script_kind==='single').map(c=>c.id):[]);state.dirty=true;await draw();}
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
    state.dirty=false;await refresh(false);if(type==='project')location.hash='#/dashboard';else if(type==='plan')location.hash=path(project)+'/plans';else if(type==='task')location.hash=path(project,plan);else await draw();toast('Deleted '+type+'.');
  }
}
async function submit(form) {
 const {project,plan,task}=context();const values=Object.fromEntries(new FormData(form));
 if(form.id==='project-create-form'){
   const automatic=form.dataset.mode==='auto',file=form.querySelector('#project-document')?.files[0];
   const name=automatic?'':(values.name||'').trim();if(!automatic&&!name)throw Error('Enter a name.');
   let imported;
   if(automatic&&!file)throw Error('Choose a requirements workbook.');
   if(automatic){if(!state.projectImport?.ready||state.projectImport.file!==file)throw Error('Wait for a valid document preview.');const review=projectImportSelection(form);if(!review)throw Error('Classify every column and confirm the review.');imported=await importProjectDocument(file,'',false,review);}
   else await api('/api/create_project','POST',{project:name});
   state.dirty=false;state.panel=null;state.projectImport=null;await refresh(false);if(automatic&&imported.projects.length>1){state.projectImportResult=imported.projects;await draw();return;}const created=state.projects.find(p=>automatic?p.id===imported.id:p.name===name);if(!automatic)state.editCreatedProject=created.id;location.hash=path(created)+'/info';return;
 }
 if(form.id==='project-information-form'){
   if(!state.infoEditing)return;
   ProjectInformationUI.capture(state.projectInformation.document);
   const saved=await api(`/api/projects/${project.id}/information`,'PUT',{revision:state.projectInformation.revision,document:state.projectInformation.document});
   Object.assign(state.projectInformation,saved);state.infoEditing=false;state.dirty=false;await draw();toast('Project information saved.');return;
 }
 if(form.id==='task-manager-form'){
   const id=form.dataset.taskId;const setup={start_date:values.start_date,end_date:values.end_date,notes:values.notes,owner:values.owner};
   if(Boolean(setup.start_date)!==Boolean(setup.end_date))throw Error('Supply both start and end dates, or leave both empty.');
   if(setup.start_date&&setup.end_date<setup.start_date)throw Error('End date must be on or after start date.');
   if(id){
     const payload={setup,expected_start_date:form.dataset.startDate||'',expected_end_date:form.dataset.endDate||'',expected_owner:form.dataset.owner||'TBD'};
     if(setup.start_date!==payload.expected_start_date||setup.end_date!==payload.expected_end_date){
       if(!values.history?.trim())throw Error('Enter History explaining the schedule change (1 to 4000 characters).');
       payload.history=values.history;
     }
     await api(`/api/tasks/${id}`,'PATCH',payload);
   }
   else{if(!form.dataset.nameReady)throw Error('Select Task Type, Project, SKU and Plan first.');await api('/api/tasks','POST',{task_type:values.task_type,project_id:values.project_id,sku_id:values.sku_id||null,plan_id:values.task_type==='Test'?values.plan_id:null,setup});}
   state.dirty=false;state.panel=null;await refresh();toast(id?'Task updated.':'Task created.');
 }else if(form.id==='plan-create-form'){
   if(state.creatingPlan)return;
   const targetProject=state.projects.find(p=>p.id===form.dataset.projectId);
   if(!targetProject)throw Error('Project not found.');
   if(!form.elements.sku_id.disabled&&!form.elements.sku_id.value)throw Error('Choose a SKU.');
   const name=values.name.trim();
   if(!name){form.elements.name.focus();throw Error('Enter a name.');}
   if(name.length>100)throw Error('Plan name must be 100 characters or fewer.');
   if(targetProject.plans.some(p=>p.name===name)){form.elements.name.focus();throw Error('A Plan with this name already exists. Please change the Plan name.');}
   state.creatingPlan=true;
   try{
     try{await api('/api/create_plan','POST',{project:targetProject.name,plan_name:name,sku_id:values.sku_id||null});}
     catch(error){if(error.status===409)throw Error('A Plan with this name already exists. Please change the Plan name.');throw error;}
     state.dirty=false;state.panel=null;$('#plan-create-dialog').close();await refresh();toast('Saved.');
   }finally{state.creatingPlan=false;}
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
   const result=await api(`/api/plans/${plan.id}/testcases/${state.caseId}/definition`,'PUT',{source:state.definition.source,settings:currentSettings(),settings_revision:state.definition.settings_revision});state.definition=result;state.dirty=false;await refresh();toast('Plan Test Case saved. All Tasks use the updated definition.');
 }else if(form.id==='case-details'){
   await api(`/api/testcases/${state.caseId}`,'PATCH',{tc_name:values.name});if(values.folder_id!==undefined)await api(`/api/plans/${plan.id}/testcases/move`,'POST',{testcase_ids:[state.caseId],folder_id:values.folder_id||null});state.dirty=false;await refresh();toast('Test Case organization saved.');
 }else if(form.id==='scope-form'){
   await api(`/api/tasks/${task.id}/testcases/import`,'POST',{testcases:[...state.scope]});state.dirty=false;state.tab='execution';await refresh();toast('Task scope saved.');
 }else if(form.id==='repository-create-folder-form'){
   if(state.repositoryCreatingFolder)return;
   const name=values.name.trim();if(!name)throw Error('Enter a name.');
   const parent=form.dataset.parentId;state.repositoryCreatingFolder=true;
   try{
     const planId=form.dataset.planId;
     const folder=await api(planId?`/api/plans/${planId}/folders`:'/api/repository/folders','POST',{name,parent_id:parent||null});
     if(planId){state.planCollapsed?.delete(parent);state.dirty=false;$('#repository-create-folder-dialog').close();await refresh();toast('Folder created.');return;}
     state.repositoryCollapsed?.delete(parent);state.repositoryFolder=folder.id;state.dirty=false;
     $('#repository-create-folder-dialog').close();await draw();
     $(`[data-folder-node="${folder.id}"]`)?.scrollIntoView({block:'nearest'});toast('Folder created.');
   }finally{state.repositoryCreatingFolder=false;}
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
document.addEventListener('submit',event=>{const form=event.target;if(form.closest('dialog')&&!['plan-create-form','repository-create-folder-form'].includes(form.id))return;event.preventDefault();const buttons=$$('button[type=submit],button:not([type]):not([data-action])',form);buttons.forEach(b=>b.disabled=true);submit(form).catch(e=>{if(form.id==='task-manager-form'){form.querySelector('#manager-form-error').textContent=e.message;}else if(form.id==='plan-create-form'){$('#plan-create-error').textContent=e.message;form.elements.name.focus();}else if(form.id==='repository-create-folder-form'){$('#repository-create-folder-error').textContent=e.message;form.elements.name.focus();}else toast(e.message,true);}).finally(()=>buttons.forEach(b=>b.disabled=false));});
document.addEventListener('input',event=>{
 const el=event.target;
 if(el.dataset.infoSku){const fields=$$('[data-info-sku]',el.closest('tr'));fields.forEach((field,index)=>field.closest('td').classList.toggle('info-sku-different',index>0&&field.value!==fields[0].value));}
 if(el.id==='project-search'){openProjectPicker();let count=0;$$('[data-project-name]').forEach(button=>{button.hidden=!button.dataset.projectName.includes(el.value.trim().toLowerCase());if(!button.hidden)count++;});$('#project-search-empty').hidden=Boolean(count);return;}
 if(el.id==='manager-search'){state.managerSearch=el.value;$('#task-manager-content').innerHTML=TaskManagement.content(state.managedTasks,el.value,context().project?'my-task':state.managerTab||'schedule');return;}

 if(el.closest('#task-manager-form')&&['start_date','end_date'].includes(el.name)){const f=el.form;f.elements.start_date.required=Boolean(f.elements.end_date.value);f.elements.end_date.required=Boolean(f.elements.start_date.value);f.elements.end_date.min=f.elements.start_date.value;}
 if(el.id==='plan-search'){state.planSearch=el.value;$('#plan-case-list').innerHTML=planCaseTable(context().plan);return;}
 if(el.id==='tree-search'){drawTree();return;}if(el.id==='case-search'||el.id==='folder-filter'){const search=($('#case-search')?.value||'').toLowerCase(),folder=$('#folder-filter')?.value;$$('#case-list [data-search]').forEach(row=>row.hidden=!row.dataset.search.includes(search)||(folder&&row.dataset.folder!==folder));return;}
 if(el.id==='repository-search'){const folder=state.repositoryFolder;$$('#repository-table [data-search]').forEach(row=>row.hidden=!row.dataset.search.includes(el.value.toLowerCase())||(folder&&folder!=='all'&&row.dataset.folder!==folder));return;}
 if(el.closest('form')&&!el.closest('#input-form,#plan-import-form,#import-conflict-form')){state.dirty=true;if($('#save-state'))$('#save-state').textContent='Unsaved changes';}
 if(el.dataset.scope){el.checked?state.scope.add(el.dataset.scope):state.scope.delete(el.dataset.scope);$('#scope-count').textContent=state.scope.size+' selected';state.dirty=true;}
});
$('#plan-create-sku').addEventListener('change',event=>{
  const selector=event.target,name=$('#plan-create-name');
  name.disabled=!selector.value;name.value=selector.value?selector.selectedOptions[0].textContent:'';
  $('#plan-create-error').textContent='';state.dirty=true;
});

function projectImportSelection(form){
 const pending=state.projectImport;
 if(!pending?.ready||!form.querySelector('#project-import-confirm')?.checked)return null;
 const classifications=[...form.querySelectorAll('[data-import-column]')].map(el=>({id:el.dataset.importColumn,kind:el.value}));
 if(classifications.some(c=>!['sku','project','skip'].includes(c.kind)))return null;
 if(classifications.length&&classifications.every(c=>c.kind==='skip'))return null;
 return {classifications,source_sha256:pending.preview.source_sha256,review_confirmed:true};
}
function updateProjectImportReview(form){
 const pending=state.projectImport;
 if(!pending?.ready)return;
 const separate=[...form.querySelectorAll('[data-import-column]')].filter(el=>el.value==='project').map(el=>pending.preview.columns.find(c=>c.id===el.dataset.importColumn).name);
 const hasMain=!pending.preview.columns.length||[...form.querySelectorAll('[data-import-column]')].some(el=>el.value==='sku');
 const names=[...(hasMain?[pending.preview.name]:[]),...separate];
 form.querySelector('#project-import-destinations').innerHTML=names.length?names.map(name=>`<li data-no-translate>${escape(name)}</li>`).join(''):'<li>No Projects selected.</li>';
 form.querySelector('[type=submit]').disabled=!projectImportSelection(form);
}
function renderProjectImportReview(form){
 const result=state.projectImport.preview,box=form.querySelector('#project-import-preview');
 box.innerHTML=`<p><span>Main Project</span>: <strong data-no-translate>${escape(result.name)}</strong></p><h3>Should any SKU become a Project?</h3><p class="help">Keep each SKU, promote it to a Project, or skip it without importing.</p>
 ${result.columns.length?`<div class="table-wrap import-classification"><table><thead><tr><th>Parsed SKU</th><th>Action</th></tr></thead><tbody>${result.columns.map(column=>`<tr><th scope="row" data-no-translate>${escape(column.name)}</th><td><select data-import-column="${escape(column.id)}" aria-label="${escape(column.name+' — promotion')}" required><option value="">Choose an answer</option><option value="sku">No, keep as SKU</option><option value="project">Yes, promote to Project</option><option value="skip">Skip (do not import)</option></select></td></tr>`).join('')}</tbody></table></div>`:'<p>No comparison columns. One Project will be created.</p>'}
 <p class="help">Skipped SKUs are not imported. Existing Projects remain unchanged.</p><h3>Projects to create</h3><ul id="project-import-destinations"></ul>
 <label class="checkbox-field"><input id="project-import-confirm" type="checkbox" required><span>I have confirmed each SKU action.</span></label>`;
 updateProjectImportReview(form);
}
async function importProjectDocument(file,name,preview,review=null){
 const data=new FormData();data.append('file',file);if(name)data.append('name',name);
 if(review){data.append('classifications',JSON.stringify(review.classifications));data.append('source_sha256',review.source_sha256);data.append('review_confirmed',String(review.review_confirmed));}
 const response=await fetch('/api/projects/import'+(preview?'/preview':''),{method:'POST',body:data});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Document import failed.');return result;
}
document.addEventListener('change',async event=>{
 if(event.target.id!=='project-document')return;
 const form=event.target.form,file=event.target.files[0],box=form.querySelector('#project-import-preview'),submit=form.querySelector('[type=submit]');
 const pending={file,ready:false};state.projectImport=pending;box.textContent='';submit.disabled=true;if(!file)return;
 box.textContent='Reading requirements document…';
 try{const result=await importProjectDocument(file,'',true);if(state.projectImport!==pending||!form.isConnected)return;
 pending.ready=true;pending.preview=result;renderProjectImportReview(form);
 }catch(error){if(state.projectImport===pending&&form.isConnected)box.textContent=error.message;}
});
document.addEventListener('change',event=>{
 if(!event.target.matches('[data-import-column],#project-import-confirm'))return;
 const form=event.target.closest('form');
 if(event.target.matches('[data-import-column]'))form.querySelector('#project-import-confirm').checked=false;
 updateProjectImportReview(form);
});
document.addEventListener('change',event=>{const el=event.target;if(el.id==='project-switcher'){const p=state.projects.find(p=>p.id===el.value);if(p){const section=!state.route[2]?'info':['info','reports','bugs'].includes(state.route[2])?state.route[2]:'plans';location.hash=path(p)+'/'+section;el.value=context().project.id;}return;}if(el.classList.contains('repository-batch-check')){state.repositorySelection??=new Set();const key=el.dataset.kind+':'+el.dataset.id;el.checked?state.repositorySelection.add(key):state.repositorySelection.delete(key);const del=$('[data-action=repository-batch-delete]');if(del)del.disabled=!state.repositorySelection.size;return;}if(el.id==='repository-folder-filter'){state.repositoryFolder=el.value;draw().catch(e=>toast(e.message,true));return;}if(el.classList.contains('repository-move')){api(`/api/repository/testcases/${el.dataset.id}/folder`,'PUT',{folder_id:el.value||null}).then(()=>draw()).catch(e=>toast(e.message,true));return;}if(el.id==='folder-filter')el.dispatchEvent(new Event('input',{bubbles:true}));if(el.dataset.run){const {task}=context();task.testcases.find(c=>c.id===el.dataset.run).selected=el.checked;api(`/api/task_testcases/${task.id}/${el.dataset.run}`,'PATCH',{selected:el.checked}).catch(e=>{el.checked=!el.checked;toast(e.message,true);});}});
document.addEventListener('click',event=>{const name=event.target.closest('.repository-folder-name strong');state.repositoryNameClick=name?.closest('.repository-folder-name').dataset.id||null;},true);
document.addEventListener('click',event=>{if(event.target.classList.contains('repository-rename')||event.target.classList.contains('repository-batch-check'))event.stopPropagation();},true);
document.addEventListener('keydown',async event=>{
 const input=event.target;if(!input.classList.contains('repository-rename')||input.classList.contains('plan-folder-rename'))return;
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

document.addEventListener('keydown',async event=>{
 const input=event.target;if(!input.classList.contains('plan-folder-rename'))return;
 if(event.key==='Escape'){event.preventDefault();state.planRename=null;$('#plan-case-list').innerHTML=planCaseTable(context().plan);return;}
 if(event.key!=='Enter')return;event.preventDefault();input.disabled=true;
 try{await api(`/api/folders/${input.dataset.id}`,'PATCH',{name:input.value});state.planRename=null;await refresh();toast('Folder renamed.');}
 catch(error){input.disabled=false;input.focus();toast(error.message,true);}
});
async function resolveImportConflicts(conflicts){
 const dialog=$('#import-conflict-dialog'),form=$('#import-conflict-form');
 let index=0;const decisions={};
 const render=()=>{
  const c=conflicts[index];
  $('#import-conflict-items').innerHTML=`<div class="conflict-case-name"><span>Test Case Name</span><strong data-no-translate>${escape(c.name)}</strong></div>${c.targets.length>1?`<label class="field"><span>Existing source version</span><select id="conflict-target">${c.targets.map(t=>`<option value="${escape(t.id)}" data-no-translate>${escape(t.source_version||'—')}</option>`).join('')}</select></label>`:''}<div class="conflict-actions"><button type="button" data-conflict-choice="overwrite">${c.same_version?'Overwrite':'Overwrite and update'}</button>${c.same_version?'':'<button type="button" data-conflict-choice="coexist">Keep both</button>'}<button type="button" data-conflict-choice="skip">Skip this Case</button><button type="button" data-action="cancel-import-conflicts">Cancel</button></div>${conflicts.length>1?`<p class="help">${index+1} / ${conflicts.length}</p>`:''}`;
 };
 render();dialog.showModal();form.querySelector('[data-conflict-choice]')?.focus();
 return new Promise(resolve=>{
  const finish=value=>{form.removeEventListener('click',choose);dialog.removeEventListener('close',cancel);dialog.close();resolve(value);};
  const cancel=()=>finish(null);
  const choose=event=>{
   const button=event.target.closest('[data-conflict-choice]');if(!button)return;event.preventDefault();event.stopPropagation();
   const c=conflicts[index],target=c.targets.find(t=>t.id===$('#conflict-target')?.value)||c.targets[0];
   decisions[c.id]={action:button.dataset.conflictChoice,target_id:target.id,target_token:target.token};
   if(++index===conflicts.length)finish(decisions);else{render();form.querySelector('[data-conflict-choice]')?.focus();}
  };
  form.addEventListener('click',choose);dialog.addEventListener('close',cancel);
 });
}
function resizeImportWorkspace(handle,value){
 const ratio=Math.max(25,Math.min(75,value)),layout=handle.closest('.plan-import-layout');
 state.importSplit=ratio;layout.style.setProperty('--import-left',ratio+'fr');layout.style.setProperty('--import-right',(100-ratio)+'fr');handle.setAttribute('aria-valuenow',String(Math.round(ratio)));
}
document.addEventListener('pointerdown',event=>{
 const handle=event.target.closest('.import-resizer');if(!handle||event.button!==0)return;
 event.preventDefault();handle.focus();handle.setPointerCapture(event.pointerId);const bounds=handle.parentElement.getBoundingClientRect();
 const move=e=>resizeImportWorkspace(handle,(e.clientX-bounds.left-6)/(bounds.width-12)*100);
 const finish=()=>{handle.removeEventListener('pointermove',move);handle.removeEventListener('lostpointercapture',finish);document.body.classList.remove('resizing-repository');};
 handle.addEventListener('pointermove',move);handle.addEventListener('lostpointercapture',finish);document.body.classList.add('resizing-repository');
});
document.addEventListener('keydown',event=>{
 const handle=event.target.closest('.import-resizer');if(!handle)return;
 const value=state.importSplit??50,next={ArrowLeft:value-2,ArrowRight:value+2,Home:25,End:75}[event.key];
 if(next!==undefined){event.preventDefault();resizeImportWorkspace(handle,next);}
});
async function importDroppedCases(plan,drag,id,insertion={}){
 const request={source_type:drag.source.type,source_plan_id:drag.source.planId,kind:drag.itemKind,id:drag.id,target_folder_id:id,...insertion,decisions:{}};
 while(context().plan?.id===plan.id){
  try{return await api(`/api/plans/${plan.id}/import-cases`,'POST',request);}
  catch(error){if(error.status!==409||!error.details?.conflicts)throw error;const decisions=await resolveImportConflicts(error.details.conflicts);if(!decisions)return null;Object.assign(request.decisions,decisions);}
 }
 return null;
}
$('#plan-import-form').addEventListener('submit',async event=>{
 event.preventDefault();event.stopPropagation();const submit=event.target.querySelector('[type=submit]');submit.disabled=true;
 const targetPlan=context().plan?.id;
 try{
  const value=$('#plan-import-source').value;let source;
  if(value==='repository'){
   const [cases,folders]=await Promise.all([api('/api/repository/testcases'),api('/api/repository/folders')]);
   source={type:'repository',label:'Test Case Repository',folders,cases:cases.map(c=>({...c,automation:c.metadata.automation}))};
  }else{
   await refresh(false);const id=value.slice(5),project=state.projects.find(p=>p.plans.some(x=>x.id===id)),plan=project?.plans.find(p=>p.id===id);
   if(!plan)throw Error('Source Plan not found');
   source={type:'plan',planId:id,label:project.name+' / '+plan.name,folders:plan.folders,cases:plan.testcases.filter(c=>c.script_kind==='single').map(c=>({...c,name:c.tc_name}))};
  }
  if(context().plan?.id!==targetPlan)return;
  if(!state.importSource)state.importSplit=50;state.importSource=source;state.importCollapsed=new Set();state.importSearch='';state.caseId=null;state.panel=null;$('#plan-import-dialog').close();await draw();
 }catch(error){$('#plan-import-error').textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('input',event=>{if(event.target.id==='import-source-search'){state.importSearch=event.target.value;$('#import-source-list').innerHTML=importSourceTable();}});
let planDrag=null,repositoryDrag=null;
const planTargets='[data-plan-folder],[data-plan-case]';
const repositoryTargets='[data-folder-node],[data-repository-id]';
function clearDrop(selector,finished=false){
 $$(selector).forEach(n=>{n.removeAttribute('data-drop');if(finished)n.removeAttribute('data-drop-allowed');});
}
function clearPlanDrop(finished=false){clearDrop(planTargets,finished);}
function clearRepositoryDrop(finished=false){clearDrop(repositoryTargets,finished);}
function descendant(folders,id,ancestor){
 const seen=new Set();
 while(id&&!seen.has(id)){if(id===ancestor)return true;seen.add(id);id=folders.find(f=>f.id===id)?.parent_id;}
 return false;
}
function dropMode(event,node,caseTarget,insideOnly){
 const rect=node.getBoundingClientRect(),fraction=(event.clientY-rect.top)/rect.height;
 return caseTarget?(fraction<.5?'before':'after'):insideOnly?'inside':fraction<.25?'before':fraction>.75?'after':'inside';
}
function planDestination(node,event){
 const {plan}=context(),drag=planDrag;if(!node||!plan||plan.locked||!drag||drag.planId!==plan.id)return null;
 const caseId=node.dataset.planCase,caseTarget=caseId!==undefined;
 if(caseTarget&&(drag.kind==='folder'||drag.kind==='import'&&drag.itemKind!=='case'||drag.kind==='case'&&drag.id===caseId))return null;
 const tc=caseTarget?plan.testcases.find(c=>c.id===caseId):null;
 const folderId=caseTarget?tc?.folder_id||null:node.dataset.planFolder||null;
 const mode=event?dropMode(event,node,caseTarget,drag.kind!=='folder'||!folderId):'inside';
 const parent=mode==='inside'||caseTarget?folderId:plan.folders.find(f=>f.id===folderId)?.parent_id;
 if(drag.kind==='folder'&&(drag.id===folderId||descendant(plan.folders,parent,drag.id)))return null;
 return {node,mode,folderId,caseId};
}
function repositoryDestination(node,event){
 const drag=repositoryDrag;if(!node||!drag)return null;
 const caseId=node.dataset.repositoryId,caseTarget=caseId!==undefined;
 const ids=drag.kind==='case'?[drag.id]:drag.case_ids||[],folders=drag.kind==='folder'?[drag.id]:drag.folder_ids||[];
 if(caseTarget&&(folders.length||ids.includes(caseId)))return null;
 const tc=caseTarget?state.repository.find(c=>c.id===caseId):null;
 const folder=state.repositoryFolders.find(f=>f.id===(caseTarget?tc?.folder_id:node.dataset.folderNode));if(!folder)return null;
 const mode=event?dropMode(event,node,caseTarget,drag.kind!=='folder'||folder.is_root):'inside';
 const parent=mode==='inside'||caseTarget?folder.id:folder.parent_id;
 if(folders.some(id=>id===folder.id||descendant(state.repositoryFolders,parent,id)))return null;
 return {node,mode,folder,caseId};
}
function markDestinations(selector,resolve){$$(selector).forEach(node=>{if(resolve(node))node.dataset.dropAllowed='true';});}
document.addEventListener('dragstart',event=>{
 const inPlan=document.body.classList.contains('plan-workspace');
 if(inPlan){
  if(context().plan?.locked||state.importBusy)return;
  const source=event.target.closest('[data-import-kind][draggable="true"]');
  if(source&&state.importSource){planDrag={kind:'import',itemKind:source.dataset.importKind,id:source.dataset.importId,source:state.importSource,planId:context().plan.id};}
  else{
   const row=event.target.closest('[data-plan-case][draggable="true"]'),folder=event.target.closest('[data-plan-folder][draggable="true"]');
   if(!row&&!folder)return;if(!discard()){event.preventDefault();return;}state.dirty=false;
   planDrag={kind:row?'case':'folder',id:row?.dataset.planCase||folder.dataset.planFolder,planId:context().plan.id};
  }
  event.dataTransfer.effectAllowed=planDrag.kind==='import'?'copy':'move';
  event.dataTransfer.setData('text/plain',JSON.stringify({kind:planDrag.kind,id:planDrag.id}));
  markDestinations(planTargets,planDestination);
 }else if(document.body.classList.contains('repository-page')){
  const row=event.target.closest('[data-repository-id][draggable="true"]'),folder=event.target.closest('[data-folder-node][draggable="true"]');
  if(!row&&!folder)return;
  const kind=row?'case':'folder',id=row?.dataset.repositoryId||folder.dataset.folderNode;
  repositoryDrag=state.repositoryBatch&&state.repositorySelection?.has(kind+':'+id)?{kind:'batch',...repositorySelectionData()}:{kind,id};
  // Batch case order follows the displayed order, not checkbox click order.
  if(repositoryDrag.case_ids)repositoryDrag.case_ids=state.repository.filter(c=>repositoryDrag.case_ids.includes(c.id)).map(c=>c.id);
  event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',JSON.stringify(repositoryDrag));
  markDestinations(repositoryTargets,repositoryDestination);
 }
});
function updateDropTarget(event){
 if(planDrag){
  clearPlanDrop();const dest=event.target.closest('.import-source-pane')?null:planDestination(event.target.closest(planTargets),event);
  if(!dest){event.dataTransfer.dropEffect='none';return;}
  event.preventDefault();event.dataTransfer.dropEffect=planDrag.kind==='import'?'copy':'move';dest.node.dataset.drop=dest.mode;
 }else if(repositoryDrag){
  clearRepositoryDrop();const dest=repositoryDestination(event.target.closest(repositoryTargets),event);
  if(!dest){event.dataTransfer.dropEffect='none';return;}
  event.preventDefault();event.dataTransfer.dropEffect='move';dest.node.dataset.drop=dest.mode;
 }
}
document.addEventListener('dragenter',updateDropTarget);
document.addEventListener('dragover',updateDropTarget);
document.addEventListener('dragleave',event=>{
 const node=event.target.closest('[data-drop]');if(node&&!node.contains(event.relatedTarget))node.removeAttribute('data-drop');
});
document.addEventListener('drop',async event=>{
 if(planDrag){
  event.preventDefault();const dest=event.target.closest('.import-source-pane')?null:planDestination(event.target.closest(planTargets),event),drag=planDrag;
  planDrag=null;clearPlanDrop(true);if(!dest)return;
  const {plan}=context(),{folderId,caseId,mode}=dest;
  const insertion=caseId?{relative_to:caseId,insertion:mode}:{};
  try{
   if(drag.kind==='import'){
    if(state.importBusy)return;state.importBusy=true;
    try{const result=await importDroppedCases(plan,drag,folderId,insertion);if(!result)return;state.planCollapsed?.delete(folderId);await refresh();toast(`Imported: ${result.added.length}; updated: ${result.updated.length}; skipped: ${result.skipped.length}.`);}
    finally{state.importBusy=false;}return;
   }
   if(drag.kind==='case')await api(`/api/plans/${plan.id}/testcases/move`,'POST',{testcase_ids:[drag.id],folder_id:folderId,...insertion});
   else{const target=plan.folders.find(f=>f.id===folderId);await api(`/api/folders/${drag.id}`,'PATCH',mode==='inside'?{parent_id:folderId}:{parent_id:target.parent_id,relative_to:folderId,insertion:mode});}
   state.planCollapsed?.delete(folderId);await refresh();toast(drag.kind==='case'?'Test Case moved.':'Folder moved.');
  }catch(error){toast(error.message,true);}
 }else if(repositoryDrag){
  event.preventDefault();const dest=repositoryDestination(event.target.closest(repositoryTargets),event),drag=repositoryDrag;
  repositoryDrag=null;clearRepositoryDrop(true);if(!dest)return;
  const {folder,caseId,mode}=dest,insertion=caseId?{relative_to:caseId,insertion:mode}:{};
  try{
   if(drag.kind==='batch'){await api('/api/repository/batch','POST',{...drag,action:'move',folder_id:folder.id,...insertion});state.repositorySelection.clear();}
   else if(drag.kind==='case')await api(`/api/repository/testcases/${drag.id}/folder`,'PUT',{folder_id:folder.id,...insertion});
   else await api(`/api/repository/folders/${drag.id}`,'PATCH',mode==='inside'?{parent_id:folder.id}:{parent_id:folder.parent_id,relative_to:folder.id,insertion:mode});
   state.repositoryCollapsed?.delete(folder.id);await draw();toast(drag.kind==='case'?'Test Case moved.':'Folder moved.');
  }catch(error){toast(error.message,true);}
 }
});
document.addEventListener('dragend',()=>{planDrag=null;repositoryDrag=null;clearPlanDrop(true);clearRepositoryDrop(true);});

$('#repository-create-folder-dialog').addEventListener('cancel',event=>{if(state.repositoryCreatingFolder)event.preventDefault();else state.dirty=false;});
$('#repository-file-picker').addEventListener('change',async event=>{
  const picker=event.target,file=picker.files[0],folder=picker.dataset.folderId,planId=picker.dataset.planId;
  if(!file||state.repositoryImporting)return;
  state.repositoryImporting=true;
  try{
    if(!file.name.toLowerCase().endsWith('.py'))throw Error('Choose a .py file.');
    await api(planId?`/api/plans/${planId}/testcases/import-python`:'/api/repository/testcases','POST',{source:await file.text(),folder_id:folder||null});
    if(planId){state.planCollapsed?.delete(folder);await refresh();toast('Test Case added.');return;}
    state.repositoryCollapsed?.delete(folder);state.repositoryFolder=folder;
    if(state.route[0]==='repository')await draw();
    toast('Standard Test Case imported with a new source timestamp.');
  }catch(error){toast(error.message,true);}
  finally{state.repositoryImporting=false;picker.value='';}
});
$('#plan-create-dialog').addEventListener('cancel',event=>{if(state.creatingPlan)event.preventDefault();else state.dirty=false;});
window.addEventListener('hashchange',()=>navigate().catch(e=>toast(e.message,true)));
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});
sizeGlobalNavigation();
$('#theme-toggle').innerHTML=icon('sun');
function theme(value){document.documentElement.dataset.theme=value;localStorage.setItem('bmc-theme',value);$('#theme-toggle').setAttribute('aria-label',`Switch to ${value==='dark'?'light':'dark'} theme`);}
theme(localStorage.getItem('bmc-theme')||'light');$('#theme-toggle').onclick=()=>theme(document.documentElement.dataset.theme==='dark'?'light':'dark');
refresh(false).then(navigate).catch(e=>{$('#workspace').setAttribute('aria-busy','false');$('#workspace').innerHTML=empty('Unable to load BMC Agent',e.message,button('Retry','retry','primary'));toast(e.message,true);});
document.addEventListener('click',event=>{if(event.target.closest('[data-action=retry]'))refresh(false).then(navigate).catch(e=>toast(e.message,true));});
})();
