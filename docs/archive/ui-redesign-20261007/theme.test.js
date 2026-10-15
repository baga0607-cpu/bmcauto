const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const sourcePath = path.join(__dirname, '../static/theme.js');

function fixture(saved, unavailable = false) {
  const attributes = {};
  const listeners = {};
  const button = { attributes: {}, listeners: {}, setAttribute(k, v) { this.attributes[k] = v; }, addEventListener(k, fn) { this.listeners[k] = fn; } };
  const values = new Map(saved === undefined ? [] : [['bmc-theme', saved]]);
  const environment = {
    document: { documentElement: { setAttribute(k, v) { attributes[k] = v; } }, getElementById() { return button; } },
    get localStorage() {
      if (unavailable) throw new Error('Storage blocked');
      return { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v) };
    },
    addEventListener(k, fn) { listeners[k] = fn; }
  };
  return { attributes, button, values, listeners, environment };
}

// Removing persistence or initial application must break these observable behavior checks.
test('theme implementation is available', () => assert.ok(fs.existsSync(sourcePath)));
if (fs.existsSync(sourcePath)) {
  const { createTheme } = require(sourcePath);
  test('restores light before button initialization and defaults invalid preferences to dark', () => {
    for (const [saved, expected] of [['light', 'light'], ['dark', 'dark'], ['unknown', 'dark'], [undefined, 'dark']]) {
      const f = fixture(saved);
      createTheme(f.environment);
      assert.equal(f.attributes['data-theme'], expected);
    }
  });
  test('button toggles theme, persists preference and updates accessible action and icon', () => {
    const f = fixture();
    const theme = createTheme(f.environment);
    theme.initialize();
    assert.match(f.button.innerHTML, /theme-sun/);
    assert.equal(f.button.attributes['aria-label'], 'Switch to light theme');
    f.button.listeners.click();
    assert.equal(f.attributes['data-theme'], 'light');
    assert.equal(f.values.get('bmc-theme'), 'light');
    assert.match(f.button.innerHTML, /theme-moon/);
    assert.equal(f.button.attributes['aria-label'], 'Switch to dark theme');
    theme.toggle();
    assert.equal(f.attributes['data-theme'], 'dark');
    assert.equal(f.values.get('bmc-theme'), 'dark');
  });
  test('blocked storage still permits initialization and repeated toggling', () => {
    const f = fixture(undefined, true);
    const theme = createTheme(f.environment);
    theme.initialize();
    theme.toggle();
    assert.equal(f.attributes['data-theme'], 'light');
    theme.toggle();
    assert.equal(f.attributes['data-theme'], 'dark');
  });
  test('cross-tab preference updates theme and button without rewriting storage', () => {
    const f = fixture();
    const theme = createTheme(f.environment);
    theme.initialize();
    f.listeners.storage({ key: 'unrelated', newValue: 'light' });
    assert.equal(f.attributes['data-theme'], 'dark');
    f.listeners.storage({ key: 'bmc-theme', newValue: 'light' });
    assert.equal(f.attributes['data-theme'], 'light');
    assert.equal(f.button.attributes['aria-label'], 'Switch to dark theme');
    assert.equal(f.values.size, 0);
    f.listeners.storage({ key: 'bmc-theme', newValue: null });
    assert.equal(f.attributes['data-theme'], 'dark');
  });
  test('initialize can run repeatedly without duplicate button handlers', () => {
    const f = fixture();
    let count = 0;
    f.button.addEventListener = () => { count++; };
    const theme = createTheme(f.environment);
    theme.initialize();
    theme.initialize();
    assert.equal(count, 1);
  });
}
