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
  let glyphs = null;

  async function readJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
    return response.json();
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
        const folio = await readJson(`folios/${name}.json`);
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

  async function goToFolio(name, updateAddress = true) {
    const section = sections.find(item => item.dataset.folio === name);
    if (!section) return;
    await loadFolio(section);
    jump.value = name;
    if (updateAddress) history.replaceState(null, "", `#${name}`);
    section.scrollIntoView({block: "start"});
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
    display.addEventListener("change", () => manuscript.dataset.display = display.value);
    document.getElementById("size").addEventListener("input", event => {
      document.documentElement.style.setProperty("--size", `${event.target.value}px`);
      document.getElementById("size-label").value = event.target.value;
    });
    manuscript.addEventListener("click", event => {
      const button = event.target.closest(".load-folio");
      if (button) loadFolio(button.closest(".folio")).catch(() => {});
    });
    jump.addEventListener("change", () => goToFolio(jump.value).catch(() => {}));
    window.addEventListener("hashchange", () => goToFolio(location.hash.slice(1), false).catch(() => {}));
    printButton.addEventListener("click", printManuscript);
    const initialFolio = sections.find(section => section.id === location.hash.slice(1));
    try {
      await loadFolio(initialFolio || sections[0]);
      if (initialFolio) initialFolio.scrollIntoView({block: "start"});
    } finally {
      // A failed first request must not disable later automatic loading.
      watchFolios();
    }
  }

  start().catch(error => {
    status.textContent = `${error.message}. Use the folio Load buttons to retry.`;
  });
})();
