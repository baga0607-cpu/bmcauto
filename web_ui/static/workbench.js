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
 const label=({automatic:'Fully automatic — runs without operator intervention',semi_automatic:'Semi-automatic — parameters or operator answers required',manual:'Fully manual — workflow not yet defined'})[value]||'Unclassified';
 const shape=value==='automatic'?'<path d="M9 3h6l.5 3 2.5 1.5 2.8-1 3 5.2-2.3 2v2.6l2.3 2-3 5.2-2.8-1-2.5 1.5-.5 3H9l-.5-3L6 22.5l-2.8 1-3-5.2 2.3-2v-2.6l-2.3-2 3-5.2 2.8 1L8.5 6z" transform="translate(2 0) scale(.83)"/><circle cx="12" cy="12" r="3"/>':value==='semi_automatic'?'<path d="M14.7 6.3a5.5 5.5 0 0 0-7 7L2.8 18.2a2.1 2.1 0 0 0 3 3l4.9-4.9a5.5 5.5 0 0 0 7-7l-3.5 3.5-3-3z"/>':value==='manual'?'<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>':'<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 5m0 3h.01"/>';
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
  if(state.route[0]==='execution'||project&&state.route[2]==='execution'){const view=executionView(),task=view.task?.id===view.active?view.task:null,owner=state.projects.find(p=>p.plans.some(plan=>plan.id===task?.plan_id));return {project:owner||project,task,plan:owner?.plans.find(p=>p.id===task?.plan_id)};}
  const plan = project?.plans.find(p=>p.id===(['plans','test-plans'].includes(state.route[2])?activePlanFor(project):state.route[3]));
  const task = plan?.tasks.find(t=>t.id===state.route[5]);
  return {project,plan,task};
}
function taskFormContext(){
  const current=context();
  if(state.route[0]!=='tasks'||state.route[1]!=='info')return current;
  for(const project of state.projects)for(const plan of project.plans){
    const task=plan.tasks.find(t=>t.id===state.route[2]);if(task)return {project,plan,task};
  }
  return current;
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
  if([base,...['info','plans','execution','test-plans','reports','bugs'].map(section=>base+'/'+section)].includes(savedRoute))return savedRoute;
  if(project.plans.some(plan=>path(project,plan)===savedRoute))return savedRoute;
  // A removed Plan should return to the surviving Project's Plan list.
  return savedRoute?.startsWith(base+'/plan/')?base+'/plans':base;
}
function drawTree() {
  const {project,plan,task}=context();
  if(project){
    localStorage.setItem('bmc-last-project',project.id);
    if(!task)localStorage.setItem('bmc-last-project-route',plan&&!['plans','test-plans'].includes(state.route[2])?path(project,plan):path(project)+'/'+(state.route[2]||'info'));
  }
  const selected=project||state.projects.find(p=>p.id===localStorage.getItem('bmc-last-project'))||state.projects[0];
  const section=state.route[2]==='execution'?'execution':task?'execution':plan||state.route[2]==='test-plans'?'plans':state.route[2]||'info';
  const navigationIcons={"Dashboard":"M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z","Schedule":"M4 5h16v16H4z M4 10h16 M8 3v4 M16 3v4 M8 14h3 M14 17h3","Task":"M8 4h12v17H4V4h4 M8 2h8v4H8z M8 12l2 2 5-5","Project:":"M3 7h7l2 2h9v11H3z M3 7V4h7l2 3 M7 13h4 M7 16h8","Plan":"M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h5","Execution":"M6 3v18l14-9z","Report":"M4 3h16v18H4z M8 17v-4 M12 17V9 M16 17v-7","bug":"M8 8h8v8a4 4 0 0 1-8 0z M9 8V5h6v3 M4 10h4 M16 10h4 M3 15h5 M16 15h5 M5 21l4-3 M19 21l-4-3","Case Repository":"M3 4h18v4H3z M5 8v13h14V8 M9 12h6 M9 16h6"};
  const navLink=(href,label,current=false)=>`<a href="${href}" aria-label="${escape(label)}" title="${escape(label)}" ${current?'aria-current="page"':''}><span class="sidebar-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="${navigationIcons[label]}"/></svg></span><span class="sidebar-label">${label}</span></a>`;
  const projectLinks=selected?`<div class="sidebar-project-heading">${navLink(path(selected)+'/info','Project:',Boolean(project&&section==='info'))}<div class="project-picker"><input id="project-search" type="text" role="combobox" aria-expanded="false" aria-controls="project-options" aria-autocomplete="list" value="${escape(selected.name)}" data-selected-name="${escape(selected.name)}" placeholder="Search Projects" aria-label="Search Projects" autocomplete="off"><div class="project-picker-menu" hidden><div id="project-options" class="project-options" role="listbox">${state.projects.map(p=>button(escape(p.name),'choose-project','',`data-project-id="${escape(p.id)}" data-project-name="${escape(p.name.toLowerCase())}" data-no-translate role="option" aria-selected="${p.id===selected.id}"`)).join('')}</div><p id="project-search-empty" class="help" hidden>No matching Projects</p></div></div></div>${[['plans','Plan'],['execution','Execution'],['reports','Report'],['bugs','bug']].map(([id,label])=>navLink(id==='execution'?'#/execution':path(selected)+'/'+id,label,Boolean(id==='execution'?state.route[0]==='execution':project&&section===id))).join('')}`:'<p class="help">Create a Project to get started.</p>';
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
  const style={PASS:'passed',CP:'cp',FAIL:'failed',Block:'blocked',NR:'tbd',Running:'running'}[value];
  return `<span class="status ${style}">${value}</span>`;
}
function sizePlanColumns() {
  const table=$('.plan-overview'),cell=table?.querySelector('thead th:nth-child(2)');
  if(!cell)return;
  const style=getComputedStyle(cell),canvas=document.createElement('canvas'),measure=canvas.getContext('2d');
  measure.font=`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
  const labels=['Total Cases','Completion','PASS','CP','FAIL','Block','Not Run','Task','測項總數','完成度'];
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
function planList(project, readOnly=false) {
  const rows=project.plans.map(plan=>{
    const summary=PlanMatrix.summarize(plan),expanded=state.expandedPlans?.has(plan.id),matrixId='matrix-'+plan.id;
    const matrix=`<div class="table-wrap plan-matrix" id="${escape(matrixId)}"><table aria-label="${escape(plan.name)} Matrix"><thead><tr><th scope="col">Case</th>${plan.tasks.map(task=>`<th scope="col"><a href="${path(project,plan,task)}">${escape(task.name)}</a></th>`).join('')}<th scope="col">Final</th></tr></thead><tbody>${summary.rows.map(row=>`<tr><th scope="row">${escape(row.name)}</th>${row.cells.map(cell=>`<td>${matrixStatus(cell)}</td>`).join('')}<td>${matrixStatus(row.final)}</td></tr>`).join('')||`<tr><td colspan="${plan.tasks.length+2}">No Test Cases</td></tr>`}</tbody></table></div>`;
    return `<tr><td><a href="${path(project,plan)}">${escape(plan.name)}</a></td><td>${summary.total}</td><td>${summary.completed}/${summary.total}</td><td>${summary.counts.PASS}</td><td>${summary.counts.CP}</td><td>${summary.counts.FAIL}</td><td>${summary.counts.Block}</td><td>${summary.counts.NR}</td><td>${button(String(plan.tasks.length),'toggle-plan-matrix','small-button matrix-toggle',`data-id="${escape(plan.id)}" aria-label="${escape(plan.name)} Task Matrix" aria-expanded="${Boolean(expanded)}" aria-controls="${escape(matrixId)}"`)}</td></tr><tr ${expanded?'':'hidden'} class="matrix-row"><td colspan="9">${matrix}</td></tr>`;
  }).join('');
  return `<div class="table-wrap plan-overview"><table><thead><tr><th>Plan</th><th>Total Cases</th><th>Completion</th><th>PASS</th><th>CP</th><th>FAIL</th><th>Block</th><th>Not Run</th><th data-no-translate>Task</th></tr></thead><tbody>${rows}${!rows?'<tr><td colspan="9">No Test Plans</td></tr>':''}</tbody></table></div>${readOnly?'':`<div class="plan-list-footer">${button('Create','new-plan','primary')}</div>`}`;
}
function planTabIds(project){
 state.planTabOrders??={};
 if(!state.planTabOrders[project.id]){
   let saved=[];try{saved=JSON.parse(localStorage.getItem('bmc-plan-tabs-'+project.id)||'[]');}catch{}
   state.planTabOrders[project.id]=Array.isArray(saved)?[...new Set(saved.filter(id=>typeof id==='string'))]:[];
 }
 const ids=state.planTabOrders[project.id].filter(id=>project.plans.some(p=>p.id===id));
 for(const plan of project.plans)if(!ids.includes(plan.id))ids.push(plan.id);
 return state.planTabOrders[project.id]=ids;
}
function selectPlanFor(project,id){
 state.activePlanTabs??={};state.activePlanTabs[project.id]=id;state.inlinePlanId=id;
 try{if(id)localStorage.setItem('bmc-plan-active-v1:'+project.id,id);else localStorage.removeItem('bmc-plan-active-v1:'+project.id);}
 catch{toast('Unable to save the selected Plan tab. Check browser storage settings.',true);}
}
function activePlanFor(project){
 if(!project)return null;
 state.activePlanTabs??={};
 if(!Object.prototype.hasOwnProperty.call(state.activePlanTabs,project.id)){
   let saved=null;try{saved=localStorage.getItem('bmc-plan-active-v1:'+project.id);}catch{}
   state.activePlanTabs[project.id]=saved;
 }
 const ids=planTabIds(project);let selected=state.activePlanTabs[project.id];
 if(!ids.includes(selected)){selected=ids[0]||null;selectPlanFor(project,selected);}
 state.inlinePlanId=selected;return selected;
}
async function planEditorList(project){
 const ids=planTabIds(project),active=activePlanFor(project),plan=project.plans.find(p=>p.id===active);
 const tabs='<div class="tabs plan-tabs" role="tablist" aria-label="Plans">'+ids.map(id=>{
   const item=project.plans.find(p=>p.id===id);
   return button(escape(item.name),'select-plan-tab','','role="tab" id="plan-tab-'+escape(id)+'" aria-selected="'+(active===id)+'" aria-controls="plan-tab-panel" draggable="true" data-plan-tab="'+escape(id)+'" data-id="'+escape(id)+'" data-no-translate');
 }).join('')+button('Add Plan','new-plan','','id="plan-tab-add" aria-haspopup="dialog"')+'</div>';

 return '<div class="plan-tabs-heading">'+heading('Plan',project.name)+tabs+'</div><section id="plan-tab-panel" '+(plan?'role="tabpanel" aria-labelledby="plan-tab-'+escape(plan.id)+'"':'aria-label="Plan workspace"')+'>'+(plan?'<div class="plan-inline-editor">'+await planPage(project,plan,true)+'</div>':empty('No Test Plans','Use Add Plan to create a Plan.'))+'</section>';
}
function reportPage(project){
  state.reportExpanded??=new Set();state.reportMatrices??=new Set();
  if(state.reportSelection?.projectId!==project.id)state.reportSelection={projectId:project.id,plans:new Set(),tasks:new Set()};
  const choice=state.reportSelection,selecting=Boolean(state.reportSelecting),busy=Boolean(state.reportBusy);
  const selected=choice.plans.size+choice.tasks.size;
  const check=(kind,plan,task=null)=>{
    if(!selecting)return '';
    const checked=kind==='plan'?choice.plans.has(plan.id):choice.plans.has(plan.id)||choice.tasks.has(task.id);
    const disabled=busy||(kind==='plan'?plan.locked:task.execution_active||choice.plans.has(plan.id));
    return `<input type="checkbox" data-report-select="${kind}" data-plan-id="${escape(plan.id)}" ${task?`data-task-id="${escape(task.id)}"`:''} aria-label="${escape((task?.name||plan.name)+' '+(task?'Task Report':'Final Report'))}" ${checked?'checked':''} ${disabled?'disabled':''}>`;
  };
  const numbers=(summary,count)=>`<td>${summary.total}</td><td>${summary.completed}/${summary.total}</td><td>${summary.counts.PASS}</td><td>${summary.counts.CP}</td><td>${summary.counts.FAIL}</td><td>${summary.counts.Block}</td><td>${summary.counts.NR}</td><td>${count}</td>`;
  const rows=project.plans.map(plan=>{
    const expanded=state.reportExpanded.has(plan.id),summary=PlanMatrix.summarize(plan),children='report-plan-'+plan.id;
    const matrix=state.reportMatrices.has(plan.id)?`<tr class="report-matrix-row"><td colspan="9"><div class="table-wrap plan-matrix"><table><thead><tr><th>Case</th>${plan.tasks.map(t=>`<th><a href="${TaskManagement.infoLink(t)}">${escape(t.name)}</a></th>`).join('')}<th>Final</th></tr></thead><tbody>${summary.rows.map(row=>`<tr><th scope="row">${escape(row.name)}</th>${row.cells.map(cell=>`<td>${matrixStatus(cell)}</td>`).join('')}<td>${matrixStatus(row.final)}</td></tr>`).join('')||`<tr><td colspan="${plan.tasks.length+2}">No Test Cases</td></tr>`}</tbody></table></div></td></tr>`:'';
    const taskRows=plan.tasks.map(task=>{
      const ids=new Set(task.testcases.map(c=>c.id)),taskSummary=PlanMatrix.summarize({...plan,testcases:plan.testcases.filter(c=>ids.has(c.id)),tasks:[task]});
      return `<tr class="report-task-row"><td><div class="report-task-label">${check('task',plan,task)}<a href="${TaskManagement.infoLink(task)}" data-no-translate>${escape(task.name)}</a></div></td>${numbers(taskSummary,'—')}</tr>`;
    }).join('')||'<tr><td colspan="9" class="help">No Tasks yet</td></tr>';
    return `<tbody><tr class="report-plan-row"><td><div class="report-plan-label">${check('plan',plan)}<button type="button" class="report-plan-toggle" data-action="report-plan-toggle" data-id="${escape(plan.id)}" aria-expanded="${expanded}" aria-controls="${escape(children)}" ${busy?'disabled':''}><span class="report-chevron ${expanded?'is-open':''}">${icon('chevron')}</span><span data-no-translate>${escape(plan.name)}</span></button></div></td>${numbers(summary,button(String(plan.tasks.length),'report-matrix','small-button',`data-id="${escape(plan.id)}" aria-label="${escape(plan.name)} Task Matrix" aria-expanded="${state.reportMatrices.has(plan.id)}" ${busy?'disabled':''}`))}</tr></tbody><tbody id="${escape(children)}" ${expanded?'':'hidden'}>${taskRows}${matrix}</tbody>`;
  }).join('');
  return `<section class="report-workspace" aria-label="Report"><div class="toolbar"><div class="actions">${button(selecting?'Cancel selection':'Select Report','report-select','',busy?'disabled':'')}${selecting?button(busy?'Generating report…':'Generate Report','report-generate','primary',!selected||busy?'disabled':''):''}</div>${selecting?'<span class="help">Select Plans or Tasks, then arrange formal and reference reports.</span>':''}</div><div class="table-wrap plan-overview report-overview"><table><thead><tr><th>Plan / Task</th><th>Total Cases</th><th>Completion</th><th>PASS</th><th>CP</th><th>FAIL</th><th>Block</th><th>Not Run</th><th>Task</th></tr></thead>${rows||'<tbody><tr><td colspan="9">No Test Plans</td></tr></tbody>'}</table></div></section>`;
}
function bindReportSelection(){
  const choice=state.reportSelection;if(!choice)return;
  const {project}=context();
  for(const input of $$('[data-report-select="plan"]')){
    const plan=project?.plans.find(p=>p.id===input.dataset.planId);
    input.indeterminate=!choice.plans.has(input.dataset.planId)&&Boolean(plan?.tasks.some(t=>choice.tasks.has(t.id)));
  }
}
function openReportComposer(project){
  const choice=state.reportSelection;if(!choice)return;
  const items=[];
  for(const plan of project.plans){
    if(choice.plans.has(plan.id))items.push({kind:'plan',id:plan.id,name:plan.name,detail:'All Tasks'});
    else for(const task of plan.tasks)if(choice.tasks.has(task.id))items.push({kind:'task',id:task.id,name:task.name,detail:plan.name});
  }
  if(!items.length)return;
  state.reportDraft={projectId:project.id,report:items,reference:[]};state.reportError='';
  renderReportComposer();$('#report-compose-dialog').showModal();
}
function renderReportComposer(focusKey=null){
  const draft=state.reportDraft;if(!draft)return;
  const busy=Boolean(state.reportBusy);
  for(const area of ['report','reference']){
    const list=$('#'+area+'-area');
    list.innerHTML=draft[area].map((item,index)=>{
      const key=item.kind+':'+item.id;
      const control=(label,action,disabled,content=label,kind='small-button')=>'<button type="button" class="'+kind+'" data-report-move="'+action+'" title="'+label+'" aria-label="'+label+'" '+(busy||disabled?'disabled':'')+'>'+content+'</button>';
      return '<li class="report-compose-item" draggable="'+!busy+'" data-report-item="'+escape(key)+'" data-area="'+area+'"><span class="report-drag-handle" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="5" r="1.5"/><circle cx="15" cy="5" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="19" r="1.5"/><circle cx="15" cy="19" r="1.5"/></svg></span><span class="report-compose-name"><strong data-no-translate>'+escape(item.name)+'</strong><span class="help" '+(item.kind==='task'?'data-no-translate':'')+'>'+escape(item.detail)+'</span></span><div class="report-item-controls">'+control('Move up','up',index===0,icon('chevron'),'small-button icon-button report-order-up')+control('Move down','down',index===draft[area].length-1,icon('chevron'),'small-button icon-button report-order-down')+control(area==='report'?'Move to Reference Area':'Move to Report Area','area',false)+'</div></li>';
    }).join('')||'<li class="report-area-empty">Drag reports here</li>';
    list.setAttribute('aria-busy',String(busy));
  }
  $('#report-compose-generate').disabled=busy||!draft.report.length;
  $('#report-compose-cancel').disabled=busy;
  $('#report-compose-error').textContent=state.reportError||(!draft.report.length?'Keep at least one report in Report Area.':'');
  $('#report-compose-status').textContent=busy?'Generating report…':'';
  if(focusKey){const row=$$('[data-report-item]').find(e=>e.dataset.reportItem===focusKey);row?.querySelector('[data-report-move=area]')?.focus();}
}
function moveReportItem(key,area,index){
  const draft=state.reportDraft;if(!draft||state.reportBusy)return;
  let item;
  for(const source of ['report','reference']){
    const from=draft[source].findIndex(i=>i.kind+':'+i.id===key);
    if(from>=0){[item]=draft[source].splice(from,1);if(source===area&&from<index)index--;break;}
  }
  if(!item)return;
  draft[area].splice(Math.max(0,Math.min(index,draft[area].length)),0,item);
  state.reportError='';renderReportComposer(key);
}
async function generateReportSelection(){
  const draft=state.reportDraft;if(!draft?.report.length||state.reportBusy)return;
  const entries=area=>draft[area].map(({kind,id})=>({kind,id}));
  const payload={report_area:entries('report'),reference_area:entries('reference')};
  state.reportBusy=true;state.reportError='';renderReportComposer();await draw();
  try{
    const response=await fetch('/api/projects/'+encodeURIComponent(draft.projectId)+'/reports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok){const error=await response.json().catch(()=>({}));throw Error(error.error||'Report generation failed.');}
    const blob=await response.blob(),disposition=response.headers.get('Content-Disposition')||'';
    const encoded=disposition.match(/filename\*=UTF-8''([^;]+)/i),plain=disposition.match(/filename="?([^";]+)/i);
    const filename=encoded?decodeURIComponent(encoded[1]):plain?plain[1]:'BMC_Report.pdf';
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('#report-compose-dialog').close();toast('Report generated.');
  }catch(error){state.reportError=error.message;}finally{state.reportBusy=false;renderReportComposer();await draw();}
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
function tasksTable(project, plan, report=false) { return plan.tasks.length?`<div class="table-wrap"><table><thead><tr><th>Task</th><th>Scope</th><th>Current results</th><th>${report?'Report':'Action'}</th></tr></thead><tbody>${plan.tasks.map(task=>`<tr><td><a href="${path(project,plan,task)}">${escape(task.name)}</a>${task.execution_active?'<p class="help">Execution active</p>':''}</td><td>${task.testcases.length} Test Cases</td><td>${task.counts.Passed} passed · ${task.counts.CP||0} CP · ${task.counts.Failed} failed${task.testcases.some(c=>c.needs_retest)?'<p class="help">Plan changed — rerun needed</p>':''}</td><td>${report?button('Generate report','report','small-button',`data-id="${escape(task.id)}" ${task.execution_active?'disabled':''}`):`<a href="${path(project,plan,task)}">Open Task</a>`}</td></tr>`).join('')}</tbody></table></div>`:empty('No Tasks yet','When the Plan is ready, create a Task and choose its Test Cases.',report?'':button('New Task','new-task','primary',plan.locked?'disabled':'')); }
function listSelectionItems(type){
 const plan=context().plan,source=state.importSource;
 if(type==='plan')return [...(plan?.folders||[]).map(f=>({kind:'folder',id:f.id})),...(plan?.testcases||[]).map(c=>({kind:'case',id:c.id}))];
 if(type==='repository')return [...state.repositoryFolders.filter(f=>!f.is_root).map(f=>({kind:'folder',id:f.id})),...state.repository.map(c=>({kind:'case',id:c.id}))];
 return [...(source?.folders||[]).filter(f=>!f.is_root).map(f=>({kind:'folder',id:f.id})),...(source?.cases||[]).map(c=>({kind:'case',id:c.id}))];
}
function itemIsSelected(type,item){
 if(type==='plan')return planSelection().has(item.kind+':'+item.id);
 if(type==='repository')return state.repositorySelection?.has(item.kind+':'+item.id)||false;
 return (item.kind==='folder'?state.importFolderSelection:state.importSelection)?.has(item.id)||false;
}
function setItemSelection(type,item,selected){
 let set,key=item.kind+':'+item.id;
 if(type==='plan')set=planSelection();
 else if(type==='repository')set=state.repositorySelection??=new Set();
 else{key=item.id;set=item.kind==='folder'?(state.importFolderSelection??=new Set()):(state.importSelection??=new Set());}
 selected?set.add(key):set.delete(key);
}
function selectionTree(type){
 const plan=context().plan,source=state.importSource;
 return type==='plan'?{folders:plan?.folders||[],cases:plan?.testcases||[]}:type==='repository'?{folders:state.repositoryFolders,cases:state.repository}:{folders:source?.folders||[],cases:source?.cases||[]};
}
function changeItemSelection(type,item,selected){
 if(item.kind!=='folder'){setItemSelection(type,item,selected);return;}
 const tree=selectionTree(type),covered=new Set([item.id]);let changed=true;
 while(changed){changed=false;for(const folder of tree.folders)if(covered.has(folder.parent_id)&&!covered.has(folder.id)){covered.add(folder.id);changed=true;}}
 for(const folder of tree.folders)if(covered.has(folder.id)&&!folder.is_root)setItemSelection(type,{kind:'folder',id:folder.id},selected);
 for(const c of tree.cases)if(covered.has(c.folder_id))setItemSelection(type,{kind:'case',id:c.id},selected);
}
function normalizeFolderSelection(type){
 const tree=selectionTree(type),states=new Map(),visiting=new Set();
 function visit(folder){
   if(states.has(folder.id))return states.get(folder.id);
   if(visiting.has(folder.id))return {checked:false,mixed:false,any:false};visiting.add(folder.id);
   const children=tree.folders.filter(f=>f.parent_id===folder.id).map(visit);
   const ownCases=tree.cases.filter(c=>c.folder_id===folder.id).map(c=>itemIsSelected(type,{kind:'case',id:c.id}));
   const count=children.length+ownCases.length;
   const checked=count?children.every(c=>c.checked)&&ownCases.every(Boolean):!folder.is_root&&itemIsSelected(type,{kind:'folder',id:folder.id});
   const any=children.some(c=>c.any)||ownCases.some(Boolean)||(!count&&checked),state={checked,mixed:any&&!checked,any};
   if(!folder.is_root)setItemSelection(type,{kind:'folder',id:folder.id},checked);
   states.set(folder.id,state);visiting.delete(folder.id);return state;
 }
 for(const folder of tree.folders)visit(folder);
 return states;
}
function listSelectAll(type){return '<input type="checkbox" class="case-select-all" data-list-select-all="'+type+'" aria-label="Select all folders and Test Cases" title="Select all folders and Test Cases">';}
function syncCaseSelections(){
 const folderStates={};for(const type of new Set($$('[data-list-select-all]').map(el=>el.dataset.listSelectAll)))folderStates[type]=normalizeFolderSelection(type);
 for(const header of $$('[data-list-select-all]')){
   const type=header.dataset.listSelectAll,items=listSelectionItems(type),count=items.filter(item=>itemIsSelected(type,item)).length;
   header.checked=items.length>0&&count===items.length;header.indeterminate=count>0&&count<items.length;header.disabled=!items.length;header.setAttribute('aria-checked',header.indeterminate?'mixed':String(header.checked));
 }
 const update=(input,type,kind,id)=>{
   const state=kind==='folder'?folderStates[type]?.get(id):null;
   input.checked=state?state.checked:itemIsSelected(type,{kind,id});input.indeterminate=state?.mixed||false;input.setAttribute('aria-checked',input.indeterminate?'mixed':String(input.checked));
 };
 for(const input of $$('.plan-selection-check'))update(input,'plan',input.dataset.kind,input.dataset.id);
 for(const input of $$('.repository-batch-check'))update(input,'repository',input.dataset.kind,input.dataset.id);
 for(const input of $$('[data-import-select]'))update(input,'import','case',input.dataset.importSelect);
 for(const input of $$('[data-import-folder-select]'))update(input,'import','folder',input.dataset.importFolderSelect);
 for(const input of $$('[data-selection-root]')){
   const type=input.dataset.selectionRoot,items=listSelectionItems(type),count=items.filter(item=>itemIsSelected(type,item)).length;
   input.checked=items.length>0&&count===items.length;input.indeterminate=count>0&&count<items.length;input.setAttribute('aria-checked',input.indeterminate?'mixed':String(input.checked));
 }
 if(document.body.classList.contains('repository-page')){
   const controls=$('.repository-page-controls');let del=$('[data-action=repository-batch-delete]');
   if(state.repositorySelection?.size&&!del)controls?.insertAdjacentHTML('beforeend',button('Delete selected','repository-batch-delete','danger'));
   else if(!state.repositorySelection?.size)del?.remove();
 }
}
function folderExpansionScope(type){
 return type==='plan'?'plan:'+context().plan.id:type==='repository'?'repository':'import:'+(state.importSource.type==='plan'?'plan:'+state.importSource.planId:'repository');
}
function savedFolderCollapse(scope,folders){
 state.folderCollapseCache??={};
 if(!state.folderCollapseCache[scope]){
   let saved=[];try{saved=JSON.parse(localStorage.getItem('bmc-folder-collapse-v1:'+scope)||'[]');}catch{}
   state.folderCollapseCache[scope]=new Set(Array.isArray(saved)?saved.filter(id=>typeof id==='string'):[]);
 }
 const collapsed=state.folderCollapseCache[scope];
 for(const id of collapsed)if(!folders.some(folder=>folder.id===id))collapsed.delete(id);
 return collapsed;
}
function saveFolderExpansions(){
 try{for(const [scope,collapsed] of Object.entries(state.folderCollapseCache||{}))localStorage.setItem('bmc-folder-collapse-v1:'+scope,JSON.stringify([...collapsed]));}
 catch{toast('Unable to save folder expansion state. Check browser storage settings.',true);}
}
function planSelection(){
 const id=context().plan?.id;state.planSelections??={};return state.planSelections[id]??=new Set();
}
function planCheck(kind,id){return '<input type="checkbox" class="plan-selection-check" data-kind="'+kind+'" data-id="'+escape(id)+'" aria-label="Select '+kind+'" '+(planSelection().has(kind+':'+id)?'checked':'')+'>';}
function planSelectionData(){const folder_ids=[],case_ids=[];for(const item of planSelection()){const at=item.indexOf(':'),kind=item.slice(0,at),id=item.slice(at+1);(kind==='folder'?folder_ids:case_ids).push(id);}return {folder_ids,case_ids};}
function planCaseTable(plan) {
  const importing=Boolean(state.importSource);
  const chosen=planSelection();for(const key of chosen){const at=key.indexOf(':'),id=key.slice(at+1);if(key.startsWith('case:')?!plan.testcases.some(c=>c.id===id):!plan.folders.some(f=>f.id===id))chosen.delete(key);}
  const query=(state.planSearch||'').trim().toLowerCase(),collapsed=state.planCollapsed=savedFolderCollapse('plan:'+plan.id,plan.folders);
  const action=(label,type,id,shape,disabled=false)=>button(icon(shape),type,'small-button icon-button'+(shape==='trash'?' danger':''),`data-id="${escape(id||'')}" title="${label}" aria-label="${label}" ${disabled?'disabled':''}`);
  const cases=(folder,depth,match)=>plan.testcases.filter(c=>(c.folder_id||null)===folder&&(match||!query||KeywordSearch.matches(c.tc_name,query))).map(c=>`<tr tabindex="0" aria-haspopup="menu" title="Right-click for actions" data-plan-case="${escape(c.id)}" draggable="${!plan.locked}" style="--depth:${depth}"><td><div class="case-selection-label">${planCheck('case',c.id)}<strong>${automation(c.automation)}${escape(c.tc_name)}</strong></div><p class="help case-source-version" data-no-translate>${escape(version(c.source_created_at))}</p></td>${importing?'':`<td>${c.parameter_count>0?button('Parameters','plan-case-parameters','small-button '+(c.parameters_complete===false?'primary case-parameters-incomplete':'case-parameters-complete'),`data-id="${escape(c.id)}"`):''}</td>`}<td><div class="actions">${action('View','plan-case-source',c.id,'eye',c.script_kind!=='single')}${action('Remove','plan-remove-case',c.id,'trash',plan.locked)}</div></td></tr>`).join('');
  const children=(parent,depth,ancestorMatch=false)=>plan.folders.filter(f=>(f.parent_id||null)===parent).sort((a,b)=>a.position-b.position).map(f=>{
    const match=ancestorMatch||Boolean(query&&KeywordSearch.matches(f.name,query)),descendants=children(f.id,depth+1,match)+cases(f.id,depth+1,match);
    if(query&&!match&&!descendants)return '';
    return `<tr tabindex="0" aria-haspopup="menu" title="Right-click for actions" class="repository-folder-row" data-plan-folder="${escape(f.id)}" draggable="${!plan.locked}" style="--depth:${depth}"><td><div class="repository-folder-line">${planCheck('folder',f.id)}${button(collapsed.has(f.id)&&!query?'&#9656;':'&#9662;','toggle-plan-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!collapsed.has(f.id)||Boolean(query)}"`)}<button class="repository-folder-name" data-action="select-plan-folder" data-id="${escape(f.id)}" aria-pressed="${state.planFolder===f.id}">${icon('folder')}<strong>${escape(f.name)}</strong></button>${state.planRename===f.id?`<input class="plan-folder-rename repository-rename" data-id="${escape(f.id)}" aria-label="Folder name" maxlength="100" value="${escape(f.name)}">`:''}</div></td>${importing?'':'<td></td>'}<td><div class="actions">${action('New folder','new-plan-folder',f.id,'folderPlus',plan.locked)}${action('Resorting','resort-plan-folder',f.id,'sort',plan.locked)}${action('Remove folder','delete-folder',f.id,'trash',plan.locked)}</div></td></tr>${collapsed.has(f.id)&&!query?'':descendants}`;
  }).join('');
  const rows=children(null,1)+cases(null,1,false);
  const html=`<div class="table-wrap repository-scroll"><table id="repository-table" class="repository-hierarchy"><thead><tr><th>${listSelectAll('plan')}Directory / Test Case</th>${importing?'':'<th>Parameters</th>'}<th>Actions</th></tr></thead><tbody><tr tabindex="0" aria-haspopup="menu" title="Right-click for actions" class="repository-folder-row" data-plan-folder=""><td><div class="repository-folder-line"><input type="checkbox" disabled data-selection-root="plan" aria-label="BMC"><span class="folder-collapse-spacer" aria-hidden="true"></span><span class="repository-folder-name">${icon('folder')}<strong>BMC</strong><span class="repository-folder-count">(${plan.testcases.length})</span></span></div></td>${importing?'':'<td></td>'}<td><div class="actions">${action('New folder','new-plan-folder','','folderPlus',plan.locked)}${action('Resorting','resort-plan-folder','','sort',plan.locked)}</div></td></tr>${rows||`<tr><td colspan="${importing?2:3}">No Test Cases</td></tr>`}</tbody></table></div>`;
  return html.replace(/<td><div class="actions">[\s\S]*?<\/div><\/td>/g,'').replace('<th>Actions</th>','').replace(/colspan="[23]"/g,'colspan="'+(importing?1:2)+'"');
}
function importSourceTable(){
  const source=state.importSource,collapsed=state.importCollapsed=savedFolderCollapse(folderExpansionScope('import'),source.folders);
  const query=(state.importSearch||'').toLowerCase().trim();
  const cases=(parent,depth,match)=>source.cases.filter(c=>(c.folder_id||null)===parent&&(match||!query||KeywordSearch.matches(c.name,query))).map(c=>`<tr data-import-kind="case" data-import-id="${escape(c.id)}" draggable="true" style="--depth:${depth}"><td><label class="import-case-choice"><input type="checkbox" data-import-select="${escape(c.id)}" aria-label="Select ${escape(c.name)}" ${state.importSelection?.has(c.id)?'checked':''}><strong>${automation(c.automation)}${escape(c.name)}</strong></label><p class="help case-source-version" data-no-translate>${escape(version(c.source_created_at))}</p></td></tr>`).join('');
  const folders=(parent,depth,match=false)=>source.folders.filter(f=>(f.parent_id||null)===parent).sort((a,b)=>a.position-b.position).map(f=>{
    const matches=match||Boolean(query&&KeywordSearch.matches(f.name,query)),contents=folders(f.id,depth+1,matches)+cases(f.id,depth+1,matches);
    if(query&&!matches&&!contents)return '';
    return `<tr class="repository-folder-row" data-import-kind="folder" data-import-id="${escape(f.id)}" draggable="${!f.is_root}" style="--depth:${depth}"><td><div class="repository-folder-line"><input type="checkbox" data-import-folder-select="${escape(f.id)}" aria-label="Select folder ${escape(f.name)}" ${f.is_root?'disabled':state.importFolderSelection?.has(f.id)?'checked':''}>${button(collapsed.has(f.id)&&!query?'&#9656;':'&#9662;','toggle-import-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!collapsed.has(f.id)||Boolean(query)}"`)}<span class="repository-folder-name">${icon('folder')}<strong>${escape(f.name)}</strong></span></div></td></tr>${collapsed.has(f.id)&&!query?'':contents}`;
  }).join('');
  return `<div class="table-wrap repository-scroll"><table class="repository-hierarchy import-source-table"><thead><tr><th>${listSelectAll('import')}Directory / Test Case</th></tr></thead><tbody>${source.type==='plan'?'<tr class="repository-folder-row"><td><div class="repository-folder-line"><input type="checkbox" disabled data-selection-root="import" aria-label="BMC"><span class="folder-collapse-spacer" aria-hidden="true"></span><span class="repository-folder-name">'+icon('folder')+'<strong>BMC</strong></span></div></td></tr>':''}${folders(null,source.type==='plan'?1:0)+cases(null,1,false)||'<tr><td colspan="1">No Test Cases</td></tr>'}</tbody></table></div>`;
}
function importSourceOptions(){
 const target=context().plan?.id,source=state.importSource;
 return '<option value="repository" '+(source?.type==='repository'?'selected':'')+'>Test Case Repository</option>'+state.projects.map(p=>'<optgroup label="'+escape(p.name)+'">'+p.plans.filter(plan=>plan.id!==target).map(plan=>'<option value="plan:'+escape(plan.id)+'" '+(source?.planId===plan.id?'selected':'')+' data-no-translate>'+escape(p.name+' / '+plan.name)+'</option>').join('')+'</optgroup>').join('');
}
function importSourcePane(){
 return '<section class="import-source-pane" aria-label="Import source"><header class="import-pane-heading"><select id="import-workspace-source" aria-label="Source Project / Plan">'+importSourceOptions()+'</select><label><span class="sr-only">Find Source Test Case</span><input id="import-source-search" type="search" placeholder="Find Source Test Case" value="'+escape(state.importSearch||'')+'"></label>'+button('Close','close-import-source','preview-close')+'</header><div id="import-source-list">'+importSourceTable()+'</div></section>';
}
async function planPage(project, plan, inline=false) {
  if(!plan.testcases.some(c=>c.id===state.caseId))state.caseId=null;
  const header=heading('Test Plan: '+plan.name,'',button('Rename','rename-plan','',plan.locked?'disabled':'')+button('Delete','delete-plan','danger',plan.locked?'disabled':''));
  let contents;
  if(state.panel==='add-repository'){
    state.repository=await api('/api/repository/testcases');state.repositoryFolders=await api('/api/repository/folders');
    contents=`<div class="toolbar"><h2>Add from Test Case Repository</h2>${button('Back to Plan','close-panel')}</div>${repositoryWorkspace(true,plan)}`;
  }else{
    contents=`<div class="repository-page-controls actions"><label><span class="sr-only">Find Test Case</span><input id="plan-search" type="search" placeholder="Find Test Case" value="${escape(state.planSearch||'')}"></label>${button('Import Test Case','choose-import-source','',plan.locked?'disabled':'')}${inline?button('Rename','plan-list-rename','','data-id="'+escape(plan.id)+'" '+(plan.locked?'disabled':''))+button('Delete','plan-list-delete','danger','data-id="'+escape(plan.id)+'" '+(plan.locked?'disabled':'')):''}</div><div class="repository-layout ${state.caseId?'has-preview':''}" style="--preview-width:${state.repositoryPreviewWidth||45}%"><div class="repository-list" id="plan-case-list">${planCaseTable(plan)}</div>${state.caseId?`<div class="repository-resizer" role="separator" tabindex="0" aria-label="Resize details panel" aria-orientation="vertical" aria-controls="case-editor" aria-valuemin="25" aria-valuemax="70" aria-valuenow="${state.repositoryPreviewWidth||45}"></div><section class="plan-case-details" aria-label="Test Case details"><div class="toolbar repository-preview-header"><h2>${escape(plan.testcases.find(c=>c.id===state.caseId)?.tc_name||'')}</h2>${button('Close','close-plan-case','preview-close')}</div><div class="repository-preview-content" id="case-editor"></div></section>`:''}</div>`;
  }
  if(state.importSource){
    const ratio=state.importSplit??50;
    const layout=`<div class="plan-import-layout" style="--import-left:${ratio}fr;--import-right:${100-ratio}fr"><section class="import-target-pane"><header class="import-pane-heading"><h1 data-no-translate>Test Plan: ${escape(plan.name)}</h1><label><span class="sr-only">Find Test Case</span><input id="plan-search" type="search" placeholder="Find Test Case" value="${escape(state.planSearch||'')}"></label></header><div class="repository-list" id="plan-case-list">${planCaseTable(plan)}</div></section><div class="import-resizer" role="separator" tabindex="0" aria-label="Resize import workspaces" aria-orientation="vertical" aria-valuemin="25" aria-valuemax="75" aria-valuenow="${ratio}"></div>${importSourcePane()}</div>`;
    return (inline?'':header)+'<div inert aria-hidden="true">'+contents.replace(/id="/g,'id="background-')+'</div><dialog id="plan-import-workspace-dialog" aria-label="Import Test Cases">'+layout+'</dialog>';
  }

  return (inline?'':header)+(plan.locked?'<div class="notice info">A Task is running. Plan structure and Task scope are locked. Only the running Test Case’s Python file and parameters are locked.</div>':'')+(state.panel==='rename-plan'?nameForm('rename-plan',plan.name):'')+contents;
}

function folderPage(plan) {
 return `<div class="toolbar"><p class="help">Organize Test Cases in root folders and one level of children.</p>${button('New folder','new-folder','',plan.locked?'disabled':'')}</div>${plan.folders.map(folder=>`<form class="folder-form inline-form" data-id="${escape(folder.id)}"><div class="fields"><label class="field"><span>Folder name</span><input name="name" value="${escape(folder.name)}" required ${plan.locked?'disabled':''}></label><label class="field"><span>Parent folder</span><select name="parent_id" ${plan.locked?'disabled':''}><option value="">Plan root</option>${plan.folders.filter(f=>f.id!==folder.id&&!f.folder_path.startsWith(folder.folder_path+'/')).map(f=>`<option value="${escape(f.id)}" ${folder.parent_id===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('')}</select></label></div><div class="form-actions"><button ${plan.locked?'disabled':''}>Save folder</button>${button('Delete folder','delete-folder','danger',`data-id="${escape(folder.id)}" ${plan.locked?'disabled':''}`)}<span class="help">${plan.testcases.filter(c=>c.folder_id===folder.id).length} direct Test Cases</span></div></form>`).join('')||empty('No folders yet','Create a folder to organize this Plan’s Test Cases.',button('New folder','new-folder','primary'))}`;
}
function caseRows(plan) { return plan.testcases.map(c=>`<button class="case-row" data-action="select-case" data-id="${escape(c.id)}" data-search="${escape(c.tc_name.toLowerCase())}" data-folder="${escape(c.folder_id||'')}" aria-pressed="${c.id===state.caseId}"><strong>${automation(c.automation)}${escape(c.tc_name)}</strong><span class="help">${escape(c.folder_path||'Unfiled')}${c.script_kind!=='single'?' · Retired':''}</span></button>`).join(''); }
function parameterFields(metadata, settings, disabled=false) { return Object.entries(metadata.parameters||{}).map(([key,spec])=>{
  const value=settings[key]; const field=spec.type==='boolean'?`<input type="checkbox" name="p:${escape(key)}" ${value?'checked':''} ${disabled?'disabled':''}>`:`<input name="p:${escape(key)}" type="${['integer','number'].includes(spec.type)?'number':'text'}" ${spec.type==='integer'?'step="1"':spec.type==='number'?'step="any"':''} value="${escape(value)}" ${disabled?'disabled':''} ${spec.type==='string'?'':'required'}>`;
  return `<label class="field"><span>${escape(spec.label||key)}</span>${field}<span class="help">${escape(key)} · ${escape(spec.type)}</span></label>`;
}).join(''); }
function planCaseReference(plan,id){
 const c=plan.testcases.find(item=>item.id===id);if(!c)throw Error('Test Case not found.');
 const project=state.projects.find(p=>p.plans.some(item=>item.id===plan.id));
 return {kind:'plan',planId:plan.id,caseId:c.id,name:c.tc_name,contextLabel:(project?.name||'')+' / '+plan.name};
}
function repositoryCaseReference(id){const c=state.repository.find(item=>item.id===id);if(!c)throw Error('Test Case not found.');return {kind:'repository',caseId:id,name:c.name,contextLabel:'Test Case Repository'};}
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
    content=`<p>Choose the Plan Test Cases included in this Task. Edit all test parameters in the <a href="${path(project,plan)}">Plan</a>.</p><div class="toolbar"><div class="actions">${button('Select all','scope-all','',plan.locked?'disabled':'')}${button('Clear selection','scope-none','',plan.locked?'disabled':'')}</div><span class="help" id="scope-count">${state.scope.size} selected</span></div><form id="scope-form"><div class="table-wrap"><table class="test-case-scope-list"><thead><tr><th>Include</th><th>Test Case</th><th>Folder</th><th>Created at</th></tr></thead><tbody>${plan.testcases.map(c=>`<tr><td class="check"><input type="checkbox" data-scope="${escape(c.id)}" aria-label="Include ${escape(c.tc_name)}" ${state.scope.has(c.id)?'checked':''} ${plan.locked||c.script_kind!=='single'?'disabled':''}></td><td>${automation(c.automation)}${escape(c.tc_name)}${c.script_kind!=='single'?'<p class="help">Retired — single .py required</p>':''}</td><td>${escape(c.folder_path||'Unfiled')}</td><td>${escape(version(c.source_created_at))}</td></tr>`).join('')}</tbody></table></div><div class="form-actions"><button class="primary" ${plan.locked?'disabled':''}>Save Task scope</button><span class="help">Removing a case also removes its current Task result and logs.</span></div></form>`;
  }
  else content=taskExecutionContent(project,plan,task);
  return breadcrumbs()+heading(task.name,'Task · '+plan.name,toolbar)+(state.panel==='rename-task'?nameForm(state.panel,task.name):'')+(needs?`<div class="notice">Plan definitions or Task connection settings changed for ${needs} Test Case(s). Existing results and logs remain available; rerun those cases before using the report.</div>`:'')+(task.execution_active?'<div class="notice info">Execution is active. Scope is locked until execution finishes or stops.</div>':'')+tabs([['settings','Connection settings'],['scope','Task scope'],['execution','Execution & results']],state.tab)+content;
}
function taskExecutionContent(project,plan,task){
 const needs=task.testcases.filter(c=>c.needs_retest).length;
 return (task.execution_active?'<div class="notice info">Execution is active. Scope is locked until execution finishes or stops.</div>':'')+(task.testcases.length?`<div class="execution-summary"><span><strong>${task.testcases.length}</strong> in scope</span><span><strong>${task.counts.Passed}</strong> passed</span><span><strong>${task.counts.Failed}</strong> failed</span><span><strong>${needs}</strong> need rerun</span></div><div class="toolbar"><p class="help">Run checked cases using the latest saved Plan settings.</p><div class="actions">${task.execution_active?button('Stop execution','stop','danger')+(!state.activeTask?button('Resume monitoring','resume','primary'):''):button('Run selected cases','run','primary',state.activeTask?'disabled title="Another Task is being monitored in this window."':'')}</div></div><div class="split"><div class="case-browser"><div class="case-list">${task.testcases.map(c=>`<div class="task-case"><label class="checkbox-field" style="padding:10px 18px 0"><input type="checkbox" data-run="${escape(c.id)}" aria-label="Run ${escape(c.tc_name)}" ${c.selected?'checked':''} ${task.execution_active||c.script_kind!=='single'?'disabled':''}><span class="help">Include in execution</span></label><button class="case-row" data-action="select-result" data-id="${escape(c.id)}" aria-pressed="${state.caseId===c.id}"><strong>${automation(c.automation)}${escape(c.tc_name)}</strong><span class="case-result-labels">${status(c.status)} ${c.needs_retest?'<span class="status stale">Rerun needed</span>':''}</span>${c.script_kind!=='single'?'<p class="help">Retired step-based case</p>':''}</button></div>`).join('')}</div></div><div class="case-editor" id="evidence">${evidence(task)}</div></div>`:empty('Set this Task’s scope','Select Test Cases from the Plan before starting an execution.','<a href="#/tasks/info/'+encodeURIComponent(task.id)+'">Open Task Info to choose Test Cases</a>'));
}
function evidence(task) {
  const tc=task.testcases.find(c=>c.id===state.caseId); if(!tc)return '';
  return `<h2>${automation(tc.automation)}${escape(tc.tc_name)}</h2><div class="metadata"><span>Latest result ${status(tc.status)}</span><span>Executed <strong>${escape(date(tc.executed_at))}</strong></span></div>${tc.needs_retest?'<div class="notice">Retained evidence predates the current Plan definition or Task connection settings. Rerun needed.</div>':''}${tc.manual_override?`<p class="help">Manual result: ${escape(tc.manual_override.status)} · ${escape(tc.manual_override.reason||'No reason recorded')}</p>`:''}<div class="actions"><strong>Test log</strong>${button('Report preview','execution-report-preview','','data-id="'+escape(tc.id)+'"')}</div><pre class="log code" id="log-output">${escape(state.activeTask===task.id && tc.status==='Running'?state.log:tc.log_text||'No test log. Run this Test Case to collect evidence.')}</pre><div id="input-slot">${state.activeTask===task.id&&state.prompt?inputForm(state.prompt.session,state.prompt.text):''}</div><details><summary>Result annotation</summary><form id="annotation-form"><div class="fields"><label class="field"><span>Manual status</span><select name="status" ${task.execution_active?'disabled':''}><option value="TBD">Not run / pending</option><option value="Passed">Passed</option><option value="CP">CP</option><option value="Failed">Failed</option><option value="Block">Block</option></select></label><label class="field"><span>Reason / Note for CP</span><input name="reason" ${task.execution_active?'disabled':''}></label><label class="field"><span>Bug ID</span><input name="bug_id" value="${escape(tc.bug_id)}" ${task.execution_active?'disabled':''}></label></div><div class="form-actions"><button ${task.execution_active?'disabled':''}>Save annotation</button></div></form></details>`;
}
function repositoryCheck(kind,id){return `<input type="checkbox" class="repository-batch-check" data-kind="${kind}" data-id="${escape(id)}" aria-label="Select ${kind}" ${state.repositorySelection?.has(kind+':'+id)?'checked':''}>`;}
function repositorySelectionData(){const folders=[],cases=[];for(const value of state.repositorySelection||[]){const [kind,id]=value.split(':');(kind==='folder'?folders:cases).push(id);}return {folder_ids:folders,case_ids:cases};}
function folderAction(label,action,id,kind=''){return button(icon(action==='new-repository-case'?'plus':action==='new-repository-folder'?'folderPlus':action==='resort-repository-folder'?'sort':'trash'),action,'small-button icon-button '+kind,`data-id="${escape(id)}" aria-label="${label}" title="${label}"`);}
function selectedRepositoryFolder(){return state.repositoryFolders.find(f=>f.id===state.repositoryFolder)||state.repositoryFolders.find(f=>f.is_root);}
function repositoryFolderOptions(selected) {
 return (state.repositoryFolders||[]).map(f=>`<option value="${escape(f.id)}" ${selected===f.id?'selected':''}>${escape(f.folder_path)}</option>`).join('');
}
function repositoryTable(add=false,plan=null) {
 state.repositoryCollapsed=savedFolderCollapse('repository',state.repositoryFolders);
 const selected=selectedRepositoryFolder();state.repositoryFolder=selected?.id;
 const folderCounts=new Map();
 const folderCount=id=>{if(!folderCounts.has(id))folderCounts.set(id,state.repository.filter(c=>c.folder_id===id).length+state.repositoryFolders.filter(f=>f.parent_id===id).reduce((n,f)=>n+folderCount(f.id),0));return folderCounts.get(id);};
 const caseRow=(c,depth)=>{const exists=plan?.testcases.some(t=>t.tc_name.toLowerCase()===c.name.toLowerCase());
 return `<tr tabindex="0" aria-haspopup="menu" title="Right-click for actions" data-repository-id="${escape(c.id)}" ${add?'':'draggable="true"'} data-search="${escape(c.name.toLowerCase())}" style="--depth:${depth}"><td><div class="case-selection-label">${repositoryCheck('case',c.id)}<strong>${automation(c.metadata.automation)}${escape(c.name)}</strong></div><p class="help">${escape(version(c.source_created_at))}</p></td><td>${add?button(exists?'Already in Plan':'Add to Plan','add-case',exists?'':'primary',`data-id="${escape(c.id)}" ${exists||plan.locked?'disabled':''}`):Object.keys(c.metadata.parameters||{}).length?button(`Parameters (${Object.keys(c.metadata.parameters||{}).length})`,'view-parameters','small-button',`data-id="${escape(c.id)}" aria-label="Parameters for ${escape(c.name)}"`):''}</td>${add?'':`<td><div class="actions">${button(icon('eye'),'view-standard','small-button icon-button',`data-id="${escape(c.id)}" title="View" aria-label="View ${escape(c.name)}"`)}${button(icon('trash'),'remove-standard','small-button icon-button danger',`data-id="${escape(c.id)}" title="Remove" aria-label="Remove ${escape(c.name)}"`)}</div></td>`}</tr>`;};
 const children=(parent,depth)=>state.repositoryFolders.filter(f=>f.parent_id===parent).sort((a,b)=>a.position-b.position).map(f=>`<tr tabindex="0" aria-haspopup="menu" title="Right-click for actions" class="repository-folder-row" data-folder-node="${escape(f.id)}" data-action="select-repository-folder" data-id="${escape(f.id)}" ${add||f.is_root?'':'draggable="true"'} style="--depth:${depth}"><td><div class="repository-folder-line">${f.is_root?'<input type="checkbox" disabled data-selection-root="repository" aria-label="BMC">':repositoryCheck('folder',f.id)}${button(state.repositoryCollapsed?.has(f.id)?'&#9656;':'&#9662;','toggle-repository-folder','folder-collapse',`data-id="${escape(f.id)}" aria-label="Toggle folder" aria-expanded="${!state.repositoryCollapsed?.has(f.id)}"`)}<button type="button" class="repository-folder-name" data-action="select-repository-folder" data-id="${escape(f.id)}" aria-pressed="${selected?.id===f.id}" title="${escape(f.folder_path)}">${icon('folder')}<strong>${escape(f.name)}</strong><span class="repository-folder-count">(${folderCount(f.id)})</span></button>${state.repositoryRename===f.id?`<input class="repository-rename" data-id="${escape(f.id)}" aria-label="Folder name" value="${escape(f.name)}" maxlength="100">`:''}</div></td>${add?'':'<td></td>'}<td><div class="actions">${add?button('Add folder to Plan','add-repository-folder','small-button',`data-id="${escape(f.id)}" ${plan.locked?'disabled':''}`):folderAction('Add Test Case','new-repository-case',f.id)+folderAction('New folder','new-repository-folder',f.id)+folderAction('Resorting','resort-repository-folder',f.id)+(f.is_root?'':folderAction('Remove folder','remove-repository-folder',f.id,'danger'))}</div></td></tr>${state.repositoryCollapsed?.has(f.id)?'':children(f.id,depth+1)+state.repository.filter(c=>c.folder_id===f.id).map(c=>caseRow(c,depth+1)).join('')}`).join('');
 const html=`${add?'<div class="toolbar"><label><span class="sr-only">Find Test Case</span><input id="repository-search" type="search" placeholder="Find Test Case"></label></div>':''}<div class="table-wrap repository-scroll"><table id="repository-table" class="repository-hierarchy"><thead><tr><th>${listSelectAll('repository')}Directory / Test Case</th><th>${add?'Plan action':'Parameters'}</th>${add?'':'<th>Actions</th>'}</tr></thead><tbody>${children(null,0)}</tbody></table></div>`;
 return add?html:html.replace(/<td><div class="actions">[\s\S]*?<\/div><\/td>/g,'').replace('<th>Actions</th>','');
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
 if(state.repositorySelection)state.repositorySelection=new Set([...state.repositorySelection].filter(key=>key.startsWith('case:')?state.repository.some(c=>c.id===key.slice(5)):state.repositoryFolders.some(f=>!f.is_root&&f.id===key.slice(7))));
 const selected=selectedRepositoryFolder(),editing=state.panel==='edit-repository-folder';
 const folderForm=['new-repository-folder','edit-repository-folder'].includes(state.panel)?`<form id="repository-folder-form" class="inline-form" data-id="${editing?escape(selected.id):''}"><h2>${editing?'Edit folder':'New folder'}</h2><p class="help">${escape(editing?selected.folder_path:selected.folder_path+'/')}</p><label class="field"><span>Name</span><input name="name" value="${editing?escape(selected.name):''}" required maxlength="100"></label><div class="form-actions"><button class="primary">${editing?'Save':'Create folder'}</button>${button('Cancel','close-panel')}</div></form>`:'';
 return `<div class="repository-page-controls actions"><label><span class="sr-only">Find Test Case</span><input id="repository-search" type="search" placeholder="Find Test Case"></label>${state.repositorySelection?.size?button('Delete selected','repository-batch-delete','danger'):''}</div>`+folderForm+(state.panel==='import-python'?`<form id="repository-form" class="inline-form"><h2>Add Test Case</h2><label class="field"><span>Python file</span><input type="file" name="file" accept=".py" required></label><label class="field"><span>Folder</span><select name="folder_id">${repositoryFolderOptions(selected.id)}</select></label><div class="form-actions"><button class="primary">Add to Repository</button>${button('Cancel','close-panel')}</div></form>`:'')+repositoryWorkspace();
}
const settingsGroups=[['BMC connection',[['host','BMC URL'],['username','Username'],['password','Password','password']]],['Console server (optional)',[['cs_host','Host'],['cs_port','Port','number'],['cs_protocol','Protocol'],['cs_username','Username'],['cs_password','Password','password']]],['DUT console commands (optional)',[['dut_connect_cmd','Connect command'],['dut_exit_cmd','Exit command'],['dut_force_connect_cmd','Force connect command']]],['DUT operating system (optional)',[['dut_os_type','OS type'],['dut_os_host_ip','Host IP'],['dut_os_username','Username'],['dut_os_password','Password','password'],['dut_os_prompt_regex','Prompt expression']]]];
async function settingsPage(task, readOnly=false) {
  let config={},missing=false; try {config=await api(`/api/tasks/${task.id}/settings`);}catch(e){if(e.status!==404)throw e;missing=true;}
  return '<h2>Connection settings</h2><p>Independent BMC and DUT connection environment for this Task. Other Tasks keep their own settings.</p>'+ (task.execution_active?'<div class="notice">This Task is executing. Connection settings are locked.</div>':'')+(missing?'<div class="notice info">Configure the BMC connection for this Task before execution.</div>':'')+`<form id="settings-form" class="settings-form"><fieldset class="connection-fields" ${task.execution_active||readOnly?'disabled':''}>${settingsGroups.map(([name,fields],i)=>`<section class="section"><h2>${name}</h2><div class="fields">${fields.map(([key,label,type='text'])=>`<label class="field"><span>${label}</span><input name="${key}" type="${type}" value="${escape(config[key]??'')}" ${key==='host'?'placeholder="https://bmc-host" required':''} autocomplete="${type==='password'?'new-password':'off'}"></label>`).join('')}${i===0?`<label class="checkbox-field"><input type="checkbox" name="verify_ssl" ${config.verify_ssl?'checked':''}>Verify TLS certificate</label>`:''}</div></section>`).join('')}${readOnly?'':`<div class="form-actions"><button class="primary">Save connection settings</button></div>`}</fieldset></form>`;
}

const executionStorageKey='bmc-execution-tabs-v1';
function executionView(){
 state.executionViews??={};
 if(!state.executionViews.global){
   let saved={};
   try{saved=JSON.parse(localStorage.getItem(executionStorageKey)||'{}')||{};}catch{}
   const ids=Array.isArray(saved.ids)?[...new Set(saved.ids.filter(id=>typeof id==='string'&&id.length>0))]:[];
   state.executionViews.global={ids,active:ids.includes(saved.active)?saved.active:ids[0]||null,cases:{},pending:new Set()};
 }
 return state.executionViews.global;
}
function saveExecutionView(){
 const view=executionView();
 try{localStorage.setItem(executionStorageKey,JSON.stringify({ids:view.ids,active:view.active}));}
 catch{toast('Unable to save Execution tabs. Check browser storage settings.',true);}
}
async function executionPage(project){
 const view=executionView(project), result=await api('/api/tasks');
 const available=result.tasks.filter(t=>t.task_type==='Test');
 view.ids=view.ids.filter(id=>available.some(t=>t.id===id));
 if(!view.ids.includes(view.active))view.active=view.ids[0]||null;
 saveExecutionView();
 let task=null,plan=null;
 if(view.active){
   const selected=view.active;
   task=await api('/api/tasks/'+encodeURIComponent(selected)+'/summary');
   if(task.id!==selected)throw Error('Task response does not match the selected Task.');
   project=state.projects.find(p=>p.plans.some(plan=>plan.id===task.plan_id));
   plan=project?.plans.find(p=>p.id===task.plan_id);
   if(!plan)throw Error("This Task’s Project or Plan is unavailable. Refresh the workspace.");
   if(view.active!==selected)return '';
   view.task=task;
   state.caseId=view.cases[selected];
   if(!task.testcases.some(c=>c.id===state.caseId))state.caseId=task.testcases[0]?.id||null;
   view.cases[selected]=state.caseId;
 }else view.task=null;
 view.available=available;
 const tabs='<div class="tabs execution-tabs" role="tablist" aria-label="Test Tasks">'+view.ids.map(id=>{
   const name=available.find(t=>t.id===id).name;
   return '<span class="execution-tab-item" role="presentation" data-execution-tab="'+escape(id)+'">'+button(escape(name),'execution-tab','', 'draggable="true" role="tab" id="execution-tab-'+escape(id)+'" aria-controls="execution-panel" aria-selected="'+(view.active===id)+'" data-task-id="'+escape(id)+'" data-no-translate')+button('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>','execution-close','execution-tab-close','aria-label="Close '+escape(name)+' tab" title="Close tab" data-task-id="'+escape(id)+'"')+'</span>';
 }).join('')+button('Add Task','execution-picker','', 'id="execution-tab-add" aria-haspopup="dialog"')+'</div>';
 const picker='<label class="field"><span>Project</span><select id="execution-picker-project" aria-label="Project">'+state.projects.map(p=>'<option value="'+escape(p.id)+'" data-no-translate>'+escape(p.name)+'</option>').join('')+'</select></label><div id="execution-picker-cases"></div><section aria-label="Selected Tasks"><h3>Selected Tasks <span id="execution-selection-count">0</span></h3><div id="execution-selected-tasks"></div></section><div class="form-actions">'+button('Cancel','execution-picker-cancel')+button('Add Selected Tasks','execution-add','primary','disabled')+'</div>';
 return heading('Execution','',project?'<a href="'+path(project)+'/test-plans">Test Plans</a>':'').replace('<p></p>','')+tabs+'<section id="execution-panel" role="tabpanel" '+(view.active?'aria-labelledby="execution-tab-'+escape(view.active)+'"':'aria-label="Execution"')+' '+(task?'data-execution-task-id="'+escape(task.id)+'"':'')+'>'+(task?'<div class="toolbar"><h2 data-no-translate>'+escape(task.name)+'</h2><a href="#/tasks/info/'+encodeURIComponent(task.id)+'">Task Info</a></div>'+taskExecutionContent(project,plan,task):empty('No Task open','Use Add Task to choose existing Test Tasks.'))+'</section><dialog id="execution-picker-dialog" aria-labelledby="execution-picker-title"><h2 id="execution-picker-title">Select Test Tasks</h2>'+picker+'</dialog>';
}
function renderExecutionPicker(){
 const view=executionView(),projectId=$('#execution-picker-project').value;
 const visible=view.available.filter(t=>t.project_id===projectId);
 $('#execution-picker-cases').innerHTML='<div class="table-wrap"><table><thead><tr><th>Select</th><th>Task</th><th>Plan</th><th>Assignee</th></tr></thead><tbody>'+visible.map(t=>'<tr><td><input type="checkbox" data-execution-choice="'+escape(t.id)+'" aria-label="Select '+escape(t.name)+'" '+(view.ids.includes(t.id)?'checked disabled':view.pending.has(t.id)?'checked':'')+'></td><td data-no-translate>'+escape(t.name)+'</td><td data-no-translate>'+escape(t.plan_name)+'</td><td data-no-translate>'+escape(t.setup?.owner||'TBD')+'</td></tr>').join('')+(!visible.length?'<tr><td colspan="4">No Test Tasks in this Project.</td></tr>':'')+'</tbody></table></div>';
 $('#execution-selection-count').textContent=view.pending.size;
 $('#execution-selected-tasks').innerHTML=[...view.pending].map(id=>{
   const task=view.available.find(t=>t.id===id);if(!task)return '';
   const project=state.projects.find(p=>p.id===task.project_id);
   return '<div class="toolbar"><span data-no-translate>'+escape(project?.name||task.project_name)+' / '+escape(task.name)+'</span>'+button('Remove','execution-unselect','','data-task-id="'+escape(id)+'" aria-label="Remove '+escape(task.name)+' from selection"')+'</div>';
 }).join('')||'<p class="help">No Tasks selected.</p>';
 $('#execution-picker-dialog [data-action=execution-add]').disabled=!view.pending.size;
}
function executionElementMatches(element){
 const pane=element.closest('[data-execution-task-id]');
 return !pane||pane.dataset.executionTaskId===context().task?.id;
}

async function taskManagementPage() {
  const result=await api('/api/tasks'); const project=context().project; state.managedTasks=project?result.tasks.filter(t=>t.project_id===project.id&&t.task_type==='Plan'):result.tasks;
  const plans=project?project.plans:state.projects.flatMap(p=>p.plans);
  const editing=state.managedTasks.find(t=>t.id===state.managerTaskId);
  if(['manager-new','manager-edit'].includes(state.panel)){const options=await api('/api/tasks/options');state.taskOptions=options.projects;state.taskOwners=options.owners||['TBD'];}
  const form=state.panel==='manager-new'?TaskManagement.form(state.taskOptions,null,state.taskOwners):state.panel==='manager-edit'&&editing?TaskManagement.form(state.taskOptions,editing,state.taskOwners):'';
  const selected=project?'my-task':state.managerTab||'schedule';
  const search=['schedule','my-schedule'].includes(selected)?'':state.managerSearch||'';
  if(['schedule','my-schedule'].includes(selected)){
    const range=TaskManagement.calendarRange(state.managedTasks),first=Date.parse(range.start+'T00:00:00Z')/86400000,last=Date.parse(range.end+'T00:00:00Z')/86400000;
    const requests=[];
    for(let value=first;value<=last;value+=366){const segment={start:new Date(value*86400000).toISOString().slice(0,10),end:new Date(Math.min(value+365,last)*86400000).toISOString().slice(0,10)};requests.push(api('/api/schedule/calendar?'+new URLSearchParams(segment)));}
    const calendars=await Promise.all(requests);
    TaskManagement.setCalendar({...calendars[0],...range,days:calendars.flatMap(item=>item.days)});
  }
  if(selected==='info'){
    const identity=state.route[0]==='tasks'&&state.route[1]==='info'?state.route[2]:null;
    const current=state.managedTasks.find(item=>item.id===identity);
    if(current)state.taskInfoPath=TaskManagement.infoLink(current);
    const info=current?await taskInfoPage(current,form):empty(identity?'Task not found.':'Select a Task',identity?'This Task may have been deleted.':'Choose a Task from Task List or My Task to configure its connection settings, scope and information.');
    return taskWorkspaceTabs(selected)+'<div id="task-manager-content" role="tabpanel" aria-labelledby="manager-tab-info">'+info+'</div>';
  }

  return (project?heading('Plan',project.name):taskWorkspaceTabs(selected))+
    (!state.projects.length?'<div class="notice info">Create a Project before adding Tasks. <a href="#/dashboard">Open Projects</a></div>':'')+form+
    `<div class="toolbar"><div class="actions">${['schedule','my-schedule'].includes(selected)?'':`<label><span class="sr-only">Find Task</span><input id="manager-search" type="search" placeholder="Find Task, Project or Plan" value="${escape(search)}"></label>`}${['schedule','my-schedule'].includes(selected)?'<button type="button" data-schedule-action="today">Today</button>':''}${['list','my-task'].includes(selected)?'<span id="manager-task-count" class="help" aria-live="polite"></span>':''}</div>${button('New Task','manager-new','primary',!state.projects.length?'disabled':'')}</div><div id="task-manager-content" ${project?'role="region" aria-label="Project Tasks"':`role="tabpanel" aria-labelledby="manager-tab-${selected}"`}>${TaskManagement.content(state.managedTasks,search,selected)}</div>`;
}
async function taskInfoPage(task,form){
  if(state.taskInfoId!==task.id){state.taskInfoId=task.id;state.taskInfoTab='content';state.taskInfoEditor=null;}
  const isTest=task.task_type==='Test';
  const items=[['content','Content'],...(isTest?[['scope','Scope'],['connection','Connection'],['dut','DUT Config']]:[]),['notes','Note & History']];
  if(!items.some(([key])=>key===state.taskInfoTab))state.taskInfoTab='content';
  const selected=state.taskInfoTab,metadataEdit=Boolean(form),editing=metadataEdit||Boolean(state.taskInfoEditor);
  const disabled=selected==='connection'?task.execution_active:task.locked;
  const controls=editing?(metadataEdit?'':button('Cancel','task-info-cancel')):selected==='dut'?'':button('Edit',['content','notes'].includes(selected)?'manager-edit':'task-info-edit','', 'data-id="'+escape(task.id)+'" '+(disabled?'disabled':''));
  const nav='<div class="tabs task-info-tabs" role="tablist" aria-label="Task information sections">'+items.map(([id,label])=>button(label,'task-info-tab','', 'id="task-info-tab-'+id+'" data-task-info-tab="'+id+'" role="tab" aria-selected="'+(selected===id)+'" tabindex="'+(selected===id?'0':'-1')+'" aria-controls="task-info-panel-'+id+'" data-no-translate')).join('')+'</div>';
  let body;
  if(['content','notes'].includes(selected)){
    const history=selected==='notes'||metadataEdit?await api('/api/tasks/'+encodeURIComponent(task.id)+'/history'):{history:[]};
    const notes='<h2>Notes</h2><p class="task-info-notes" data-no-translate>'+escape(task.setup.notes||'—')+'</p>'+TaskManagement.historyList(history.history);
    body=metadataEdit?form+'<div id="task-info-edit-history">'+TaskManagement.historyList(history.history)+'</div>':selected==='content'?TaskManagement.taskInfo(task,{heading:false,notes:false}):notes;
  }else if(selected==='dut')body='<h2 data-no-translate>DUT Configuration</h2>';
  else{
    const summary=await api('/api/tasks/'+encodeURIComponent(task.id)+'/summary');
    if(selected==='connection')body=await settingsPage(summary,state.taskInfoEditor!=='connection');
    else{
      const {project,plan}=taskFormContext();
      body=project&&plan?taskInfoScope(project,plan,summary,state.taskInfoEditor==='scope'):empty('Plan not found.','Reload the Task to view its scope.');
    }
  }
  return '<section class="task-info-workspace"><div class="page-heading"><h1 data-no-translate>'+escape(task.name)+'</h1><div class="actions">'+controls+'</div></div>'+nav+(metadataEdit?body:'<section id="task-info-panel-'+selected+'" role="tabpanel" aria-labelledby="task-info-tab-'+selected+'">'+body+'</section>')+'</section>';
}
function taskInfoScope(project,plan,task,editing){
  const rows=editing?plan.testcases:task.testcases;
  return (editing?'<p>Choose the Plan Test Cases included in this Task.</p><div class="toolbar"><div class="actions">'+button('Select all','scope-all','',plan.locked?'disabled':'')+button('Clear selection','scope-none','',plan.locked?'disabled':'')+'</div><span class="help" id="scope-count">'+state.scope.size+' selected</span></div><form id="scope-form">':'')+
    '<div class="table-wrap"><table class="test-case-scope-list"><thead><tr>'+(editing?'<th>Include</th>':'')+'<th>Test Case</th><th>Folder</th><th>Created at</th>'+(editing?'':'<th>Status</th>')+'</tr></thead><tbody>'+rows.map(c=>'<tr>'+(editing?'<td class="check"><input type="checkbox" data-scope="'+escape(c.id)+'" aria-label="Include '+escape(c.tc_name)+'" '+(state.scope.has(c.id)?'checked':'')+' '+(plan.locked||c.script_kind!=='single'?'disabled':'')+'></td>':'')+'<td>'+automation(c.automation)+escape(c.tc_name)+'</td><td>'+escape(c.folder_path||'Unfiled')+'</td><td data-no-translate>'+escape(version(c.source_created_at))+'</td>'+(editing?'':'<td>'+status(c.status)+'</td>')+'</tr>').join('')+(rows.length?'':'<tr><td colspan="4">No Test Cases</td></tr>')+'</tbody></table></div>'+(editing?'<div class="form-actions"><button class="primary" '+(plan.locked?'disabled':'')+'>Save Task scope</button></div></form>':'');
}
function applyTaskInfoTab(){
  const selected=state.taskInfoTab;
  for(const tab of $$('[data-task-info-tab]')){tab.setAttribute('aria-selected',String(tab.dataset.taskInfoTab===selected));tab.tabIndex=tab.dataset.taskInfoTab===selected?0:-1;}
  for(const panel of $$('.task-info-workspace [data-info-form-panel]'))panel.hidden=panel.dataset.infoFormPanel!==selected;
}
function bindTaskInfoForm(){
  if(!$('.task-info-workspace'))return;
  const form=$('#task-manager-form');if(!form)return;
  const content=form.querySelector('.fields'),notes=document.createElement('div');
  content.dataset.infoFormPanel='content';content.id='task-info-panel-content';content.setAttribute('role','tabpanel');content.setAttribute('aria-labelledby','task-info-tab-content');
  notes.dataset.infoFormPanel='notes';notes.id='task-info-panel-notes';notes.setAttribute('role','tabpanel');notes.setAttribute('aria-labelledby','task-info-tab-notes');
  notes.append(form.elements.notes.closest('label'),form.querySelector('#manager-history-field'));
  const history=$('#task-info-edit-history');if(history){notes.append(...history.childNodes);history.remove();}
  content.after(notes);applyTaskInfoTab();
  form.addEventListener('invalid',event=>{state.taskInfoTab=event.target.closest('[data-info-form-panel]')?.dataset.infoFormPanel||'content';applyTaskInfoTab();},true);
}
function taskWorkspaceTabs(selected) {
  const tabs=['schedule','my-schedule'].includes(selected)?[['schedule','Schedule'],['my-schedule','My Schedule']]:[['list','Task List'],['my-task','My Task'],['info','Task Info']];
  return `<div class="tabs ${['schedule','my-schedule'].includes(selected)?'schedule-tabs':['list','my-task'].includes(selected)?'task-list-tabs':''}" role="tablist" aria-label="Task workspace">${tabs.map(([id,label])=>button(label,'manager-tab','',`id="manager-tab-${id}" role="tab" aria-selected="${selected===id}" aria-controls="task-manager-content" data-manager-tab="${id}" data-no-translate`)).join('')}</div>`;
}
function missingWorkspaceParent() {
  if(state.route[0]!=='project')return null;
  const {project,plan,task}=context();
  if(!project)return '#/dashboard';
  if(state.route[2]==='plan'&&!plan)return path(project)+'/plans';
  if(state.route[4]==='task'&&!task)return path(project,plan);
  return null;
}
let caseContextMenu=null,caseContextRow=null;
function closeCaseContextMenu(restore=false){
 const row=caseContextRow;caseContextMenu?.remove();caseContextMenu=null;caseContextRow=null;
 if(restore&&row?.isConnected)row.focus({preventScroll:true});
}
function caseContextItems(row){
 const {plan}=context(),items=[];
 const add=(label,action,id,disabled=false,danger=false)=>items.push({label,action,id,disabled,danger});
 if(row.hasAttribute('data-plan-case')&&plan){
   const c=plan.testcases.find(item=>item.id===row.dataset.planCase);if(!c)return [];
   add('View Python source','plan-case-source',c.id,c.script_kind!=='single');
   if(c.parameter_count>0)add('Edit parameters','plan-case-parameters',c.id,c.script_kind!=='single');
   add('Delete Test Case','plan-remove-case',c.id,plan.locked,true);
 }else if(row.hasAttribute('data-plan-folder')&&plan){
   const id=row.dataset.planFolder;
   add('New folder','new-plan-folder',id,plan.locked);
   add('Sort Test Cases','resort-plan-folder',id,plan.locked);
   if(id){add('Rename','rename-plan-folder',id,plan.locked);add('Delete folder','delete-folder',id,plan.locked,true);}
 }else if(document.body.classList.contains('repository-page')&&row.hasAttribute('data-repository-id')){
   const c=state.repository.find(item=>item.id===row.dataset.repositoryId);if(!c)return [];
   add('View Python source','view-standard',c.id);
   if(Object.keys(c.metadata.parameters||{}).length)add('View parameters','view-parameters',c.id);
   add('Delete Test Case','remove-standard',c.id,false,true);
 }else if(document.body.classList.contains('repository-page')&&row.hasAttribute('data-folder-node')){
   const folder=state.repositoryFolders.find(item=>item.id===row.dataset.folderNode);if(!folder)return [];
   add('Add Test Case','new-repository-case',folder.id);
   add('New folder','new-repository-folder',folder.id);
   add('Sort Test Cases','resort-repository-folder',folder.id);
   if(!folder.is_root){add('Rename','rename-repository-folder',folder.id);add('Delete folder','remove-repository-folder',folder.id,false,true);}
 }
 if(plan&&(row.hasAttribute('data-plan-case')||row.hasAttribute('data-plan-folder'))&&planSelection().size>1)add('Delete selected items','plan-selection-delete','',plan.locked||state.importBusy,true);
 if(document.body.classList.contains('repository-page')&&state.repositorySelection?.size>1)add('Delete selected items','repository-batch-delete','',false,true);
 const planGroup=plan&&planSelection().size>1&&((row.hasAttribute('data-plan-case')&&planSelection().has('case:'+row.dataset.planCase))||(row.hasAttribute('data-plan-folder')&&planSelection().has('folder:'+row.dataset.planFolder)));
 const repoGroup=state.repositorySelection?.size>1&&((row.hasAttribute('data-repository-id')&&state.repositorySelection.has('case:'+row.dataset.repositoryId))||(row.hasAttribute('data-folder-node')&&state.repositorySelection.has('folder:'+row.dataset.folderNode)));
 if(planGroup||repoGroup)for(let i=items.length-1;i>=0;i--)if(['plan-remove-case','delete-folder','remove-standard','remove-repository-folder'].includes(items[i].action))items.splice(i,1);
 return items;
}
function openCaseContextMenu(row,x,y){
 if(row.closest('[inert]'))return false;
 const items=caseContextItems(row);if(!items.length)return false;
 closeCaseContextMenu();caseContextRow=row;
 const menu=document.createElement('div');menu.className='case-context-menu';menu.setAttribute('role','menu');menu.setAttribute('aria-label','Case and folder actions');
 menu.innerHTML=items.map(item=>button(escape(item.label),item.action,item.danger?'danger':'','role="menuitem" tabindex="-1" data-id="'+escape(item.id)+'" '+(item.disabled?'disabled':''))).join('');
 (row.closest('dialog')||document.body).append(menu);caseContextMenu=menu;
 const rect=menu.getBoundingClientRect();menu.style.left=Math.max(8,Math.min(x,innerWidth-rect.width-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-rect.height-8))+'px';
 menu.addEventListener('click',event=>{
   event.stopPropagation();const item=event.target.closest('button');if(!item||item.disabled)return;
   closeCaseContextMenu();doAction(item.dataset.action,item).catch(e=>toast(e.message,true));
 });
 menu.addEventListener('keydown',event=>{
   const options=[...menu.querySelectorAll('button:not(:disabled)')],index=options.indexOf(document.activeElement);
   if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeCaseContextMenu(true);return;}
   if(event.key==='Tab'){closeCaseContextMenu(true);return;}
   if(!['ArrowDown','ArrowUp','Home','End'].includes(event.key)||!options.length)return;
   event.preventDefault();event.stopPropagation();const next=event.key==='Home'?0:event.key==='End'?options.length-1:(index+(event.key==='ArrowDown'?1:-1)+options.length)%options.length;options[next].focus({preventScroll:true});
 });
 menu.querySelector('button:not(:disabled)')?.focus({preventScroll:true});return true;
}
const caseContextSelector='#repository-table [data-plan-case],#repository-table [data-plan-folder],#repository-table [data-repository-id],#repository-table [data-folder-node]';
document.addEventListener('contextmenu',event=>{
 const row=event.target.closest(caseContextSelector);if(row&&openCaseContextMenu(row,event.clientX,event.clientY))event.preventDefault();
});
document.addEventListener('keydown',event=>{
 if(event.key!=='ContextMenu'&&!(event.shiftKey&&event.key==='F10'))return;
 const row=event.target.closest(caseContextSelector);if(!row)return;const rect=row.getBoundingClientRect();
 if(openCaseContextMenu(row,rect.left+20,rect.bottom)){event.preventDefault();event.stopPropagation();}
});
document.addEventListener('pointerdown',event=>{if(caseContextMenu&&!caseContextMenu.contains(event.target))closeCaseContextMenu();},true);
window.addEventListener('resize',()=>closeCaseContextMenu());
window.addEventListener('scroll',event=>{if(caseContextMenu&&!caseContextMenu.contains(event.target))closeCaseContextMenu();},true);

async function draw() {
  saveFolderExpansions();
  closeCaseContextMenu();
  const parent=missingWorkspaceParent();
  if(parent){location.replace(parent);return;}

  const generation=++state.generation; const workspace=$('#workspace'); workspace.setAttribute('aria-busy','true');
  const section=state.route[0]||'dashboard'; document.body.classList.toggle('repository-page',section==='repository'); $$('.global-nav a').forEach(a=>a.toggleAttribute('aria-current',a.dataset.section===(context().task?'tasks':section==='project'?'projects':section))); $$('.global-nav [aria-current]').forEach(a=>a.setAttribute('aria-current','page'));

  const {project,plan,task}=context(); document.body.classList.toggle('plan-workspace',Boolean(plan&&!task));document.body.classList.toggle('plan-list-workspace',section==='project'&&['plans','test-plans'].includes(state.route[2]));let html;
  if(task&&state.route[0]!=='execution'&&state.route[2]!=='execution') Object.assign(task, await api(`/api/tasks/${task.id}/summary`));
  if(generation!==state.generation)return;
  if(section==='execution') html=await executionPage();
  else if(section==='tasks') html=await taskManagementPage(); else if(section==='repository') html=await repositoryPage(); else if(section==='settings') html=empty('Choose a Task','Connection settings belong to each Task. Open a Task and select Connection settings.'); else if(section==='project'&&!project || state.route[2]==='plan'&&!plan || state.route[4]==='task'&&!task) html=empty('Workspace not found','This item may have been deleted. Choose an existing Project from the navigator.','<a href="#/dashboard">Go to Projects</a>');
  else if(project&&state.route[2]==='execution') html=await executionPage(project);
  else if(project&&state.route[2]==='plans') html=await planEditorList(project);
  else if(project&&state.route[2]==='test-plans') html=await planEditorList(project);
  else if(project&&state.route[2]==='reports') html=reportPage(project);
  else if(project&&(!state.route[2]||['info','reports','bugs'].includes(state.route[2]))) html=await projectSectionPage(project); else if(task) html=await taskPage(project,plan,task); else if(plan) html=await planPage(project,plan); else html=projectPage(project);
  if(task)state.taskInfoPath=TaskManagement.infoLink(task);
  if(generation!==state.generation)return; workspace.innerHTML=html; sizePlanColumns(); workspace.setAttribute('aria-busy','false'); drawTree();
  const importDialog=$('#plan-import-workspace-dialog');
  if(importDialog){
    importDialog.addEventListener('cancel',event=>{event.preventDefault();if(state.importBusy)return;state.importSource=null;draw().catch(e=>toast(e.message,true));});
    importDialog.showModal();
  }
  TaskManagement.bindForm(state.taskOptions||[],api);
  if(project&&state.route[2]==='plans'&&state.panel==='manager-new'){
    const form=$('#task-manager-form'),type=form.elements.task_type,selector=form.elements.project_id;
    [...type.options].forEach(option=>{if(option.value!=='Plan')option.remove();});
    type.value='Plan';type.dispatchEvent(new Event('change',{bubbles:true}));
    [...selector.options].forEach(option=>{if(option.value!==project.id)option.remove();});
    selector.value=project.id;selector.dispatchEvent(new Event('change',{bubbles:true}));
  }
  TaskManagement.bindSchedule(api,draw,toast);
  ProjectInformationUI.bind();
  bindTaskInfoForm();
  bindReportSelection();
  syncCaseSelections();
  if(plan&&!task) await loadCase();
  if(state.panel && $('#name-form input')) $('#name-form input').focus();
}
function discard() { return (!state.dirty || window.confirm('Discard unsaved changes?'))&&CaseWindows.confirmDiscard(); }
async function navigate() {
  if(state.restoringHash){state.restoringHash=false;return;}
  if(!discard()){state.restoringHash=true;location.hash=previousHash;return;}
  CaseWindows.closeAll(true);
  if(!state.reportBusy)$('#report-compose-dialog')?.close();
  state.managerTab=state.nextManagerTab||(location.hash==='#/tasks/list'?'list':location.hash==='#/tasks/my-task'?'my-task':location.hash==='#/tasks/my-schedule'?'my-schedule':location.hash.startsWith('#/tasks/info/')?'info':'schedule');state.nextManagerTab=null;
  state.taskInfoEditor=null;state.taskInfoId=null;
  state.infoEditing=false;state.projectImport=null;state.projectInformation=null;state.infoCollapsed=new Set();state.infoSection='spec';
  previousHash=location.hash||'#/dashboard'; state.route=previousHash.slice(2).split('/').map(decodeURIComponent); state.panel=null;state.dirty=false;state.definition=null;state.caseId=null;state.planSearch='';state.planCollapsed=new Set();state.planFolder=null;state.planRename=null;state.planTargetFolder=null;state.importSource=null;state.repositoryDefinition=null;document.body.classList.toggle('repository-page',state.route[0]==='repository');
  if(state.route[0]==='project'&&state.route[2]==='execution'){location.replace('#/execution');return;}
  if(state.route[0]==='project'&&state.route[4]==='task'&&state.route[6]==='info'){location.replace('#/tasks/info/'+encodeURIComponent(state.route[5]));return;}
  $('#workspace').innerHTML='<div class="loading">Loading workspace…</div>';
  $('#workspace').setAttribute('aria-busy','true');
  await refresh(false);
  if(state.route[0]==='projects'){location.replace(projectEntryRoute());return;}
  state.tab=state.route[4]==='task'?'settings':'cases'; const {task}=context(); state.scope=new Set(task?.testcases.map(c=>c.id)||[]);
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
  const {project,plan,task}=taskFormContext();
  if(!executionElementMatches(element))return;
  if(action==='execution-picker'){
    const view=executionView();view.pending=new Set();const selector=$('#execution-picker-project');selector.value=view.pickerProject||state.projects[0]?.id||'';renderExecutionPicker();
    $('#execution-picker-dialog').showModal();return;
  }
  if(action==='execution-unselect'){executionView().pending.delete(element.dataset.taskId);renderExecutionPicker();return;}
  if(action==='execution-picker-cancel'){$('#execution-picker-dialog').close();return;}
  if(['execution-tab','execution-add','execution-close'].includes(action)){
    if(!discard())return;
    const view=executionView(project);
    if(task)view.cases[task.id]=state.caseId;
    if(action==='execution-close'){
      const id=element.dataset.taskId,index=view.ids.indexOf(id);
      view.ids=view.ids.filter(item=>item!==id);
      if(view.active===id)view.active=view.ids[Math.min(index,view.ids.length-1)]||null;
    }else if(action==='execution-add'){
      const chosen=[...view.pending].filter(id=>!view.ids.includes(id)&&view.available.some(t=>t.id===id));
      if(!chosen.length){toast('Select at least one Test Task.',true);return;}
      view.ids=[...new Set([...view.ids,...chosen])];view.active=chosen[0];
      $('#execution-picker-dialog').close();
    }else view.active=element.dataset.taskId;
    saveExecutionView();
    view.task=null;state.caseId=null;state.dirty=false;
    $('#execution-panel').inert=true;
    await draw();$('#execution-tab-'+(view.active||'add'))?.focus();return;
  }
  if(action==='plan-list-rename'||action==='plan-list-delete'){
    if(!discard())return;
    if(state.inlinePlanId!==element.dataset.id){state.caseId=null;state.definition=null;state.planSearch='';state.planCollapsed=new Set();state.planFolder=null;state.planRename=null;state.importSource=null;}
    selectPlanFor(project,element.dataset.id);state.panel=null;state.dirty=false;state.tab='cases';
    await draw();return doAction(action==='plan-list-rename'?'rename-plan':'delete-plan',element);
  }
  if(action==='expand-plan-editor'||action==='select-plan-tab'){
    if(!discard())return;
    selectPlanFor(project,element.dataset.id);
    state.caseId=null;state.definition=null;state.planSearch='';state.planCollapsed=new Set();state.planFolder=null;state.planRename=null;state.importSource=null;state.panel=null;state.dirty=false;state.tab='cases';
    await draw();return;
  }
  if(action==='task-info-tab'){
    const selected=element.dataset.taskInfoTab;
    if($('#task-manager-form')&&['content','notes'].includes(selected)){state.taskInfoTab=selected;applyTaskInfoTab();return;}
    if(!discard())return;state.dirty=false;state.panel=null;state.taskInfoEditor=null;state.taskInfoTab=selected;await draw();$('#task-info-tab-'+selected)?.focus();return;
  }
  if(action==='task-info-edit'){
    state.taskInfoEditor=state.taskInfoTab;state.dirty=false;
    if(state.taskInfoTab==='scope'){const summary=await api('/api/tasks/'+encodeURIComponent(task.id)+'/summary');state.scope=new Set(summary.testcases.map(c=>c.id));}
    await draw();return;
  }
  if(action==='task-info-cancel'){
    if(!discard())return;state.dirty=false;state.taskInfoEditor=null;state.panel=null;await draw();return;
  }
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
  else if(action==='execution-report-preview'){const tc=task?.testcases.find(c=>c.id===element.dataset.id);if(!tc)return;await ReportPreview.open({taskId:task.id,caseId:tc.id,taskName:task.name,caseName:tc.tc_name,opener:element});}
  else if(action==='select-result'){state.caseId=element.dataset.id;if(state.route[0]==='execution'||project&&state.route[2]==='execution')executionView(project).cases[task.id]=state.caseId;await draw();}
  else if(action==='report-select'){state.reportSelecting=!state.reportSelecting;state.reportSelection=null;state.reportError='';await draw();}
  else if(action==='report-plan-toggle'){state.reportExpanded??=new Set();state.reportExpanded.has(element.dataset.id)?state.reportExpanded.delete(element.dataset.id):state.reportExpanded.add(element.dataset.id);await draw();}
  else if(action==='report-matrix'){state.reportExpanded??=new Set();state.reportMatrices??=new Set();state.reportExpanded.add(element.dataset.id);state.reportMatrices.has(element.dataset.id)?state.reportMatrices.delete(element.dataset.id):state.reportMatrices.add(element.dataset.id);await draw();}
  else if(action==='report-generate'){openReportComposer(project);}
  else if(action==='toggle-plan-matrix'){state.expandedPlans??=new Set();const id=element.dataset.id;state.expandedPlans.has(id)?state.expandedPlans.delete(id):state.expandedPlans.add(id);const expanded=state.expandedPlans.has(id);element.setAttribute('aria-expanded',String(expanded));element.closest('tr').nextElementSibling.hidden=!expanded;}
  else if(action==='toggle-repository-folder'){state.repositoryCollapsed??=new Set();state.repositoryCollapsed.has(element.dataset.id)?state.repositoryCollapsed.delete(element.dataset.id):state.repositoryCollapsed.add(element.dataset.id);saveFolderExpansions();await draw();}
  else if(action==='plan-selection-delete'){
    if(plan.locked||state.importBusy||!discard())return;
    const selection=planSelectionData();if(!selection.folder_ids.length&&!selection.case_ids.length)return;
    if(!await confirmDelete('Delete selected items?',selection.folder_ids.length+' folders and '+selection.case_ids.length+' Test Cases selected. Selected folders, their descendants and affected Task results/logs will be deleted.'))return;
    await api('/api/plans/'+plan.id+'/items/delete','POST',{...selection,confirm:true,acknowledgement:true});
    planSelection().clear();state.caseId=null;state.planRename=null;state.dirty=false;await refresh();toast('Selected items deleted.');
  }
  else if(action==='repository-batch-delete'){const selection=repositorySelectionData();if(!await confirmDelete('Delete selected items?',`${selection.folder_ids.length} directories and ${selection.case_ids.length} Test Cases selected. Selected directories and all their contents will be permanently deleted. Plan copies remain independent.`))return;await api('/api/repository/batch','POST',{...selection,action:'delete',confirm:true});state.repositorySelection.clear();state.repositoryDefinition=null;await draw();toast('Selected items deleted.');}
  else if(action==='rename-repository-folder'){
    const folder=state.repositoryFolders.find(f=>f.id===element.dataset.id);
    if(!folder||folder.is_root||!discard())return;
    state.dirty=false;state.repositoryFolder=folder.id;state.repositoryRename=folder.id;state.panel=null;
    await draw();const input=$('.repository-rename');input?.focus();input?.select();
  }
  else if(action==='rename-plan-folder'){
    if(plan.locked||state.importBusy||!discard())return;
    const folder=plan.folders.find(f=>f.id===element.dataset.id);if(!folder)return;
    state.dirty=false;state.planFolder=folder.id;state.planRename=folder.id;
    $('#plan-case-list').innerHTML=planCaseTable(plan);syncCaseSelections();const input=$('.plan-folder-rename');input?.focus();input?.select();
  }
  else if(action==='select-repository-folder'){
    state.repositoryRename=null;state.repositoryFolder=element.dataset.id;state.repositoryDefinition=null;if(state.route[0]==='repository')state.panel=null;await draw();
  }
  else if(action==='select-plan-folder'){
    if(!discard())return;state.dirty=false;
    state.planFolder=element.dataset.id;state.planRename=null;$('#plan-case-list').innerHTML=planCaseTable(plan);syncCaseSelections();
  }
  else if(action==='plan-import-case'){
    if(state.repositoryImporting||plan.locked||!discard())return;
    state.dirty=false;const picker=$('#repository-file-picker');picker.dataset.planId=plan.id;picker.dataset.folderId=element.dataset.id||'';picker.value='';picker.click();
  }
  else if(action==='toggle-plan-folder'){state.planCollapsed??=new Set();const id=element.dataset.id;state.planCollapsed.has(id)?state.planCollapsed.delete(id):state.planCollapsed.add(id);saveFolderExpansions();$('#plan-case-list').innerHTML=planCaseTable(plan);syncCaseSelections();}
  else if(['plan-case-parameters','plan-case-source'].includes(action)){if(state.dirty&&!discard())return;const ref=planCaseReference(plan,element.dataset.id);state.dirty=false;if(state.importSource){state.importSource=null;await draw();}await CaseWindows.open(action==='plan-case-source'?'viewer':'parameters',ref);}
  else if(action==='close-plan-case'){if(!discard())return;state.dirty=false;state.caseId=null;await draw();}
  else if(action==='plan-remove-case'){
    if(!discard())return;const current=plan.testcases.find(c=>c.id===element.dataset.id);if(!current)return;
    if(!await confirmDelete(`Delete Test Case: ${current.tc_name}?`,'This deletes the Plan Test Case and its current results and logs from every Task in this Plan.'))return;
    await api(`/api/testcases/${current.id}`,'DELETE',{confirm:true,acknowledgement:true});state.dirty=false;await refresh();toast('Deleted Test Case.');
  }
  else if(action==='choose-import-source'){
    if(plan.locked||!discard())return;state.dirty=false;element.disabled=true;
    try{await loadImportSource('repository');}finally{element.disabled=false;}
  }
  else if(action==='cancel-import-conflicts')$('#import-conflict-dialog').close();
  else if(action==='cancel-import-source')$('#plan-import-dialog').close();
  else if(action==='close-import-source'){if(state.importBusy){toast('Wait for the current import to finish.',true);return;}state.importSource=null;await draw();}
  else if(action==='toggle-import-folder'){state.importCollapsed??=new Set();const id=element.dataset.id;state.importCollapsed.has(id)?state.importCollapsed.delete(id):state.importCollapsed.add(id);saveFolderExpansions();$('#import-source-list').innerHTML=importSourceTable();syncCaseSelections();}
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
  else if(action==='run'){if(state.activeTask)throw Error('This window is already monitoring an execution.');const ids=$$('[data-run]:checked').map(e=>e.dataset.run);if(!ids.length)throw Error('Select at least one Test Case to run.');if(task.testcases.some(c=>ids.includes(c.id)&&c.result)&&!window.confirm('Run selected cases again? Their current results and logs will be replaced.'))return;const config=await api(`/api/tasks/${task.id}/settings`).catch(()=>{throw Error('Configure this Task?s BMC connection in Connection settings before running.');});if(!config.host)throw Error('Set this Task?s BMC URL in Connection settings before running.');const result=await api(`/api/tasks/${task.id}/execution/start`,'POST',{testcase_ids:ids});runTask(task.id,ids,result.execution_token).catch(e=>toast(e.message,true));}
  else if(action==='resume'){const current=await api(`/api/tasks/${task.id}/execution`);runTask(task.id,current.testcase_ids,current.execution_token,current.session_id).catch(e=>toast(e.message,true));}
  else if(action==='stop'){const current=await api(`/api/tasks/${task.id}/execution`);await api(`/api/tasks/${task.id}/execution/stop`,'POST',{execution_token:current.execution_token});toast('Stop requested. Waiting for the running Test Case to finish.');}
  else if(action==='report'){element.disabled=true;try{const response=await fetch(`/api/tasks/${element.dataset.id}/report`);if(!response.ok){const err=await response.json();throw Error(err.error||'Report generation failed.');}const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`BMC_Test_Report_${element.dataset.id}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Task report generated.');}finally{element.disabled=false;}}
  else if(action==='delete-folder'){const impact=await api(`/api/folders/${element.dataset.id}/impact`);if(!await confirmDelete('Delete folder and contents?',`${impact.testcase_count} Test Case(s), ${impact.descendant_folder_count} child folder(s) and evidence in ${impact.affected_task_count} Task(s) will be deleted.`))return;await api(`/api/folders/${element.dataset.id}`,'DELETE',{confirm:true,acknowledgement:true});state.dirty=false;await refresh();toast('Folder and contents deleted.');}
  else if(['view-standard','view-parameters'].includes(action)){if(state.dirty&&!discard())return;state.dirty=false;await CaseWindows.open(action==='view-standard'?'viewer':'parameters',repositoryCaseReference(element.dataset.id));}
  else if(action==='remove-standard'){
    if(!discard())return;const current=state.repository.find(c=>c.id===element.dataset.id);if(!current)return;
    if(!await confirmDelete(`Remove Test Case: ${current.name}?`,'Remove this Repository Test Case. Existing Plan copies, settings and Task evidence remain.'))return;
    await api(`/api/repository/testcases/${current.id}`,'DELETE',{confirm:true});
    if(state.repositoryDefinition?.id===current.id)state.repositoryDefinition=null;
    state.dirty=false;state.panel=null;await draw();toast('Repository Test Case removed.');
  }
  else if(action==='close-standard'){state.repositoryDefinition=null;await draw();}
  else if(action==='export-case'){const c=plan.testcases.find(c=>c.id===state.caseId);download(c.tc_name+'.json',JSON.stringify({script_kind:'single',tc_name:c.tc_name,source:state.definition.source,source_version:c.source_version,source_created_at:c.source_created_at,settings:state.definition.settings,folder_path:c.folder_path},null,2),'application/json');}
  else if(action.startsWith('delete-')) {
    const type=action.split('-')[1],tc=plan?.testcases.find(c=>c.id===state.caseId);const name=type==='project'?project.name:type==='plan'?plan.name:type==='task'?task.name:tc.tc_name;
    if(!await confirmDelete(`Delete ${type}: ${name}?`,type==='case'?'This deletes the Plan Test Case and its current results and logs from every Task in this Plan.':`This permanently deletes the ${type} and its contained items, including current test evidence.`))return;
    if(type==='project')await api('/api/delete_project','POST',{project_id:project.id,project:project.name,confirm:true});else if(type==='plan')await api('/api/delete_plan','POST',{plan_id:plan.id,confirm:true});else if(type==='task')await api(`/api/tasks/${task.id}`,'DELETE');else await api(`/api/testcases/${tc.id}`,'DELETE',{confirm:true,acknowledgement:true});
    state.dirty=false;await refresh(false);if(type==='project')location.hash='#/dashboard';else if(type==='plan'){selectPlanFor(project,null);state.caseId=null;const target=path(project)+'/plans';if(location.hash===target)await draw();else location.hash=target;}else if(type==='task')location.hash=path(project,plan);else await draw();toast('Deleted '+type+'.');
  }
}
async function submit(form) {
  if(!executionElementMatches(form))return;
 const {project,plan,task}=taskFormContext();const values=Object.fromEntries(new FormData(form));
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
   const id=form.dataset.taskId;const setup={start_date:values.start_date,end_date:values.end_date,actual_start_date:values.actual_start_date,actual_end_date:values.actual_end_date,notes:values.notes,owner:values.owner,task_status:values.task_status||'New',...TaskManagement.metadataValues(form)};
   if(!setup.start_date||!setup.end_date)setup.task_status='Not Scheduled';
   if(setup.start_date&&setup.end_date&&setup.end_date<setup.start_date)throw Error('End date must be on or after start date.');
   if(id){
     const payload={setup,expected_idesign:JSON.parse(form.dataset.idesign||'{}'),expected_fw_package:JSON.parse(form.dataset.fwPackage||'[]'),expected_actual_start_date:form.dataset.actualStartDate||'',expected_actual_end_date:form.dataset.actualEndDate||'',expected_start_date:form.dataset.startDate||'',expected_end_date:form.dataset.endDate||'',expected_owner:form.dataset.owner||'TBD',expected_task_status:form.dataset.taskStatus||'New'};
     if(setup.actual_start_date!==payload.expected_actual_start_date||setup.actual_end_date!==payload.expected_actual_end_date||setup.start_date!==payload.expected_start_date||setup.end_date!==payload.expected_end_date||setup.task_status!==payload.expected_task_status){
       if(!values.history?.trim())throw Error('Enter History explaining the date or status change (1 to 4000 characters).');
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
     try{const created=await api('/api/create_plan','POST',{project:targetProject.name,plan_name:name,sku_id:values.sku_id||null});selectPlanFor(targetProject,created.plan_id);state.caseId=null;state.definition=null;state.importSource=null;state.planSearch='';}
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
   await api(`/api/tasks/${task.id}/testcases/import`,'POST',{testcases:[...state.scope]});state.dirty=false;state.tab='execution';state.taskInfoEditor=null;await refresh();toast('Task scope saved.');
 }else if(form.id==='repository-create-folder-form'){
   if(state.repositoryCreatingFolder)return;
   const name=values.name.trim();if(!name)throw Error('Enter a name.');
   const parent=form.dataset.parentId;state.repositoryCreatingFolder=true;
   try{
     const planId=form.dataset.planId;
     const folder=await api(planId?`/api/plans/${planId}/folders`:'/api/repository/folders','POST',{name,parent_id:parent||null});
     if(planId){state.planCollapsed?.delete(parent);saveFolderExpansions();state.dirty=false;$('#repository-create-folder-dialog').close();await refresh();toast('Folder created.');return;}
     state.repositoryCollapsed?.delete(parent);saveFolderExpansions();state.repositoryFolder=folder.id;state.dirty=false;
     $('#repository-create-folder-dialog').close();await draw();
     $(`[data-folder-node="${folder.id}"]`)?.scrollIntoView({block:'nearest'});toast('Folder created.');
   }finally{state.repositoryCreatingFolder=false;}
 }else if(form.id==='repository-folder-form'){const selected=selectedRepositoryFolder(),id=form.dataset.id;const f=await api('/api/repository/folders'+(id?'/'+id:''),id?'PATCH':'POST',{name:values.name,parent_id:id?selected.parent_id:selected.id});state.repositoryFolder=f.id;state.panel=null;state.dirty=false;await draw();toast(id?'Folder updated.':'Repository folder created.');
 }else if(form.id==='repository-form'){
   const file=form.elements.file.files[0];if(!file||!file.name.toLowerCase().endsWith('.py'))throw Error('Choose a .py file.');await api('/api/repository/testcases','POST',{source:await file.text(),folder_id:values.folder_id||null});state.panel=null;state.dirty=false;await draw();toast('Standard Test Case imported with a new source timestamp.');
 }else if(form.id==='settings-form'){
   values.verify_ssl=form.elements.verify_ssl.checked;await api(`/api/tasks/${task.id}/settings`,'PUT',values);state.dirty=false;state.taskInfoEditor=null;await refresh();toast('Task connection settings saved.');
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
   for(const tcId of ids){const current=await api(`/api/tasks/${id}/execution`);if(!current.execution_active||current.stop_requested)break;const summary=await api(`/api/tasks/${id}/summary`);const tc=summary.testcases.find(c=>c.id===tcId);if(!tc||tc.status==='Passed'||tc.status==='Failed'||tc.status==='CP')continue;
     const run=await api('/api/run','POST',{task_id:id,testcase_id:tcId,execution_token:token});state.log='';for(const view of Object.values(state.executionViews||{}))if(view.ids.includes(id))view.cases[id]=tcId;if(context().task?.id===id)state.caseId=tcId;await refresh();await stream(run.session_id,id);
   }
   const current=await api(`/api/tasks/${id}/execution`);if(current.execution_active&&!current.session_id)await api(`/api/tasks/${id}/execution/finish`,'POST',{execution_token:token});
   toast('Task execution finished. Current results are available.');
 }finally{state.activeTask=null;await refresh();}
}
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('.execution-tabs [role=tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();const items=$$('.execution-tabs [role=tab]'),index=items.indexOf(tab);
 const next=event.key==='Home'?items[0]:event.key==='End'?items.at(-1):items[(index+(event.key==='ArrowRight'?1:-1)+items.length)%items.length];next.focus();next.click();
});
document.addEventListener('click',event=>{const element=event.target.closest('[data-action]');if(!element||element.disabled)return;doAction(element.dataset.action,element).catch(e=>toast(e.message,true));});
document.addEventListener('submit',event=>{const form=event.target;if(form.closest('dialog')&&!['plan-create-form','repository-create-folder-form'].includes(form.id))return;event.preventDefault();const buttons=$$('button[type=submit],button:not([type]):not([data-action])',form);buttons.forEach(b=>b.disabled=true);submit(form).catch(e=>{if(form.id==='task-manager-form'){form.querySelector('#manager-form-error').textContent=e.message;}else if(form.id==='plan-create-form'){$('#plan-create-error').textContent=e.message;form.elements.name.focus();}else if(form.id==='repository-create-folder-form'){$('#repository-create-folder-error').textContent=e.message;form.elements.name.focus();}else toast(e.message,true);}).finally(()=>buttons.forEach(b=>b.disabled=false));});
document.addEventListener('input',event=>{
 const el=event.target;
 if(el.dataset.infoSku){const fields=$$('[data-info-sku]',el.closest('tr'));fields.forEach((field,index)=>field.closest('td').classList.toggle('info-sku-different',index>0&&field.value!==fields[0].value));}
 if(el.id==='project-search'){openProjectPicker();let count=0;$$('[data-project-name]').forEach(button=>{button.hidden=!button.dataset.projectName.includes(el.value.trim().toLowerCase());if(!button.hidden)count++;});$('#project-search-empty').hidden=Boolean(count);return;}
 if(el.id==='manager-search'){state.managerSearch=el.value;$('#task-manager-content').innerHTML=TaskManagement.content(state.managedTasks,el.value,context().project?'my-task':state.managerTab||'schedule');TaskManagement.bindSchedule(api,draw,toast);return;}

 if(el.closest('#task-manager-form')&&['start_date','end_date'].includes(el.name)){const f=el.form;f.elements.start_date.required=false;f.elements.end_date.required=false;f.elements.end_date.min=f.elements.start_date.value;}
 if(el.id==='plan-search'){state.planSearch=el.value;$('#plan-case-list').innerHTML=planCaseTable(context().plan);syncCaseSelections();return;}
 if(el.id==='tree-search'){drawTree();return;}if(el.id==='case-search'||el.id==='folder-filter'){const search=($('#case-search')?.value||'').toLowerCase(),folder=$('#folder-filter')?.value;$$('#case-list [data-search]').forEach(row=>row.hidden=!KeywordSearch.matches(row.dataset.search,search)||(folder&&row.dataset.folder!==folder));return;}
 if(el.id==='repository-search'){$$('#repository-table [data-search]').forEach(row=>row.hidden=!KeywordSearch.matches(row.dataset.search,el.value));return;}
 if(el.closest('form')&&!el.closest('#input-form,#plan-import-form,#import-conflict-form,#task-cell-form,#task-meta-form')){state.dirty=true;if($('#save-state'))$('#save-state').textContent='Unsaved changes';}
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
document.addEventListener('change',event=>{
 const input=event.target;if(!input.matches('[data-report-select]'))return;
 const choice=state.reportSelection;if(!choice||state.reportBusy)return;
 const plan=context().project?.plans.find(p=>p.id===input.dataset.planId);if(!plan)return;
 state.reportError='';
 if(input.dataset.reportSelect==='plan'){
   input.checked?choice.plans.add(plan.id):choice.plans.delete(plan.id);
   for(const task of plan.tasks)choice.tasks.delete(task.id);
 }else input.checked?choice.tasks.add(input.dataset.taskId):choice.tasks.delete(input.dataset.taskId);
 draw().catch(error=>toast(error.message,true));
});
const reportDialog=$('#report-compose-dialog');
reportDialog.addEventListener('close',()=>{state.reportDraft=null;state.reportDrag=null;state.reportError='';});
reportDialog.addEventListener('cancel',event=>{if(state.reportBusy)event.preventDefault();});
$('#report-compose-cancel').addEventListener('click',()=>reportDialog.close());
$('#report-compose-generate').addEventListener('click',()=>generateReportSelection());
reportDialog.addEventListener('click',event=>{
 const control=event.target.closest('[data-report-move]');if(!control||state.reportBusy)return;
 const row=control.closest('[data-report-item]'),area=row.dataset.area,key=row.dataset.reportItem;
 const index=state.reportDraft[area].findIndex(i=>i.kind+':'+i.id===key);
 if(control.dataset.reportMove==='area')moveReportItem(key,area==='report'?'reference':'report',state.reportDraft[area==='report'?'reference':'report'].length);
 else moveReportItem(key,area,index+(control.dataset.reportMove==='up'?-1:2));
});
function clearReportDrop(){for(const el of $$('#report-compose-dialog [data-drop]'))delete el.dataset.drop;}
reportDialog.addEventListener('dragstart',event=>{
 const row=event.target.closest('[data-report-item]');if(!row||state.reportBusy){event.preventDefault();return;}
 state.reportDrag=row.dataset.reportItem;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',state.reportDrag);row.classList.add('is-dragging');
});
reportDialog.addEventListener('dragover',event=>{
 const list=event.target.closest('[data-report-area]');if(!list||!state.reportDrag||state.reportBusy)return;
 event.preventDefault();event.dataTransfer.dropEffect='move';clearReportDrop();
 const row=event.target.closest('[data-report-item]');
 if(row){const rect=row.getBoundingClientRect();row.dataset.drop=event.clientY<rect.top+rect.height/2?'before':'after';}
 else list.dataset.drop='inside';
 const bounds=list.getBoundingClientRect();if(event.clientY<bounds.top+28)list.scrollTop-=12;else if(event.clientY>bounds.bottom-28)list.scrollTop+=12;
});
reportDialog.addEventListener('drop',event=>{
 const list=event.target.closest('[data-report-area]');if(!list||!state.reportDrag||state.reportBusy)return;
 event.preventDefault();const area=list.dataset.reportArea,row=event.target.closest('[data-report-item]');
 let index=state.reportDraft[area].length;
 if(row){index=state.reportDraft[area].findIndex(i=>i.kind+':'+i.id===row.dataset.reportItem);const rect=row.getBoundingClientRect();if(event.clientY>=rect.top+rect.height/2)index++;}
 const key=state.reportDrag;state.reportDrag=null;clearReportDrop();moveReportItem(key,area,index);
});
reportDialog.addEventListener('dragend',()=>{state.reportDrag=null;clearReportDrop();for(const row of $$('.report-compose-item.is-dragging'))row.classList.remove('is-dragging');});
document.addEventListener('change',event=>{const el=event.target;
 if(el.hasAttribute('data-list-select-all')){const type=el.dataset.listSelectAll;for(const item of listSelectionItems(type))setItemSelection(type,item,el.checked);syncCaseSelections();return;}
 if(el.classList.contains('plan-selection-check')){changeItemSelection('plan',{kind:el.dataset.kind,id:el.dataset.id},el.checked);syncCaseSelections();return;}
 if(el.hasAttribute('data-import-folder-select')){changeItemSelection('import',{kind:'folder',id:el.dataset.importFolderSelect},el.checked);syncCaseSelections();return;}
 if(el.hasAttribute('data-import-select')){state.importSelection??=new Set();el.checked?state.importSelection.add(el.dataset.importSelect):state.importSelection.delete(el.dataset.importSelect);syncCaseSelections();return;}
 if(el.id==='execution-picker-project'){executionView().pickerProject=el.value;renderExecutionPicker();return;}
 if(el.hasAttribute('data-execution-choice')){const view=executionView();el.checked?view.pending.add(el.dataset.executionChoice):view.pending.delete(el.dataset.executionChoice);renderExecutionPicker();return;}
if(el.id==='project-switcher'){const p=state.projects.find(p=>p.id===el.value);if(p){const section=!state.route[2]?'info':['info','reports','bugs'].includes(state.route[2])?state.route[2]:'plans';location.hash=path(p)+'/'+section;el.value=context().project.id;}return;}if(el.classList.contains('repository-batch-check')){changeItemSelection('repository',{kind:el.dataset.kind,id:el.dataset.id},el.checked);syncCaseSelections();return;}if(el.id==='repository-folder-filter'){state.repositoryFolder=el.value;draw().catch(e=>toast(e.message,true));return;}if(el.classList.contains('repository-move')){api(`/api/repository/testcases/${el.dataset.id}/folder`,'PUT',{folder_id:el.value||null}).then(()=>draw()).catch(e=>toast(e.message,true));return;}if(el.id==='folder-filter')el.dispatchEvent(new Event('input',{bubbles:true}));if(el.dataset.run){if(!executionElementMatches(el))return;const {task}=context();if(!task?.testcases.some(c=>c.id===el.dataset.run))return;task.testcases.find(c=>c.id===el.dataset.run).selected=el.checked;api(`/api/task_testcases/${task.id}/${el.dataset.run}`,'PATCH',{selected:el.checked}).catch(e=>{el.checked=!el.checked;toast(e.message,true);});}});
document.addEventListener('click',event=>{if(event.target.classList.contains('repository-rename')||event.target.classList.contains('repository-batch-check')||event.target.classList.contains('plan-selection-check'))event.stopPropagation();},true);
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('[data-task-info-tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();const tabs=$$('[data-task-info-tab]'),index=tabs.indexOf(tab);
 const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
 tabs[next].focus();tabs[next].click();
});
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
 if(event.key==='Escape'){event.preventDefault();state.planRename=null;$('#plan-case-list').innerHTML=planCaseTable(context().plan);syncCaseSelections();return;}
 if(event.key!=='Enter')return;event.preventDefault();input.disabled=true;
 try{await api(`/api/folders/${input.dataset.id}`,'PATCH',{name:input.value});state.planRename=null;await refresh();toast('Folder renamed.');}
 catch(error){input.disabled=false;input.focus();toast(error.message,true);}
});
async function resolveImportConflicts(conflicts){
 const dialog=$('#import-conflict-dialog'),form=$('#import-conflict-form');
 let index=0;const decisions={};
 const render=()=>{
  const c=conflicts[index];
  $('#import-conflict-items').innerHTML=`<div class="conflict-case-name"><span>Test Case Name</span><strong data-no-translate>${escape(c.name)}</strong></div>${c.targets.length>1?`<label class="field"><span>Created at</span><select id="conflict-target">${c.targets.map(t=>`<option value="${escape(t.id)}" data-no-translate>${escape(version(t.source_created_at))}</option>`).join('')}</select></label>`:''}<div class="conflict-actions"><button type="button" data-conflict-choice="overwrite">${c.same_version?'Overwrite':'Overwrite and update'}</button>${c.same_version?'':'<button type="button" data-conflict-choice="coexist">Keep both</button>'}<button type="button" data-conflict-choice="skip">Skip this Case</button><button type="button" data-action="cancel-import-conflicts">Cancel</button></div>${conflicts.length>1?`<p class="help">${index+1} / ${conflicts.length}</p>`:''}`;
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
 const request={source_type:drag.source.type,source_plan_id:drag.source.planId,kind:drag.itemKind,id:drag.id,...(drag.itemKind==='selection'?{case_ids:drag.caseIds||[],folder_ids:drag.folderIds}:drag.caseIds?.length?{case_ids:drag.caseIds}:{}),target_folder_id:id,...insertion,decisions:{}};
 while(context().plan?.id===plan.id){
  try{return await api(`/api/plans/${plan.id}/import-cases`,'POST',request);}
  catch(error){if(error.status!==409||!error.details?.conflicts)throw error;const decisions=await resolveImportConflicts(error.details.conflicts);if(!decisions)return null;Object.assign(request.decisions,decisions);}
 }
 return null;
}
async function loadImportSource(value){
 const targetPlan=context().plan?.id,previousSource=state.importSource;let source;
 if(value==='repository'){
   const [cases,folders]=await Promise.all([api('/api/repository/testcases'),api('/api/repository/folders')]);
   source={type:'repository',label:'Test Case Repository',folders,cases:cases.map(c=>({...c,automation:c.metadata.automation}))};
 }else{
   await refresh(false);const id=value.slice(5),project=state.projects.find(p=>p.plans.some(x=>x.id===id)),plan=project?.plans.find(p=>p.id===id);
   if(!plan)throw Error('Source Plan not found');
   source={type:'plan',planId:id,label:project.name+' / '+plan.name,folders:plan.folders,cases:plan.testcases.filter(c=>c.script_kind==='single').map(c=>({...c,name:c.tc_name}))};
 }
 if(context().plan?.id!==targetPlan||previousSource&&state.importSource!==previousSource)return;
 if(!state.importSource)state.importSplit=50;
 state.importSource=source;state.importSelection=new Set();state.importFolderSelection=new Set();state.importCollapsed=new Set();state.importSearch='';state.caseId=null;state.panel=null;$('#plan-import-dialog').close();await draw();
}
$('#plan-import-form').addEventListener('submit',async event=>{
 event.preventDefault();event.stopPropagation();const submit=event.target.querySelector('[type=submit]');submit.disabled=true;
 try{await loadImportSource($('#plan-import-source').value);}catch(error){$('#plan-import-error').textContent=error.message;}finally{submit.disabled=false;}
});
document.addEventListener('change',async event=>{
 const selector=event.target;if(selector.id!=='import-workspace-source')return;
 if(state.importBusy){selector.value=state.importSource.type==='repository'?'repository':'plan:'+state.importSource.planId;return;}
 selector.disabled=true;
 try{await loadImportSource(selector.value);}catch(error){selector.value=state.importSource.type==='repository'?'repository':'plan:'+state.importSource.planId;toast(error.message,true);}finally{selector.disabled=false;}
});
document.addEventListener('input',event=>{if(event.target.id==='import-source-search'){state.importSearch=event.target.value;$('#import-source-list').innerHTML=importSourceTable();syncCaseSelections();}});
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
 if(caseTarget&&(drag.kind==='batch'&&(drag.folder_ids.length||drag.case_ids.includes(caseId))||drag.kind==='folder'||drag.kind==='import'&&drag.itemKind!=='case'||drag.kind==='case'&&drag.id===caseId))return null;
 const tc=caseTarget?plan.testcases.find(c=>c.id===caseId):null;
 const folderId=caseTarget?tc?.folder_id||null:node.dataset.planFolder||null;
 const mode=event?dropMode(event,node,caseTarget,drag.kind!=='folder'||!folderId):'inside';
 const parent=mode==='inside'||caseTarget?folderId:plan.folders.find(f=>f.id===folderId)?.parent_id;
 if(drag.kind==='batch'&&drag.folder_ids.some(id=>id===folderId||descendant(plan.folders,parent,id)))return null;
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
let draggedExecutionTab=null;
function clearExecutionTabDrop(){document.querySelectorAll('.execution-tabs [data-tab-drop]').forEach(el=>el.removeAttribute('data-tab-drop'));}
document.addEventListener('dragstart',event=>{
 const tab=event.target.closest('.execution-tabs [role=tab][draggable="true"]');if(!tab)return;
 draggedExecutionTab=tab.dataset.taskId;event.stopImmediatePropagation();event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',draggedExecutionTab);
});
document.addEventListener('dragover',event=>{
 if(!draggedExecutionTab)return;
 const target=event.target.closest('[data-execution-tab],#execution-tab-add');if(!target)return;
 event.preventDefault();event.stopImmediatePropagation();event.dataTransfer.dropEffect='move';clearExecutionTabDrop();
 target.dataset.tabDrop=target.id==='execution-tab-add'||event.clientX<target.getBoundingClientRect().left+target.getBoundingClientRect().width/2?'before':'after';
});
document.addEventListener('drop',event=>{
 if(!draggedExecutionTab)return;
 const target=event.target.closest('[data-execution-tab],#execution-tab-add'),id=draggedExecutionTab;draggedExecutionTab=null;clearExecutionTabDrop();
 if(!target)return;
 event.preventDefault();event.stopImmediatePropagation();
 const view=executionView();if(!view.ids.includes(id)||target.dataset.executionTab===id)return;
 const ids=view.ids.filter(item=>item!==id),after=event.clientX>target.getBoundingClientRect().left+target.getBoundingClientRect().width/2;
 const index=target.id==='execution-tab-add'?ids.length:ids.indexOf(target.dataset.executionTab)+(after?1:0);
 if(index<0)return;
 ids.splice(index,0,id);view.ids=ids;saveExecutionView();
 const row=target.parentElement,add=document.getElementById('execution-tab-add');
 for(const taskId of ids)row.insertBefore(document.getElementById('execution-tab-'+taskId).closest('[data-execution-tab]'),add);
});
document.addEventListener('dragend',()=>{draggedExecutionTab=null;clearExecutionTabDrop();});
let draggedPlanTab=null;
document.addEventListener('dragstart',event=>{
 const tab=event.target.closest('[data-plan-tab]');if(!tab)return;
 draggedPlanTab={id:tab.dataset.planTab,projectId:context().project.id};event.stopImmediatePropagation();event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain',tab.dataset.planTab);
});
document.addEventListener('dragover',event=>{
 if(!draggedPlanTab)return;
 const target=event.target.closest('[data-plan-tab],#plan-tab-add');if(!target)return;
 event.preventDefault();event.stopImmediatePropagation();event.dataTransfer.dropEffect='move';
 document.querySelectorAll('.plan-tabs [data-tab-drop]').forEach(el=>el.removeAttribute('data-tab-drop'));
 const after=event.clientX>target.getBoundingClientRect().left+target.getBoundingClientRect().width/2;
 target.dataset.tabDrop=target.id==='plan-tab-add'?'before':after?'after':'before';
});
document.addEventListener('drop',event=>{
 if(!draggedPlanTab)return;
 const target=event.target.closest('[data-plan-tab],#plan-tab-add'),project=context().project,drag=draggedPlanTab;draggedPlanTab=null;
 document.querySelectorAll('.plan-tabs [data-tab-drop]').forEach(el=>el.removeAttribute('data-tab-drop'));
 if(!target||!project||project.id!==drag.projectId)return;
 event.preventDefault();event.stopImmediatePropagation();if(target.dataset.planTab===drag.id)return;
 const ids=planTabIds(project).filter(id=>id!==drag.id);
 const after=event.clientX>target.getBoundingClientRect().left+target.getBoundingClientRect().width/2;
 const index=target.id==='plan-tab-add'?ids.length:ids.indexOf(target.dataset.planTab)+(after?1:0);
 ids.splice(index,0,drag.id);state.planTabOrders[project.id]=ids;
 try{localStorage.setItem('bmc-plan-tabs-'+project.id,JSON.stringify(ids));}catch{toast('Unable to save Plan tab order.',true);}
 const row=target.parentElement;
 for(const id of ids)row.insertBefore(document.getElementById('plan-tab-'+id),document.getElementById('plan-tab-add'));
});
document.addEventListener('dragend',()=>{draggedPlanTab=null;document.querySelectorAll('.plan-tabs [data-tab-drop]').forEach(el=>el.removeAttribute('data-tab-drop'));});
document.addEventListener('keydown',event=>{
 const tab=event.target.closest('.plan-tabs [role=tab]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 event.preventDefault();const items=[...document.querySelectorAll('.plan-tabs [role=tab]')],index=items.indexOf(tab);
 const next=event.key==='Home'?items[0]:event.key==='End'?items.at(-1):items[(index+(event.key==='ArrowRight'?1:-1)+items.length)%items.length];next.focus();next.click();
});
document.addEventListener('dragstart',event=>{
 const inPlan=document.body.classList.contains('plan-workspace');
 if(inPlan){
  if(context().plan?.locked||state.importBusy)return;
  const source=event.target.closest('[data-import-kind][draggable="true"]');
  if(source&&state.importSource){
    const kind=source.dataset.importKind,id=source.dataset.importId,selected=kind==='case'?state.importSelection?.has(id):(state.importFolderSelection?.has(id)||source.querySelector('[data-import-folder-select]')?.indeterminate);
    const caseIds=selected?state.importSource.cases.filter(c=>state.importSelection?.has(c.id)).map(c=>c.id):null;
    const folderIds=selected?state.importSource.folders.filter(f=>!f.is_root&&state.importFolderSelection?.has(f.id)).map(f=>f.id):[];
    planDrag={kind:'import',itemKind:folderIds.length||kind==='folder'&&selected?'selection':kind,id,source:state.importSource,planId:context().plan.id,caseIds,folderIds};
  }
  else{
   const row=event.target.closest('[data-plan-case][draggable="true"]'),folder=event.target.closest('[data-plan-folder][draggable="true"]');
   if(!row&&!folder)return;if(!discard()){event.preventDefault();return;}state.dirty=false;
   const kind=row?'case':'folder',id=row?.dataset.planCase||folder.dataset.planFolder,selection=planSelectionData();
   planDrag=(planSelection().has(kind+':'+id)&&(selection.case_ids.length+selection.folder_ids.length>1)||folder?.querySelector('.plan-selection-check')?.indeterminate)?{kind:'batch',id,...selection,planId:context().plan.id}:{kind,id,planId:context().plan.id};
  }
  event.dataTransfer.effectAllowed=planDrag.kind==='import'?'copy':'move';
  event.dataTransfer.setData('text/plain',JSON.stringify({kind:planDrag.kind,id:planDrag.id}));
  markDestinations(planTargets,planDestination);
 }else if(document.body.classList.contains('repository-page')){
  const row=event.target.closest('[data-repository-id][draggable="true"]'),folder=event.target.closest('[data-folder-node][draggable="true"]');
  if(!row&&!folder)return;
  const kind=row?'case':'folder',id=row?.dataset.repositoryId||folder.dataset.folderNode;
  repositoryDrag=(state.repositorySelection?.has(kind+':'+id)||folder?.querySelector('.repository-batch-check')?.indeterminate)?{kind:'batch',...repositorySelectionData()}:{kind,id};
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
    try{const result=await importDroppedCases(plan,drag,folderId,insertion);if(!result)return;for(const id of drag.caseIds||[drag.id])state.importSelection?.delete(id);for(const id of drag.folderIds||[])state.importFolderSelection?.delete(id);state.planCollapsed?.delete(folderId);saveFolderExpansions();await refresh();toast(`Imported: ${result.added.length}; updated: ${result.updated.length}; skipped: ${result.skipped.length}.`);}
    finally{state.importBusy=false;}return;
   }
   if(drag.kind==='batch'){await api(`/api/plans/${plan.id}/items/move`,'POST',{folder_ids:drag.folder_ids,case_ids:drag.case_ids,folder_id:folderId,...insertion});planSelection().clear();}
   else if(drag.kind==='case')await api(`/api/plans/${plan.id}/testcases/move`,'POST',{testcase_ids:[drag.id],folder_id:folderId,...insertion});
   else{const target=plan.folders.find(f=>f.id===folderId);await api(`/api/folders/${drag.id}`,'PATCH',mode==='inside'?{parent_id:folderId}:{parent_id:target.parent_id,relative_to:folderId,insertion:mode});}
   state.planCollapsed?.delete(folderId);saveFolderExpansions();await refresh();toast(drag.kind==='case'?'Test Case moved.':'Folder moved.');
  }catch(error){toast(error.message,true);}
 }else if(repositoryDrag){
  event.preventDefault();const dest=repositoryDestination(event.target.closest(repositoryTargets),event),drag=repositoryDrag;
  repositoryDrag=null;clearRepositoryDrop(true);if(!dest)return;
  const {folder,caseId,mode}=dest,insertion=caseId?{relative_to:caseId,insertion:mode}:{};
  try{
   if(drag.kind==='batch'){await api('/api/repository/batch','POST',{...drag,action:'move',folder_id:folder.id,...insertion});state.repositorySelection.clear();}
   else if(drag.kind==='case')await api(`/api/repository/testcases/${drag.id}/folder`,'PUT',{folder_id:folder.id,...insertion});
   else await api(`/api/repository/folders/${drag.id}`,'PATCH',mode==='inside'?{parent_id:folder.id}:{parent_id:folder.parent_id,relative_to:folder.id,insertion:mode});
   state.repositoryCollapsed?.delete(folder.id);saveFolderExpansions();await draw();toast(drag.kind==='case'?'Test Case moved.':'Folder moved.');
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
    if(planId){state.planCollapsed?.delete(folder);saveFolderExpansions();await refresh();toast('Test Case added.');return;}
    state.repositoryCollapsed?.delete(folder);saveFolderExpansions();state.repositoryFolder=folder;
    if(state.route[0]==='repository')await draw();
    toast('Standard Test Case imported with a new source timestamp.');
  }catch(error){toast(error.message,true);}
  finally{state.repositoryImporting=false;picker.value='';}
});
$('#plan-create-dialog').addEventListener('cancel',event=>{if(state.creatingPlan)event.preventDefault();else state.dirty=false;});
window.addEventListener('hashchange',()=>navigate().catch(e=>toast(e.message,true)));
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});
async function selectFloatingCase(row){
 if(!CaseWindows.isOpen())return;
 if(state.dirty&&!discard())return;state.dirty=false;
 const {plan}=context();const ref=row.hasAttribute('data-plan-case')?planCaseReference(plan,row.dataset.planCase):repositoryCaseReference(row.dataset.repositoryId);
 if(state.importSource){state.importSource=null;await draw();}
 await CaseWindows.select(ref);
}
document.addEventListener('click',event=>{
 if(event.target.closest('button,input,select,a,label'))return;
 const row=event.target.closest('#repository-table [data-plan-case],#repository-table [data-repository-id]');if(row&&!row.closest('[inert]'))selectFloatingCase(row).catch(e=>toast(e.message,true));
});
document.addEventListener('keydown',event=>{
 if(event.key!=='Enter'||!event.target.matches('#repository-table [data-plan-case],#repository-table [data-repository-id]'))return;
 event.preventDefault();selectFloatingCase(event.target).catch(e=>toast(e.message,true));
});
CaseWindows.configure({api,renderFields:parameterFields,onSaved:async()=>{await refresh();toast('Parameters saved.');},onError:error=>toast(error.message,true),onSelected:ref=>{
 for(const row of document.querySelectorAll('[data-plan-case],[data-repository-id]')){const selected=ref.kind==='plan'?row.dataset.planCase===ref.caseId&&context().plan?.id===ref.planId:row.dataset.repositoryId===ref.caseId;row.toggleAttribute('data-window-selected',selected);}
}});
sizeGlobalNavigation();
$('#theme-toggle').innerHTML=icon('sun');
function theme(value){document.documentElement.dataset.theme=value;localStorage.setItem('bmc-theme',value);$('#theme-toggle').setAttribute('aria-label',`Switch to ${value==='dark'?'light':'dark'} theme`);}
theme(localStorage.getItem('bmc-theme')||'light');$('#theme-toggle').onclick=()=>theme(document.documentElement.dataset.theme==='dark'?'light':'dark');
refresh(false).then(navigate).catch(e=>{$('#workspace').setAttribute('aria-busy','false');$('#workspace').innerHTML=empty('Unable to load BMC Agent',e.message,button('Retry','retry','primary'));toast(e.message,true);});
document.addEventListener('click',event=>{if(event.target.closest('[data-action=retry]'))refresh(false).then(navigate).catch(e=>toast(e.message,true));});
})();

/* Match Task List's viewport bottom spacing for the normal Plan list. */
let planListSizeFrame=0;
function schedulePlanListSize(){
 if(planListSizeFrame)return;
 planListSizeFrame=requestAnimationFrame(()=>{
  planListSizeFrame=0;
  const layout=document.querySelector('body.plan-workspace #workspace .repository-layout');
  if(!layout||layout.closest('[inert],dialog'))return;
  const height=Math.max(120,window.innerHeight-layout.getBoundingClientRect().top-24)+'px';
  if(layout.style.getPropertyValue('--plan-list-height')!==height)layout.style.setProperty('--plan-list-height',height);
 });
}
new MutationObserver(schedulePlanListSize).observe(document.getElementById('workspace'),{childList:true,subtree:true});
new ResizeObserver(schedulePlanListSize).observe(document.getElementById('workspace'));
window.addEventListener('resize',schedulePlanListSize);
schedulePlanListSize();
