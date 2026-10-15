const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'static', 'index.html'), 'utf8');

function sliceBetween(startMarker, endMarker) {
  const start = html.indexOf(startMarker);
  const end = html.indexOf(endMarker, start);
  assert.notEqual(start, -1, `missing ${startMarker}`);
  assert.notEqual(end, -1, `missing ${endMarker}`);
  return html.slice(start, end);
}

function loadMoveDialogFunctions(context) {
  const close = sliceBetween('function closePlanMoveDialog()', 'function refreshPlanMoveDialog()');
  const submit = sliceBetween('async function submitPlanTestCaseMove()', 'function renderPlanDetailCaseActions');
  vm.runInNewContext(
    `${close}\n${submit}\nglobalThis.testApi = { closePlanMoveDialog, submitPlanTestCaseMove };`,
    context,
  );
  return context.testApi;
}

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('move dialog close during lock preflight cancels with zero move requests', async () => {
  const preflight = deferred();
  const dialog = {
    ids: ['tc-a'],
    destinationKey: 'custom:IBM',
    query: '',
    error: null,
    submitting: false,
  };
  let requests = 0;
  const context = {
    planDetailState: { moveDialog: dialog },
    refreshLockedProjects: () => preflight.promise,
    refreshPlanMoveDialog: () => {},
    requestPlanTestCaseMove: async () => { requests += 1; return {}; },
    reloadProjects: async () => {},
    refreshAllTestcases: async () => {},
    renderPlanDetail: () => {},
    document: { getElementById: () => null },
    lockedProjectIds: [],
    isPlanLocked: () => false,
    currentProjId: 'project-a',
    isRunning: false,
    alert: () => {},
    Symbol,
    Promise,
  };
  const api = loadMoveDialogFunctions(context);

  const submission = api.submitPlanTestCaseMove();
  assert.equal(dialog.submitting, true);
  api.closePlanMoveDialog();
  preflight.resolve();
  await submission;

  assert.equal(context.planDetailState.moveDialog, null);
  assert.equal(requests, 0);
});

test('move dialog cannot close after its POST has started', async () => {
  const request = deferred();
  const requestBegan = deferred();
  const dialog = {
    ids: ['tc-a'],
    destinationKey: 'custom:IBM',
    query: '',
    error: null,
    submitting: false,
  };
  const context = {
    planDetailState: { moveDialog: dialog },
    refreshLockedProjects: async () => {},
    refreshPlanMoveDialog: () => {},
    requestPlanTestCaseMove: () => {
      requestBegan.resolve();
      return request.promise;
    },
    reloadProjects: async () => {},
    refreshAllTestcases: async () => {},
    renderPlanDetail: () => {},
    document: { getElementById: () => null },
    lockedProjectIds: [],
    isPlanLocked: () => false,
    currentProjId: 'project-a',
    isRunning: false,
    alert: () => {},
    Symbol,
    Promise,
  };
  const api = loadMoveDialogFunctions(context);

  const submission = api.submitPlanTestCaseMove();
  await requestBegan.promise;
  assert.equal(dialog.requestStarted, true);
  api.closePlanMoveDialog();
  assert.equal(context.planDetailState.moveDialog, dialog);
  request.resolve({ moved_ids: ['tc-a'], skipped_ids: [], destination: 'Custom / IBM' });
  await submission;
});

function createViewDocument() {
  const ids = new Map();
  for (const id of [
    'view-dashboard',
    'view-project-workspace',
    'view-projects',
    'view-plan-detail',
    'view-task-detail',
    'view-execution-detail',
    'view-plan',
    'sidebar-resizer',
    'project-select',
  ]) ids.set(id, { style: {}, value: '' });
  const sidebar = { style: {} };
  const logContainer = { style: {} };
  return {
    ids,
    document: {
      getElementById: id => ids.get(id) || null,
      querySelector: selector => selector === '.sidebar' ? sidebar : logContainer,
      documentElement: { className: '' },
    },
  };
}

function loadShowView(context) {
  const source = sliceBetween('function showView(viewId, options = {})', 'function stateFromLocation()');
  vm.runInNewContext(`${source}\nglobalThis.testApi = { showView };`, context);
  return context.testApi.showView;
}

test('forced Dashboard renders in the current tab while ordinary running navigation still opens a tab', () => {
  const opened = [];
  const rendered = [];
  const viewDocument = createViewDocument();
  const context = {
    ...viewDocument,
    window: { open: (...args) => opened.push(args) },
    isRunning: true,
    currentProjId: null,
    currentPlanId: null,
    currentViewId: 'plan-detail',
    cancelPlanTcPointerDrag: () => {},
    stopPlanDragScrolling: () => {},
    stopPlanFolderResize: () => {},
    closePlanRowActions: () => {},
    findProj: () => null,
    getPlanTasks: () => [],
    getCurrentTaskId: () => null,
    setCurrentTaskId: () => {},
    renderDashboard: () => rendered.push('dashboard'),
    updateAppNavActive: () => {},
    renderProjectWorkspace: () => {},
    renderProjectManager: () => {},
    renderPlanDetail: () => {},
    renderTaskDetail: () => {},
    renderExecutionDetail: () => {},
    renderMain: () => {},
    syncNavigationState: () => {},
  };
  const showView = loadShowView(context);

  showView('dashboard', { forceCurrentTab: true });
  assert.deepEqual(opened, []);
  assert.deepEqual(rendered, ['dashboard']);
  assert.equal(viewDocument.ids.get('view-dashboard').style.display, 'flex');

  showView('projects');
  assert.deepEqual(opened, [['/?view=projects', '_blank']]);
});

test('clearing project requests the narrowly forced current-tab Dashboard path', async () => {
  const calls = [];
  const source = sliceBetween('async function changeProject(pid)', 'function switchSidebarTab(tab)');
  const context = {
    refreshLockedProjects: async () => {},
    currentProjId: 'project-a',
    currentPlanId: 'plan-a',
    setCurrentTaskId: value => calls.push(['task', value]),
    renderProjectSelect: () => calls.push(['render-select']),
    showView: (...args) => calls.push(['show-view', ...args]),
    isRunning: true,
    window: { open: (...args) => calls.push(['open', ...args]) },
    document: { getElementById: () => ({ value: '' }) },
    findProj: () => null,
    renderSidebar: () => {},
    renderLibrary: () => {},
    currentProjectWorkspaceTab: 'overview',
  };
  vm.runInNewContext(`${source}\nglobalThis.changeProjectForTest = changeProject;`, context);

  await context.changeProjectForTest('');

  assert.equal(calls.length, 3);
  assert.deepEqual(calls[0], ['task', null]);
  assert.deepEqual(calls[1], ['render-select']);
  assert.equal(calls[2][0], 'show-view');
  assert.equal(calls[2][1], 'dashboard');
  assert.equal(calls[2][2].forceCurrentTab, true);
});
