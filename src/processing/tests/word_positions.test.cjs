/* Evaluate the shipped renderer and exporter against the actual embedded data. */
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
const html = fs.readFileSync(path.join(root, 'docs/pages/word-positions/index.html'), 'utf8');
const code = fs.readFileSync(path.join(root, 'src/processing/templates/word_positions.js'), 'utf8');
const settle = async () => {
  for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve));
};

function fixture() {
  const dom = new JSDOM(html, {
    runScripts: 'outside-only',
    url: 'https://example.test/pages/word-positions/'
  });
  const {
    window
  } = dom, doc = window.document, blobs = [], downloads = [], draws = [];
  window.URL.createObjectURL = blob => {
    blobs.push(blob);
    return 'blob:test/' + blobs.length;
  };
  window.URL.revokeObjectURL = () => {};
  window.HTMLAnchorElement.prototype.click = function() {
    downloads.push({
      filename: this.download,
      url: this.href
    });
  };
  window.Image = class {
    set src(value) {
      this.source = value;
      queueMicrotask(() => this.onload());
    }
  };
  window.HTMLCanvasElement.prototype.getContext = function() {
    return {
      drawImage: (image, x, y, width, height) => draws.push({
        width,
        height,
        source: image.source
      })
    };
  };
  window.HTMLCanvasElement.prototype.toBlob = function(callback, type) {
    callback(new window.Blob(['test png'], {
      type
    }));
  };
  window.eval(code);

  function choose(id, value) {
    doc.getElementById(id).value = value;
    doc.getElementById(id).dispatchEvent(new window.Event(id === 'spacing' ? 'input' : 'change'));
  }
  return {
    dom,
    window,
    doc,
    blobs,
    downloads,
    draws,
    choose
  };
}

function blobText(window, blob) {
  return new Promise(resolve => {
    const reader = new window.FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsText(blob);
  });
}

test('every mode/scale/order/layout preserves source counts and sorted symbols', () => {
  const f = fixture();
  const source = JSON.parse(f.doc.getElementById('position-data').textContent);
  for (const mode of ['groups', 'letters'])
    for (const scale of ['own', 'shared'])
      for (const order of ['alphabetical', 'frequency'])
        for (const layout of ['panels', 'ridges']) {
          f.choose('mode', mode);
          f.choose('scale', scale);
          f.choose('order', order);
          f.choose('layout', layout);
          const groups = [...f.doc.querySelectorAll('#chart g[data-symbol]')];
          const stats = source.statistics[mode];
          assert.equal(groups.length, Object.keys(stats.hist).length);
          assert.equal(groups.reduce((sum, g) => sum + Number(g.dataset.count), 0), stats.total);
          const expected = Object.keys(stats.hist).sort((a, b) => (order === 'frequency' ? (stats.counts[b] || 0) - (stats.counts[a] || 0) : 0) || (a < b ? -1 : a > b ? 1 : 0));
          assert.deepEqual(groups.map(g => g.dataset.symbol), expected);
          assert.ok(!f.doc.getElementById('chart').innerHTML.includes('NaN'));
          assert.equal(f.doc.getElementById('spacing-control').hidden, layout !== 'ridges');
        }
  f.dom.window.close();
});

test('SVG and both PNG entry points export the selected snapshot with matching names', async () => {
  const f = fixture();
  f.choose('mode', 'letters');
  f.choose('scale', 'shared');
  f.choose('order', 'frequency');
  f.choose('layout', 'ridges');
  f.choose('spacing', '38');
  const expected = 'eva_word_positions_letters_shared_frequency_ridges_38px';
  f.doc.getElementById('save').click();
  assert.equal(f.downloads[0].filename, expected + '.svg');
  const xml = await blobText(f.window, f.blobs[0]);
  assert.match(xml, /letters; shared count scale; frequency order; overlapping ridgelines/);
  assert.match(xml, /Ridgelines, 38 px spacing/);
  assert.ok(!xml.includes('data-symbol="ch"'));
  // Capture the PNG before the selectors change while its image loads.
  f.doc.getElementById('save-png').click();
  f.choose('mode', 'groups');
  await settle();
  assert.equal(f.downloads[1].filename, expected + '.png');
  assert.equal(f.draws[0].width, 2240);
  assert.equal(f.draws[0].height, Number(new f.window.DOMParser().parseFromString(xml, 'image/svg+xml').documentElement.getAttribute('height')) * 2);
  assert.equal(f.blobs[2].type, 'image/png');
  const pngSource = await blobText(f.window, f.blobs[1]);
  assert.equal(pngSource, xml);
  f.doc.querySelector('[data-current-export="png"]').dispatchEvent(new f.window.MouseEvent('click', {
    bubbles: true,
    cancelable: true
  }));
  await settle();
  assert.match(f.downloads[2].filename, /groups_shared_frequency_ridges_38px.png/);
  assert.match(f.doc.getElementById('export-status').textContent, /Current PNG downloaded/);
  f.dom.window.close();
});

test('PNG canvas failure reports a useful error and restores the button', async () => {
  const f = fixture();
  f.window.HTMLCanvasElement.prototype.toBlob = function(callback) {
    callback(null);
  };
  f.doc.getElementById('save-png').click();
  await settle();
  assert.match(f.doc.getElementById('export-status').textContent, /PNG encoding failed/);
  assert.equal(f.doc.getElementById('save-png').disabled, false);
  assert.equal(f.downloads.length, 0);
  f.dom.window.close();
});
