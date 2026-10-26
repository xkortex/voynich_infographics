/* Explorable aggregate statistics. No corpus text or chart library is loaded. */
(() => {
  "use strict";
  const SVG = "http://www.w3.org/2000/svg";
  const colors = {vms: "#b04732", selected: "#1d7d88", other: "#9eaaa1"};
  const ids = ["comparison", "vms", "boundary", "alphabet-range", "matrix-measure", "repair", "shuffle"];
  const controls = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
  const tooltip = document.getElementById("tooltip");
  const cache = new Map();
  let rows = [];
  let heatmapRevision = 0;
  let languageNames;
  try { languageNames = new Intl.DisplayNames(["en"], {type: "language"}); } catch (_) {}

  const number = value => value.toLocaleString("en-US");
  const percent = value => Number.isFinite(value) ? value.toFixed(2) + "%" : "n/a";
  const selected = () => rows.find(row => row.id === controls.comparison.value);
  const vms = () => rows.find(row => row.id === controls.vms.value);
  const name = row => {
    if (row.kind === "vms") return row.label;
    let label;
    try { label = languageNames?.of(row.label); } catch (_) {}
    return label && label !== row.label ? `${label} (${row.label})` : row.label;
  };

  function element(tag, attributes = {}, text) {
    const node = document.createElementNS(SVG, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function paragraph(parent, text) {
    const node = document.createElement("p");
    node.textContent = text;
    parent.append(node);
  }

  async function readJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  }

  function showTooltip(text, event) {
    tooltip.textContent = text;
    tooltip.hidden = false;
    const bounds = event.target.getBoundingClientRect();
    const left = event.clientX || bounds.left;
    const top = event.clientY || bounds.top;
    tooltip.style.left = Math.max(8, Math.min(innerWidth - 340, left + 12)) + "px";
    tooltip.style.top = Math.max(8, Math.min(innerHeight - 120, top + 14)) + "px";
  }

  function point(svg, row, x, y, description, hollow = false) {
    const comparison = row.id === controls.comparison.value;
    const color = row.kind === "vms" ? colors.vms : comparison ? colors.selected : colors.other;
    const circle = element("circle", {
      cx: x, cy: y, r: row.kind === "vms" || comparison ? 6 : 3.5,
      fill: hollow ? "white" : color, stroke: color,
      "stroke-width": hollow ? 2 : 1, opacity: row.kind === "vms" || comparison ? 1 : .65,
      class: "point", tabindex: 0, role: "button", "aria-label": description,
    });
    circle.append(element("title", {}, description));
    circle.addEventListener("mouseenter", event => showTooltip(description, event));
    circle.addEventListener("focus", event => showTooltip(description, event));
    circle.addEventListener("mouseleave", () => tooltip.hidden = true);
    circle.addEventListener("blur", () => tooltip.hidden = true);
    const choose = () => {
      if (row.kind === "wmf") controls.comparison.value = row.id;
      else controls.vms.value = row.id;
      tooltip.hidden = true;
      render();
    };
    circle.addEventListener("click", choose);
    circle.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); }
    });
    svg.append(circle);
    return circle;
  }

  function chartFrame(title, xLabel, yLabel, xTicks, yTicks, xScale, yScale) {
    const svg = element("svg", {viewBox: "0 0 1000 485", role: "img", "aria-label": title});
    svg.append(element("title", {}, title));
    for (const tick of yTicks) {
      svg.append(element("line", {x1: 76, x2: 965, y1: yScale(tick), y2: yScale(tick), class: "grid"}));
      svg.append(element("text", {x: 63, y: yScale(tick) + 4, "text-anchor": "end", "font-size": 12}, tick));
    }
    for (const tick of xTicks) {
      svg.append(element("line", {x1: xScale(tick), x2: xScale(tick), y1: 24, y2: 410, class: "grid"}));
      svg.append(element("text", {x: xScale(tick), y: 435, "text-anchor": "middle", "font-size": 12}, number(tick)));
    }
    svg.append(element("text", {x: 520, y: 475, "text-anchor": "middle", class: "axis-label"}, xLabel));
    svg.append(element("text", {x: 20, y: 220, transform: "rotate(-90 20 220)", "text-anchor": "middle", class: "axis-label"}, yLabel));
    return svg;
  }

  function drawEntropy() {
    const boundary = controls.boundary.value;
    const visible = rows.filter(row => controls["alphabet-range"].value === "all" || row[boundary].alphabet <= 200 || row.kind === "vms" || row.id === controls.comparison.value);
    const maxX = Math.max(...visible.map(row => row[boundary].alphabet)) * 1.12;
    const minX = Math.min(10, ...visible.map(row => row[boundary].alphabet));
    const maxY = Math.ceil(Math.max(...visible.map(row => row[boundary].h2)) + .3);
    const minY = Math.min(1.5, ...visible.map(row => row[boundary].h2));
    const log = controls["alphabet-range"].value === "all";
    const x = value => 76 + (log ? Math.log(value / minX) / Math.log(maxX / minX) : value / maxX) * 889;
    const y = value => 410 - (value - minY) / (maxY - minY) * 386;
    const xTicks = (log ? [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000] : [0, 25, 50, 100, 150, 200, 300, 500]).filter(tick => tick >= (log ? minX : 0) && tick <= maxX);
    const yTicks = Array.from({length: maxY}, (_, index) => index + 1).filter(tick => tick >= minY);
    const svg = chartFrame("Conditional character entropy versus observed inventory", `Observed character inventory (${log ? "logarithmic" : "linear"} scale; ${boundary === "spaces" ? "including word space" : "spaces removed"})`, "h₂ · bits per next character", xTicks, yTicks, x, y);
    // Draw selected points last so they remain visible over the background cloud.
    const ordered = visible.slice().sort((left, right) => Number(left.kind === "vms" || left.id === controls.comparison.value) - Number(right.kind === "vms" || right.id === controls.comparison.value));
    for (const row of ordered) {
      const stats = row[boundary];
      point(svg, row, x(stats.alphabet), y(stats.h2), `${name(row)} · h₂ ${stats.h2.toFixed(3)} bits · ${stats.alphabet} symbols · ${number(stats.units)} sampled units · ${number(row.words)} words`);
      if (row.kind === "vms") svg.append(element("text", {x: x(stats.alphabet) + 10, y: y(stats.h2) + (row.id === "vms-eva" ? 16 : -10), "font-size": 12}, row.id === "vms-eva" ? "VMS · letters" : "VMS · groups"));
    }
    document.getElementById("entropy-plot").replaceChildren(svg);
    const reading = document.getElementById("entropy-reading");
    reading.replaceChildren();
    for (const row of [vms(), selected()]) {
      const stats = row[boundary];
      paragraph(reading, `${name(row)}: h₂ ${stats.h2.toFixed(3)} bits; ${stats.alphabet} observed symbols; ${number(stats.units)} units, ${number(stats.pair_count)} adjacent pairs; ${number(row.words)} words in ${number(row.documents)} documents${row.limited ? " (shorter than the word limit)" : ""}.`);
    }
    paragraph(reading, `${visible.filter(row => row.kind === "wmf").length} of ${rows.filter(row => row.kind === "wmf").length} WMF language samples displayed. Character inventory includes rare symbols; it is not an estimated phoneme inventory.`);
  }

  function color(value, maximum) {
    const amount = Math.max(0, Math.min(1, value / maximum));
    const low = [246, 244, 229], high = [29, 106, 101];
    return `rgb(${low.map((channel, index) => Math.round(channel + (high[index] - channel) * amount)).join(",")})`;
  }

  function symbolLabel(symbol) {
    if (symbol === " ") return "␠";
    return /^\p{M}$/u.test(symbol) ? "◌" + symbol : symbol;
  }

  async function getMatrices(row) {
    if (!cache.has(row.id)) cache.set(row.id, readJson("data/" + row.matrix_file).catch(error => { cache.delete(row.id); throw error; }));
    return cache.get(row.id);
  }

  function drawMatrix(target, captionTarget, row, matrix) {
    const measure = controls["matrix-measure"].value;
    const maximum = {conditional: 1, joint: .05, entropy: .15}[measure];
    const count = matrix.symbols.length, cell = 448 / count;
    const svg = element("svg", {viewBox: "0 0 590 565", role: "img", "aria-label": `Character-pair matrix for ${name(row)}`});
    svg.append(element("title", {}, `${name(row)} · preceding character by following character`));
    svg.append(element("text", {x: 315, y: 20, "text-anchor": "middle", "font-size": 13}, "Following character →"));
    svg.append(element("text", {x: 7, y: 53, "font-size": 12}, "Previous ↓"));
    matrix.symbols.forEach((symbol, index) => {
      svg.append(element("text", {x: 92 + (index + .5) * cell, y: 58, "text-anchor": "middle", class: "axis-symbol"}, symbolLabel(symbol)));
      svg.append(element("text", {x: 80, y: 74 + (index + .65) * cell, "text-anchor": "end", class: "axis-symbol"}, symbolLabel(symbol)));
    });
    for (let previous = 0; previous < count; previous++) for (let next = 0; next < count; next++) {
      const occurrences = matrix.counts[previous][next];
      const conditional = matrix.outgoing[previous] ? occurrences / matrix.outgoing[previous] : 0;
      const joint = matrix.pair_count ? occurrences / matrix.pair_count : 0;
      const entropy = occurrences ? -joint * Math.log2(conditional) : 0;
      const value = {conditional, joint, entropy}[measure];
      const description = `${name(row)}: ${symbolLabel(matrix.symbols[previous])} → ${symbolLabel(matrix.symbols[next])} · ${number(occurrences)} pairs · P(next | previous) ${(conditional * 100).toFixed(2)}% · pair share ${(joint * 100).toFixed(3)}% · h₂ contribution ${entropy.toFixed(5)} bits`;
      const rect = element("rect", {x: 92 + next * cell, y: 74 + previous * cell, width: cell, height: cell, fill: color(value, maximum), tabindex: previous === 0 && next === 0 ? 0 : -1, "data-row": previous, "data-column": next, "aria-label": description});
      rect.append(element("title", {}, description));
      const inspect = () => document.getElementById("pair-detail").textContent = description;
      rect.addEventListener("mouseenter", inspect);
      rect.addEventListener("focus", inspect);
      rect.addEventListener("keydown", event => {
        const moves = {ArrowRight: [0, 1], ArrowLeft: [0, -1], ArrowDown: [1, 0], ArrowUp: [-1, 0]};
        const move = moves[event.key];
        if (!move) return;
        event.preventDefault();
        const targetRow = Math.max(0, Math.min(count - 1, previous + move[0]));
        const targetColumn = Math.max(0, Math.min(count - 1, next + move[1]));
        const target = svg.querySelector(`[data-row="${targetRow}"][data-column="${targetColumn}"]`);
        rect.setAttribute("tabindex", "-1");
        target.setAttribute("tabindex", "0");
        target.focus();
      });
      svg.append(rect);
    }
    document.getElementById(target).replaceChildren(svg);
    const caption = document.getElementById(captionTarget);
    caption.replaceChildren(document.createTextNode(`${count} / ${matrix.full_alphabet} symbols shown; ${(100 * matrix.shown_pair_count / matrix.pair_count).toFixed(1)}% of pair occurrences visible. `));
    const link = document.createElement("a");
    link.href = "data/" + row.matrix_file;
    link.textContent = "Counts & full statistics";
    caption.append(link);
  }

  async function drawHeatmaps() {
    const revision = ++heatmapRevision;
    const left = vms(), right = selected();
    try {
      const [leftData, rightData] = await Promise.all([getMatrices(left), getMatrices(right)]);
      if (revision !== heatmapRevision) return;
      const boundary = controls.boundary.value;
      document.getElementById("left-title").textContent = name(left);
      document.getElementById("right-title").textContent = name(right);
      drawMatrix("matrix-left", "left-caption", left, leftData[boundary]);
      drawMatrix("matrix-right", "right-caption", right, rightData[boundary]);
      document.getElementById("matrix-scale").textContent = {
        conditional: "Shared color scale: 0 → 100% conditional probability. Every row uses all outgoing pairs in its denominator.",
        joint: "Shared color scale: 0 → 5% of all pairs; values above 5% use the darkest color.",
        entropy: "Shared color scale: 0 → 0.15 bits contributed to h₂; larger contributions use the darkest color.",
      }[controls["matrix-measure"].value];
    } catch (error) {
      if (revision === heatmapRevision) document.getElementById("pair-detail").textContent = `Matrix data could not load: ${error.message}. Change the comparison or reload to retry.`;
    }
  }

  function drawTrigrams() {
    const repair = controls.repair.value;
    const corpusRows = rows.filter(row => row.id !== "vms-groups" && Number.isFinite(row.native.percent) && Number.isFinite(row[repair].percent));
    const x = value => 76 + value / 100 * 889, y = value => 410 - value / 100 * 386;
    const label = repair === "prefix3" ? "Prefix-3" : "Suffix-3";
    const svg = chartFrame("Repeated three-word-window coverage, native versus truncated word forms", "Native exact three-word-window coverage (%)", `${label} repeated-window coverage (%)`, [0, 20, 40, 60, 80, 100], [0, 20, 40, 60, 80, 100], x, y);
    svg.append(element("line", {x1: x(0), x2: x(100), y1: y(0), y2: y(100), stroke: "#9aab9a", "stroke-dasharray": "5 5"}));
    const ordered = corpusRows.slice().sort((a, b) => Number(a.kind === "vms" || a.id === controls.comparison.value) - Number(b.kind === "vms" || b.id === controls.comparison.value));
    for (const row of ordered) {
      point(svg, row, x(row.native.percent), y(row[repair].percent), `${name(row)} · native ${percent(row.native.percent)} → ${label} ${percent(row[repair].percent)} · ${number(row.words)} words`);
    }
    const canonicalVms = rows.find(row => row.id === "vms-eva");
    if (controls.shuffle.checked) for (const row of [canonicalVms, selected()]) {
      const shuffledNative = row.native_shuffled.percent, shuffledRepair = row[repair + "_shuffled"].percent;
      svg.append(element("line", {x1: x(row.native.percent), x2: x(shuffledNative), y1: y(row[repair].percent), y2: y(shuffledRepair), stroke: row.kind === "vms" ? colors.vms : colors.selected, "stroke-dasharray": "3 4"}));
      point(svg, row, x(shuffledNative), y(shuffledRepair), `${name(row)} · shuffled native ${percent(shuffledNative)} → ${label} ${percent(shuffledRepair)}`, true);
    }
    document.getElementById("trigram-plot").replaceChildren(svg);
    const reading = document.getElementById("trigram-reading");
    reading.replaceChildren();
    for (const row of [canonicalVms, selected()]) {
      paragraph(reading, `${name(row)}: native ${percent(row.native.percent)} → ${label} ${percent(row[repair].percent)} (+${(row[repair].percent - row.native.percent).toFixed(2)} percentage points). Shuffled ${label}: ${percent(row[repair + "_shuffled"].percent)}. Sample: ${number(row.words)} words.`);
    }
    paragraph(reading, "The VMS trigram series always uses the same EVA word strings; changing the character representation above affects the character plots, not these word-window counts.");
  }

  function render() {
    tooltip.hidden = true;
    drawEntropy();
    drawHeatmaps();
    drawTrigrams();
  }

  async function start() {
    rows = await readJson("data/summary.json");
    if (!Array.isArray(rows) || !rows.some(row => row.id === "vms-eva")) throw new Error("Invalid statistics summary");
    const languages = rows.filter(row => row.kind === "wmf").sort((a, b) => name(a).localeCompare(name(b)));
    for (const row of languages) {
      const option = document.createElement("option"); option.value = row.id; option.textContent = name(row); controls.comparison.append(option);
    }
    controls.comparison.value = "wmf-en";
    const canonicalVms = rows.find(row => row.id === "vms-eva");
    const tiles = [
      [canonicalVms.spaces.h2.toFixed(2) + " bits", "VMS h₂ · letters + spaces"],
      [percent(canonicalVms.native.percent), "VMS exact three-word-window coverage"],
      [percent(canonicalVms.prefix3.percent), "VMS prefix-3 coverage · shuffled " + percent(canonicalVms.prefix3_shuffled.percent)],
    ];
    for (const [value, description] of tiles) {
      const tile = document.createElement("div"); tile.className = "stat";
      const strong = document.createElement("strong"); strong.textContent = value;
      const span = document.createElement("span"); span.textContent = description;
      tile.append(strong, span); document.getElementById("headline").append(tile);
    }
    const minimum = Math.min(...languages.map(row => row.spaces.h2));
    document.getElementById("status").textContent = `Computed from ${languages.length} WMF language samples, excluding Tamil. Baseline with spaces: lowest WMF h₂ ${minimum.toFixed(2)} bits. Controls update all linked views.`;
    Object.values(controls).forEach(control => control.addEventListener("change", render));
    render();
  }

  start().catch(error => document.getElementById("status").textContent = `Could not load the graphics: ${error.message}. The summary CSV and methods remain available below.`);
})();
