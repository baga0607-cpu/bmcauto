const test = require('node:test');
const assert = require('node:assert/strict');

const {
  getEdgeScrollSpeed,
  createDragScrollController,
  clampPanelWidth,
  getMoveTestcaseIds,
  filterFolderOptions,
  hasPointerDragStarted,
  classifyPointerDropTarget,
  getFloatingMenuPosition,
  createPointerCommitIdentity,
  getPlanTestcaseDestinationKey,
  runPlanPointerRowCommit,
  runPlanPointerFolderCommit,
} = require('../static/plan_workspace_interactions.js');

test('edge scroll speed is zero outside both edge zones', () => {
  assert.equal(getEdgeScrollSpeed(150, 0, 300, 60, 18), 0);
});

test('edge scroll speed points up or down and increases near the edge', () => {
  assert.equal(getEdgeScrollSpeed(0, 0, 300, 60, 18), -18);
  assert.equal(getEdgeScrollSpeed(300, 0, 300, 60, 18), 18);
  assert.ok(Math.abs(getEdgeScrollSpeed(10, 0, 300, 60, 18)) > Math.abs(getEdgeScrollSpeed(40, 0, 300, 60, 18)));
  assert.ok(getEdgeScrollSpeed(290, 0, 300, 60, 18) > getEdgeScrollSpeed(260, 0, 300, 60, 18));
});

test('edge scroll speed tolerates invalid geometry without scrolling', () => {
  assert.equal(getEdgeScrollSpeed(20, 100, 100, 60, 18), 0);
  assert.equal(getEdgeScrollSpeed(Number.NaN, 0, 300, 60, 18), 0);
});

test('drag scroll controller prioritizes the folder list over the page', () => {
  const callbacks = [];
  const page = { scrollTop: 0 };
  const folder = {
    scrollTop: 0,
    getBoundingClientRect: () => ({ top: 100, bottom: 300 }),
  };
  const controller = createDragScrollController({
    pageElement: page,
    requestFrame: callback => (callbacks.push(callback), callbacks.length),
    cancelFrame: () => {},
    edgeSize: 60,
    maxSpeed: 18,
  });

  controller.update({ pointerY: 295, viewportHeight: 800, folderElement: folder });
  assert.equal(callbacks.length, 1);
  callbacks.shift()();
  assert.equal(folder.scrollTop, 16.5);
  assert.equal(page.scrollTop, 0);
});

test('drag scroll controller scrolls the page and supports wheel input', () => {
  const callbacks = [];
  const page = { scrollTop: 20 };
  const controller = createDragScrollController({
    pageElement: page,
    requestFrame: callback => (callbacks.push(callback), callbacks.length),
    cancelFrame: () => {},
    edgeSize: 60,
    maxSpeed: 18,
  });

  controller.update({ pointerY: 790, viewportHeight: 800, folderElement: null });
  callbacks.shift()();
  assert.equal(page.scrollTop, 35);
  controller.scrollWheel(120, null);
  assert.equal(page.scrollTop, 155);
});

test('drag scroll controller stop cancels pending movement', () => {
  const callbacks = [];
  const cancelled = [];
  const page = { scrollTop: 0 };
  const controller = createDragScrollController({
    pageElement: page,
    requestFrame: callback => (callbacks.push(callback), 41),
    cancelFrame: frame => cancelled.push(frame),
  });

  controller.update({ pointerY: 799, viewportHeight: 800, folderElement: null });
  controller.stop();
  assert.deepEqual(cancelled, [41]);
  callbacks.shift()();
  assert.equal(page.scrollTop, 0);
});

test('panel width clamps stored and pointer values to the shared range', () => {
  assert.equal(clampPanelWidth(180, 220, 440, 300), 220);
  assert.equal(clampPanelWidth(520, 220, 440, 300), 440);
  assert.equal(clampPanelWidth('336', 220, 440, 300), 336);
});

test('panel width falls back when storage contains an invalid value', () => {
  assert.equal(clampPanelWidth('wide', 220, 440, 300), 300);
  assert.equal(clampPanelWidth(null, 220, 440, 300), 300);
});

test('move ids use the whole selection only when the opened row is selected', () => {
  const refs = [
    { id: 'tc_a', selected: true },
    { id: 'tc_b', selected: false },
    { id: 'tc_c', selected: true },
  ];
  assert.deepEqual(getMoveTestcaseIds(refs, 0), ['tc_a', 'tc_c']);
  assert.deepEqual(getMoveTestcaseIds(refs, 1), ['tc_b']);
  assert.deepEqual(getMoveTestcaseIds(refs, 99), []);
});

test('folder option search matches names and full paths case-insensitively', () => {
  const options = [
    { key: 'category:Resource_Chassis', label: 'Resource_Chassis', path: 'Resource_Chassis' },
    { key: 'category:Custom', label: 'Custom', path: 'Custom' },
    { key: 'custom:IBM', label: 'IBM', path: 'Custom / IBM' },
  ];
  assert.deepEqual(filterFolderOptions(options, 'ibm').map(item => item.key), ['custom:IBM']);
  assert.deepEqual(filterFolderOptions(options, 'CUSTOM').map(item => item.key), ['category:Custom', 'custom:IBM']);
  assert.equal(filterFolderOptions(options, '').length, 3);
});

test('pointer drag starts only after movement reaches the threshold', () => {
  assert.equal(hasPointerDragStarted({ x: 10, y: 10 }, { x: 13, y: 14 }, 6), false);
  assert.equal(hasPointerDragStarted({ x: 10, y: 10 }, { x: 20, y: 10 }, 6), true);
});

test('pointer drop target classifies testcase rows', () => {
  const row = {
    dataset: { planTcIndex: '4' },
    closest: selector => selector === '[data-plan-tc-index]' ? row : null,
  };

  assert.deepEqual(classifyPointerDropTarget(row), { kind: 'row', index: 4 });
});

test('pointer drop target rejects a row with a blank testcase index', () => {
  const row = {
    dataset: { planTcIndex: '' },
    closest: selector => selector === '[data-plan-tc-index]' ? row : null,
  };

  assert.equal(classifyPointerDropTarget(row), null);
});

test('pointer drop target classifies plan folders before rows', () => {
  const folder = {
    dataset: { planDropKey: 'custom:IBM', planTcIndex: '4' },
    closest: selector => {
      if (selector === '[data-plan-drop-key]') return folder;
      if (selector === '[data-plan-tc-index]') return folder;
      return null;
    },
  };

  assert.deepEqual(classifyPointerDropTarget(folder), { kind: 'folder', key: 'custom:IBM' });
});

test('floating menu flips above and clamps against the viewport edge', () => {
  assert.deepEqual(
    getFloatingMenuPosition(
      { left: 700, right: 730, top: 570, bottom: 600 },
      { width: 800, height: 620 },
      { width: 210, height: 130 },
      5
    ),
    { top: 435, left: 582 }
  );
});

function createPointerCommitHarness(testcases, options = {}) {
  const events = [];
  const context = {
    projectId: 'project-a',
    planId: 'plan-a',
    viewId: 'plan-detail',
  };
  const dependencies = {
    refreshLocks: async () => {
      events.push(['refresh-locks']);
      if (options.contextAfterRefresh) Object.assign(context, options.contextAfterRefresh);
    },
    getContext: () => ({ ...context }),
    isLocked: () => false,
    getTestcases: () => testcases.map(testcase => ({ ...testcase })),
    moveTestcase: async operation => {
      events.push(['move', operation]);
      if (options.moveError) throw options.moveError;
    },
    reorderTestcases: async operation => {
      events.push(['reorder', operation]);
      if (options.reorderError) throw options.reorderError;
    },
    reload: async () => events.push(['reload']),
  };
  return { context, dependencies, events };
}

test('pointer row commit derives exact transactional destinations across folder boundaries', async () => {
  const cases = [
    {
      name: 'native to Custom child',
      testcases: [
        { id: 'source', category: 'Resource_Chassis', custom_subfolder: null },
        { id: 'target', category: 'Custom', custom_subfolder: 'IBM' },
      ],
      destination: 'custom:IBM',
    },
    {
      name: 'Custom child to native',
      testcases: [
        { id: 'source', category: 'Custom', custom_subfolder: 'IBM' },
        { id: 'target', category: 'Resource_Manager', custom_subfolder: null },
      ],
      destination: 'category:Resource_Manager',
    },
    {
      name: 'Custom child A to child B',
      testcases: [
        { id: 'source', category: 'Custom', custom_subfolder: 'A' },
        { id: 'target', category: 'Custom', custom_subfolder: 'B' },
      ],
      destination: 'custom:B',
    },
  ];

  for (const scenario of cases) {
    const harness = createPointerCommitHarness(scenario.testcases);
    const identity = createPointerCommitIdentity({
      projectId: 'project-a',
      planId: 'plan-a',
      viewId: 'plan-detail',
      sourceTestcaseId: 'source',
      targetTestcaseId: 'target',
    });

    const result = await runPlanPointerRowCommit(identity, harness.dependencies);

    assert.equal(result.status, 'committed', scenario.name);
    assert.deepEqual(harness.events, [
      ['refresh-locks'],
      ['move', { planId: 'plan-a', testcaseId: 'source', targetKey: scenario.destination }],
      ['reorder', { planId: 'plan-a', order: ['source', 'target'] }],
      ['reload'],
    ], scenario.name);
  }
});

test('pointer same-folder row reorder skips the move endpoint', async () => {
  const harness = createPointerCommitHarness([
    { id: 'first', category: 'Resource_Chassis', custom_subfolder: null },
    { id: 'source', category: 'Resource_Chassis', custom_subfolder: null },
    { id: 'target', category: 'Resource_Chassis', custom_subfolder: null },
  ]);
  const identity = createPointerCommitIdentity({
    projectId: 'project-a',
    planId: 'plan-a',
    viewId: 'plan-detail',
    sourceTestcaseId: 'source',
    targetTestcaseId: 'first',
  });

  await runPlanPointerRowCommit(identity, harness.dependencies);

  assert.deepEqual(harness.events, [
    ['refresh-locks'],
    ['reorder', { planId: 'plan-a', order: ['source', 'first', 'target'] }],
    ['reload'],
  ]);
});

test('pointer row commit reloads server state after move or reorder failure', async t => {
  for (const [name, options] of [
    ['move failure', { moveError: new Error('move failed') }],
    ['reorder failure', { reorderError: new Error('reorder failed') }],
  ]) {
    await t.test(name, async () => {
      const harness = createPointerCommitHarness([
        { id: 'source', category: 'Custom', custom_subfolder: 'A' },
        { id: 'target', category: 'Custom', custom_subfolder: 'B' },
      ], options);
      const identity = createPointerCommitIdentity({
        projectId: 'project-a',
        planId: 'plan-a',
        viewId: 'plan-detail',
        sourceTestcaseId: 'source',
        targetTestcaseId: 'target',
      });

      await assert.rejects(runPlanPointerRowCommit(identity, harness.dependencies), options.moveError || options.reorderError);
      assert.deepEqual(harness.events.at(-1), ['reload']);
    });
  }
});

test('pointer commits abort after lock refresh when project or plan context changes', async () => {
  const rowHarness = createPointerCommitHarness([
    { id: 'source', category: 'Custom', custom_subfolder: 'A' },
    { id: 'target', category: 'Custom', custom_subfolder: 'B' },
  ], { contextAfterRefresh: { projectId: 'project-b', planId: 'plan-b' } });
  const rowIdentity = createPointerCommitIdentity({
    projectId: 'project-a',
    planId: 'plan-a',
    viewId: 'plan-detail',
    sourceTestcaseId: 'source',
    targetTestcaseId: 'target',
  });

  const rowResult = await runPlanPointerRowCommit(rowIdentity, rowHarness.dependencies);

  assert.equal(rowResult.status, 'aborted');
  assert.deepEqual(rowHarness.events, [['refresh-locks']]);

  const folderHarness = createPointerCommitHarness([], {
    contextAfterRefresh: { planId: 'plan-b' },
  });
  const folderIdentity = createPointerCommitIdentity({
    projectId: 'project-a',
    planId: 'plan-a',
    viewId: 'plan-detail',
    sourceTestcaseId: 'source',
    targetFolderKey: 'custom:IBM',
  });

  const folderResult = await runPlanPointerFolderCommit(folderIdentity, folderHarness.dependencies);

  assert.equal(folderResult.status, 'aborted');
  assert.deepEqual(folderHarness.events, [['refresh-locks']]);
});

test('pointer commit identity is frozen and folder key derivation is exact', () => {
  const identity = createPointerCommitIdentity({
    projectId: 'project-a',
    planId: 'plan-a',
    viewId: 'plan-detail',
    sourceTestcaseId: 'source',
    targetFolderKey: 'custom:IBM',
  });

  assert.equal(Object.isFrozen(identity), true);
  assert.equal(getPlanTestcaseDestinationKey({ category: 'Custom', custom_subfolder: 'IBM' }), 'custom:IBM');
  assert.equal(getPlanTestcaseDestinationKey({ category: 'Resource_Chassis' }), 'category:Resource_Chassis');
});
