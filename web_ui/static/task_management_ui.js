'use strict';
window.KeywordSearch=Object.freeze({
  matches(text,query){
    const value=String(text??'').toLowerCase();
    return String(query??'').split(',').map(word=>word.trim().toLowerCase()).filter(Boolean).every(word=>value.includes(word));
  }
});
window.TaskManagement = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const day = value => Date.parse(value + 'T00:00:00Z') / 86400000;
  const iso = value => new Date(value * 86400000).toISOString().slice(0,10);
  const link = task => task.task_type==='Plan'? `#/project/${encodeURIComponent(task.project_id)}/plans` : `#/project/${encodeURIComponent(task.project_id)}/plan/${encodeURIComponent(task.plan_id)}/task/${encodeURIComponent(task.id)}`;
  const infoLink = task => `#/tasks/info/${encodeURIComponent(task.id)}`;
  const action = (label, name, task) => `<button type="button" class="small-button ${name==='manager-delete'?'danger':''}" data-action="${name}" data-id="${escape(task.id)}" aria-label="${label} ${escape(task.name)}" ${task.locked?'disabled':''}>${label}</button>`;
  const statuses=['Not Scheduled','New','On-Going','Complete','Cancel','Pending'];
  const statusOptions=value=>statuses.map(s=>`<option value="${s}" ${s===value?'selected':''} data-no-translate>${s}</option>`).join('');
  const scheduled = task => Boolean(task.setup.start_date && task.setup.end_date && Number.isFinite(day(task.setup.start_date)) && Number.isFinite(day(task.setup.end_date)));

  function bindDateRange(start,end){
    const sync=()=>{
      end.min=start.value;
      const invalid=Boolean(start.value&&end.value&&end.value<start.value);
      end.setCustomValidity(invalid?(document.documentElement.lang==='zh-Hant'?'結束日期不可早於開始日期。':'End date must be on or after start date.'):'');
    };
    start.addEventListener('input',sync);end.addEventListener('input',sync);
    start.addEventListener('change',sync);end.addEventListener('change',sync);sync();
  }

  function bindDateStatus(start,end,status,isNew=false){
    bindDateRange(start,end);
    const sync=()=>{
      const complete=Boolean(start.value&&end.value);
      if(!complete)status.value='Not Scheduled';
      else if(status.value==='Not Scheduled'||isNew)status.value='New';
      for(const option of status.options)option.disabled=complete?option.value==='Not Scheduled':option.value!=='Not Scheduled';
      status.disabled=isNew;
      end.min=start.value;
    };
    start.addEventListener('input',sync);end.addEventListener('input',sync);
    start.addEventListener('change',sync);end.addEventListener('change',sync);sync();
  }

  function filter(tasks, value) {
    const query = value.trim().toLowerCase();
    return tasks.filter(t => KeywordSearch.matches(`${t.name} ${t.project_name} ${t.sku_name||""} ${t.plan_name}`,query));
  }


  let tableTasks=[];
  const editLabels={task_status:'Status',start_date:'Plan Start Date',end_date:'Plan End Date',actual_start_date:'Actual Start Date',actual_end_date:'Actual End Date',owner:'Assignee'};
  const cellValue=(task,field)=>task.setup[field]||(field==='owner'?'TBD':field==='task_status'?'New':'');
  const editableCell=(task,field)=>`<td><button type="button" class="task-cell-edit" data-task-edit="${field}" aria-label="${editLabels[field]} — ${escape(cellValue(task,field)||'—')}" title="Double-click or press Enter to edit&#10;${escape(cellValue(task,field)||'—')}" ${task.locked?'disabled':''} data-no-translate>${escape(cellValue(task,field)||'—')}</button></td>`;
  const defaultComponents=['BL','1BMC','BMConf'];
  function referenceValue(setup){
    const ref=setup.idesign||{};let valid=false;try{valid=['http:','https:'].includes(new URL(ref.hyperlink).protocol);}catch{}
    return ref.request_id&&valid?`<a href="${escape(ref.hyperlink)}" target="_blank" rel="noopener noreferrer" title="${escape(ref.request_id)}" data-no-translate>${escape(ref.request_id)}</a>`:'<span>—</span>';
  }
  function packageItems(setup){
    const items=setup.fw_package||[];
    return [...defaultComponents.map(component=>({component,version:items.find(item=>item.component.toLowerCase()===component.toLowerCase())?.version||''})),...items.filter(item=>!defaultComponents.some(name=>name.toLowerCase()===item.component.toLowerCase()))];
  }
  function packageValue(setup,summary=false){
    const items=packageItems(setup).filter(item=>!summary||['1BMC','BMConf'].includes(item.component));
    return items.map(item=>`<span class="fw-package-line" data-no-translate><strong>${escape(item.component)}</strong>: ${escape(item.version||'—')}</span>`).join('');
  }
  const referenceDisplay=task=>referenceValue(task.setup);
  const packageDisplay=task=>task.task_type==='Test'?packageValue(task.setup):'<span>—</span>';
  const referenceCell=task=>`<td class="task-reference-cell" data-task-meta="idesign" data-task-id="${escape(task.id)}" tabindex="${task.locked?'-1':'0'}" title="Double-click or press Enter to edit">${referenceValue(task.setup)}</td>`;
  function packageCell(task){
    if(task.task_type!=='Test')return '<td>—</td>';
    const full=packageItems(task.setup).map(item=>item.component+': '+(item.version||'—')).join('\n');
    return `<td><button type="button" class="task-cell-edit" data-task-meta="fw_package" data-task-id="${escape(task.id)}" title="${escape(full)}" aria-label="FW Package — ${escape(full)}" ${task.locked?'disabled':''}>${packageValue(task.setup,true)}</button></td>`;
  }
  const referenceFields=value=>`<fieldset class="task-reference-fields field full"><legend data-no-translate>iDesign ID</legend><div class="fields"><label class="field"><span>Request ID</span><input name="idesign_request_id" maxlength="200" value="${escape(value?.request_id||'')}"></label><label class="field"><span>Hyperlink</span><input name="idesign_hyperlink" type="url" pattern="https?://.+" maxlength="2048" value="${escape(value?.hyperlink||'')}"></label></div></fieldset>`;
  const packageRow=item=>`<div class="fw-package-row" ${defaultComponents.includes(item.component)?`data-fw-default="${escape(item.component)}"`:''}><label class="field"><span>Component</span><input data-fw-component maxlength="200" required value="${escape(item.component||'')}"></label><label class="field"><span>Version</span><input data-fw-version maxlength="255" ${!item.version&&defaultComponents.includes(item.component)?'':'required'} value="${escape(item.version||'')}"></label><button type="button" class="small-button danger" data-fw-remove>Remove</button></div>`;
  const packageFields=(items=[],enabled=true)=>`<fieldset class="task-fw-editor field full" ${enabled?'':'disabled'}><legend data-no-translate>FW Package</legend><div data-fw-rows>${packageItems({fw_package:items}).map(packageRow).join('')}</div><button type="button" class="small-button" data-fw-add>Add item</button><p class="help">FW Package is editable for Test Tasks only.</p></fieldset>`;
  function metadataValues(form){
    const result={},request=form.querySelector('[name="idesign_request_id"]'),packageEditor=form.querySelector('.task-fw-editor');
    if(request)result.idesign={request_id:request.value.trim(),hyperlink:form.querySelector('[name="idesign_hyperlink"]').value.trim()};
    if(packageEditor&&!packageEditor.disabled)result.fw_package=[...packageEditor.querySelectorAll('.fw-package-row')].filter(row=>!(row.dataset.fwDefault===row.querySelector('[data-fw-component]').value.trim()&&!row.querySelector('[data-fw-version]').value.trim())).map(row=>({component:row.querySelector('[data-fw-component]').value.trim(),version:row.querySelector('[data-fw-version]').value.trim()}));
    return result;
  }
  function bindMetadata(form){
    form.addEventListener('input',event=>{const row=event.target.closest('.fw-package-row');if(row)row.querySelector('[data-fw-version]').required=!(row.dataset.fwDefault===row.querySelector('[data-fw-component]').value.trim()&&!row.querySelector('[data-fw-version]').value.trim());});
    const request=form.querySelector('[name="idesign_request_id"]'),url=form.querySelector('[name="idesign_hyperlink"]');
    if(request){const sync=()=>{request.required=Boolean(url.value.trim());url.required=Boolean(request.value.trim());};request.addEventListener('input',sync);url.addEventListener('input',sync);sync();}
    form.addEventListener('click',event=>{
      const button=event.target.closest('[data-fw-add],[data-fw-remove]');if(!button||button.closest('fieldset').disabled)return;
      if(button.hasAttribute('data-fw-add')){const rows=form.querySelector('[data-fw-rows]');if(rows.children.length>=100)return;rows.insertAdjacentHTML('beforeend',packageRow({}));rows.lastElementChild.querySelector('input').focus();}
      else button.closest('.fw-package-row').remove();
      form.dispatchEvent(new Event('input',{bubbles:true}));
    });
  }
  async function openMetadata(control){
    const task=tableTasks.find(t=>t.id===control.dataset.taskId),field=control.dataset.taskMeta;
    if(!task||task.locked||!['idesign','fw_package'].includes(field)||field==='fw_package'&&task.task_type!=='Test')return;
    let dialog=document.getElementById('task-meta-dialog');if(dialog?.open)return;
    if(!dialog){dialog=document.createElement('dialog');dialog.id='task-meta-dialog';dialog.setAttribute('aria-labelledby','task-meta-title');document.body.append(dialog);}
    const original=task.setup[field]||(field==='idesign'?{}:[]);
    dialog.innerHTML=`<form id="task-meta-form"><h2 id="task-meta-title">Edit ${field==='idesign'?'iDesign ID':'FW Package'}</h2><p data-no-translate>${escape(task.name)}</p>${field==='idesign'?referenceFields(original):packageFields(original)}<p id="task-meta-error" class="plan-create-error" role="alert"></p><div class="form-actions"><button type="submit" class="primary">Save Task</button><button type="button" id="task-meta-cancel">Cancel</button></div></form>`;
    const form=dialog.querySelector('form');bindMetadata(form);let saving=false;
    dialog.oncancel=event=>{if(saving)event.preventDefault();};dialog.onclose=()=>{if(control.isConnected)control.focus({preventScroll:true});};
    form.querySelector('#task-meta-cancel').onclick=()=>dialog.close();
    form.onsubmit=async event=>{event.preventDefault();if(saving||!form.reportValidity())return;
      const changes=metadataValues(form),payload={setup:changes,['expected_'+field]:original};
      const scroll=document.querySelector('.managed-tasks-wrap'),position=scroll?{left:scroll.scrollLeft,top:scroll.scrollTop}:null;
      saving=true;for(const button of form.querySelectorAll('button'))button.disabled=true;
      try{await scheduleApi('/api/tasks/'+encodeURIComponent(task.id),'PATCH',payload);dialog.close();await redraw();const next=document.querySelector('.managed-tasks-wrap');if(next&&position){next.scrollLeft=position.left;next.scrollTop=position.top;}notify('Task updated.');}
      catch(error){if(dialog.open)form.querySelector('#task-meta-error').textContent=error.message;else notify(error.message,true);}
      finally{saving=false;for(const button of form.querySelectorAll('button'))button.disabled=false;}
    };
    dialog.showModal();(form.querySelector('input')||form.querySelector('[data-fw-add]')).focus();
  }

  const assignmentEdit=(task,field)=>`<button type="button" class="task-assignment-edit" data-task-edit="${field}" title="${escape(cellValue(task,field))}" aria-label="${editLabels[field]} — ${escape(cellValue(task,field))}" ${task.locked?'disabled':''}>${escape(cellValue(task,field))}</button>`;
  const taskLabel=task=>`<td class="task-list-label"><a href="${infoLink(task)}" title="${escape(task.name)}">${escape(task.name)}</a><span class="schedule-owner task-list-assignment" data-no-translate><span class="task-list-assignee">Assignee: ${assignmentEdit(task,'owner')}</span><span class="task-list-status">· Status: ${assignmentEdit(task,'task_status')}</span></span></td>`;
  function table(tasks, searching=false) {
    tableTasks=tasks;
    return `<div class="table-wrap managed-tasks-wrap" tabindex="0" role="region" aria-label="Task List"><table class="managed-tasks"><colgroup>${[25,11,16,9,9,9,9,12].map(width=>`<col style="width:${width}%">`).join('')}</colgroup><thead><tr><th>Task</th><th data-no-translate>iDesign ID</th><th data-no-translate>FW Package</th><th>Plan Start Date</th><th>Plan End Date</th><th>Actual Start Date</th><th>Actual End Date</th><th data-no-translate>Days (Actual/Plan)</th></tr></thead><tbody>${tasks.map(t=>`<tr data-task-id="${escape(t.id)}">${taskLabel(t)}${referenceCell(t)}${packageCell(t)}${['start_date','end_date','actual_start_date','actual_end_date'].map(field=>editableCell(t,field)).join('')}<td data-no-translate ${t.calendar_complete===false||t.actual_calendar_complete===false?'title="Official holidays cover 2025–2027. Other years use weekends only; set holidays manually."':''}>${t.actual_working_days??'—'} / ${t.working_days??'—'}</td></tr>`).join('')||'<tr><td colspan="8">No matching Tasks</td></tr>'}</tbody></table></div>`;
  }

  async function openCellEditor(control){
    const task=tableTasks.find(t=>t.id===control.closest('tr').dataset.taskId),field=control.dataset.taskEdit;
    if(!task||task.locked||!editLabels[field])return;
    let dialog=document.getElementById('task-cell-dialog');
    if(dialog?.open)return;
    const owners=field==='owner'?(await scheduleApi('/api/tasks/options')).owners||['TBD']:[];
    if(!control.isConnected)return;
    if(!dialog){dialog=document.createElement('dialog');dialog.id='task-cell-dialog';dialog.setAttribute('aria-labelledby','task-cell-title');document.body.append(dialog);}
    const original=cellValue(task,field),isOwner=field==='owner',isStatus=field==='task_status',isDate=field.endsWith('_date');
    const dateFields=field.startsWith('actual_')?['actual_start_date','actual_end_date']:['start_date','end_date'];
    const title=isDate?(field.startsWith('actual_')?'Edit Actual dates':'Edit Plan dates'):'Edit '+editLabels[field];
    const options=[...new Set(['TBD',...owners,original])];
    const editor=isOwner?`<select name="value">${options.map(value=>`<option value="${escape(value)}" ${value===original?'selected':''} data-no-translate>${escape(value)}</option>`).join('')}</select>`:isStatus?`<select name="value">${statusOptions(original)}</select>`:`<input type="date" name="value" value="${escape(original)}">`;
    const fields=isDate?`<div class="fields">${dateFields.map(key=>`<label class="field"><span>${editLabels[key]}</span><input type="date" name="${key}" value="${escape(cellValue(task,key))}"></label>`).join('')}</div>`:`<label class="field"><span>${editLabels[field]}</span>${editor}</label>`;
    dialog.innerHTML=`<form id="task-cell-form"><h2 id="task-cell-title">${title}</h2><p data-no-translate>${escape(task.name)}</p>${fields}${isOwner?'<p class="help">Assignee changes are recorded automatically in History.</p>':'<label class="field task-cell-history"><span>History — reason for date or status change</span><textarea name="history" rows="3" maxlength="4000" required></textarea></label>'}<p id="task-cell-error" class="plan-create-error" role="alert"></p><div class="form-actions"><button type="submit" class="primary">Save Task</button><button type="button" id="task-cell-cancel">Cancel</button></div></form>`;
    const form=dialog.querySelector('form');
    if(isStatus){const complete=Boolean(task.setup.start_date&&task.setup.end_date);for(const option of form.elements.value.options)option.disabled=complete?option.value==='Not Scheduled':option.value!=='Not Scheduled';}
    if(isDate)bindDateRange(form.elements[dateFields[0]],form.elements[dateFields[1]]);
    let saving=false;
    dialog.oncancel=event=>{if(saving)event.preventDefault();};
    dialog.onclose=()=>{if(control.isConnected)control.focus({preventScroll:true});};
    document.getElementById('task-cell-cancel').onclick=()=>dialog.close();
    form.onsubmit=async event=>{
      event.preventDefault();if(saving)return;
      if(!form.reportValidity())return;
      const changes=isDate?Object.fromEntries(dateFields.map(key=>[key,form.elements[key].value])):{[field]:form.elements.value.value};
      if(Object.entries(changes).every(([key,value])=>value===cellValue(task,key))){dialog.close();return;}
      const setup=task.setup,payload={setup:changes,expected_start_date:setup.start_date||'',expected_end_date:setup.end_date||'',expected_actual_start_date:setup.actual_start_date||'',expected_actual_end_date:setup.actual_end_date||'',expected_owner:setup.owner||'TBD',expected_task_status:setup.task_status||'New'};
      if(!isOwner)payload.history=form.elements.history.value;
      const scroll=document.querySelector('.managed-tasks-wrap'),position={left:scroll.scrollLeft,top:scroll.scrollTop};
      saving=true;for(const button of form.querySelectorAll('button'))button.disabled=true;
      try{
        await scheduleApi('/api/tasks/'+encodeURIComponent(task.id),'PATCH',payload);
        dialog.close();await redraw();const next=document.querySelector('.managed-tasks-wrap');if(next){next.scrollLeft=position.left;next.scrollTop=position.top;}
        for(const row of document.querySelectorAll('.managed-tasks tr[data-task-id]'))if(row.dataset.taskId===task.id)row.querySelector('[data-task-edit="'+field+'"]').focus({preventScroll:true});
        notify('Task updated.');
      }catch(error){if(dialog.open)document.getElementById('task-cell-error').textContent=error.message;else notify(error.message,true);}
      finally{saving=false;for(const button of form.querySelectorAll('button'))button.disabled=false;}
    };
    dialog.showModal();form.elements[isDate?field:'value'].focus();
  }

let calendar=null, viewStart=null, selectedDay=null, selectedTask=null, scheduleTasks=[], scheduleApi, redraw, notify;
  const cellWidth=48;
  const todayISO=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function calendarRange(tasks){
    const dated=tasks.filter(scheduled),today=day(todayISO());
    const first=Math.min(today-60,...dated.map(t=>day(t.setup.start_date)-7));
    const ends=tasks.map(t=>t.setup?.end_date).filter(value=>/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(day(value)));
    let last=today+60;
    if(ends.length){
      const latest=iso(Math.max(...ends.map(day))),end=new Date(0);
      end.setUTCFullYear(Number(latest.slice(0,4)),Number(latest.slice(5,7))-1+4,0);
      last=Math.min(Math.floor(end.getTime()/86400000),day('9999-12-31'));
    }
    viewStart=iso(Math.max(day('0001-01-01'),Math.min(first,last)));
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
        const description=hasDates?`${t.name}: ${t.setup.start_date} to ${t.setup.end_date} · ${t.working_days} working days · Status: ${t.setup.task_status||'New'}`:`${t.name}: not scheduled`;
        return `<div class="gantt-row"><div class="gantt-label"><a href="${infoLink(t)}">${escape(t.name)}</a><span class="schedule-owner" data-no-translate>Assignee: ${escape(t.setup.owner||'TBD')} · Status: ${escape(t.setup.task_status||'New')}</span></div><div class="gantt-track"><div class="gantt-days" aria-hidden="true">${dates.map(d=>`<i class="gantt-day ${d.is_working?'':'is-off'} ${d.date===today?'is-today':''}"></i>`).join('')}</div>${hasDates&&left<=right?`<button type="button" class="gantt-bar ${t.execution_active?'is-running':''}" data-schedule-action="task" data-task-id="${escape(t.id)}" ${t.locked?'disabled':''} style="left:${(left-first)*cellWidth+2}px;width:${(right-left+1)*cellWidth-4}px" title="${escape(description)}" aria-label="${escape(description)}"><span data-no-translate>${escape(t.setup.task_status||'New')}</span></button>`:!hasDates?'<span class="gantt-unscheduled">Not scheduled</span>':'<span class="gantt-unscheduled">Outside displayed dates</span>'}</div></div>`;
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
    editor.innerHTML=`<h2 id="schedule-task-title">Edit Task schedule</h2><p data-no-translate>${escape(task.name)}</p><div class="fields"><label class="field"><span>Start date</span><input type="date" id="schedule-task-start" required value="${escape(task.setup.start_date)}"></label><label class="field"><span>End date</span><input type="date" id="schedule-task-end" required min="${escape(task.setup.start_date)}" value="${escape(task.setup.end_date)}"></label><label class="field full"><span data-no-translate>Status</span><select id="schedule-task-status">${statusOptions(task.setup.task_status||'New')}</select></label><label class="field full"><span>History — reason for date or status change</span><textarea id="schedule-task-history" rows="3" maxlength="4000" required></textarea></label></div><p id="schedule-task-error" class="plan-create-error" role="alert"></p><div class="form-actions"><button type="button" class="primary" data-schedule-action="task-save">Save schedule</button><button type="button" data-schedule-action="task-cancel">Cancel</button></div>`;
    editor.showModal();
    for(const id of ['schedule-task-start','schedule-task-end'])document.getElementById(id).required=false;
    bindDateStatus(document.getElementById('schedule-task-start'),document.getElementById('schedule-task-end'),document.getElementById('schedule-task-status'));
    document.getElementById('schedule-task-start').focus();
  }
  function centerToday(scroll){
    if(!scroll||!calendar)return;
    const index=day(todayISO())-day(calendar.start);
    scroll.scrollLeft=index*cellWidth+cellWidth/2-(scroll.clientWidth-280)/2;
  }

  function sizeSchedule(){
    const list=document.querySelector('.task-list-section'),count=document.querySelector('#manager-task-count');
    if(list&&count)count.textContent=list.dataset.visibleCount+' of '+list.dataset.totalCount+' Tasks';
    for(const selector of ['.gantt-scroll','.managed-tasks-wrap']){
      const scroll=document.querySelector(selector);if(!scroll)continue;
      const available=window.innerHeight-scroll.getBoundingClientRect().top-24;
      scroll.style.setProperty(selector==='.gantt-scroll'?'--schedule-height':'--task-list-height',Math.max(120,available)+'px');
    }
  }

  function bindSchedule(api,refresh,toast){
    sizeSchedule();
    centerToday(document.querySelector('.gantt-scroll'));
    scheduleApi=api;redraw=refresh;notify=toast;
    if(document.documentElement.dataset.scheduleBound)return;
    document.documentElement.dataset.scheduleBound='true';
    window.addEventListener('resize',sizeSchedule);
    let referenceClickTimer=null;
    document.addEventListener('click',event=>{
      const link=event.target.closest('.managed-tasks .task-reference-cell a');
      if(!link||!event.detail||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
      event.preventDefault();clearTimeout(referenceClickTimer);
      if(event.detail===1)referenceClickTimer=setTimeout(()=>window.open(link.href,'_blank','noopener,noreferrer'),500);
    });
    const editMetadata=event=>{
      const control=event.target.closest('.managed-tasks [data-task-meta]');if(!control)return;
      if(event.type==='keydown'&&(!['Enter',' ','F2'].includes(event.key)||(event.target.closest('a')&&event.key!=='F2')))return;
      event.preventDefault();clearTimeout(referenceClickTimer);openMetadata(control).catch(error=>notify(error.message,true));
    };
    document.addEventListener('dblclick',editMetadata);document.addEventListener('keydown',editMetadata);
    const editCell=event=>{const control=event.target.closest('[data-task-edit]');if(!control)return;if(event.type==='keydown'&&!['Enter',' ','F2'].includes(event.key))return;event.preventDefault();openCellEditor(control).catch(error=>notify(error.message,true));};
    document.addEventListener('dblclick',editCell);document.addEventListener('keydown',editCell);
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
          await scheduleApi('/api/tasks/'+selectedTask.id+'/schedule','PATCH',{start_date:document.getElementById('schedule-task-start').value,end_date:document.getElementById('schedule-task-end').value,history:document.getElementById('schedule-task-history').value,expected_start_date:selectedTask.setup.start_date||'',expected_end_date:selectedTask.setup.end_date||'',task_status:document.getElementById('schedule-task-status').value,expected_task_status:selectedTask.setup.task_status||'New'});
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
    if(['list','my-task'].includes(tab))return `<section class="task-list-section" aria-labelledby="task-list-title" data-visible-count="${visible.length}" data-total-count="${tasks.length}"><h2 id="task-list-title" class="sr-only">Task List</h2>${table(visible,Boolean(query.trim()))}</section>`;
    return `<section aria-label="Schedule">${gantt(visible)}</section>`;
  }

  function historyList(rows){
    const period=(start,end)=>escape(start||'—')+' ~ '+escape(end||'—');
    const stamp=value=>new Date(value).toLocaleString('sv-SE',{timeZone:'Asia/Taipei',hour12:false});
    return `<section class="task-history" aria-label="History List"><h2 data-no-translate>History List</h2>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Time (Taipei)</th><th>Previous dates</th><th>New dates</th><th data-no-translate>History</th></tr></thead><tbody>${rows.map(row=>`<tr><td data-no-translate>${escape(stamp(row.created_at))}</td><td data-no-translate>${period(row.previous_start_date,row.previous_end_date)}</td><td data-no-translate>${period(row.start_date,row.end_date)}</td><td class="history-text" data-no-translate>${escape(row.history)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="help">No History yet.</p>'}</section>`;
  }

  function taskInfo(task, options={}){
    const setup=task.setup||{};
    const fields=[['Task name',task.name],['Task Type',task.task_type],['Assignee',setup.owner||'TBD'],['Status',setup.task_status||'New'],['Project',task.project_name],['SKU name',task.sku_name||'—'],['Plan Start Date',setup.start_date||'—'],['Plan End Date',setup.end_date||'—'],['Actual Start Date',setup.actual_start_date||'—'],['Actual End Date',setup.actual_end_date||'—'],['Days (Actual/Plan)',`${task.actual_working_days??'—'} / ${task.working_days??'—'}`]];
    return `${options.heading===false?'':`<div class="page-heading"><h1 data-no-translate>${escape(task.name)}</h1><div class="actions">${action('Edit','manager-edit',task)}</div></div>`}<dl class="planning-task-info">${fields.map(([label,value])=>`<div><dt>${label}</dt><dd data-no-translate>${escape(value)}</dd></div>`).join('')}<div><dt data-no-translate>iDesign ID</dt><dd>${referenceDisplay(task)}</dd></div><div><dt data-no-translate>FW Package</dt><dd>${packageDisplay(task)}</dd></div></dl>${options.notes===false?'':`<h2>Notes</h2><p class="task-info-notes" data-no-translate>${escape(setup.notes||'—')}</p>`}`;
  }

  function planOptions(project, selected) {
    return `<option value="">${project&&!project.plans.length?'No Plans in this Project':'Select Plan'}</option>`+ (project?.plans||[]).map(p=>`<option value="${escape(p.id)}" ${selected===p.id?'selected':''} ${p.locked?'disabled':''}>${escape(p.name)}${p.locked?' (execution active)':''}</option>`).join('');
  }


  function form(projects, task=null, owners=['TBD']) {
    const setup={...(task?.setup||{})}, fixed=task?'disabled':'';
    setup.task_status=setup.start_date&&setup.end_date?(setup.task_status==='Not Scheduled'?'New':setup.task_status||'New'):'Not Scheduled';
    const option=(value,label,selected=false)=>`<option value="${escape(value)}" ${selected?'selected':''} data-no-translate>${escape(label)}</option>`;
    const project=projects.find(p=>p.id===task?.project_id), sku=project?.skus.find(s=>s.id===task?.sku_id);
    const owner=setup.owner||'TBD', ownerNames=[...new Set(['TBD',...owners,owner])];
    return `<form id="task-manager-form" class="task-manager-form" data-task-id="${escape(task?.id||'')}" data-start-date="${escape(setup.start_date||'')}" data-end-date="${escape(setup.end_date||'')}" data-idesign="${escape(JSON.stringify(setup.idesign||{}))}" data-fw-package="${escape(JSON.stringify(setup.fw_package||[]))}" data-actual-start-date="${escape(setup.actual_start_date||'')}" data-actual-end-date="${escape(setup.actual_end_date||'')}" data-owner="${escape(owner)}" data-task-status="${escape(setup.task_status||'New')}"><h2>${task?'Edit Task':'New Task'}</h2><div class="fields">
      <label class="field full"><span>Task Type</span><select name="task_type" id="manager-type" required ${fixed}><option value="">Select Task Type</option>${option('Plan','Plan',task?.task_type==='Plan')}${option('Test','Test',Boolean(task)&&task.task_type!=='Plan')}</select></label>
      <label class="field"><span>Project</span><select name="project_id" id="manager-project" required disabled><option value="">Select Project</option>${projects.map(p=>option(p.id,p.name,task?.project_id===p.id)).join('')}</select></label>
      <label class="field"><span>SKU name</span><select name="sku_id" id="manager-sku" disabled><option value="">${project?.skus.length?'Select SKU':'No SKUs'}</option>${project?.skus.map(s=>option(s.id,s.full_name,s.id===task?.sku_id)).join('')||''}${task?.sku_id&&!sku?option(task.sku_id,task.sku_name||task.sku_id,true):''}</select></label>
      <label class="field full"><span>Plan</span><select name="plan_id" id="manager-plan" disabled><option value="">Select Plan</option>${task?.plan_id?option(task.plan_id,task.plan_name,true):''}</select></label>
      <label class="field"><span>Plan Start Date</span><input type="date" name="start_date" value="${escape(setup.start_date||'')}"></label>
      <label class="field"><span>Plan End Date</span><input type="date" name="end_date" value="${escape(setup.end_date||'')}"></label>
      <label class="field"><span>Actual Start Date</span><input type="date" name="actual_start_date" value="${escape(setup.actual_start_date||'')}"></label>
      <label class="field"><span>Actual End Date</span><input type="date" name="actual_end_date" value="${escape(setup.actual_end_date||'')}"></label>
      <label class="field full"><span data-no-translate>Status</span><select name="task_status" id="manager-status" ${task?'':'disabled'}>${statusOptions(setup.task_status||'New')}</select></label>
      ${task?'<label class="field full" id="manager-history-field" hidden><span>History — reason for schedule change</span><textarea name="history" id="manager-history" rows="3" maxlength="4000" disabled></textarea><span class="help" id="manager-owner-history" data-no-translate hidden></span></label>':''}
      <label class="field full"><span data-no-translate>Assignee</span><select name="owner" id="manager-owner" required>${ownerNames.map(name=>option(name,name,name===owner)).join('')}</select></label>
      <label class="field full"><span>Task name</span><input name="name" id="manager-name" readonly value="${escape(task?.name||'')}" aria-describedby="manager-name-help"><span class="help" id="manager-name-help">Task name is generated automatically.</span></label>

      ${referenceFields(setup.idesign)}${packageFields(setup.fw_package||[],task?.task_type==='Test')}
      <label class="field full"><span>Notes</span><textarea name="notes" rows="3">${escape(setup.notes||'')}</textarea></label></div>
      <p class="help">Missing either date sets Status to Not Scheduled. Dates do not automatically start execution.</p>
      <p id="manager-form-error" class="plan-create-error" role="alert"></p>
      <div class="form-actions"><button type="submit" class="primary" ${task?'':'disabled'}>${task?'Save Task':'Create Task'}</button><button type="button" data-action="close-panel">Cancel</button></div></form>`;
  }

  function bindForm(projects, api) {
    const form=document.getElementById('task-manager-form');
    if(!form)return;
    bindMetadata(form);
    const updatePackageType=()=>{form.querySelector('.task-fw-editor').disabled=form.elements.task_type.value!=='Test';};
    form.elements.task_type.addEventListener('change',updatePackageType);updatePackageType();
    bindDateStatus(form.elements.start_date,form.elements.end_date,form.elements.task_status,!form.dataset.taskId);
    bindDateRange(form.elements.actual_start_date,form.elements.actual_end_date);
    if(form.dataset.taskId){
      let mode='none',scheduleReason='';
      const updateHistory=()=>{
        const changed=form.elements.actual_start_date.value!==(form.dataset.actualStartDate||'')||form.elements.actual_end_date.value!==(form.dataset.actualEndDate||'')||form.elements.start_date.value!==(form.dataset.startDate||'')||form.elements.end_date.value!==(form.dataset.endDate||'')||form.elements.task_status.value!==(form.dataset.taskStatus||'New');
        const ownerChanged=form.elements.owner.value!==(form.dataset.owner||'TBD');
        const field=form.querySelector('#manager-history-field'),input=form.elements.history,preview=form.querySelector('#manager-owner-history');
        const ownerMessage='Assignee: '+(form.dataset.owner||'TBD')+' → '+form.elements.owner.value;
        if(mode==='date')scheduleReason=input.value;
        const next=changed?'date':ownerChanged?'owner':'none';
        field.hidden=next==='none';input.disabled=next==='none';input.required=changed;input.readOnly=next==='owner';
        if(next==='date'&&mode!=='date')input.value=scheduleReason;
        if(next==='owner')input.value=ownerMessage;
        field.querySelector('span').textContent=changed?'History — reason for date or status change':'History';
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
  return {metadataValues, content, historyList, taskInfo, infoLink, form, planOptions, link, bindForm, calendarRange, setCalendar, bindSchedule};
})();
