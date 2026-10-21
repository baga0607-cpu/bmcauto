'use strict';
window.TaskManagement = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const day = value => Date.parse(value + 'T00:00:00Z') / 86400000;
  const iso = value => new Date(value * 86400000).toISOString().slice(0,10);
  const link = task => `#/project/${encodeURIComponent(task.project_id)}/plan/${encodeURIComponent(task.plan_id)}/task/${encodeURIComponent(task.id)}`;
  const action = (label, name, task) => `<button type="button" class="small-button ${name==='manager-delete'?'danger':''}" data-action="${name}" data-id="${escape(task.id)}" aria-label="${label} ${escape(task.name)}" ${task.locked?'disabled':''}>${label}</button>`;
  const scheduled = task => Boolean(task.setup.start_date && task.setup.end_date && Number.isFinite(day(task.setup.start_date)) && Number.isFinite(day(task.setup.end_date)));

  function filter(tasks, value) {
    const query = value.trim().toLowerCase();
    return tasks.filter(t => `${t.name} ${t.project_name} ${t.plan_name}`.toLowerCase().includes(query));
  }

  function table(tasks, searching=false) {
    if (!tasks.length) return `<div class="empty"><h3>${searching?'No matching Tasks':'No Tasks yet'}</h3><p>${searching?'Try another Task, Project or Plan.':'Create your first Task to define its planned dates.'}</p></div>`;
    return `<div class="table-wrap"><table class="managed-tasks"><thead><tr><th>Task</th><th>Project / Plan</th><th>Start date</th><th>End date</th><th>Scope</th><th>Execution</th><th>Actions</th></tr></thead><tbody>${tasks.map(t=>`<tr data-task-id="${escape(t.id)}"><td><a href="${link(t)}">${escape(t.name)}</a></td><td>${escape(t.project_name)}<p class="help">${escape(t.plan_name)}</p></td><td>${escape(t.setup.start_date||'—')}</td><td>${escape(t.setup.end_date||'—')}</td><td>${t.scope_count} ${t.scope_count===1?'case':'cases'}</td><td><span class="status ${t.execution_active?'running':''}">${t.execution_active?'Running':'Idle'}</span>${t.locked?'<p class="help">Plan locked</p>':''}</td><td><div class="actions">${action('Edit','manager-edit',t)}${action('Delete','manager-delete',t)}</div></td></tr>`).join('')}</tbody></table></div>`;
  }

  function gantt(tasks) {
    if (!tasks.length) return '<div class="empty"><p>No Tasks to display on the timeline.</p></div>';
    const dated = tasks.filter(scheduled);
    const today = day(new Date().getFullYear()+'-'+String(new Date().getMonth()+1).padStart(2,'0')+'-'+String(new Date().getDate()).padStart(2,'0'));
    const first = dated.length ? Math.min(...dated.map(t=>day(t.setup.start_date)))-1 : today-3;
    const last = dated.length ? Math.max(...dated.map(t=>day(t.setup.end_date)))+2 : today+11;
    const total = last-first;
    const step = Math.max(1, Math.ceil(total/8));
    const ticks=[];
    for(let value=first;value<last;value+=step) ticks.push(`<span style="left:${100*(value-first)/total}%">${escape(new Date(value*86400000).toLocaleDateString('en-GB',{day:'2-digit',month:'short',timeZone:'UTC'}))}</span>`);
    const todayLine = today>=first && today<last ? `<i class="gantt-today" style="left:${100*(today-first)/total}%" aria-hidden="true"></i>` : '';
    return `<div class="toolbar"><p class="help">${escape(iso(first))} to ${escape(iso(last-1))} · ${dated.length} scheduled · ${tasks.length-dated.length} unscheduled</p><span class="help">Planned dates · daily scale</span></div><div class="gantt-scroll"><div class="gantt" style="--grid-step:${100*step/total}%"><div class="gantt-heading"><strong>Task</strong><div class="gantt-scale">${ticks.join('')}</div></div>${tasks.map(t=>{
      const hasDates=scheduled(t), start=day(t.setup.start_date), end=day(t.setup.end_date);
      const description=hasDates?`${t.name}: ${t.setup.start_date} to ${t.setup.end_date}`:`${t.name}: not scheduled`;
      return `<div class="gantt-row"><div class="gantt-label"><a href="${link(t)}">${escape(t.name)}</a><span class="help">${escape(t.project_name)} / ${escape(t.plan_name)}</span></div><div class="gantt-track">${todayLine}${hasDates?`<a class="gantt-bar ${t.execution_active?'is-running':''}" href="${link(t)}" style="left:${100*(start-first)/total}%;width:${100*(end-start+1)/total}%" title="${escape(description)}" aria-label="${escape(description)}"><span>${end-start+1}d</span></a>`:'<span class="gantt-unscheduled">Not scheduled</span>'}</div></div>`;
    }).join('')}</div></div>`;
  }

  function content(tasks, query, tab='schedule') {
    const visible=filter(tasks,query);
    if(['list','my-task'].includes(tab))return `<section aria-labelledby="task-list-title"><div class="toolbar"><h2 id="task-list-title">Task List</h2><span class="help">${visible.length} of ${tasks.length} Tasks</span></div>${table(visible,Boolean(query.trim()))}</section>`;
    return `<section aria-labelledby="task-timeline-title"><h2 id="task-timeline-title">Task Timeline</h2>${gantt(visible)}</section>`;
  }

  function planOptions(project, selected) {
    return `<option value="">${project&&!project.plans.length?'No Plans in this Project':'Select Plan'}</option>`+ (project?.plans||[]).map(p=>`<option value="${escape(p.id)}" ${selected===p.id?'selected':''} ${p.locked?'disabled':''}>${escape(p.name)}${p.locked?' (execution active)':''}</option>`).join('');
  }

  function form(projects, task=null) {
    const setup=task?.setup||{}, project=projects.find(p=>p.id===task?.project_id);
    return `<form id="task-manager-form" class="task-manager-form" data-task-id="${escape(task?.id||'')}"><h2>${task?'Edit Task':'New Task'}</h2><div class="fields"><label class="field full"><span>Task name</span><input name="name" required maxlength="255" value="${escape(task?.name||'')}" autocomplete="off"></label><label class="field"><span>Project</span><select id="manager-project" required ${task?'disabled':''}><option value="">Select Project</option>${projects.map(p=>`<option value="${escape(p.id)}" ${task?.project_id===p.id?'selected':''}>${escape(p.name)}</option>`).join('')}</select></label><label class="field"><span>Plan</span><select name="plan_id" id="manager-plan" required ${task?'disabled':''}>${planOptions(project,task?.plan_id)}</select></label><label class="field"><span>Start date</span><input type="date" name="start_date" value="${escape(setup.start_date||'')}" ${setup.end_date?'required':''}></label><label class="field"><span>End date</span><input type="date" name="end_date" value="${escape(setup.end_date||'')}" ${setup.start_date?`required min="${escape(setup.start_date)}"`:''}></label><label class="field full"><span>Notes</span><textarea name="notes" rows="3">${escape(setup.notes||'')}</textarea></label></div><p class="help">${task?'Project and Plan stay fixed. ':''}Leave both dates empty for an unscheduled Task. Dates do not automatically start execution.</p><div class="form-actions"><button class="primary">${task?'Save Task':'Create Task'}</button><button type="button" data-action="close-panel">Cancel</button></div></form>`;
  }

  return {content, form, planOptions, link};
})();
