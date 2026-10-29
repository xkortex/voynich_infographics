/* All model fitting is reproducible offline; this page only explores saved data. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const cache = new Map();
  let manifest, glyphs = {},
    current, selected, related = [],
    version = 0,
    revealed = false;
  let assignments = [];
  const fmt = n => Number(n).toLocaleString(undefined, {
    maximumFractionDigits: 2
  });
  const percent = n => fmt(n * 100) + '%';

  function el(tag, text) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function svg(tag, attributes = {}, text) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function option(value, label) {
    const node = el('option', label);
    node.value = value;
    return node;
  }
  async function read(file) {
    if (!cache.has(file)) cache.set(file, fetch('data/' + file).then(response => {
      if (!response.ok) throw new Error(`Could not load ${file} (${response.status})`);
      return response.json();
    }).catch(error => {
      cache.delete(file);
      throw error;
    }));
    return cache.get(file);
  }

  function reference(symbol) {
    return symbol === 'æ' || symbol === 'œ' || 'aeiou'.includes(symbol.normalize('NFD')[0]);
  }

  function fitted() {
    return current[$('method').value].map(value => value === null ? null : ($('method').value === 'hmm' ? (value >= .5) : Boolean(value)));
  }

  function visible() {
    const minimum = Math.max(1, Number($('minimum').value) || 1);
    return current.symbols.map((_, i) => i).filter(i => current.counts[i] >= minimum);
  }

  function glyph(index) {
    const box = el('span');
    box.className = 'symbol';
    const symbol = current.symbols[index];
    if (selected.source.length === 2 && glyphs[symbol]) {
      const holder = el('span');
      holder.innerHTML = glyphs[symbol];
      box.append(holder);
    }
    box.append(el('code', symbol));
    return box;
  }

  function badge(value) {
    const node = el('span', value === null ? '—' : value ? 'A' : 'B');
    node.className = 'badge ' + (value === null ? 'unknown' : value ? 'a' : 'b');
    return node;
  }

  function bar(A, n) {
    const box = el('span');
    if (!n) {
      box.textContent = 'unseen';
      return box;
    }
    const track = el('span');
    track.className = 'bar';
    const fill = el('i');
    fill.style.width = (100 * A / n) + '%';
    track.append(fill);
    box.append(track, el('small', `${A}/${n} A`));
    return box;
  }

  function perturbations() {
    const method = $('method').value;
    const heading = el('tr');
    heading.append(el('th', 'Symbol'));
    related.forEach(({
      scenario
    }) => heading.append(el('th', scenario.source + ' · ' + scenario.mode + ' · ' + scenario.scope + ' · ' + scenario.control)));
    $('perturbation-head').replaceChildren(heading);
    $('perturbation-rows').replaceChildren();
    visible().sort((a, b) => current.counts[b] - current.counts[a] || a - b).forEach(i => {
      const row = el('tr'),
        label = el('td');
      label.append(glyph(i));
      row.append(label);
      related.forEach(({
        data,
        scenario
      }) => {
        const j = data.symbols.indexOf(current.symbols[i]);
        const p = j < 0 ? null : data[method][j];
        const cell = el('td');
        cell.append(badge(p === null ? null : method === 'hmm' ? p >= .5 : Boolean(p)));
        cell.title = scenario.id + ' · seed ' + data.seed_symbol + (p === null ? ' · unseen' : '');
        row.append(cell);
      });
      $('perturbation-rows').append(row);
    });
    const summary = $('reference-summary');
    summary.textContent = '';
    if (revealed && selected.source.length !== 2) {
      let tp = 0,
        fp = 0,
        fn = 0;
      current.symbols.forEach((symbol, i) => {
        const vowel = reference(symbol),
          count = current.counts[i];
        if (assignments[i] === true) {
          if (vowel) tp += count;
          else fp += count;
        } else if (vowel) fn += count;
      });
      summary.textContent = 'Orthographic reference check (token weighted): A precision ' + (tp + fp ? percent(tp / (tp + fp)) : 'undefined; no A tokens') + ' · vowel-letter recall ' + (tp + fn ? percent(tp / (tp + fn)) : 'undefined; reference vowels deleted') + '. Reference labels did not enter fitting.';
    }
  }

  function metrics() {
    const holder = $('metrics');
    holder.replaceChildren();
    const A = assignments.filter(value => value === true).length,
      B = assignments.filter(value => value === false).length;
    const values = [
      [fmt(current.words), 'retained word occurrences'],
      [fmt(current.pairs.flat().reduce((a, b) => a + b, 0)), 'within-word adjacent pairs'],
      [`${A} / ${B}`, 'symbol types assigned A / B'],
      [fmt(current.fit_words), 'words in full HMM training sample']
    ];
    values.forEach(([value, label]) => {
      const card = el('div');
      card.className = 'metric';
      card.append(el('strong', value), el('span', label));
      holder.append(card);
    });
  }

  function table() {
    $('symbol-rows').replaceChildren();
    visible().sort((a, b) => current.counts[b] - current.counts[a] || a - b).forEach(i => {
      const row = el('tr'),
        symbolCell = el('td');
      symbolCell.append(glyph(i));
      row.append(symbolCell, el('td', fmt(current.counts[i])));
      const suk = el('td');
      suk.append(badge(current.sukhotin[i]));
      row.append(suk);
      const hmm = el('td');
      hmm.append(badge(current.hmm[i] === null ? null : current.hmm[i] >= .5));
      if (current.hmm[i] !== null) hmm.append(el('small', ' ' + percent(current.hmm[i]) + ' A occupancy'));
      row.append(hmm);
      ['sukhotin', 'hmm'].forEach(method => {
        const td = el('td'),
          s = current.bootstrap[method][i];
        td.append(bar(s.A, s.n));
        row.append(td);
      });
      const restart = el('td');
      restart.append(current.restart_A_fraction[i] === null ? el('span', 'unseen') : bar(Math.round(current.restart_A_fraction[i] * manifest.restarts), manifest.restarts));
      row.append(restart);
      const edit = el('td'),
        choice = el('select');
      choice.setAttribute('aria-label', 'Class for ' + current.symbols[i]);
      choice.append(option('A', 'A'), option('B', 'B'), option('?', 'Unassigned'));
      choice.value = assignments[i] === null ? '?' : assignments[i] ? 'A' : 'B';
      choice.addEventListener('change', () => {
        assignments[i] = choice.value === '?' ? null : choice.value === 'A';
        metrics();
        matrix();
        examples();
        perturbations();
      });
      edit.append(choice);
      row.append(edit);
      row.append(el('td', selected.source.length === 2 ? 'unknown' : revealed ? (reference(current.symbols[i]) ? 'vowel letter' : 'other letter') : 'hidden'));
      $('symbol-rows').append(row);
    });
    $('stability-note').textContent = `${manifest.bootstraps} block resamples; ${current.document_count} source ${selected.source.length===2?'folios':'200-word blocks'}. Full HMM: ${current.hmm_fit.iterations} EM iterations; seed symbol ${current.seed_symbol}. ${fmt(current.dropped_words)} words become empty under this treatment. ${fmt(current.omitted_long_words)} words exceed the HMM’s 30-unit limit.`;
  }

  function matrix() {
    const indices = visible();
    if ($('matrix-order').value === 'classes') indices.sort((a, b) => (assignments[a] === null ? 2 : assignments[a] ? 0 : 1) - (assignments[b] === null ? 2 : assignments[b] ? 0 : 1) || a - b);
    else indices.sort((a, b) => a - b);
    const n = indices.length,
      cell = 23,
      pad = 70,
      width = pad + n * cell + 20;
    const root = $('matrix');
    root.replaceChildren();
    root.setAttribute('viewBox', `0 0 ${width} ${width}`);
    if (!n) {
      $('cell-detail').textContent = 'No symbols meet the minimum count.';
      return;
    }
    const rowTotals = current.pairs.map(row => row.reduce((a, b) => a + b, 0));
    const colTotals = current.symbols.map((_, j) => current.pairs.reduce((sum, row) => sum + row[j], 0));
    const total = rowTotals.reduce((a, b) => a + b, 0);
    indices.forEach((i, pos) => {
      const color = assignments[i] === null ? '#777' : assignments[i] ? '#267b95' : '#b45b3c';
      const left = svg('text', {
        x: pad - 8,
        y: pad + pos * cell + 16,
        'text-anchor': 'end'
      }, current.symbols[i]);
      left.style.fill = color;
      const top = svg('text', {
        transform: `translate(${pad+pos*cell+15} ${pad-8}) rotate(-60)`
      }, current.symbols[i]);
      top.style.fill = color;
      root.append(left, top);
      indices.forEach((j, col) => {
        const count = current.pairs[i][j],
          probability = rowTotals[i] ? count / rowTotals[i] : 0;
        const expected = total ? colTotals[j] / total : 0;
        const lift = count && expected ? Math.log2(probability / expected) : null;
        let color;
        if ($('matrix-measure').value === 'lift') color = lift === null ? '#f1f0e9' : lift >= 0 ? `rgba(38,123,149,${Math.min(1,lift/4)})` : `rgba(180,91,60,${Math.min(1,-lift/4)})`;
        else color = `rgba(38,123,149,${Math.sqrt(probability)})`;
        const rect = svg('rect', {
          x: pad + col * cell,
          y: pad + pos * cell,
          width: cell - 1,
          height: cell - 1,
          fill: color,
          tabindex: 0
        });
        const detail = `${current.symbols[i]} → ${current.symbols[j]}: ${fmt(count)} pairs; P(next | first) ${percent(probability)}; log₂ lift ${lift===null?'undefined (zero observed/expected)':fmt(lift)}.`;
        rect.append(svg('title', {}, detail));
        rect.setAttribute('aria-label', detail);
        ['mouseenter', 'focus'].forEach(event => rect.addEventListener(event, () => {
          $('cell-detail').textContent = detail;
        }));
        root.append(rect);
      });
    });
    let cross = 0,
      eligible = 0;
    const countsTotal = current.counts.reduce((a, b) => a + b, 0);
    current.pairs.forEach((row, i) => row.forEach((count, j) => {
      if (assignments[i] !== null && assignments[j] !== null) {
        eligible += count;
        if (assignments[i] !== assignments[j]) cross += count;
      }
    }));
    const massA = current.counts.reduce((sum, count, i) => sum + (assignments[i] === true ? count : 0), 0) / countsTotal;
    const massB = current.counts.reduce((sum, count, i) => sum + (assignments[i] === false ? count : 0), 0) / countsTotal;
    $('contact-summary').textContent = `Across all symbols: ${percent(total?cross/total:0)} of all pairs cross A/B; ${percent(total?eligible/total:0)} have two assigned symbols. Frequency-only reference 2p(A)p(B): ${percent(2*massA*massB)}. This is not a significance test.`;
  }

  function examples() {
    $('examples').replaceChildren();
    current.examples.forEach(example => {
      const word = el(example.folio ? 'a' : 'span');
      word.className = 'word';
      if (example.folio) {
        word.href = 'https://www.voynichese.com/#/' + encodeURIComponent(example.folio) + '/exa:' + encodeURIComponent(example.original);
        word.target = '_blank';
        word.rel = 'noopener';
      }
      word.title = example.original + (example.folio ? ' · ' + example.folio : '') + ' · original spelling';
      example.symbols.forEach(symbol => {
        const value = assignments[current.symbols.indexOf(symbol)],
          unit = el('span', symbol);
        unit.className = 'unit ' + (value === null ? 'unknown' : value ? 'a' : 'b');
        word.append(unit);
      });
      $('examples').append(word, document.createTextNode(' '));
    });
    $('text-note').textContent = `First ${current.examples.length} retained words in this dataset${selected.control==='native'&&selected.scope==='whole'?'':'; displayed spellings reflect the selected transformation'}. Hover a word for its original spelling${selected.source.length===2?'; click to open its source folio in Voynichese':''}.`;
  }

  function render() {
    metrics();
    table();
    matrix();
    examples();
    perturbations();
  }
  async function load() {
    const token = ++version;
    const source = $('source').value,
      vms = source.length === 2;
    $('mode').disabled = !vms;
    $('mode').parentElement.hidden = !vms;
    $('control').querySelector('option[value=deleted]').disabled = vms;
    if (vms && $('control').value === 'deleted') $('control').value = 'native';
    $('reveal').disabled = vms;
    const requested = manifest.scenarios.find(item => item.source === source && item.mode === (vms ? $('mode').value : 'letters') && item.scope === $('scope').value && item.control === $('control').value);
    $('status').textContent = 'Loading fitted classes…';
    current = null;
    selected = null;
    ['metrics', 'symbol-rows', 'matrix', 'examples', 'perturbation-head', 'perturbation-rows', 'contact-summary', 'stability-note', 'reference-summary'].forEach(id => $(id).replaceChildren());
    ['method', 'reset', 'download', 'minimum'].forEach(id => $(id).disabled = true);
    try {
      const cases = manifest.scenarios.filter(item => vms ?
        ((item.mode === requested.mode && item.scope === 'whole' && item.control === 'native' && item.source.length === 2) ||
          (item.source === source && item.mode === requested.mode && ((item.scope === 'interior' && item.control === 'native') || (item.scope === 'whole' && item.control === 'shuffle'))) ||
          (item.source === source && item.mode !== requested.mode && item.scope === 'whole' && item.control === 'native')) :
        (item.source === source && item.mode === 'letters' && ((item.scope === 'whole') || (item.scope === 'interior' && item.control !== 'shuffle'))));
      const [value, comparisons] = await Promise.all([read(requested.file), Promise.all(cases.map(async scenario => ({
        scenario,
        data: await read(scenario.file)
      })))]);
      if (token !== version) return;
      current = value;
      selected = requested;
      related = comparisons;
      assignments = fitted();
      render();
      ['method', 'reset', 'download', 'minimum'].forEach(id => $(id).disabled = false);
      $('status').textContent = manifest.sources.find(item => item.id === source).label + ' · ' + $('scope').selectedOptions[0].textContent + ' · ' + $('control').selectedOptions[0].textContent + '. All models were fitted without reference vowel labels.';
    } catch (error) {
      if (token === version) $('status').textContent = error.message + '. Change a selection to retry.';
    }
  }

  function download() {
    if (!current) return;
    const quote = value => '"' + String(value ?? '').replaceAll('"', '""') + '"';
    const rows = [
      ['scenario', 'symbol', 'count', 'sukhotin_A', 'hmm_A_occupancy', 'sukhotin_boot_A', 'sukhotin_boot_n', 'hmm_boot_A', 'hmm_boot_n', 'current_class']
    ];
    current.symbols.forEach((symbol, i) => rows.push([selected.id, symbol, current.counts[i], current.sukhotin[i], current.hmm[i], current.bootstrap.sukhotin[i].A, current.bootstrap.sukhotin[i].n, current.bootstrap.hmm[i].A, current.bootstrap.hmm[i].n, assignments[i] === null ? '?' : assignments[i] ? 'A' : 'B']));
    const url = URL.createObjectURL(new Blob([rows.map(row => row.map(quote).join(',')).join('\n')], {
      type: 'text/csv;charset=utf-8'
    }));
    const link = el('a');
    link.href = url;
    link.download = selected.id + '-classes.csv';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function init() {
    [manifest, glyphs] = await Promise.all([read('manifest.json'), read('glyphs.json')]);
    $('source').replaceChildren(...manifest.sources.map(source => option(source.id, source.id + ' · ' + source.label)));
    ['source', 'mode', 'scope', 'control'].forEach(id => $(id).addEventListener('change', load));
    $('method').addEventListener('change', () => {
      if (current) {
        assignments = fitted();
        render();
      }
    });
    $('minimum').addEventListener('input', () => {
      if (current) {
        table();
        matrix();
        perturbations();
      }
    });
    ['matrix-measure', 'matrix-order'].forEach(id => $(id).addEventListener('change', () => {
      if (current) matrix();
    }));
    $('reset').addEventListener('click', () => {
      if (current) {
        assignments = fitted();
        render();
      }
    });
    $('reveal').addEventListener('click', () => {
      revealed = !revealed;
      $('reveal').textContent = revealed ? 'Hide reference vowel letters' : 'Reveal reference vowel letters';
      if (current) {
        table();
        perturbations();
      }
    });
    $('download').addEventListener('click', download);
    manifest.sources.forEach(source => {
      const li = el('li'),
        link = el('a', source.id + ' · source');
      link.href = source.url;
      li.append(link, document.createTextNode(' · SHA-256 ' + source.sha256));
      $('source-links').append(li);
    });
    await load();
  }
  init().catch(error => {
    $('status').textContent = 'Could not initialize the explorer: ' + error.message;
  });
})();
