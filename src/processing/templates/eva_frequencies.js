(function() {
  'use strict';
  const chart = document.getElementById('chart'),
    initial = chart.innerHTML;
  try {
    const data = JSON.parse(document.getElementById('reference').textContent),
      glyphs = JSON.parse(document.getElementById('glyphData').textContent);
    for (const key of ['letters', 'groups']) {
      if (!Array.isArray(data[key]) || !data[key].length || data[key].some(x => typeof x.symbol !== 'string' || !Number.isSafeInteger(x.count) || x.count < 0 || !glyphs[x.symbol]) || !data[key].some(x => x.count > 0)) throw Error('Invalid embedded reference data');
    }
    const mode = document.getElementById('mode'),
      sort = document.getElementById('sort'),
      scale = document.getElementById('scale');

    function render() {
      const a = data[mode.value].slice().sort((a, b) => sort.value === 'alphabet' ? a.symbol.localeCompare(b.symbol) : b.count - a.count || a.symbol.localeCompare(b.symbol));
      const total = a.reduce((s, x) => s + x.count, 0),
        max = Math.max(...a.map(x => x.count)),
        log = scale.value === 'log',
        frag = document.createDocumentFragment();
      for (const x of a) {
        const tr = document.createElement('tr'),
          th = document.createElement('th');
        th.scope = 'row';
        const g = document.createElement('span');
        g.className = 'glyph';
        g.innerHTML = glyphs[x.symbol];
        const code = document.createElement('code');
        code.textContent = x.symbol;
        th.append(g, code);
        tr.append(th);
        const td = document.createElement('td'),
          track = document.createElement('div'),
          bar = document.createElement('div');
        track.className = 'track';
        bar.className = 'bar';
        bar.style.width = (100 * (log ? Math.log1p(x.count) / Math.log1p(max) : x.count / max)) + '%';
        track.append(bar);
        td.append(track);
        tr.append(td);
        for (const val of [x.count.toLocaleString('en-US'), (100 * x.count / total).toFixed(3) + '%']) {
          const cell = document.createElement('td');
          cell.className = 'num';
          cell.textContent = val;
          tr.append(cell)
        }
        frag.append(tr)
      }
      chart.replaceChildren(frag);
      document.getElementById('total').textContent = total.toLocaleString('en-US');
      document.getElementById('unit').textContent = mode.value === 'groups' ? 'counted grouped tokens' : 'counted EVA letters';
      document.getElementById('scaleLabel').textContent = log ? '(logarithmic)' : '(linear)';
      document.getElementById('status').textContent = 'Embedded reference data · ' + a.length + ' categories · ' + (log ? 'logarithmic' : 'linear') + ' bars. Percentages use all counted tokens in this mode.';
    }
    for (const el of [mode, sort, scale]) el.addEventListener('change', render);
    document.getElementById('download').addEventListener('click', () => {
      const a = data[mode.value],
        total = a.reduce((s, x) => s + x.count, 0),
        csv = 'eva,count,percent,mode\n' + a.map(x => [x.symbol, x.count, (100 * x.count / total).toFixed(6), mode.value].join(',')).join('\n');
      const url = URL.createObjectURL(new Blob([csv], {
          type: 'text/csv;charset=utf-8'
        })),
        link = document.createElement('a');
      link.href = url;
      link.download = 'voynich_eva_' + mode.value + '.csv';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    });
    render();
    document.getElementById('controls').hidden = false;
  } catch (e) {
    chart.innerHTML = initial;
    document.getElementById('controls').hidden = true;
    document.getElementById('status').textContent = 'Interactive controls unavailable. Showing the embedded default chart: grouped forms, linear bars.';
  }
})();
