/* Exercise the shipped browser code, not a duplicate chart implementation. */
const {
  test
} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  JSDOM
} = require('jsdom');
const templates = path.join(__dirname, '..', 'templates');
const manifest = {
  sources: [{
    id: 'VT',
    label: 'fixture',
    tokens: 9,
    basic_tokens: 8,
    sha256: 'fixture',
    url: 'https://example.test/source',
    shards: ['vocab.json'],
    maps: {
      none: 'none.json',
      prefix1: 'prefix1.json'
    }
  }],
  treatments: [
    ['none', 'Whole words'],
    ['prefix1', 'Prefix-1']
  ]
};
const assets = {
  'manifest.json': manifest,
  'vocab.json': [
    ['daiin', 4, 'f1r'],
    ['dain', 3, 'f2v'],
    ['or', 1, 'f1r'],
    ['o?', 1, 'f3r']
  ],
  'none.json': {
    keys: ['daiin', 'dain', 'or', 'o?'],
    map: [0, 1, 2, 3]
  },
  'prefix1.json': {
    keys: ['d', 'o', 'o?'],
    map: [0, 0, 1, 2]
  }
};
async function settle(dom) {
  for (let i = 0; i < 20; i++) await new Promise(resolve => setImmediate(resolve));
  assert.ok(!dom.window.document.getElementById('status').textContent.includes('Could not'));
}
async function fixture() {
  const dom = new JSDOM(fs.readFileSync(path.join(templates, 'word_frequencies.html'), 'utf8'), {
    runScripts: 'outside-only',
    url: 'https://example.test/pages/word-frequencies/'
  });
  dom.window.fetch = async url => ({
    ok: true,
    json: async () => structuredClone(assets[url.replace('data/', '')])
  });
  dom.window.eval(fs.readFileSync(path.join(templates, 'word_frequencies.js'), 'utf8'));
  await settle(dom);
  // The production default source is ZL; choose our VT fixture explicitly.
  const doc = dom.window.document;
  doc.querySelector('#sources input').checked = true;
  doc.querySelector('#treatments input').checked = true;
  doc.getElementById('update').click();
  await settle(dom);
  return dom;
}
test('count/abundance curves, literal population and inspectable family links', async () => {
  const dom = await fixture(),
    doc = dom.window.document;
  assert.match(doc.getElementById('summary').textContent, /8 source tokens/);
  assert.match(doc.querySelector('#rows tr').textContent, /50%/);
  doc.querySelector('#treatments input[value=none]').checked = false;
  doc.querySelector('#treatments input[value=prefix1]').checked = true;
  doc.getElementById('update').click();
  await settle(dom);
  assert.match(doc.getElementById('summary').textContent, /3 original types → 2 families/);
  assert.match(doc.querySelector('#rows tr').textContent, /87.5%/);
  doc.querySelector('#rows button').click();
  assert.equal(doc.querySelectorAll('#family a').length, 2);
  assert.equal(doc.querySelector('#family a').href, 'https://www.voynichese.com/#/f1r/exa:daiin');
  doc.getElementById('population').value = 'all';
  doc.getElementById('update').click();
  await settle(dom);
  assert.match(doc.getElementById('summary').textContent, /9 source tokens/);
  assert.match(doc.getElementById('summary').textContent, /4 original types → 3 families/);
  doc.getElementById('view').value = 'histogram';
  doc.getElementById('view').dispatchEvent(new dom.window.Event('change'));
  assert.match(doc.getElementById('plot-description').textContent, /Share of family types/);
  doc.getElementById('measure').value = 'count';
  doc.getElementById('measure').dispatchEvent(new dom.window.Event('change'));
  assert.match(doc.getElementById('plot-description').textContent, /Number of family types/);
  assert.ok(!doc.querySelector('#chart').innerHTML.includes('NaN'));
  doc.getElementById('filter').value = 'daiin';
  doc.getElementById('filter').dispatchEvent(new dom.window.Event('input'));
  assert.equal(doc.querySelectorAll('#rows tr').length, 1);
  dom.window.close();
});
test('missing mapping reports a retryable error instead of a broken plot', async () => {
  const dom = await fixture(),
    doc = dom.window.document;
  dom.window.fetch = async () => ({
    ok: false,
    status: 503
  });
  // Existing assets are cached. A fresh fixture failure tests the startup path.
  dom.window.close();
  const failed = new JSDOM(fs.readFileSync(path.join(templates, 'word_frequencies.html'), 'utf8'), {
    runScripts: 'outside-only',
    url: 'https://example.test/'
  });
  failed.window.fetch = async () => ({
    ok: false,
    status: 503
  });
  failed.window.eval(fs.readFileSync(path.join(templates, 'word_frequencies.js'), 'utf8'));
  for (let i = 0; i < 10; i++) await new Promise(resolve => setImmediate(resolve));
  assert.match(failed.window.document.getElementById('status').textContent, /Could not load the chart/);
  failed.window.close();
});
