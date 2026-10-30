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
const templates = path.join(root, 'src/processing/templates');
const settle = async () => {
  for (let i = 0; i < 15; i++) await new Promise(resolve => setImmediate(resolve));
};
const model = {
  alphabet: [' ', 'a', 'b', 'c'],
  starts: [
    [1, 2],
    [2, 1]
  ],
  start_pairs: {
    '1': [
      [0, 2]
    ],
    '2': [
      [0, 1]
    ]
  },
  first: {
    '1': [
      [0, 2]
    ],
    '2': [
      [0, 2]
    ],
    '3': [
      [0, 1]
    ],
    '0': [
      [1, 1],
      [2, 2],
      [3, 2]
    ]
  },
  second: {
    '1,0': [
      [2, 1],
      [3, 1]
    ],
    '0,2': [
      [0, 1]
    ],
    '2,0': [
      [1, 1],
      [3, 1]
    ],
    '0,3': [
      [0, 1]
    ],
    '3,0': [
      [2, 1]
    ]
  },
  runs: 3
};
async function fixture(data = model) {
  const dom = new JSDOM(fs.readFileSync(path.join(templates, 'markov_transitions.html'), 'utf8'), {
    runScripts: 'outside-only',
    url: 'https://example.test/'
  });
  const doc = dom.window.document;
  const manifest = {
    sources: ['ZL', 'IT'].map(id => ({
      id,
      label: id,
      sha256: 'fixture',
      url: 'https://example.test/source',
      files: {
        groups: id + '.json',
        letters: id + '.json'
      }
    }))
  };
  dom.window.fetch = async url => ({
    ok: true,
    json: async () => url.includes('manifest') ? manifest : url.includes('glyphs') ? {} : structuredClone(data)
  });
  dom.window.eval(fs.readFileSync(path.join(templates, 'markov_transitions.js'), 'utf8'));
  await settle();
  const choose = (id, value) => {
    doc.getElementById(id).value = value;
    doc.getElementById(id).dispatchEvent(new dom.window.Event('change'));
  };
  const append = id => doc.querySelector(`#diagram .destination[data-unit="${id}"]`).dispatchEvent(new dom.window.MouseEvent('click', {
    bubbles: true
  }));
  return {
    dom,
    doc,
    choose,
    append
  };
}
test('first/second order context, spaces, manual nodes, undo and reset', async () => {
  const f = await fixture();
  f.append(1);
  f.append(0);
  assert.equal(f.doc.getElementById('output').textContent, 'a␠');
  assert.equal(f.doc.querySelectorAll('#choices tr').length, 3);
  assert.match(f.doc.getElementById('choices').textContent, /40%/);
  f.choose('order', '2');
  assert.equal(f.doc.getElementById('output').textContent, 'a␠');
  assert.match(f.doc.getElementById('context').textContent, /a · ␠/);
  assert.equal(f.doc.querySelectorAll('#choices tr').length, 2);
  assert.match(f.doc.getElementById('choices').textContent, /50%/);
  f.append(3);
  f.append(0);
  f.append(2);
  f.append(0);
  f.append(1);
  assert.equal(f.doc.getElementById('next').disabled, true); // pair space,a is terminal only.
  assert.match(f.doc.getElementById('status').textContent, /no observed successor/);
  f.doc.getElementById('undo').click();
  assert.equal(f.doc.getElementById('next').disabled, false);
  f.doc.getElementById('reset').click();
  assert.match(f.doc.getElementById('context').textContent, /START/);
  assert.equal(f.doc.getElementById('undo').disabled, true);
  f.choose('order', '2');
  f.append(1);
  assert.match(f.doc.getElementById('basis').textContent, /warm-up/);
  f.choose('source', 'IT');
  await settle();
  assert.match(f.doc.getElementById('context').textContent, /START/);
  f.dom.window.close();
});
test('weighted draws honor cumulative boundaries and current-node random advance', async () => {
  for (const [random, expected] of [
      [0, 'b'],
      [.39999, 'b'],
      [.4, 'c'],
      [.79999, 'c'],
      [.8, 'a'],
      [.99999, 'a']
    ]) {
    const f = await fixture();
    f.append(1);
    f.append(0);
    f.dom.window.Math.random = () => random;
    f.doc.querySelector('#diagram .current-node').dispatchEvent(new f.dom.window.MouseEvent('click', {
      bubbles: true
    }));
    assert.equal(f.doc.getElementById('output').textContent, 'a␠' + expected);
    assert.match(f.doc.getElementById('last-choice').textContent, /Sampled/);
    f.dom.window.close();
  }
});
test('hidden tail still participates in Next sampling', async () => {
  const alphabet = [' ', 'x', ...'abcdefghijklmno'];
  const tail = alphabet.slice(2).map((_, index) => [index + 2, 1]);
  const wide = {
    alphabet,
    starts: [
      [1, 1]
    ],
    start_pairs: {
      '1': [
        [0, 1]
      ]
    },
    first: {
      '1': [
        [0, 1]
      ],
      '0': tail
    },
    second: {
      '1,0': tail
    },
    runs: 1
  };
  const f = await fixture(wide);
  f.append(1);
  f.append(0);
  assert.equal(f.doc.querySelectorAll('#diagram .destination').length, 12);
  assert.equal(f.doc.querySelectorAll('#choices tr').length, 15);
  f.dom.window.Math.random = () => .9999;
  f.doc.getElementById('next').click();
  assert.equal(f.doc.getElementById('output').textContent, 'x␠o');
  f.dom.window.close();
});
