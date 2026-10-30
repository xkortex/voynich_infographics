/* Normalize complete sparse rows; diagram filtering never changes sampling. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const version = document.querySelector('script[data-version]')?.dataset.version || 'development';
  const cache = new Map();
  let manifest, glyphs = {},
    model = null,
    source = null,
    requestVersion = 0;
  let history = [],
    choices = [];
  const fmt = value => Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 4
  });
  const pct = value => fmt(value * 100) + '%';
  const label = unit => unit === ' ' ? '␠ space' : unit;
  const contextLabel = ids => ids.length ? ids.map(id => model.alphabet[id] === ' ' ? '␠' : model.alphabet[id]).join(' · ') : 'START';

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

  function option(value, text) {
    const node = el('option', text);
    node.value = value;
    return node;
  }
  async function json(file) {
    if (!cache.has(file)) cache.set(file, fetch('data/' + file + '?v=' + encodeURIComponent(version)).then(response => {
      if (!response.ok) throw new Error(`Could not load ${file} (${response.status})`);
      return response.json();
    }).catch(error => {
      cache.delete(file);
      throw error;
    }));
    return cache.get(file);
  }

  function distribution() {
    let rows, context, basis;
    if (!history.length) {
      rows = model.starts;
      context = [];
      basis = 'Run-initial first-unit distribution.';
    } else if ($('order').value === '1') {
      context = history.slice(-1);
      rows = model.first[String(context[0])] || [];
      basis = 'P(next | previous unit).';
    } else if (history.length === 1) {
      context = history.slice(-1);
      rows = model.start_pairs[String(context[0])] || [];
      basis = 'Second-order warm-up: P(second unit | first unit, run start).';
    } else {
      context = history.slice(-2);
      rows = model.second[context.join(',')] || [];
      basis = 'P(next | previous two units).';
    }
    rows = [...rows].sort((a, b) => b[1] - a[1] || a[0] - b[0]);
    return {
      rows,
      context,
      basis,
      total: rows.reduce((sum, row) => sum + row[1], 0)
    };
  }

  function sample(rows, total, random = Math.random) {
    if (!total) return null;
    let target = random() * total;
    for (const [unit, count] of rows) {
      if (target < count) return unit;
      target -= count;
    }
    return rows.at(-1)[0]; // Floating-point guard at the upper boundary.
  }

  function appendUnit(id, random = false) {
    if (!model) return;
    const state = distribution(),
      row = state.rows.find(([unit]) => unit === id);
    if (!row) return;
    history.push(id);
    choices.push({
      id,
      count: row[1],
      total: state.total,
      context: state.context,
      basis: state.basis,
      order: $('order').value,
      random
    });
    render();
  }

  function next() {
    if (!model) return;
    const state = distribution(),
      id = sample(state.rows, state.total);
    if (id !== null) appendUnit(id, true);
  }

  function glyph(parent, unit, x, y, size) {
    if (unit === ' ' || !glyphs[unit]) {
      parent.append(svg('text', {
        x: x + size / 2,
        y: y + size * .68,
        'text-anchor': 'middle',
        'font-size': size * .65
      }, unit === ' ' ? '␠' : unit));
      return;
    }
    const text = glyphs[unit].replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" ');
    const node = new DOMParser().parseFromString(text, 'image/svg+xml').documentElement;
    node.setAttribute('x', x);
    node.setAttribute('y', y);
    node.setAttribute('width', size);
    node.setAttribute('height', size);
    node.setAttribute('aria-hidden', 'true');
    parent.append(document.importNode(node, true));
  }

  function diagram(state) {
    const root = $('diagram');
    root.replaceChildren();
    const limit = $('limit').value === 'all' ? state.rows.length : Number($('limit').value);
    const visible = state.rows.slice(0, limit),
      height = Math.max(310, visible.length * 58 + 50),
      center = height / 2;
    root.setAttribute('viewBox', `0 0 1080 ${height}`);
    root.append(svg('title', {}, `Outgoing transitions from ${contextLabel(state.context)}`));
    const defs = svg('defs'),
      marker = svg('marker', {
        id: 'transition-arrow',
        viewBox: '0 0 10 10',
        refX: 9,
        refY: 5,
        markerWidth: 6,
        markerHeight: 6,
        orient: 'auto-start-reverse',
        markerUnits: 'userSpaceOnUse'
      });
    marker.append(svg('path', {
      d: 'M 0 0 L 10 5 L 0 10 Z',
      fill: '#356f8b'
    }));
    defs.append(marker);
    root.append(defs);
    visible.forEach(([id, count], index) => {
      const y = 42 + index * 58,
        p = count / state.total;
      const edge = svg('path', {
        d: `M 300 ${center} C 475 ${center}, 545 ${y}, 830 ${y}`,
        fill: 'none',
        stroke: '#356f8b',
        'stroke-width': 1 + 7 * Math.sqrt(p),
        opacity: .35 + .65 * Math.sqrt(p),
        'marker-end': 'url(#transition-arrow)'
      });
      edge.append(svg('title', {}, `${contextLabel(state.context)} → ${label(model.alphabet[id])}: ${count}/${state.total} = ${pct(p)}`));
      root.append(edge);
      root.append(svg('text', {
        x: 800,
        y: y - 11,
        'text-anchor': 'end',
        'font-size': 15
      }, pct(p)));
      const node = svg('g', {
        class: 'destination',
        role: 'button',
        tabindex: 0,
        'aria-label': `Append ${label(model.alphabet[id])}, probability ${pct(p)}`,
        'data-unit': id
      });
      node.append(svg('circle', {
        cx: 860,
        cy: y,
        r: 25,
        fill: model.alphabet[id] === ' ' ? '#f5e7d9' : '#e6eff0',
        stroke: '#7c9c9c',
        'stroke-width': 1.5
      }));
      glyph(node, model.alphabet[id], 837, y - 23, 46);
      node.append(svg('text', {
        x: 901,
        y: y + 6,
        'font-size': 16
      }, label(model.alphabet[id])));
      node.addEventListener('click', () => appendUnit(id));
      node.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          appendUnit(id);
        }
      });
      root.append(node);
    });
    const box = svg('g', {
      class: 'current-node',
      role: 'button',
      tabindex: state.total ? 0 : -1,
      'aria-disabled': !state.total,
      'aria-label': 'Randomly sample next unit from ' + contextLabel(state.context)
    });
    box.addEventListener('click', next);
    box.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        next();
      }
    });
    box.append(svg('rect', {
      x: 20,
      y: center - 69,
      width: 280,
      height: 138,
      rx: 12,
      fill: '#edf0e5',
      stroke: '#a2b3a1'
    }));
    box.append(svg('text', {
      x: 160,
      y: center - 43,
      'text-anchor': 'middle',
      'font-size': 13
    }, history.length ? 'CURRENT CONTEXT' : 'START OF A READABLE RUN'));
    if (state.context.length) {
      const size = 52,
        offset = 160 - state.context.length * size / 2;
      state.context.forEach((id, index) => glyph(box, model.alphabet[id], offset + index * size, center - 32, size));
      box.append(svg('text', {
        x: 160,
        y: center + 48,
        'text-anchor': 'middle',
        'font-size': 16
      }, contextLabel(state.context)));
    } else box.append(svg('text', {
      x: 160,
      y: center + 13,
      'text-anchor': 'middle',
      'font-size': 25
    }, 'START'));
    box.append(svg('text', {
      x: 160,
      y: center + 63,
      'text-anchor': 'middle',
      'font-size': 10
    }, state.total ? 'Click to sample next' : 'No observed successor'));
    root.append(box);
    if (!state.rows.length) root.append(svg('text', {
      x: 650,
      y: center,
      'text-anchor': 'middle',
      'font-size': 18
    }, 'No observed next unit · Undo or Reset'));
    const mass = visible.reduce((sum, row) => sum + row[1], 0);
    $('coverage').textContent = `Showing ${visible.length} of ${state.rows.length} observed successors${state.total?' · '+pct(mass/state.total)+' of next-unit probability shown':''}. Random draws use every successor.`;
  }

  function render() {
    if (!model) return;
    const state = distribution();
    $('context').textContent = 'Context: ' + contextLabel(state.context);
    $('basis').textContent = state.basis + ' ' + fmt(state.total) + ' outgoing observations.';
    $('next').disabled = !state.total;
    $('undo').disabled = !history.length;
    $('reset').disabled = !history.length;
    $('copy').disabled = !history.length;
    $('output').replaceChildren();
    if (!history.length) {
      const placeholder = el('span', 'Choose a first unit below or press Next.');
      placeholder.className = 'placeholder';
      $('output').append(placeholder);
    } else history.forEach((id, index) => {
      const unit = model.alphabet[id],
        span = el('span', unit === ' ' && $('show-spaces').checked ? '␠' : unit);
      if (index === history.length - 1) span.className = 'recent';
      $('output').append(span);
    });
    $('output').scrollTop = $('output').scrollHeight;
    $('generation-summary').textContent = `${history.length} appended units · ${history.filter(id=>model.alphabet[id]===' ').length} spaces · ${source.id} · ${$('order').value==='1'?'first':'second'} order · synthetic output.`;
    const last = choices.at(-1);
    $('last-choice').textContent = last ? `${last.random?'Sampled':'Chose'} ${label(model.alphabet[last.id])} from ${contextLabel(last.context)} · ${fmt(last.count)}/${fmt(last.total)} = ${pct(last.count/last.total)} · order ${last.order}.` : '';
    $('status').textContent = state.total ? `${source.label} · ${fmt(model.runs)} readable runs · spaces included. Click a destination or press Next.` : 'This context has no observed successor. No backoff or smoothing was applied; use Undo or Reset.';
    $('choices').replaceChildren();
    state.rows.forEach(([id, count]) => {
      const row = el('tr');
      row.append(el('td', label(model.alphabet[id])), el('td', fmt(count)), el('td', pct(count / state.total) + ` (${count}/${state.total})`));
      const action = el('td'),
        button = el('button', 'Append ' + label(model.alphabet[id]));
      button.addEventListener('click', () => appendUnit(id));
      action.append(button);
      row.append(action);
      $('choices').append(row);
    });
    diagram(state);
  }

  function reset() {
    history = [];
    choices = [];
    render();
  }
  async function load() {
    const token = ++requestVersion,
      requested = manifest.sources.find(item => item.id === $('source').value),
      mode = $('units').value;
    model = null;
    history = [];
    choices = [];
    ['next', 'undo', 'reset', 'copy'].forEach(id => $(id).disabled = true);
    ['diagram', 'choices', 'output'].forEach(id => $(id).replaceChildren());
    $('context').textContent = 'Loading…';
    $('basis').textContent = '';
    $('last-choice').textContent = '';
    $('coverage').textContent = '';
    $('generation-summary').textContent = '';
    $('status').textContent = 'Loading observed transition counts…';
    try {
      const data = await json(requested.files[mode]);
      if (token !== requestVersion) return;
      model = data;
      source = requested;
      render();
    } catch (error) {
      if (token === requestVersion) $('status').textContent = error.message + '. Change a selection to retry.';
    }
  }
  async function init() {
    [manifest, glyphs] = await Promise.all([json('manifest.json'), json('glyphs.json')]);
    $('source').replaceChildren(...manifest.sources.map(item => option(item.id, item.id + ' · ' + item.label)));
    ['source', 'units'].forEach(id => $(id).addEventListener('change', load));
    ['order', 'limit', 'show-spaces'].forEach(id => $(id).addEventListener('change', () => {
      if (model) render();
    }));
    $('next').addEventListener('click', next);
    $('reset').addEventListener('click', reset);
    $('undo').addEventListener('click', () => {
      history.pop();
      choices.pop();
      render();
    });
    $('copy').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(history.map(id => model.alphabet[id]).join(''));
        $('status').textContent = 'Generated text copied with ordinary spaces.';
      } catch (error) {
        $('status').textContent = 'Copy is unavailable; select the generated text to copy it manually.';
      }
    });
    manifest.sources.forEach(item => {
      const li = el('li'),
        link = el('a', item.id + ' · source file');
      link.href = item.url;
      li.append(link, document.createTextNode(' · SHA-256 ' + item.sha256));
      $('source-links').append(li);
    });
    await load();
  }
  init().catch(error => {
    $('status').textContent = 'Could not initialize the explorer: ' + error.message;
  });
})();
