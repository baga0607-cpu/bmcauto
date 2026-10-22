'use strict';
window.TaskManagement = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const day = value => Date.parse(value + 'T00:00:00Z') / 86400000;
  const iso = value => new Date(value * 86400000).toISOString().slice(0,10);
  const link = task => task.task_type==='Plan'? `#/project/${encodeURIComponent(task.project_id)}/plans` : `#/project/${encodeURIComponent(task.project_id)}/plan/${encodeURIComponent(task.plan_id)}/task/${encodeURIComponent(task.id)}`;
  const infoLink = task => task.task_type==='Plan'?`#/tasks/info/${encodeURIComponent(task.id)}`:link(task)+'/info';
  const action = (label, name, task) => `<button type="button" class="small-button ${name==='manager-delete'?'danger':''}" data-action="${name}" data-id="${escape(task.id)}" aria-label="${label} ${escape(task.name)}" ${task.locked?'disabled':''}>${label}</button>`;
  const scheduled = task => Boolean(task.setup.start_date && task.setup.end_date && Number.isFinite(day(task.setup.start_date)) && Number.isFinite(day(task.setup.end_date)));

  function filter(tasks, value) {
    const query = value.trim().toLowerCase();
    return tasks.filter(t => `${t.name} ${t.project_name} ${t.sku_name||""} ${t.plan_name}`.toLowerCase().includes(query));
  }

  function table(tasks, searching=false) {
    if (!tasks.length) return `<div class="empty"><h3>${searching?'No matching Tasks':'No Tasks yet'}</h3><p>${searching?'Try another Task, Project or Plan.':'Create your first Task to define its planned dates.'}</p></div>`;
    return `<div class="table-wrap"><table class="managed-tasks"><thead><tr><th>Task</th><th>Task Type</th><th>Project / SKU / Plan</th><th>Start date</th><th>End date</th><th>Working days</th><th>Scope</th><th>Execution</th><th>Actions</th></tr></thead><tbody>${tasks.map(t=>`<tr data-task-id="${escape(t.id)}"><td><a href="${link(t)}">${escape(t.name)}</a></td><td data-no-translate>${escape(t.task_type||"Test")}</td><td>${escape(t.project_name)}<p class="help">${escape(t.sku_name||"")}</p><p class="help">${escape(t.plan_name)}</p></td><td>${escape(t.setup.start_date||'—')}</td><td>${escape(t.setup.end_date||'—')}</td><td>${t.working_days??'—'}</td><td>${t.task_type==='Plan'?'—':t.scope_count+' '+(t.scope_count===1?'case':'cases')}</td><td><span class="status ${t.execution_active?'running':''}">${t.task_type==='Plan'?'—':t.execution_active?'Running':'Idle'}</span>${t.locked?'<p class="help">Plan locked</p>':''}</td><td><div class="actions">${action('Edit','manager-edit',t)}${action('Delete','manager-delete',t)}</div></td></tr>`).join('')}</tbody></table></div>`;
  }

let calendar=null, viewStart=null, selectedDay=null, selectedTask=null, scheduleTasks=[], scheduleApi, redraw, notify;
  const cellWidth=48;
  const todayISO=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function calendarRange(tasks){
    const dated=tasks.filter(scheduled),today=day(todayISO());
    const first=Math.min(today-60,...dated.map(t=>day(t.setup.start_date)-7));
    const last=Math.max(today+60,...dated.map(t=>day(t.setup.end_date)+7));
    viewStart=iso(Math.max(day('0001-01-01'),first));
    return {start:viewStart,end:iso(Math.min(last,day('9999-12-31')))};
  }
  function setCalendar(value){calendar=value;}
  function gantt(tasks){
    scheduleTasks=tasks;
    const dates=calendar?.days||[],first=day(calendar?.start||viewStart),today=todayISO();
    const unknown=dates.some(d=>!d.covered)||tasks.some(t=>!t.calendar_complete);
    return `
      ${unknown?'<p class="notice info">Official holidays cover 2025–2027. Other years use weekends only; set holidays manually.</p>':''}
      <div class="gantt-scroll" tabindex="0" role="region" aria-label="Task schedule"><div class="gantt" style="--schedule-days:${dates.length};--day-width:${cellWidth}px">
      <div class="gantt-heading"><strong>Task</strong><div class="gantt-scale">${dates.map(d=>`<button type="button" class="schedule-date ${d.is_working?'':'is-off'} ${d.overridden?'is-custom':''} ${d.date===today?'is-today':''}" data-schedule-action="day" data-date="${d.date}" aria-label="${d.date} — ${d.is_working?'Working day':'Non-working day'}${d.name?' — '+escape(d.name):''}" title="${escape(d.name||d.date)}"><span>${d.date.slice(5).replace('-','/')}</span><small>${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][new Date(d.date+'T00:00:00Z').getUTCDay()]}</small></button>`).join('')}</div></div>
      ${tasks.map(t=>{
        const hasDates=scheduled(t),start=day(t.setup.start_date),end=day(t.setup.end_date),left=Math.max(start,first),right=Math.min(end,first+dates.length-1);
        const description=hasDates?`${t.name}: ${t.setup.start_date} to ${t.setup.end_date} · ${t.working_days} working days`:`${t.name}: not scheduled`;
        return `<div class="gantt-row"><div class="gantt-label"><a href="${infoLink(t)}">${escape(t.name)}</a><span class="schedule-owner" data-no-translate>Owner: ${escape(t.setup.owner||'TBD')}</span></div><div class="gantt-track"><div class="gantt-days" aria-hidden="true">${dates.map(d=>`<i class="gantt-day ${d.is_working?'':'is-off'} ${d.date===today?'is-today':''}"></i>`).join('')}</div>${hasDates&&left<=right?`<button type="button" class="gantt-bar ${t.execution_active?'is-running':''}" data-schedule-action="task" data-task-id="${escape(t.id)}" ${t.locked?'disabled':''} style="left:${(left-first)*cellWidth+2}px;width:${(right-left+1)*cellWidth-4}px" title="${escape(description)}" aria-label="${escape(description)}"><span data-no-translate>${t.working_days}d</span></button>`:!hasDates?'<span class="gantt-unscheduled">Not scheduled</span>':'<span class="gantt-unscheduled">Outside displayed dates</span>'}</div></div>`;
      }).join('')}${!tasks.length?'<p class="schedule-empty">No Tasks to display on the timeline.</p>':''}</div></div>`;
  }
  function openDay(key){
    selectedDay=calendar.days.find(d=>d.date===key);if(!selectedDay)return;
    let dialog=document.getElementById('schedule-day-dialog');
    if(!dialog){dialog=document.createElement('dialog');dialog.id='schedule-day-dialog';dialog.setAttribute('aria-labelledby','schedule-day-title');document.body.append(dialog);}
    dialog.innerHTML=`<h2 id="schedule-day-title" data-no-translate>${selectedDay.date}</h2><fieldset class="schedule-day-choices"><legend class="sr-only">Day setting</legend><label><input type="radio" name="schedule-day-working" value="working" ${selectedDay.is_working?'checked':''}><span>Working day</span></label><label><input type="radio" name="schedule-day-working" value="off" ${selectedDay.is_working?'':'checked'}><span>Non-working day</span></label></fieldset><p id="schedule-day-error" role="alert"></p><div class="actions"><button type="button" data-schedule-action="cancel">Cancel</button><button type="button" class="primary" data-schedule-action="save">Save</button></div>`;
    dialog.showModal();
  }
  function openTask(id){
    selectedTask=scheduleTasks.find(t=>t.id===id);if(!selectedTask||selectedTask.locked)return;
    const task=selectedTask;
    let editor=document.getElementById('schedule-task-editor');
    if(!editor){editor=document.createElement('dialog');editor.id='schedule-task-editor';editor.setAttribute('aria-labelledby','schedule-task-title');document.body.append(editor);}
    editor.innerHTML=`<h2 id="schedule-task-title">Edit Task schedule</h2><p data-no-translate>${escape(task.name)}</p><div class="fields"><label class="field"><span>Start date</span><input type="date" id="schedule-task-start" required value="${escape(task.setup.start_date)}"></label><label class="field"><span>End date</span><input type="date" id="schedule-task-end" required min="${escape(task.setup.start_date)}" value="${escape(task.setup.end_date)}"></label><label class="field full"><span>History — reason for schedule change</span><textarea id="schedule-task-history" rows="3" maxlength="4000" required></textarea></label></div><p id="schedule-task-error" class="plan-create-error" role="alert"></p><div class="form-actions"><button type="button" class="primary" data-schedule-action="task-save">Save schedule</button><button type="button" data-schedule-action="task-cancel">Cancel</button></div>`;
    editor.showModal();
    document.getElementById('schedule-task-start').focus();
  }
  function centerToday(scroll){
    if(!scroll||!calendar)return;
    const index=day(todayISO())-day(calendar.start);
    scroll.scrollLeft=index*cellWidth+cellWidth/2-(scroll.clientWidth-280)/2;
  }

  function sizeSchedule(){
    const scroll=document.querySelector('.gantt-scroll');
    if(!scroll)return;
    const available=window.innerHeight-scroll.getBoundingClientRect().top-24;
    scroll.style.setProperty('--schedule-height',Math.max(120,available)+'px');
  }

  function bindSchedule(api,refresh,toast){
    sizeSchedule();
    centerToday(document.querySelector('.gantt-scroll'));
    scheduleApi=api;redraw=refresh;notify=toast;
    if(document.documentElement.dataset.scheduleBound)return;
    document.documentElement.dataset.scheduleBound='true';
    window.addEventListener('resize',sizeSchedule);
    let dragging=null, suppressClick=false;
    document.addEventListener('pointerdown',event=>{
      const track=event.target.closest('.gantt-track');
      if(event.button!==0||event.pointerType!=='mouse'||!track||event.target.closest('a,button,input,select,textarea'))return;
      const scroll=track.closest('.gantt-scroll');
      dragging={scroll,pointerId:event.pointerId,x:event.clientX,left:scroll.scrollLeft,moved:false};
      scroll.setPointerCapture(event.pointerId);scroll.focus({preventScroll:true});
      event.preventDefault();
    });
    document.addEventListener('pointermove',event=>{
      if(!dragging||event.pointerId!==dragging.pointerId)return;
      const distance=event.clientX-dragging.x;
      if(!dragging.moved&&Math.abs(distance)<4)return;
      dragging.moved=true;dragging.scroll.classList.add('is-dragging');
      dragging.scroll.scrollLeft=dragging.left-distance;
      event.preventDefault();
    });
    const endDrag=event=>{
      if(!dragging||event.pointerId!==dragging.pointerId)return;
      const {scroll,pointerId,moved}=dragging;
      dragging=null;scroll.classList.remove('is-dragging');suppressClick=moved;
      if(scroll.hasPointerCapture(pointerId))scroll.releasePointerCapture(pointerId);
    };
    document.addEventListener('pointerup',endDrag);
    document.addEventListener('pointercancel',endDrag);
    document.addEventListener('lostpointercapture',endDrag);
    document.addEventListener('click',event=>{
      if(!suppressClick)return;suppressClick=false;
      if(event.target.closest('.gantt-scroll')){event.preventDefault();event.stopImmediatePropagation();}
    },true);
    document.addEventListener('click',async event=>{
      const control=event.target.closest('[data-schedule-action]');if(!control)return;
      const action=control.dataset.scheduleAction;
      if(action==='task'){openTask(control.dataset.taskId);return;}
      if(action==='task-cancel'){document.getElementById('schedule-task-editor').close();document.querySelector('[data-task-id="'+selectedTask.id+'"]')?.focus();return;}
      if(action==='day'){openDay(control.dataset.date);return;}
      if(action==='task-save'){
        const fields=['schedule-task-start','schedule-task-end','schedule-task-history'].map(id=>document.getElementById(id));
        fields[1].min=fields[0].value;
        if(!fields.every(field=>field.reportValidity()))return;
      }
      if(action==='cancel'){document.getElementById('schedule-day-dialog').close();document.querySelector('[data-date="'+selectedDay.date+'"]')?.focus();return;}
      control.disabled=true;
      const scroll=document.querySelector('.gantt-scroll'),position=scroll?{left:scroll.scrollLeft,top:scroll.scrollTop}:null;
      try{
        if(action==='task-save'){
          await scheduleApi('/api/tasks/'+selectedTask.id+'/schedule','PATCH',{start_date:document.getElementById('schedule-task-start').value,end_date:document.getElementById('schedule-task-end').value,history:document.getElementById('schedule-task-history').value,expected_start_date:selectedTask.setup.start_date||'',expected_end_date:selectedTask.setup.end_date||''});
          document.getElementById('schedule-task-editor').close();
        }
        if(action==='save'){
          const setting=document.querySelector('#schedule-day-dialog input:checked').value;
          await scheduleApi('/api/schedule/calendar/'+selectedDay.date,'PATCH',{is_working:setting==='working',expected_is_working:selectedDay.is_working});
          document.getElementById('schedule-day-dialog').close();
        }
        await redraw();
        const next=document.querySelector('.gantt-scroll');
        if(next&&position)next.scrollTop=position.top;
        if(next&&action==='today'){
          centerToday(next);
        }else if(next&&position)next.scrollLeft=position.left;
        if(action==='task-save'){notify('Task schedule saved.');document.querySelector('[data-task-id="'+selectedTask.id+'"]')?.focus({preventScroll:true});}
        if(action==='save'){notify('Calendar day saved.');document.querySelector('[data-date="'+selectedDay.date+'"]')?.focus({preventScroll:true});}
      }catch(error){const message=document.getElementById(action==='task-save'?'schedule-task-error':'schedule-day-error');if(['save','task-save'].includes(action)&&message)message.textContent=error.message;else notify(error.message,true);}
      finally{control.disabled=false;}
    });

  }

  function content(tasks, query, tab='schedule') {
    const visible=filter(tasks,query);
    if(['list','my-task'].includes(tab))return `<section aria-labelledby="task-list-title"><div class="toolbar"><h2 id="task-list-title">Task List</h2><span class="help">${visible.length} of ${tasks.length} Tasks</span></div>${table(visible,Boolean(query.trim()))}</section>`;
    return `<section aria-label="Schedule">${gantt(visible)}</section>`;
  }

  function historyList(rows){
    const period=(start,end)=>escape(start||'—')+' ~ '+escape(end||'—');
    const stamp=value=>new Date(value).toLocaleString('sv-SE',{timeZone:'Asia/Taipei',hour12:false});
    return `<section class="task-history" aria-label="History List"><h2 data-no-translate>History List</h2>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Time (Taipei)</th><th>Previous dates</th><th>New dates</th><th data-no-translate>History</th></tr></thead><tbody>${rows.map(row=>`<tr><td data-no-translate>${escape(stamp(row.created_at))}</td><td data-no-translate>${period(row.previous_start_date,row.previous_end_date)}</td><td data-no-translate>${period(row.start_date,row.end_date)}</td><td class="history-text" data-no-translate>${escape(row.history)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="help">No History yet.</p>'}</section>`;
  }

  function planningInfo(task){
    const setup=task.setup||{};
    const fields=[['Task Type',task.task_type],['Project',task.project_name],['SKU name',task.sku_name||'—'],['Owner',setup.owner||'TBD'],['Start date',setup.start_date||'—'],['End date',setup.end_date||'—'],['Working days',task.working_days??'—']];
    return `<div class="page-heading"><h1 data-no-translate>${escape(task.name)}</h1><div class="actions">${action('Edit','manager-edit',task)}</div></div><dl class="planning-task-info">${fields.map(([label,value])=>`<div><dt>${label}</dt><dd data-no-translate>${escape(value)}</dd></div>`).join('')}</dl><h2>Notes</h2><p class="task-info-notes" data-no-translate>${escape(setup.notes||'—')}</p>`;
  }

  function planOptions(project, selected) {
    return `<option value="">${project&&!project.plans.length?'No Plans in this Project':'Select Plan'}</option>`+ (project?.plans||[]).map(p=>`<option value="${escape(p.id)}" ${selected===p.id?'selected':''} ${p.locked?'disabled':''}>${escape(p.name)}${p.locked?' (execution active)':''}</option>`).join('');
  }


  function form(projects, task=null, owners=['TBD']) {
    const setup=task?.setup||{}, fixed=task?'disabled':'';
    const option=(value,label,selected=false)=>`<option value="${escape(value)}" ${selected?'selected':''} data-no-translate>${escape(label)}</option>`;
    const project=projects.find(p=>p.id===task?.project_id), sku=project?.skus.find(s=>s.id===task?.sku_id);
    const owner=setup.owner||'TBD', ownerNames=[...new Set(['TBD',...owners,owner])];
    return `<form id="task-manager-form" class="task-manager-form" data-task-id="${escape(task?.id||'')}" data-start-date="${escape(setup.start_date||'')}" data-end-date="${escape(setup.end_date||'')}" data-owner="${escape(owner)}"><h2>${task?'Edit Task':'New Task'}</h2><div class="fields">
      <label class="field full"><span>Task Type</span><select name="task_type" id="manager-type" required ${fixed}><option value="">Select Task Type</option>${option('Plan','Plan',task?.task_type==='Plan')}${option('Test','Test',Boolean(task)&&task.task_type!=='Plan')}</select></label>
      <label class="field"><span>Project</span><select name="project_id" id="manager-project" required disabled><option value="">Select Project</option>${projects.map(p=>option(p.id,p.name,task?.project_id===p.id)).join('')}</select></label>
      <label class="field"><span>SKU name</span><select name="sku_id" id="manager-sku" disabled><option value="">${project?.skus.length?'Select SKU':'No SKUs'}</option>${project?.skus.map(s=>option(s.id,s.full_name,s.id===task?.sku_id)).join('')||''}${task?.sku_id&&!sku?option(task.sku_id,task.sku_name||task.sku_id,true):''}</select></label>
      <label class="field full"><span>Plan</span><select name="plan_id" id="manager-plan" disabled><option value="">Select Plan</option>${task?.plan_id?option(task.plan_id,task.plan_name,true):''}</select></label>
      <label class="field"><span>Start date</span><input type="date" name="start_date" value="${escape(setup.start_date||'')}" ${setup.end_date?'required':''}></label>
      <label class="field"><span>End date</span><input type="date" name="end_date" value="${escape(setup.end_date||'')}" ${setup.start_date?`required min="${escape(setup.start_date)}"`:''}></label>
      ${task?'<label class="field full" id="manager-history-field" hidden><span>History — reason for schedule change</span><textarea name="history" id="manager-history" rows="3" maxlength="4000" disabled></textarea><span class="help" id="manager-owner-history" data-no-translate hidden></span></label>':''}
      <label class="field full"><span data-no-translate>Owner</span><select name="owner" id="manager-owner" required>${ownerNames.map(name=>option(name,name,name===owner)).join('')}</select></label>
      <label class="field full"><span>Task name</span><input name="name" id="manager-name" readonly value="${escape(task?.name||'')}" aria-describedby="manager-name-help"><span class="help" id="manager-name-help">Task name is generated automatically.</span></label>
      
      <label class="field full"><span>Notes</span><textarea name="notes" rows="3">${escape(setup.notes||'')}</textarea></label></div>
      <p class="help">Leave both dates empty for an unscheduled Task. Dates do not automatically start execution.</p>
      <p id="manager-form-error" class="plan-create-error" role="alert"></p>
      <div class="form-actions"><button type="submit" class="primary" ${task?'':'disabled'}>${task?'Save Task':'Create Task'}</button><button type="button" data-action="close-panel">Cancel</button></div></form>`;
  }

  function bindForm(projects, api) {
    const form=document.getElementById('task-manager-form');
    if(!form)return;
    if(form.dataset.taskId){
      let mode='none',scheduleReason='';
      const updateHistory=()=>{
        const changed=form.elements.start_date.value!==(form.dataset.startDate||'')||form.elements.end_date.value!==(form.dataset.endDate||'');
        const ownerChanged=form.elements.owner.value!==(form.dataset.owner||'TBD');
        const field=form.querySelector('#manager-history-field'),input=form.elements.history,preview=form.querySelector('#manager-owner-history');
        const ownerMessage='Owner: '+(form.dataset.owner||'TBD')+' → '+form.elements.owner.value;
        if(mode==='date')scheduleReason=input.value;
        const next=changed?'date':ownerChanged?'owner':'none';
        field.hidden=next==='none';input.disabled=next==='none';input.required=changed;input.readOnly=next==='owner';
        if(next==='date'&&mode!=='date')input.value=scheduleReason;
        if(next==='owner')input.value=ownerMessage;
        field.querySelector('span').textContent=changed?'History — reason for schedule change':'History';
        preview.hidden=!(changed&&ownerChanged);preview.textContent=ownerMessage;
        mode=next;
      };
      form.addEventListener('input',updateHistory);form.addEventListener('change',updateHistory);updateHistory();return;
    }
    const type=form.elements.task_type, project=form.elements.project_id, sku=form.elements.sku_id, plan=form.elements.plan_id, name=form.elements.name;
    const error=form.querySelector('#manager-form-error'), submit=form.querySelector('[type=submit]');
    let version=0;
    const fill=(select,placeholder,items)=>{
      select.replaceChildren(new Option(placeholder,''));
      for(const item of items){const option=new Option(item.full_name||item.name,item.id);option.dataset.noTranslate='';option.disabled=Boolean(item.locked);select.add(option);}
    };
    form.addEventListener('change',async event=>{
      if(![type,project,sku,plan].includes(event.target))return;
      const current=++version;form.dataset.nameReady='';name.value='';error.textContent='';submit.disabled=true;
      if(event.target===type){project.value='';project.disabled=!type.value;}
      const selected=projects.find(p=>p.id===project.value);
      if([type,project].includes(event.target)){
        fill(sku,selected?.skus.length?'Select SKU':'No SKUs',selected?.skus||[]);
        sku.disabled=!selected?.skus.length;sku.required=Boolean(selected?.skus.length);
      }
      if(event.target!==plan){
        const available=(selected?.plans||[]).filter(p=>!selected.skus.length||p.sku_id===sku.value);
        fill(plan,type.value==='Plan'?'Not applicable':available.length?'Select Plan':'No Plans for this SKU',type.value==='Plan'?[]:available);
      }
      plan.disabled=type.value!=='Test'||!selected||(selected.skus.length>0&&!sku.value);
      plan.required=type.value==='Test';
      if(!type.value||!selected||(!sku.disabled&&!sku.value)||(type.value==='Test'&&!plan.value))return;
      const params=new URLSearchParams({task_type:type.value,project_id:project.value,sku_id:sku.disabled?'':sku.value,plan_id:plan.disabled?'':plan.value});
      try{
        const result=await api('/api/tasks/name-preview?'+params);
        if(current!==version||!form.isConnected)return;
        name.value=result.name;form.dataset.nameReady='true';submit.disabled=false;
      }catch(e){if(current===version&&form.isConnected)error.textContent=e.message;}
    });
  }
  return {content, historyList, planningInfo, infoLink, form, planOptions, link, bindForm, calendarRange, setCalendar, bindSchedule};
})();
