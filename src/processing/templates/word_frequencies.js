/* No chart libraries or remote runtime dependencies. Data are local text assets. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const namespace = 'http://www.w3.org/2000/svg';
  const colors = ['#a44832', '#315e4d', '#486fa0', '#9761a1', '#bd830c', '#27858b'];
  const basic = /^[a-vxyz]+$/;
  const cache = new Map();
  let manifest, series = [],
    version = 0,
    page = 0;
  const number = value => value.toLocaleString(undefined, {
    maximumFractionDigits: 3
  });

  async function json(path) {
    if (!cache.has(path)) cache.set(path, fetch('data/' + path).then(response => {
      if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
      return response.json();
    }).catch(error => {
      cache.delete(path);
      throw error;
    }));
    return cache.get(path);
  }

  function node(tag, attributes = {}, text) {
    const element = document.createElementNS(namespace, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function option(value, label) {
    const element = document.createElement('option');
    element.value = value;
    element.textContent = label;
    return element;
  }

  function choices(id, values, defaults) {
    $(id).replaceChildren();
    values.forEach(([value, text]) => {
      const label = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.value = value;
      input.checked = defaults.includes(value);
      label.append(input, document.createTextNode(' ' + text));
      $(id).append(label);
    });
  }

  function selected(id) {
    return [...$(id).querySelectorAll('input:checked')].map(input => input.value);
  }

  async function loadSeries(source, treatment, all) {
    const [chunks, mapping] = await Promise.all([
      Promise.all(source.shards.map(json)), json(source.maps[treatment])
    ]);
    const vocabulary = chunks.flat();
    if (vocabulary.length !== mapping.map.length) throw new Error('Vocabulary/mapping length mismatch');
    const groups = new Map();
    let tokens = 0,
      originalTypes = 0,
      changedTokens = 0;
    vocabulary.forEach(([word, count, folio, verified], index) => {
      if (!all && !basic.test(word)) return;
      const key = mapping.keys[mapping.map[index]];
      if (typeof key !== 'string') throw new Error('Invalid family mapping');
      if (!groups.has(key)) groups.set(key, {
        key,
        count: 0,
        members: []
      });
      const group = groups.get(key);
      group.count += count;
      group.members.push({
        word,
        count,
        folio,
        verified
      });
      tokens += count;
      originalTypes++;
      if (key !== word && !key.startsWith('~short:')) changedTokens += count;
    });
    const rows = [...groups.values()].sort((a, b) => b.count - a.count || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
    rows.forEach((row, index) => {
      row.rank = index + 1;
      row.members.sort((a, b) => b.count - a.count || (a.word < b.word ? -1 : a.word > b.word ? 1 : 0));
    });
    const label = source.id + ' · ' + manifest.treatments.find(([id]) => id === treatment)[1];
    return {
      source,
      treatment,
      rows,
      tokens,
      originalTypes,
      changedTokens,
      label
    };
  }

  async function compare() {
    const current = ++version;
    const sources = selected('sources'),
      treatments = selected('treatments');
    if (!sources.length || !treatments.length || sources.length * treatments.length > 6) {
      $('status').textContent = 'Choose between one and six source × treatment combinations; the current plot is unchanged.';
      return;
    }
    $('status').textContent = 'Loading selected counts and family mappings…';
    try {
      const results = await Promise.all(sources.flatMap(id => treatments.map(treatment =>
        loadSeries(manifest.sources.find(source => source.id === id), treatment, $('population').value === 'all'))));
      if (current !== version) return;
      series = results;
      $('inspect').replaceChildren(...series.map((item, index) => option(index, item.label)));
      page = 0;
      renderPlot();
      renderTable();
      $('family').replaceChildren(document.createTextNode('Select a family to inspect its source words.'));
      $('status').textContent = `${series.length} series loaded. Population: ${$('population').selectedOptions[0].textContent}.`;
    } catch (error) {
      if (current === version) $('status').textContent = `${error.message}. Retry with Compare selections.`;
    }
  }

  function pointsFor(item) {
    const relative = $('measure').value === 'relative';
    if ($('view').value === 'rank') return item.rows.map(row => ({
      x: row.rank,
      y: relative ? row.count / item.tokens * 100 : row.count,
      row,
      detail: `${displayKey(row.key)} · ${number(row.count)} tokens`
    }));
    const histogram = new Map();
    item.rows.forEach(row => histogram.set(row.count, (histogram.get(row.count) || 0) + 1));
    return [...histogram].sort((a, b) => a[0] - b[0]).map(([count, families]) => ({
      x: count,
      y: relative ? families / item.rows.length * 100 : families,
      detail: `${number(families)} families occurring ${number(count)} times`
    }));
  }

  function ticks(maximum, logarithmic) {
    if (logarithmic) {
      const values = [];
      for (let exponent = Math.floor(Math.log10(maximum)) - 6; exponent <= Math.ceil(Math.log10(maximum)); exponent++) {
        const value = 10 ** exponent;
        if (value <= maximum) values.push(value);
      }
      return values;
    }
    return Array.from({
      length: 6
    }, (_, index) => maximum * index / 5);
  }

  function renderPlot() {
    if (!series.length) return;
    const svg = $('chart');
    svg.replaceChildren();
    const rank = $('view').value === 'rank',
      relative = $('measure').value === 'relative',
      log = $('log').checked;
    const data = series.map(pointsFor);
    const all = data.flat();
    const maxX = Math.max(...all.map(point => point.x));
    const maxY = Math.max(...all.map(point => point.y));
    const minY = Math.min(...all.map(point => point.y));
    const left = 85,
      right = 1040,
      top = 28,
      bottom = 440;
    const rangeYMin = log ? Math.min(minY, maxY / 10) : 0;
    const xDenom = log ? Math.log10(Math.max(10, maxX)) : Math.max(1, maxX);
    const yDenom = log ? Math.log10(maxY) - Math.log10(rangeYMin) : maxY;
    const x = value => left + (log ? Math.log10(value) / xDenom : value / xDenom) * (right - left);
    const y = value => bottom - (log ? (Math.log10(value) - Math.log10(rangeYMin)) / yDenom : value / yDenom) * (bottom - top);
    $('plot-title').textContent = rank ? 'Rank–frequency' : 'Frequency of frequencies';
    const yLabel = rank ? (relative ? 'Source-token abundance (%)' : 'Source-word token count') : (relative ? 'Share of family types (%)' : 'Number of family types');
    $('plot-description').textContent = `${yLabel} against ${rank ? 'family rank' : 'exact occurrence count k'}. ${log ? 'Both axes use logarithmic scales.' : 'Both axes use linear scales.'}`;
    ticks(maxY, log).filter(value => value >= rangeYMin).forEach(value => {
      svg.append(node('line', {
        x1: left,
        x2: right,
        y1: y(value),
        y2: y(value),
        stroke: '#e0e2d9'
      }), node('text', {
        x: left - 12,
        y: y(value) + 4,
        'text-anchor': 'end'
      }, number(value)));
    });
    ticks(maxX, log).filter(value => value >= (log ? 1 : 0)).forEach(value => {
      svg.append(node('text', {
        x: x(value),
        y: bottom + 25,
        'text-anchor': 'middle'
      }, number(value)));
    });
    svg.append(node('line', {
      x1: left,
      x2: right,
      y1: bottom,
      y2: bottom,
      stroke: '#829081'
    }));
    svg.append(node('text', {
      x: (left + right) / 2,
      y: bottom + 55,
      'text-anchor': 'middle'
    }, rank ? 'Family rank (each series ranked separately)' : 'Occurrences per family, k'));
    svg.append(node('text', {
      transform: `translate(20 ${(top+bottom)/2}) rotate(-90)`,
      'text-anchor': 'middle'
    }, yLabel));
    $('legend').replaceChildren();
    data.forEach((points, index) => {
      const color = colors[index];
      const legend = document.createElement('span');
      legend.style.setProperty('--series', color);
      legend.textContent = series[index].label;
      $('legend').append(legend);
      if (rank) svg.append(node('path', {
        d: points.map((point, i) => `${i ? 'L':'M'}${x(point.x)},${y(point.y)}`).join(' '),
        fill: 'none',
        stroke: color,
        'stroke-width': 2,
        opacity: .8
      }));
      if (!rank) points.forEach(point => svg.append(node('line', {
        x1: x(point.x),
        x2: x(point.x),
        y1: bottom,
        y2: y(point.y),
        stroke: color,
        'stroke-width': 3,
        opacity: 0.2
      })));
      // Keep a full-resolution path; focusable markers sample long tails for performance.
      points.forEach((point, i) => {
        if (points.length > 400 && i > 100 && i % Math.ceil(points.length / 300)) return;
        const circle = node('circle', {
          cx: x(point.x),
          cy: y(point.y),
          r: rank ? 2.5 : 3,
          fill: color,
          tabindex: 0
        });
        circle.append(node('title', {}, `${series[index].label}\n${point.detail}\nx ${number(point.x)} · y ${number(point.y)}${relative ? '%':''}`));
        if (point.row) circle.addEventListener('click', () => {
          $('inspect').value = index;
          page = 0;
          renderTable();
          inspectFamily(point.row, series[index]);
        });
        svg.append(circle);
      });
    });
  }

  function displayKey(key) {
    return key.startsWith('~short:') ? key.slice(7) + ' [too short to trim]' : key;
  }

  function active() {
    return series[Number($('inspect').value) || 0];
  }

  function renderTable() {
    const item = active();
    if (!item) return;
    const filter = $('filter').value.trim().toLowerCase();
    const rows = item.rows.filter(row => row.key.toLowerCase().includes(filter) || row.members.some(member => member.word.toLowerCase().includes(filter)));
    page = Math.max(0, Math.min(page, Math.ceil(rows.length / 30) - 1));
    $('rows').replaceChildren();
    rows.slice(page * 30, page * 30 + 30).forEach(row => {
      const tr = document.createElement('tr');
      [row.rank, displayKey(row.key), number(row.count), number(row.count / item.tokens * 100) + '%', number(row.members.length)].forEach(value => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.append(td);
      });
      const td = document.createElement('td'),
        button = document.createElement('button');
      button.textContent = 'Members';
      button.addEventListener('click', () => inspectFamily(row, item));
      td.append(button);
      tr.append(td);
      $('rows').append(tr);
    });
    const hapax = item.rows.filter(row => row.count === 1).length;
    const topTen = item.rows.slice(0, 10).reduce((sum, row) => sum + row.count, 0);
    $('summary').textContent = `${number(item.tokens)} source tokens · ${number(item.originalTypes)} original types → ${number(item.rows.length)} families · ${number(hapax)} singleton families (${number(hapax/item.rows.length*100)}% of families) · top 10 hold ${number(topTen/item.tokens*100)}% of tokens · ${number(item.changedTokens/item.tokens*100)}% of tokens receive a changed family key.`;
    $('page-number').textContent = rows.length ? `${number(rows.length)} matching families · page ${page+1} / ${Math.ceil(rows.length/30)}` : 'No matching families';
    $('previous').disabled = page === 0;
    $('next').disabled = (page + 1) * 30 >= rows.length;
  }

  function memberURL(member) {
    return 'https://www.voynichese.com/#/' + encodeURIComponent(member.folio) + (basic.test(member.word) ? '/exa:' + encodeURIComponent(member.word) : '');
  }

  function inspectFamily(row, item) {
    const panel = $('family');
    panel.replaceChildren();
    const title = document.createElement('h2');
    title.textContent = displayKey(row.key);
    panel.append(title);
    const intro = document.createElement('p');
    intro.textContent = `${number(row.count)} tokens, ${number(row.count/item.tokens*100)}% of this source. ${row.members.length} original word types. Links show exact-spelling candidates on an observed folio; another transcription may read them differently.`;
    panel.append(intro);
    const list = document.createElement('ul');
    row.members.forEach(member => {
      const li = document.createElement('li'),
        link = document.createElement('a');
      link.href = memberURL(member);
      link.target = '_blank';
      link.rel = 'noopener';
      link.textContent = `${member.word} · ${number(member.count)} tokens · ${member.folio} ↗${basic.test(member.word) ? (member.verified ? ' exact spelling verified in VT' : ' exact-spelling candidate') : ' folio only (marked token)'}`;
      li.append(link);
      list.append(li);
    });
    panel.append(list);
  }

  function download() {
    const item = active();
    if (!item) return;
    const quote = value => '"' + String(value).replaceAll('"', '""') + '"';
    const rows = [
      ['source', 'treatment', 'rank', 'family', 'family_count', 'token_percent', 'member', 'member_count', 'example_folio', 'voynichese_url', 'spelling_verified_in_VT']
    ];
    item.rows.forEach(row => row.members.forEach(member => rows.push([item.source.id, item.treatment, row.rank, displayKey(row.key), row.count, row.count / item.tokens * 100, member.word, member.count, member.folio, memberURL(member), Boolean(member.verified)])));
    const blob = new Blob([rows.map(row => row.map(quote).join(',')).join('\r\n')], {
      type: 'text/csv;charset=utf-8'
    });
    const url = URL.createObjectURL(blob),
      link = document.createElement('a');
    link.href = url;
    link.download = `${item.source.id}-${item.treatment}-word-frequencies.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function init() {
    manifest = await json('manifest.json');
    choices('sources', manifest.sources.map(source => [source.id, source.id + ' · ' + source.label]), ['ZL']);
    choices('treatments', manifest.treatments, ['none', 'morf1', 'edit1']);
    manifest.sources.forEach(source => {
      const li = document.createElement('li'),
        link = document.createElement('a');
      link.href = source.url;
      link.textContent = `${source.id} · original source`;
      li.append(link, document.createTextNode(` · ${number(source.tokens)} parsed tokens; ${number(source.basic_tokens)} complete basic-EVA tokens · SHA-256 ${source.sha256}`));
      $('source-links').append(li);
    });
    $('update').addEventListener('click', compare);
    $('preset-sources').addEventListener('click', () => {
      $('sources').querySelectorAll('input').forEach(input => {
        input.checked = true;
      });
      $('treatments').querySelectorAll('input').forEach(input => {
        input.checked = input.value === 'none';
      });
      compare();
    });
    $('preset-treatments').addEventListener('click', () => {
      $('sources').querySelectorAll('input').forEach(input => {
        input.checked = input.value === 'ZL';
      });
      $('treatments').querySelectorAll('input').forEach(input => {
        input.checked = ['none', 'morf1', 'edit1', 'prefix3', 'suffix3', 'infix1'].includes(input.value);
      });
      compare();
    });
    ['view', 'measure', 'log'].forEach(id => $(id).addEventListener('change', renderPlot));
    $('inspect').addEventListener('change', () => {
      page = 0;
      renderTable();
      $('family').textContent = 'Select a family to inspect its source words.';
    });
    $('filter').addEventListener('input', () => {
      page = 0;
      renderTable();
    });
    $('previous').addEventListener('click', () => {
      page--;
      renderTable();
    });
    $('next').addEventListener('click', () => {
      page++;
      renderTable();
    });
    $('download').addEventListener('click', download);
    await compare();
  }
  init().catch(error => {
    $('status').textContent = 'Could not load the chart: ' + error.message + '. Reload to retry.';
  });
})();
