const {
  test
} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  JSDOM
} = require('jsdom');
const root = path.resolve(__dirname, '../../..');
const page = path.join(root, 'docs/pages/vowel-discovery');
async function settle(f) {
  for (let i = 0; i < 50; i++) await new Promise(resolve => setImmediate(resolve));
  assert.ok(!f.doc.getElementById('status').textContent.includes('Could not'));
}
async function fixture() {
  const dom = new JSDOM(fs.readFileSync(path.join(page, 'index.html'), 'utf8'), {
    runScripts: 'outside-only',
    url: 'https://example.test/pages/vowel-discovery/'
  });
  dom.window.fetch = async url => ({
    ok: true,
    json: async () => JSON.parse(fs.readFileSync(path.join(page, url), 'utf8'))
  });
  dom.window.eval(fs.readFileSync(path.join(root, 'src/processing/templates/vowel_discovery.js'), 'utf8'));
  const doc = dom.window.document;
  const choose = (id, value) => {
    doc.getElementById(id).value = value;
    doc.getElementById(id).dispatchEvent(new dom.window.Event(id === 'minimum' ? 'input' : 'change'));
  };
  const f = {
    dom,
    doc,
    choose
  };
  await settle(f);
  return f;
}
test('glyph stability, related treatments, contacts and original-word links load', async () => {
  const f = await fixture();
  assert.ok(f.doc.querySelectorAll('#symbol-rows tr').length > 10);
  assert.equal(f.doc.querySelectorAll('#perturbation-head th').length, 8);
  assert.ok(f.doc.querySelector('#examples a').href.startsWith('https://www.voynichese.com/#/f1r/exa:'));
  assert.ok(f.doc.querySelectorAll('#matrix rect').length > 100);
  assert.ok(!f.doc.getElementById('matrix').innerHTML.includes('NaN'));
  const row = f.doc.querySelector('#symbol-rows tr');
  const selector = row.querySelector('select');
  const before = f.doc.getElementById('contact-summary').textContent;
  selector.value = '?';
  selector.dispatchEvent(new f.dom.window.Event('change'));
  assert.notEqual(f.doc.getElementById('contact-summary').textContent, before);
  f.doc.getElementById('reset').click();
  assert.equal(f.doc.getElementById('contact-summary').textContent, before);
  f.dom.window.close();
});
test('reference labels stay hidden until revealed and deletion retains no reference vowels', async () => {
  const f = await fixture();
  f.choose('source', 'forme');
  await settle(f);
  assert.equal(f.doc.getElementById('mode').disabled, true);
  assert.match(f.doc.querySelector('#symbol-rows tr').lastChild.textContent, /hidden/);
  f.doc.getElementById('reveal').click();
  assert.match(f.doc.getElementById('reference-summary').textContent, /precision/);
  f.choose('control', 'deleted');
  await settle(f);
  assert.match(f.doc.getElementById('reference-summary').textContent, /reference vowels deleted/);
  assert.ok(!f.doc.querySelector('#examples a'));
  assert.equal(f.doc.querySelectorAll('#perturbation-head th').length, 6);
  f.choose('method', 'hmm');
  f.choose('minimum', '1000000');
  assert.equal(f.doc.querySelectorAll('#symbol-rows tr').length, 0);
  f.choose('source', 'ZL');
  await settle(f);
  assert.equal(f.doc.getElementById('control').value, 'native');
  assert.equal(f.doc.getElementById('reveal').disabled, true);
  f.dom.window.close();
});
