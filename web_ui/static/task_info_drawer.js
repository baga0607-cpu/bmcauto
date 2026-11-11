'use strict';
window.TaskInfoDrawer = (() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pages = [['overview','Overview'],['scope','Scope'],['connection','Connection'],['dut','DUT Config'],['note','Note']];
  let host, services, task, page = 'overview', baseline = '', settings, summary, saving = false, loading = false, opening = false, origin;
  const query = selector => host?.querySelector(selector);
  const form = () => query('form');
  const snapshot = () => form() ? JSON.stringify({fields:[...new FormData(form()).entries()],firmware:[...form().querySelectorAll('[data-fw-component],[data-fw-version]')].map(input => input.value)}) : '';
  const dirty = () => Boolean(host && baseline !== snapshot());
  const locked = () => page === 'connection' ? task.execution_active : task.locked;
  let collapsedFolders = new Set();

  function scopeTree(plan, included) {
    const folders = plan.folders || [];
    const cases = (parent, ancestors) => plan.testcases.filter(c => (c.folder_id || null) === parent).map(c =>
      `<tr data-scope-ancestors="${escape(JSON.stringify(ancestors))}"><td><label class="scope-tree-line" style="--depth:${ancestors.length + 1}"><span class="scope-tree-spacer"></span><input type="checkbox" name="case" value="${escape(c.id)}" aria-label="Include ${escape(c.tc_name)}" ${included.has(c.id) ? 'checked' : ''} ${c.script_kind !== 'single' ? 'data-retired disabled' : ''}><span>${escape(c.tc_name)}</span></label></td></tr>`).join('');
    const children = (parent, ancestors) => folders.filter(f => (f.parent_id || null) === parent).sort((a,b) => a.position - b.position).map(f => {
      const path = [...ancestors, f.id];
      return `<tr data-scope-ancestors="${escape(JSON.stringify(ancestors))}"><td><div class="scope-tree-line" style="--depth:${ancestors.length + 1}"><button type="button" data-scope-toggle="${escape(f.id)}" aria-label="Toggle ${escape(f.name)}" aria-expanded="true">▾</button><input type="checkbox" data-scope-folder="${escape(f.id)}" aria-label="Include folder ${escape(f.name)}"><strong>${escape(f.name)}</strong></div></td></tr>` + children(f.id, path) + cases(f.id, path);
    }).join('');
    return '<table class="scope-tree"><thead><tr><th>Directory / Test Case</th></tr></thead><tbody><tr><td><strong>BMC</strong></td></tr>' + children(null, []) + cases(null, []) + (!plan.testcases.length && !folders.length ? '<tr><td>No Test Cases</td></tr>' : '') + '</tbody></table>';
  }

  function folderCases(id) {
    return [...form().querySelectorAll('[data-scope-ancestors]')].filter(row => JSON.parse(row.dataset.scopeAncestors).includes(id)).flatMap(row => [...row.querySelectorAll('[name=case]:not(:disabled)')]);
  }

  function syncTree() {
    form()?.querySelectorAll('[data-scope-ancestors]').forEach(row => {
      row.hidden = JSON.parse(row.dataset.scopeAncestors).some(id => collapsedFolders.has(id));
    });
    form()?.querySelectorAll('[data-scope-toggle]').forEach(button => {
      const expanded = !collapsedFolders.has(button.dataset.scopeToggle);
      button.textContent = expanded ? '▾' : '▸';button.setAttribute('aria-expanded',String(expanded));
    });
    form()?.querySelectorAll('[data-scope-folder]').forEach(input => {
      const cases = folderCases(input.dataset.scopeFolder), count = cases.filter(c => c.checked).length;
      input.checked = cases.length > 0 && count === cases.length;
      input.indeterminate = count > 0 && count < cases.length;
      input.disabled = !cases.length;
      input.setAttribute('aria-checked',input.indeterminate ? 'mixed' : String(input.checked));
    });
  }

  function sync() {
    query('[data-drawer-save]').disabled = saving || loading || locked() || !dirty() || (!task.id && !form()?.dataset.nameReady);
    query('[data-drawer-save]').textContent = task.id ? 'Save changes' : 'Create Task';
    query('[data-drawer-discard]').disabled = saving || loading || !dirty();
    query('[data-drawer-status]').textContent = saving ? 'Saving…' : dirty() ? 'Unsaved changes' : 'Saved';
  }

  async function permitLeave() {
    if (saving || loading) return false;
    if (!dirty()) return true;
    const dialog = document.createElement('dialog');
    dialog.className = 'task-drawer-confirm';
    dialog.setAttribute('aria-labelledby', 'drawer-confirm-title');
    dialog.innerHTML = '<h2 id="drawer-confirm-title">Unsaved changes</h2><p>Save changes before leaving this page?</p><form method="dialog"><div class="form-actions"><button value="stay">Keep editing</button><button value="discard">Discard and continue</button><button value="save" class="primary">Save and continue</button></div></form>';
    document.body.append(dialog);
    dialog.showModal();
    const answer = await new Promise(resolve => dialog.addEventListener('close', () => resolve(dialog.returnValue), {once:true}));
    dialog.remove();
    if (answer === 'save') return save();
    return answer === 'discard';
  }

  function input(name, label, value, type = 'text') {
    return `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${escape(value)}" autocomplete="${type === 'password' ? 'new-password' : 'off'}"></label>`;
  }

  async function render() {
    loading = true;
    query('[data-drawer-content]').setAttribute('aria-busy', 'true');
    query('[data-drawer-error]').textContent = '';
    try {
      const content = query('[data-drawer-content]');
      content.replaceChildren();
      baseline = '';
      if (page === 'overview') {
        const options = await services.api('/api/tasks/options');
        content.innerHTML = TaskManagement.form(options.projects, task.id ? task : null, options.owners);
        TaskManagement.bindForm(options.projects, services.api, 'Note', sync, true);
        form().querySelectorAll(':scope > .help, .task-fw-editor > .help').forEach(element => element.remove());
        form().querySelector('h2').remove();
        if (task.id) form().elements.notes.closest('label').remove();
        else form().elements.notes.closest('label').querySelector('span').textContent = 'Note';
        form().querySelector('.form-actions').remove();
        for (const name of ['task_type','plan_id','task_status','owner']) form().elements[name].closest('label').classList.remove('full');
        form().elements.name.closest('label').hidden = Boolean(task.id);
        const start = form().elements.start_date.closest('label');
        start.before(form().elements.owner.closest('label'), form().elements.task_status.closest('label'));
        const reference = form().querySelector('.task-reference-fields');
        const request = form().elements.idesign_request_id.closest('label');
        const link = form().elements.idesign_hyperlink.closest('label');
        request.querySelector('span').textContent = 'iDesign Request ID';
        link.querySelector('span').textContent = 'iDesign Link';
        reference.replaceWith(request, link);
        if (task.id) for (const [name, title] of [['start_date','Plan Start Date'],['end_date','Plan End Date'],['actual_start_date','Actual Start Date'],['actual_end_date','Actual End Date'],['task_status','Status']]) {
          const input = form().elements[name], button = document.createElement('button');
          input.hidden = true;
          button.type = 'button';button.className = 'drawer-field-editor';button.dataset.drawerField = name;
          button.setAttribute('aria-label',title);button.textContent = input.value || '—';
          input.after(button);
        }
      } else if (page === 'note') {
        const result = await services.api(`/api/tasks/${task.id}/history`);
        content.innerHTML = `<form><label class="field"><span>Note</span><textarea name="notes" rows="6">${escape(task.setup.notes || '')}</textarea></label></form><section class="task-drawer-history">${TaskManagement.historyList(result.history)}</section>`;
        const history = content.querySelector('.task-history');
        history.setAttribute('aria-label','Note records');
        history.querySelector('h2').textContent = 'Note records';
        history.querySelectorAll('th').forEach(th => {if (th.textContent === 'History') th.textContent = 'Note';});
        const emptyHistory = history.querySelector('.help');
        if (emptyHistory) emptyHistory.textContent = 'No Notes yet.';
      } else if (page === 'dut') {
        content.innerHTML = '<p class="help">DUT configuration fields have not been defined.</p>';
      } else if (task.task_type !== 'Test') {
        content.innerHTML = `<p class="help">${page === 'scope' ? 'Scope' : 'Connection'} is available for Test Tasks. This is a Plan Task.</p>`;
      } else if (page === 'connection') {
        settings = await services.api(`/api/tasks/${task.id}/settings`);
        const port = settings.dut_connect_cmd?.match(/^telnet\s+(?:0|localhost)\s+(.+)$/)?.[1] || '';
        const group = (label, fields) => '<details class="connection-group" open><summary>' + label + '</summary><div class="fields">' + fields + '</div></details>';
        content.innerHTML = '<form>' +
          group('BMC', input('host','BMC IP',settings.host) +
            input('username','BMC User',settings.username) + input('password','BMC Password',settings.password,'password')) +
          group('Console Server', input('cs_host','Server IP',settings.cs_host) +
            input('cs_username','Server User',settings.cs_username) + input('cs_password','Server Password',settings.cs_password,'password') +
            input('console_port','Console Port',port)) +
          group('DUT OS', input('dut_os_username','DUT User',settings.dut_os_username) +
            input('dut_os_password','DUT Password',settings.dut_os_password,'password')) +
          '</form>' + (settings.dut_connect_cmd && !port ? '<p class="help">An existing custom console command is configured. Leave Console Port empty to retain it. Entering a port replaces it with telnet 0 &lt;port&gt;.</p>' : '');
        form().addEventListener('invalid', event => {
          const group = event.target.closest('details');
          if (group) group.open = true;
        }, true);
      } else {
        summary = await services.api(`/api/tasks/${task.id}/summary`);
        const project = services.projects().find(p => p.plans.some(plan => plan.id === task.plan_id));
        const plan = project?.plans.find(p => p.id === task.plan_id);
        if (!plan) throw Error('The Task Plan was not found. Reload and try again.');
        const included = new Set(summary.testcases.map(c => c.id));
        content.innerHTML = '<form><div class="toolbar"><div class="actions"><button type="button" data-drawer-select="all">Select all</button><button type="button" data-drawer-select="none">Clear selection</button></div><span data-drawer-count></span></div><p class="help">Removing a case also removes its current Task result and logs.</p>' + scopeTree(plan, included) + '</form>';
        updateCount();
      }
      if (form() && locked()) {
        const fieldset = document.createElement('fieldset');
        fieldset.disabled = true;
        fieldset.append(...form().childNodes);
        form().append(fieldset);
        content.insertAdjacentHTML('afterbegin','<p class="notice">Execution is active. These settings are locked.</p>');
      }
      host.querySelectorAll('[data-drawer-tab]').forEach(button => {
        button.setAttribute('aria-selected', String(button.dataset.drawerTab === page));
        button.tabIndex = button.dataset.drawerTab === page ? 0 : -1;
      });
      content.setAttribute('aria-labelledby', 'drawer-tab-' + page);
      content.dataset.page = page;
      content.scrollTop = 0;
      baseline = snapshot();
    } catch (error) {
      query('[data-drawer-content]').innerHTML = '<p class="help">This page could not be loaded.</p><button type="button" data-drawer-retry>Retry</button>';
      query('[data-drawer-error]').textContent = error.message.replace(/\bHistory\b/g, 'Note');
      baseline = '';
    } finally {
      loading = false;
      query('[data-drawer-content]').setAttribute('aria-busy', 'false');
      sync();
    }
  }

  function updateCount() {
    const count = query('[data-drawer-count]');
    if (count) count.textContent = form().querySelectorAll('[name=case]:checked').length + ' selected';
    if (page === 'scope') syncTree();
  }

  function overviewPayload() {
    const values = Object.fromEntries(new FormData(form()));
    const keys = ['start_date','end_date','actual_start_date','actual_end_date','owner','task_status'];
    const setup = Object.fromEntries(keys.map(key => [key, values[key]]));
    Object.assign(setup, TaskManagement.metadataValues(form()));
    const payload = {setup, expected_idesign: task.setup.idesign || {}, expected_fw_package: task.setup.fw_package || []};
    keys.forEach(key => {payload['expected_' + key] = task.setup[key] || (key === 'owner' ? 'TBD' : key === 'task_status' ? 'New' : '');});
    return payload;
  }

  async function save() {
    if (saving || loading || locked() || !form()) return false;
    if (!form().reportValidity()) return false;
    query('[data-drawer-error]').textContent = '';
    saving = true; sync();
    host.inert = true;
    try {
      let payload, url = `/api/tasks/${task.id}`, method = 'PATCH';
      if (!task.id) {
        const values = Object.fromEntries(new FormData(form()));
        if (!form().dataset.nameReady) throw Error('Select Task Type, Project, SKU and Plan first.');
        const setup = Object.fromEntries(['start_date','end_date','actual_start_date','actual_end_date','owner','task_status','notes'].map(key => [key,values[key] || '']));
        setup.task_status = setup.start_date && setup.end_date ? 'New' : 'Not Scheduled';
        Object.assign(setup, TaskManagement.metadataValues(form()));
        payload = {task_type:values.task_type,project_id:values.project_id,sku_id:values.sku_id || null,plan_id:values.task_type === 'Test' ? values.plan_id : null,setup};
        url = '/api/tasks';method = 'POST';
      }
      else if (page === 'overview') payload = overviewPayload();
      else if (page === 'note') {
        const latest = (await services.api('/api/tasks')).tasks.find(item => item.id === task.id);
        if (!latest || (latest.setup.notes || '') !== (task.setup.notes || '')) throw Error('The Note changed. Discard changes to reload before editing again.');
        payload = {setup:{notes:form().elements.notes.value}};
      }
      else if (page === 'scope') {
        payload = {testcases:[...form().querySelectorAll('[name=case]:checked')].map(input => input.value)};
        if (summary.testcases.some(c => !payload.testcases.includes(c.id)) && !window.confirm('Remove the unchecked cases and their current Task results and logs?')) return false;
        url += '/testcases/import'; method = 'POST';
      } else if (page === 'connection') {
        const latest = await services.api(`/api/tasks/${task.id}/settings`);
        if (JSON.stringify(latest) !== JSON.stringify(settings)) throw Error('Connection settings changed. Discard changes to reload before editing again.');
        payload = {...settings, ...Object.fromEntries(new FormData(form()))};
        const port = payload.console_port;
        delete payload.console_port;
        if (port) payload.dut_connect_cmd = 'telnet 0 ' + port;
        if (payload.host && !/^https?:\/\//i.test(payload.host)) payload.host = 'https://' + payload.host.trim();
        url += '/settings'; method = 'PUT';
      } else return false;
      const response = await services.api(url, method, payload);
      const createdId = !task.id ? response.id : null;
      baseline = snapshot();
      await services.updated();
      if (createdId) {
        remove();
        await openTask(createdId);
        services.toast('Task created.');
        return true;
      }
      const result = await services.api('/api/tasks');
      task = result.tasks.find(item => item.id === task.id);
      if (!task) {remove(); return true;}
      await render();
      services.toast('Task changes saved.');
      return true;
    } catch (error) {
      query('[data-drawer-error]').textContent = error.message.replace(/\bHistory\b/g, 'Note');
      return false;
    } finally {
      saving = false;
      if (host) {
        host.inert = false;
        sync();
      }
    }
  }

  function remove() {
    host?.remove(); host = null; baseline = ''; task = null;
    origin?.focus({preventScroll:true});
  }

  async function deleteTask() {
    if (!task?.id || saving || loading || task.locked) return;
    if (!await permitLeave()) return;
    if (dirty()) await render();
    const id = task.id, dialog = document.createElement('dialog');
    dialog.className = 'task-drawer-confirm';
    dialog.setAttribute('aria-labelledby','drawer-delete-title');
    dialog.innerHTML = '<form><h2 id="drawer-delete-title">Delete Task?</h2><p>The Task will be marked Deleted and hidden. Its data and results will be retained.</p><label class="field"><span>Deletion reason (recorded in Note)</span><textarea name="reason" rows="4" maxlength="4000" required></textarea></label><p role="alert"></p><div class="form-actions"><button type="submit" class="danger">Delete Task</button><button type="button" data-cancel>Cancel</button></div></form>';
    document.body.append(dialog);
    dialog.addEventListener('input', event => {event.stopPropagation();dialog.querySelector('[role=alert]').textContent = '';});
    dialog.addEventListener('change', event => event.stopPropagation());
    dialog.oncancel = event => {if (saving) event.preventDefault();};
    dialog.onclose = () => {dialog.remove();query('[data-drawer-delete]')?.focus();};
    dialog.querySelector('[data-cancel]').onclick = () => dialog.close();
    dialog.querySelector('form').onsubmit = async event => {
      event.preventDefault();event.stopPropagation();
      const reason = dialog.querySelector('textarea').value.trim();
      if (saving) return;
      if (!reason) {dialog.querySelector('[role=alert]').textContent = 'Enter a deletion reason.';return;}
      saving = true;sync();
      dialog.querySelectorAll('button,textarea').forEach(control => control.disabled = true);
      try {
        await services.api(`/api/tasks/${id}`, 'DELETE', {reason});
        dialog.close();remove();
        await services.updated();
        services.toast('Task marked Deleted. Reason recorded in Note.');
      } catch (error) {
        if (dialog.isConnected) dialog.querySelector('[role=alert]').textContent = error.message;
        else services.toast(error.message, true);
      } finally {
        saving = false;
        dialog.querySelectorAll('button,textarea').forEach(control => control.disabled = false);
        if (host) sync();
      }
    };
    dialog.showModal();dialog.querySelector('textarea').focus();
  }

  async function open(id) {
    if (opening) return;
    opening = true;
    try {await openTask(id);} finally {opening = false;}
  }

  async function openTask(id) {
    if (host && !await permitLeave()) return;
    const requestedHash = location.hash;
    const result = id ? await services.api('/api/tasks') : null;
    if (location.hash !== requestedHash) return;
    const selected = id ? result.tasks.find(item => item.id === id) : {id:null,name:'New Task',task_type:'New',setup:{},locked:false};
    if (!selected) throw Error('Task not found. It may have been removed.');
    origin = document.activeElement;
    host?.remove();
    task = selected; page = 'overview'; baseline = '';collapsedFolders = new Set();
    host = document.createElement('section');
    host.className = 'task-info-drawer';
    host.setAttribute('role','region');host.setAttribute('aria-labelledby','task-drawer-title');
    const visiblePages = !task.id ? pages.filter(([key]) => key === 'overview') : task.task_type === 'Test' ? pages : pages.filter(([key]) => ['overview','note'].includes(key));
    host.innerHTML = `<header class="task-drawer-heading"><div><h1 id="task-drawer-title" data-no-translate>${escape(task.name)}</h1><span class="help" data-no-translate>${escape(task.task_type)} Task · ${escape(task.project_name)} / ${escape(task.sku_name || '—')}</span></div><button type="button" data-drawer-close aria-label="Close Task Info">Close</button></header><div class="task-drawer-body"><nav role="tablist" aria-label="Task Info" aria-orientation="vertical">${visiblePages.map(([key,label]) => `<button type="button" id="drawer-tab-${key}" role="tab" data-drawer-tab="${key}" aria-selected="${key === page}" aria-controls="task-drawer-content">${label}</button>`).join('')}</nav><section id="task-drawer-content" data-drawer-content role="tabpanel"></section></div><div data-drawer-error role="alert" class="task-drawer-error"></div><footer><span data-drawer-status role="status" class="help"></span><div class="actions"><button type="button" data-drawer-discard>Discard changes</button><button type="button" class="primary" data-drawer-save>Save changes</button></div></footer>`;
    document.body.append(host);
    if (!task.id) query('.task-drawer-heading .help').textContent = 'Choose Task Type, Project and assignment';
    if (task.id) {
      const deleteButton = document.createElement('button');
      deleteButton.type = 'button';deleteButton.className = 'danger';deleteButton.dataset.drawerDelete = '';
      deleteButton.textContent = 'Delete Task';deleteButton.disabled = Boolean(task.locked);
      query('[data-drawer-close]').before(deleteButton);
    }
    host.addEventListener('input', event => {event.stopPropagation();if (!event.target.hasAttribute('data-scope-folder')) updateCount();sync();});
    host.addEventListener('change', event => {
      event.stopPropagation();
      if (event.target.hasAttribute('data-scope-folder')) folderCases(event.target.dataset.scopeFolder).forEach(input => input.checked = event.target.checked);
      updateCount();sync();
    });
    host.addEventListener('submit', event => {event.preventDefault();event.stopPropagation();save();});
    host.addEventListener('click', event => {
      event.stopPropagation();
      const button = event.target.closest('button');
      if (!button || button.disabled || saving || loading) return;
      act(button).catch(error => {query('[data-drawer-error]').textContent = error.message.replace(/\bHistory\b/g, 'Note');});
    });
    host.addEventListener('keydown', event => {
      if (event.key === 'Escape') {event.preventDefault();event.stopPropagation();close();}
      const tab = event.target.closest('[data-drawer-tab]');
      if (!tab || !['ArrowUp','ArrowDown','Home','End'].includes(event.key)) return;
      event.preventDefault();
      const buttons = [...host.querySelectorAll('[data-drawer-tab]')], index = buttons.indexOf(tab);
      const next = event.key === 'Home' ? buttons[0] : event.key === 'End' ? buttons.at(-1) : buttons[(index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length];
      next.click();
    });
    await render();query('[data-drawer-close]').focus();
  }

  async function act(button) {
    if (button.dataset.drawerField) {
      const field = button.dataset.drawerField;
      if (!await permitLeave()) return;
      if (dirty()) await render();
      const control = query(`[data-drawer-field="${field}"]`);
      const editedId = task.id;
      return TaskManagement.openCellEditor(control, {task, field, api:services.api, toast:services.toast, updated:async () => {
        await services.updated();
        const latest = (await services.api('/api/tasks')).tasks.find(item => item.id === editedId);
        if (!host || task.id !== editedId) return;
        if (!latest) {remove();return;}
        task = latest;await render();query(`[data-drawer-field="${field}"]`)?.focus();
      }});
    }
    if (button.hasAttribute('data-scope-toggle')) {
      const id = button.dataset.scopeToggle;
      collapsedFolders.has(id) ? collapsedFolders.delete(id) : collapsedFolders.add(id);
      syncTree();return;
    }
    if (button.hasAttribute('data-drawer-close')) return close();
    if (button.hasAttribute('data-drawer-save')) return save();
    if (button.hasAttribute('data-drawer-delete')) return deleteTask();
    if (button.hasAttribute('data-drawer-discard')) {
      if (!task.id) return render();
      const latest = (await services.api('/api/tasks')).tasks.find(item => item.id === task.id);
      if (!latest) {remove();return;}
      task = latest;
      return render();
    }
    if (button.hasAttribute('data-drawer-retry')) return render();
    if (button.dataset.drawerTab && button.dataset.drawerTab !== page) {
      if (!await permitLeave()) return;
      page = button.dataset.drawerTab;await render();query('[data-drawer-tab="' + page + '"]').focus();
    }
    if (button.dataset.drawerSelect) {
      form().querySelectorAll('[name=case]:not(:disabled)').forEach(input => input.checked = button.dataset.drawerSelect === 'all');
      updateCount();sync();
    }
  }

  async function close() {if (await permitLeave()) remove();}
  async function leave() {if (!host) return true;if (!await permitLeave()) return false;remove();return true;}
  window.addEventListener('beforeunload', event => {if (dirty() || saving) {event.preventDefault();event.returnValue = '';}});
  return {configure: value => {services = value;}, open, leave, dirty, deleteTask};
})();
