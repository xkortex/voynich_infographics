/* Load the reading edition a folio at a time, without changing XML word order. */
(() => {
  "use strict";
  const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
  const manuscript = document.getElementById("manuscript");
  const sections = [...manuscript.querySelectorAll(".folio")];
  const jump = document.getElementById("folio-jump");
  const display = document.getElementById("display");
  const status = document.getElementById("status");
  const printButton = document.getElementById("print");
  const pending = new Map();
  const folioData = new Map();
  const toolbar = document.querySelector(".toolbar");
  const searchForm = document.getElementById("eva-search");
  const searchInput = document.getElementById("eva-query");
  const searchStatus = document.getElementById("search-status");
  const resultsList = document.getElementById("search-results");
  let navigationVersion = 0;
  let navigationAnchor = null;
  let searchVersion = 0;
  let matches = [];
  let matchCursor = -1;
  let shownMatches = 40;
  let matchedWordIds = new Set();
  let glyphs = null;

  async function readJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
    return response.json();
  }

  function readFolio(name) {
    if (!folioData.has(name)) {
      const request = readJson(`folios/${name}.json`).catch(error => {
        folioData.delete(name);
        throw error;
      });
      folioData.set(name, request);
    }
    return folioData.get(name);
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS(SVG_NAMESPACE, name);
    for (const [attribute, value] of Object.entries(attributes)) {
      element.setAttribute(attribute, value);
    }
    return element;
  }

  function installGlyphDefinitions(data) {
    const sprite = svgElement("svg", {width: 0, height: 0, "aria-hidden": "true"});
    sprite.style.position = "absolute";
    const definitions = svgElement("defs");
    for (const [character, glyph] of Object.entries(data)) {
      definitions.append(svgElement("path", {
        id: `reader-glyph-${character.charCodeAt(0)}`,
        d: glyph.path,
      }));
    }
    sprite.append(definitions);
    document.body.prepend(sprite);
  }

  function connectedForm(eva) {
    // The font uses capital gallows and S for these connected groups.
    return eva.replace(/c([fkpt])h|sh/g, (match, gallows) =>
      gallows ? `c${gallows.toUpperCase()}h` : "Sh"
    );
  }

  function renderGlyphWord(eva) {
    const characters = [...connectedForm(eva)];
    const advance = characters.reduce((sum, character) => sum + glyphs[character].advance, 0);
    const width = advance + 440;
    const svg = svgElement("svg", {viewBox: `0 0 ${width} 2000`, "aria-hidden": "true"});
    svg.style.width = `${width / 2000 * 1.5}em`;
    const group = svgElement("g", {transform: "translate(220 1400) scale(1 -1)"});
    let position = 0;
    for (const character of characters) {
      group.append(svgElement("use", {
        href: `#reader-glyph-${character.charCodeAt(0)}`,
        x: position,
      }));
      position += glyphs[character].advance;
    }
    svg.append(group);
    return svg;
  }

  function renderWord(word, folio) {
    const link = document.createElement("a");
    link.className = "word";
    link.href = `https://www.voynichese.com/#/${folio}/exa:${encodeURIComponent(word.eva)}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.id = `${folio}-word-${word.index}`;
    link.classList.toggle("search-match", matchedWordIds.has(link.id));
    link.title = `${word.eva} · ${folio}, XML word ${word.index} · Open exact-spelling matches on this folio`;
    link.setAttribute("aria-label", `${word.eva}, ${folio}, open in Voynichese`);
    if (glyphs) link.append(renderGlyphWord(word.eva));
    const text = document.createElement("span");
    text.className = "eva";
    text.textContent = word.eva;
    link.append(text);
    return link;
  }

  function loadFolio(section) {
    if (section.dataset.loaded === "true") return Promise.resolve();
    const name = section.dataset.folio;
    if (pending.has(name)) return pending.get(name);
    const task = (async () => {
      const placeholder = section.querySelector(".folio-placeholder");
      placeholder.textContent = `Loading ${name}…`;
      try {
        const folio = await readFolio(name);
        if (folio.folio !== name || !Array.isArray(folio.words)) {
          throw new Error(`Invalid folio data for ${name}`);
        }
        const paragraph = document.createElement("p");
        paragraph.className = "words";
        for (const word of folio.words) {
          paragraph.append(renderWord(word, name), document.createTextNode(" "));
        }
        placeholder.replaceWith(paragraph);
        section.dataset.loaded = "true";
        alignNavigationAnchor();
      } catch (error) {
        placeholder.textContent = `Could not load ${name}. `;
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "load-folio";
        retry.textContent = "Retry";
        placeholder.append(retry);
        status.textContent = `${error.message}. Use Retry on the affected folio.`;
        throw error;
      } finally {
        pending.delete(name);
      }
    })();
    pending.set(name, task);
    return task;
  }

  function parseDestination(fragment) {
    let id;
    try { id = decodeURIComponent(fragment.replace(/^#\/?/, "")); }
    catch (_) { return null; }
    const match = id.match(/^(f\d+[rv]\d*)(?:-word-(\d+))?$/i);
    if (match) {
      const name = match[1].toLowerCase();
      const section = sections.find(item => item.dataset.folio === name);
      if (!section) return null;
      return {section, id: match[2] === undefined ? name : `${name}-word-${match[2]}`};
    }
    const element = id && document.getElementById(id);
    return element ? {id, section: null} : null;
  }

  function anchorElement(destination) {
    if (destination.section && destination.id === destination.section.id) {
      return destination.section.querySelector(".folio-heading");
    }
    return document.getElementById(destination.id) || destination.section;
  }

  function alignNavigationAnchor() {
    if (!navigationAnchor) return;
    const target = anchorElement(navigationAnchor);
    if (!target) return;
    const offset = toolbar.offsetHeight + 16;
    document.documentElement.style.setProperty("--reader-offset", `${offset}px`);
    const top = Math.max(0, window.scrollY + target.getBoundingClientRect().top - offset);
    // Use one explicit offset; smooth scrolling and nested scroll margins used
    // to compound the offset and race with expanding lazy-loaded folios.
    window.scrollTo({top, behavior: "auto"});
  }

  function releaseNavigationAnchor() {
    navigationVersion++;
    navigationAnchor = null;
  }

  async function goToFragment(fragment, updateAddress = true) {
    const destination = parseDestination(fragment);
    if (!destination) {
      releaseNavigationAnchor();
      if (fragment && fragment !== "#") status.textContent = "That reader location was not found.";
      return;
    }
    const version = ++navigationVersion;
    navigationAnchor = destination;
    alignNavigationAnchor();
    if (destination.section) await loadFolio(destination.section);
    // A slow older request must never scroll over a newer jump.
    if (version !== navigationVersion) return;
    if (destination.section) jump.value = destination.section.id;
    if (updateAddress && location.hash !== `#${destination.id}`) {
      history.pushState(null, "", `#${destination.id}`);
    }
    document.querySelectorAll(".navigation-target").forEach(node => node.classList.remove("navigation-target"));
    const target = anchorElement(destination);
    if (target) target.classList.add("navigation-target");
    if (navigationAnchor === destination) alignNavigationAnchor();
  }

  function inspectMatches(folio, query, wholeWords) {
    const offsets = [];
    let text = "";
    for (const word of folio.words) {
      if (text) text += " ";
      offsets.push(text.length);
      text += word.eva;
    }
    const found = [];
    const seen = new Set();
    let start = text.indexOf(query);
    let firstWord = 0;
    while (start !== -1) {
      const end = start + query.length;
      if (!wholeWords || ((start === 0 || text[start - 1] === " ") && (end === text.length || text[end] === " "))) {
        while (firstWord + 1 < offsets.length && offsets[firstWord + 1] <= start) firstWord++;
        let lastWord = firstWord;
        while (lastWord + 1 < offsets.length && offsets[lastWord + 1] < end) lastWord++;
        const key = `${firstWord}:${lastWord}`;
        if (!seen.has(key)) {
          seen.add(key);
          found.push({
            folio: folio.folio,
            id: `${folio.folio}-word-${folio.words[firstWord].index}`,
            wordIds: folio.words.slice(firstWord, lastWord + 1).map(word => `${folio.folio}-word-${word.index}`),
            context: folio.words.slice(Math.max(0, firstWord - 3), Math.min(folio.words.length, lastWord + 5)).map(word => word.eva).join(" "),
          });
        }
      }
      start = text.indexOf(query, start + 1);
    }
    return found;
  }

  function updateMatchControls() {
    document.getElementById("previous-match").disabled = !matches.length;
    document.getElementById("next-match").disabled = !matches.length;
    document.getElementById("match-position").textContent = matches.length
      ? `${matchCursor >= 0 ? matchCursor + 1 : "–"} / ${matches.length}` : "";
  }

  function paintSearchMatches() {
    manuscript.querySelectorAll(".word").forEach(word => {
      word.classList.toggle("search-match", matchedWordIds.has(word.id));
    });
  }

  function renderSearchResults() {
    resultsList.replaceChildren();
    matches.slice(0, shownMatches).forEach((match, index) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = `#${match.id}`;
      link.textContent = `${match.folio} · ${match.context}`;
      link.addEventListener("click", event => {
        event.preventDefault();
        jumpToMatch(index);
      });
      item.append(link);
      resultsList.append(item);
    });
    document.getElementById("more-matches").hidden = shownMatches >= matches.length;
    updateMatchControls();
    alignNavigationAnchor();
  }

  function jumpToMatch(index) {
    if (!matches.length) return;
    matchCursor = (index + matches.length) % matches.length;
    updateMatchControls();
    goToFragment(matches[matchCursor].id).catch(error => {
      searchStatus.textContent = `Could not open this match: ${error.message}`;
    });
  }

  async function searchEva(event) {
    event.preventDefault();
    releaseNavigationAnchor();
    const query = searchInput.value.trim().toLowerCase().replace(/\s+/g, " ");
    const version = ++searchVersion;
    matches = [];
    matchCursor = -1;
    matchedWordIds = new Set();
    shownMatches = 40;
    renderSearchResults();
    paintSearchMatches();
    if (!query || !/^[a-z]+(?: [a-z]+)*$/.test(query)) {
      searchStatus.textContent = "Enter EVA letters, or an EVA phrase separated by spaces.";
      return;
    }
    const wholeWords = document.getElementById("search-mode").value === "words";
    const found = [];
    let failed = 0;
    for (let start = 0; start < sections.length; start += 6) {
      if (version !== searchVersion) return;
      const batch = sections.slice(start, start + 6);
      const data = await Promise.all(batch.map(section => readFolio(section.id).catch(() => { failed++; return null; })));
      if (version !== searchVersion) return;
      data.forEach(folio => { if (folio) found.push(...inspectMatches(folio, query, wholeWords)); });
      searchStatus.textContent = `Searching ${Math.min(start + 6, sections.length)} / ${sections.length} folios…`;
    }
    matches = found;
    matchedWordIds = new Set(matches.flatMap(match => match.wordIds));
    paintSearchMatches();
    renderSearchResults();
    searchStatus.textContent = `${matches.length} matching passage${matches.length === 1 ? "" : "s"} for “${query}” across ${sections.length - failed} folios.${failed ? ` ${failed} folios could not load; submit again to retry.` : ""} Matches do not cross folio boundaries.`;
  }

  function clearSearch() {
    releaseNavigationAnchor();
    searchVersion++;
    searchInput.value = "";
    matches = [];
    matchCursor = -1;
    matchedWordIds = new Set();
    paintSearchMatches();
    renderSearchResults();
    searchStatus.textContent = "Search cleared.";
  }

  function watchFolios() {
    if (!("IntersectionObserver" in window)) {
      status.textContent = "Use each folio’s Load button, or Load all & print, in this browser.";
      return;
    }
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          loadFolio(entry.target).then(() => observer.unobserve(entry.target)).catch(() => {});
        }
      }
    }, {rootMargin: "900px 0px"});
    sections.forEach(section => observer.observe(section));
  }

  async function printManuscript() {
    printButton.disabled = true;
    try {
      // Bounded batches avoid hundreds of simultaneous requests.
      for (let start = 0; start < sections.length; start += 4) {
        await Promise.all(sections.slice(start, start + 4).map(loadFolio));
        status.textContent = `Preparing print edition: ${Math.min(start + 4, sections.length)} / ${sections.length} folios`;
      }
      status.textContent = "All folios loaded. Use your browser’s print dialog to save a PDF.";
      window.print();
    } catch (error) {
      status.textContent = `${error.message}. Printing stopped; retry after loading the missing folio.`;
    } finally {
      printButton.disabled = false;
    }
  }

  async function start() {
    try {
      glyphs = await readJson("glyphs.json");
      installGlyphDefinitions(glyphs);
    } catch (error) {
      manuscript.dataset.display = "eva";
      display.value = "eva";
      display.disabled = true;
      status.textContent = "Glyph artwork could not load. Showing the readable EVA transcription instead.";
    }
    display.addEventListener("change", () => {
      manuscript.dataset.display = display.value;
      alignNavigationAnchor();
    });
    document.getElementById("size").addEventListener("input", event => {
      document.documentElement.style.setProperty("--size", `${event.target.value}px`);
      document.getElementById("size-label").value = event.target.value;
      alignNavigationAnchor();
    });
    manuscript.addEventListener("click", event => {
      const button = event.target.closest(".load-folio");
      if (button) loadFolio(button.closest(".folio")).catch(() => {});
    });
    jump.addEventListener("change", () => goToFragment(jump.value).catch(() => {}));
    window.addEventListener("hashchange", () => {
      if (!location.hash || location.hash === "#") {
        navigationVersion++;
        releaseNavigationAnchor();
        return;
      }
      goToFragment(location.hash, false).catch(() => {});
    });
    // Only deliberate user gestures release the jump lock. Programmatic scroll
    // events from layout correction must not undo it.
    ["wheel", "touchstart", "pointerdown"].forEach(type => {
      window.addEventListener(type, releaseNavigationAnchor, {passive: true});
    });
    window.addEventListener("keydown", event => {
      if (!["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(event.key)) return;
      if (!event.target.closest("input,select,button,textarea")) releaseNavigationAnchor();
    });
    let trackingScroll = false;
    window.addEventListener("scroll", () => {
      if (navigationAnchor || trackingScroll) return;
      trackingScroll = true;
      requestAnimationFrame(() => {
        trackingScroll = false;
        if (navigationAnchor) return;
        const offset = toolbar.offsetHeight + 16;
        const current = sections.find(section => section.getBoundingClientRect().bottom > offset);
        if (current) jump.value = current.id;
      });
    }, {passive: true});
    window.addEventListener("resize", alignNavigationAnchor);
    if ("ResizeObserver" in window) new ResizeObserver(alignNavigationAnchor).observe(manuscript);
    searchForm?.addEventListener("submit", searchEva);
    document.getElementById("clear-search")?.addEventListener("click", clearSearch);
    document.getElementById("previous-match")?.addEventListener("click", () => jumpToMatch(matchCursor < 0 ? matches.length - 1 : matchCursor - 1));
    document.getElementById("next-match")?.addEventListener("click", () => jumpToMatch(matchCursor + 1));
    document.getElementById("more-matches")?.addEventListener("click", () => { shownMatches += 40; renderSearchResults(); });
    printButton.addEventListener("click", printManuscript);
    try {
      if (location.hash && location.hash !== "#") await goToFragment(location.hash, false);
      else await loadFolio(sections[0]);
    } finally {
      // A failed first request must not disable later automatic loading.
      watchFolios();
    }
  }

  start().catch(error => {
    status.textContent = `${error.message}. Use the folio Load buttons to retry.`;
  });
})();
