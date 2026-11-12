/* Read-only, single-Case report preview. The iframe uses the export renderer. */
window.ReportPreview = (() => {
  let current = null;
  function close() {
    const view = current;
    if (!view) return;
    current = null;
    view.request?.abort();
    view.dialog.close();
    view.dialog.remove();
    const opener = view.opener?.isConnected ? view.opener : document.querySelector(
      '[data-action="execution-report-preview"][data-id="'+CSS.escape(view.caseId)+'"]');
    opener?.focus({preventScroll:true});
  }
  async function refresh(view) {
    view.request?.abort();
    const request = new AbortController();
    view.request = request;
    view.refresh.disabled = true;
    view.frame.hidden = true;
    view.frame.removeAttribute('srcdoc');
    view.error.textContent = '';
    view.status.textContent = 'Loading report preview…';
    view.dialog.setAttribute('aria-busy', 'true');
    try {
      const url = '/api/tasks/'+encodeURIComponent(view.taskId)+'/testcases/'+encodeURIComponent(view.caseId)+'/report-preview';
      const response = await fetch(url, {signal:request.signal, cache:'no-store'});
      const data = await response.json().catch(() => ({}));
      if (!response.ok || typeof data.html !== 'string') throw Error(data.error || 'Unable to load the report preview. Try Refresh.');
      if (current !== view || view.request !== request) return;
      view.frame.srcdoc = data.html;
      view.frame.hidden = false;
      view.status.textContent = 'Saved results · Preview loaded '+new Date().toLocaleTimeString();
    } catch (error) {
      if (current !== view || view.request !== request || error.name === 'AbortError') return;
      view.status.textContent = '';
      view.error.textContent = error.message;
    } finally {
      if (current === view && view.request === request) {
        view.refresh.disabled = false;
        view.dialog.setAttribute('aria-busy', 'false');
      }
    }
  }
  function open({taskId, caseId, taskName, caseName, opener}) {
    close();
    const dialog = document.createElement('dialog');
    dialog.className = 'report-preview-dialog';
    dialog.setAttribute('aria-labelledby', 'report-preview-title');
    dialog.innerHTML = '<header class="report-preview-header"><div><h2 id="report-preview-title">Report preview</h2><p class="help" data-preview-identity data-no-translate></p></div><div class="report-preview-actions"><button type="button" data-preview-refresh>Refresh</button><button type="button" data-preview-close autofocus>Close</button></div></header><p class="help report-preview-status" role="status"></p><p class="report-preview-error" role="alert"></p><iframe class="report-preview-frame" title="Test Case report preview" sandbox="allow-same-origin" referrerpolicy="no-referrer" hidden></iframe>';
    dialog.querySelector('[data-preview-identity]').textContent = taskName+' / '+caseName;
    const view = {dialog, taskId, caseId, opener,
      refresh:dialog.querySelector('[data-preview-refresh]'),
      frame:dialog.querySelector('iframe'), status:dialog.querySelector('[role=status]'),
      error:dialog.querySelector('[role=alert]')};
    current = view;
    // Keep scripts disabled; relay Escape when focus is inside the report.
    view.frame.onload = () => {
      if (current !== view) return;
      view.frame.contentDocument?.addEventListener('keydown', event => {
        if (event.key === 'Escape') {event.preventDefault(); close();}
      });
    };
    view.refresh.onclick = () => refresh(view);
    dialog.querySelector('[data-preview-close]').onclick = close;
    dialog.addEventListener('cancel', event => {event.preventDefault(); close();});
    document.body.append(dialog);
    dialog.showModal();
    return refresh(view);
  }
  window.addEventListener('hashchange', close);
  return {open, close};
})();
