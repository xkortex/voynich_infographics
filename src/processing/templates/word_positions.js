/* Rebuild an embedded SVG for the selected view; export that same snapshot. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const colors = ['#fff9bf', '#ffe28a', '#ffc267', '#ff963e', '#ff602e', '#e52722', '#b9002e'];
  const thresholds = [.1, .5, 1, 2, 5, 9];
  const colorLabels = ['<0.1%', '0.1–0.5%', '0.5–1%', '1–2%', '2–5%', '5–9%', '≥9%'];
  const escape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  const format = value => value.toLocaleString('en-US');
  let data;

  function text(x, y, content, attributes = '') {
    return `<text x="${x}" y="${y}" ${attributes}>${escape(content)}</text>`;
  }

  function render() {
    const mode = $('mode').value,
      shared = $('scale').value === 'shared';
    const frequencyOrder = $('order').value === 'frequency';
    const ridges = $('layout').value === 'ridges',
      spacing = Number($('spacing').value);
    $('spacing-control').hidden = !ridges;
    $('spacing-value').value = `${spacing} px`;
    const stats = data.statistics[mode];
    const symbols = Object.keys(stats.hist).sort((a, b) =>
      (frequencyOrder ? (stats.counts[b] || 0) - (stats.counts[a] || 0) : 0) || (a < b ? -1 : a > b ? 1 : 0));
    const rows = ridges ? symbols.length : Math.ceil(symbols.length / 2);
    const step = ridges ? spacing : 105;
    const footerY = (ridges ? 260 : 215) + rows * step;
    const height = footerY + 230;
    const globalPeak = Math.max(1, ...Object.values(stats.hist).flat());
    const pieces = [
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 ${height}" width="1120" height="${height}" role="img" aria-labelledby="title desc">`,
      '<title id="title">Where EVA symbols occur within words</title>',
      `<desc id="desc">${escape(`${mode}; ${shared ? 'shared count scale' : 'each symbol’s own peak'}; ${frequencyOrder ? 'frequency order' : 'alphabetical order'}; ${ridges ? 'overlapping ridgelines' : 'separate panels'}. Beginning at left, end at right.`)}</desc>`,
      '<rect width="1120" height="100%" fill="#fffdf7"/>',
      '<style>text{font-family:system-ui,sans-serif;fill:#263a37}.small{font-size:13px;fill:#62716c}.label{font:16px monospace}.head{font:42px Georgia,serif}.axis{stroke:#9da79e;stroke-width:1}</style>',
      text(45, 62, 'Where EVA symbols occur within words', 'class="head"'),
      text(45, 98, `Beginning → middle → end · ${mode === 'groups' ? 'Grouped EVA forms' : 'Individual EVA letters'}`, 'font-size="18"'),
      text(45, 128, `${format(data.word_count)} word occurrences · ${format(stats.total)} counted tokens · Zandbergen–Landini 3b`, 'class="small"'),
      text(45, 153, `${shared ? 'Shared bin-count scale' : 'Each symbol scaled to its own peak'} · ${frequencyOrder ? 'Most frequent first' : 'Alphabetical'} · ${ridges ? `Ridgelines, ${spacing} px spacing` : 'Separate panels'}`, 'class="small"')
    ];
    symbols.forEach((symbol, index) => {
      const column = ridges ? 0 : Math.floor(index / rows),
        row = index % rows;
      const x = 45 + column * 550;
      const baseline = ridges ? 260 + row * step : 276 + row * step;
      const plotX = ridges ? 160 : x + 100,
        width = ridges ? 795 : 410,
        peakHeight = ridges ? 66 : 61;
      const counts = stats.hist[symbol],
        count = stats.counts[symbol] || 0;
      const peak = shared ? globalPeak : Math.max(1, ...counts);
      const share = count / stats.total * 100;
      const color = colors[thresholds.findIndex(threshold => share < threshold) === -1 ? 6 : thresholds.findIndex(threshold => share < threshold)];
      const points = [
        [plotX, baseline], ...counts.map((value, bin) => [plotX + (bin + .5) / counts.length * width, baseline - value / peak * peakHeight]), [plotX + width, baseline]
      ];
      const path = 'M' + points.map(([px, py]) => `${px.toFixed(2)},${py.toFixed(2)}`).join(' L') + ' Z';
      pieces.push(`<g data-symbol="${symbol}" data-count="${count}">`);
      // A paper-colored underlay hides the lower part of the preceding ridge.
      if (ridges) pieces.push(`<path d="${path}" fill="#fffdf7"/>`);
      pieces.push(`<path d="${path}" fill="${color}" fill-opacity="${ridges ? '.25' : '1'}" stroke="#665d4e" stroke-width="${ridges ? '1.6' : '1.1'}"/>`);
      pieces.push(`<line x1="${plotX}" x2="${plotX + width}" y1="${baseline}" y2="${baseline}" class="axis"/>`);
      const glyphY = ridges ? baseline - 42 : baseline - 115;
      const glyphSize = ridges ? 44 : 66;
      pieces.push(data.glyphs[symbol].replace('<svg aria-hidden="true"', `<svg aria-hidden="true" x="${x}" y="${glyphY}" width="${glyphSize}" height="${glyphSize}"`));
      pieces.push(text(ridges ? 105 : x + 32, ridges ? baseline - 10 : baseline - 36, symbol, `class="label"${ridges ? '' : ' text-anchor="middle"'}`));
      if (ridges) {
        pieces.push(text(1075, baseline - 20, format(count), 'class="small" text-anchor="end"'));
        pieces.push(text(1075, baseline - 3, share.toFixed(3) + '%', 'class="small" text-anchor="end"'));
      } else {
        pieces.push(text(plotX, baseline - 70, format(count) + ' occurrences', 'class="small"'));
        pieces.push(text(plotX + width, baseline - 70, share.toFixed(3) + '%', 'class="small" text-anchor="end"'));
      }
      if (!count) pieces.push(text(plotX + width / 2, baseline - 12, 'No occurrences in this mode', 'class="small" text-anchor="middle"'));
      pieces.push('</g>');
    });
    pieces.push(text(45, footerY, 'Color = overall token frequency', 'font-size="15"'));
    colors.forEach((color, index) => {
      pieces.push(`<rect x="${45 + index * 110}" y="${footerY + 14}" width="110" height="15" fill="${color}"/>`);
      pieces.push(text(45 + index * 110, footerY + 48, colorLabels[index], 'class="small"'));
    });
    const notes = [
      'Position = token index / (word length − 1), binned into 15 equal intervals. Left = beginning; right = end.',
      'Single-token words map to the middle. Every word occurrence contributes; repeated types are not deduplicated.',
      'Uncertain words are omitted in full. Grouped forms: cfh, ckh, cph, cth, ch, sh use longest match.',
      ridges ? 'Ridgelines overlap with opaque underlays. Reduced spacing can obscure part of the preceding shape.' : 'Own-peak scaling compares shapes; shared scaling compares absolute bin counts.',
      'Data: Zandbergen & Landini, ZL3b-n.txt (CC0). Glyph outlines: Gabriel Landini, EVA2.ttf (2025).'
    ];
    notes.forEach((note, index) => pieces.push(text(45, footerY + 79 + index * 21, note, 'class="small"')));
    pieces.push('</svg>');
    $('chart').innerHTML = pieces.join('');
  }

  function snapshot() {
    const svg = $('chart').querySelector('svg');
    if (!svg) throw new Error('The chart is not ready.');
    const [, , width, height] = svg.getAttribute('viewBox').split(/\s+/).map(Number);
    const settings = [$('mode').value, $('scale').value, $('order').value, $('layout').value];
    if ($('layout').value === 'ridges') settings.push($('spacing').value + 'px');
    return {
      xml: new XMLSerializer().serializeToString(svg),
      width,
      height,
      filename: 'eva_word_positions_' + settings.join('_')
    };
  }

  function download(blob, filename) {
    const url = URL.createObjectURL(blob),
      link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function save(format) {
    const status = $('export-status');
    try {
      // Capture before any asynchronous work so a later choice cannot change it.
      const current = snapshot();
      if (format === 'svg') {
        download(new Blob([current.xml], {
          type: 'image/svg+xml;charset=utf-8'
        }), current.filename + '.svg');
        status.textContent = 'Current SVG downloaded.';
        return;
      }
      $('save-png').disabled = true;
      status.textContent = 'Rendering current PNG…';
      const url = URL.createObjectURL(new Blob([current.xml], {
        type: 'image/svg+xml;charset=utf-8'
      }));
      try {
        const image = new Image();
        await new Promise((resolve, reject) => {
          image.onload = resolve;
          image.onerror = () => reject(new Error('Could not render the chart image. Try SVG export.'));
          image.src = url;
        });
        const canvas = document.createElement('canvas');
        const zoom = Math.min(2, Math.sqrt(16000000 / (current.width * current.height)));
        canvas.width = Math.round(current.width * zoom);
        canvas.height = Math.round(current.height * zoom);
        const context = canvas.getContext('2d');
        if (!context) throw new Error('PNG export is unavailable in this browser. Try SVG export.');
        context.drawImage(image, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('PNG encoding failed. Try SVG export.')), 'image/png'));
        download(blob, current.filename + '.png');
        status.textContent = 'Current PNG downloaded.';
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      status.textContent = error.message;
    } finally {
      $('save-png').disabled = false;
    }
  }

  try {
    data = JSON.parse($('position-data').textContent);
    ['mode', 'scale', 'order', 'layout'].forEach(id => $(id).addEventListener('change', render));
    $('spacing').addEventListener('input', render);
    $('save').addEventListener('click', () => save('svg'));
    $('save-png').addEventListener('click', () => save('png'));
    document.querySelectorAll('[data-current-export]').forEach(link => link.addEventListener('click', event => {
      event.preventDefault();
      save(link.dataset.currentExport);
    }));
    render();
    $('controls').hidden = false;
  } catch (error) {
    // Keep the pre-rendered default available if the interactive renderer fails.
    $('controls').hidden = false;
    $('export-status').textContent = 'Interactive controls could not load: ' + error.message;
  }
})();
