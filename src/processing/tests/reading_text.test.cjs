/* Run with: node --test src/processing/tests/reading_text.test.cjs */
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM, VirtualConsole} = require("jsdom");
const root = path.resolve(__dirname, "../../../docs/pages/reading-text");
const script = fs.readFileSync(path.join(root, "reader.js"), "utf8");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function until(check) {
  for (let attempt = 0; attempt < 150; attempt++) {
    if (check()) return;
    await sleep(5);
  }
  throw new Error("Reader condition timed out");
}

function reader({hash = "", delays = {}, failGlyphs = false} = {}) {
  const errors = [];
  const dom = new JSDOM(html, {
    runScripts: "outside-only", pretendToBeVisual: true,
    url: "https://example.test/pages/reading-text/" + hash,
    virtualConsole: new VirtualConsole().on("jsdomError", error => errors.push(error.message)),
  });
  const w = dom.window, d = w.document;
  [...d.querySelectorAll(".folio")].slice(3).forEach(section => section.remove());
  const sections = [...d.querySelectorAll(".folio")];
  Object.defineProperty(d.querySelector(".toolbar"), "offsetHeight", {get: () => 120});
  let scrollY = 0;
  Object.defineProperty(w, "scrollY", {get: () => scrollY});
  w.scrollTo = options => { scrollY = options.top; };
  const height = section => section.dataset.loaded === "true" ? 1200 : 150;
  // Model the precise failure: rendering an earlier folio expands the document.
  w.Element.prototype.getBoundingClientRect = function () {
    const section = this.classList.contains("folio") ? this : this.closest(".folio");
    if (!section) return {top: 0, bottom: 0, left: 0, width: 100, height: 100};
    const preceding = sections.slice(0, sections.indexOf(section));
    const absolute = 600 + (d.getElementById("search-results").children.length ? 280 : 0) + preceding.reduce((sum, item) => sum + height(item), 0);
    const offset = this.classList.contains("folio-heading") ? 34 : this.classList.contains("word") ? 90 : 0;
    return {top: absolute + offset - scrollY, bottom: absolute + height(section) - scrollY, left: 0, width: 800, height: height(section)};
  };
  w.IntersectionObserver = class {
    constructor(callback) { w.loadNearby = section => callback([{isIntersecting: true, target: section}]); }
    observe() {}
    unobserve() {}
  };
  w.fetch = async url => {
    await sleep(delays[url] || 0);
    if (failGlyphs && url === "glyphs.json") return {ok: false, status: 503};
    return {ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(root, url), "utf8"))};
  };
  w.print = () => {};
  w.eval(script);
  const change = (id, value) => {
    d.getElementById(id).value = value;
    d.getElementById(id).dispatchEvent(new w.Event("change"));
  };
  return {w, d, dom, errors, change};
}

test("late preceding-folio expansion does not move an explicit jump", async () => {
  const app = reader({delays: {"folios/f1v.json": 100}});
  try {
    await until(() => app.w.loadNearby);
    app.w.loadNearby(app.d.getElementById("f1v"));
    app.change("folio-jump", "f2r");
    await until(() => app.d.getElementById("f2r").dataset.loaded === "true");
    assert.equal(app.d.querySelector("#f2r .folio-heading").getBoundingClientRect().top, 136);
    await until(() => app.d.getElementById("f1v").dataset.loaded === "true");
    assert.equal(app.d.querySelector("#f2r .folio-heading").getBoundingClientRect().top, 136);
    assert.equal(app.w.location.hash, "#f2r");
    assert.deepEqual(app.errors, []);
  } finally { app.dom.window.close(); }
});

test("a slow old jump cannot override a newer folio selection", async () => {
  const app = reader({delays: {"folios/f1v.json": 100}});
  try {
    await until(() => app.w.loadNearby);
    app.change("folio-jump", "f1v");
    app.change("folio-jump", "f2r");
    await until(() => app.d.getElementById("f1v").dataset.loaded === "true");
    assert.equal(app.d.getElementById("folio-jump").value, "f2r");
    assert.equal(app.w.location.hash, "#f2r");
    assert.equal(app.d.querySelector("#f2r .folio-heading").getBoundingClientRect().top, 136);
  } finally { app.dom.window.close(); }
});

test("a direct word fragment loads its folio and targets the exact local word", async () => {
  const app = reader({hash: "#f2r-word-0"});
  try {
    await until(() => app.d.querySelector("#f2r-word-0.navigation-target"));
    assert.equal(app.d.getElementById("folio-jump").value, "f2r");
    assert.equal(app.d.getElementById("f2r-word-0").getBoundingClientRect().top, 136);
  } finally { app.dom.window.close(); }
});

test("manual scrolling releases the navigation anchor", async () => {
  const app = reader({delays: {"folios/f1v.json": 100}});
  try {
    await until(() => app.w.loadNearby);
    app.w.loadNearby(app.d.getElementById("f1v"));
    app.change("folio-jump", "f2r");
    await until(() => app.d.getElementById("f2r").dataset.loaded === "true");
    app.w.dispatchEvent(new app.w.Event("wheel"));
    app.w.scrollTo({top: 500});
    await until(() => app.d.getElementById("f1v").dataset.loaded === "true");
    assert.equal(app.w.scrollY, 500);
  } finally { app.dom.window.close(); }
});

test("EVA phrases search unrendered text and link to local occurrences", async () => {
  const app = reader();
  try {
    await until(() => app.w.loadNearby);
    app.d.getElementById("eva-query").value = "FACHYS   YKAL";
    app.change("search-mode", "words");
    app.d.getElementById("eva-search").dispatchEvent(new app.w.Event("submit", {cancelable: true}));
    await until(() => app.d.querySelectorAll("#search-results li").length === 1);
    assert.equal(app.d.querySelector("#search-results a").hash, "#f1r-word-0");
    assert.equal(app.d.getElementById("f1r-word-0").classList.contains("search-match"), true);
    assert.equal(app.d.getElementById("f1r-word-1").classList.contains("search-match"), true);
    app.d.querySelector("#search-results a").click();
    await until(() => app.w.location.hash === "#f1r-word-0");
    assert.equal(app.d.getElementById("f1r-word-0").getBoundingClientRect().top, 136);
    assert.notEqual(app.d.getElementById("f1v").dataset.loaded, "true", "search must not render every folio");
    app.d.getElementById("clear-search").click();
    assert.equal(app.d.querySelectorAll(".search-match").length, 0);
    assert.equal(app.d.getElementById("next-match").disabled, true);
  } finally { app.dom.window.close(); }
});

test("contains search, exact-word search, next/previous, and no-match results", async () => {
  const app = reader({failGlyphs: true});
  try {
    await until(() => app.w.loadNearby);
    assert.equal(app.d.getElementById("manuscript").dataset.display, "eva");
    app.d.getElementById("eva-query").value = "aiin";
    app.d.getElementById("eva-search").dispatchEvent(new app.w.Event("submit", {cancelable: true}));
    await until(() => app.d.getElementById("search-status").textContent.includes("matching passage"));
    assert(app.d.querySelectorAll("#search-results li").length > 1);
    app.d.getElementById("next-match").click();
    await until(() => app.d.querySelector(".navigation-target.word"));
    assert(app.d.getElementById("match-position").textContent.startsWith("1 /"));
    app.d.getElementById("previous-match").click();
    assert(!app.d.getElementById("match-position").textContent.startsWith("1 /"));
    app.d.getElementById("eva-query").value = "zzzzzzzzzz";
    app.d.getElementById("eva-search").dispatchEvent(new app.w.Event("submit", {cancelable: true}));
    await until(() => app.d.getElementById("search-status").textContent.startsWith("0 matching passages"));
    assert.equal(app.d.querySelectorAll("#search-results li").length, 0);
  } finally { app.dom.window.close(); }
});


test("back and forward restore the corresponding loaded folios", async () => {
  const app = reader();
  try {
    await until(() => app.w.loadNearby);
    app.change("folio-jump", "f1v");
    await until(() => app.w.location.hash === "#f1v");
    app.change("folio-jump", "f2r");
    await until(() => app.w.location.hash === "#f2r");
    app.w.history.back();
    await until(() => app.w.location.hash === "#f1v" && app.d.getElementById("folio-jump").value === "f1v");
    assert.equal(app.d.querySelector("#f1v .folio-heading").getBoundingClientRect().top, 136);
    app.w.history.forward();
    await until(() => app.w.location.hash === "#f2r" && app.d.getElementById("folio-jump").value === "f2r");
    assert.equal(app.d.querySelector("#f2r .folio-heading").getBoundingClientRect().top, 136);
  } finally { app.dom.window.close(); }
});

test("search results finishing above a new jump do not shift its target", async () => {
  const app = reader({delays: {"folios/f1v.json": 100}});
  try {
    await until(() => app.w.loadNearby);
    app.d.getElementById("eva-query").value = "daiin";
    app.d.getElementById("eva-search").dispatchEvent(new app.w.Event("submit", {cancelable: true}));
    app.change("folio-jump", "f2r");
    await until(() => app.d.getElementById("f2r").dataset.loaded === "true");
    await until(() => app.d.getElementById("search-results").children.length > 0);
    assert.equal(app.d.querySelector("#f2r .folio-heading").getBoundingClientRect().top, 136);
  } finally { app.dom.window.close(); }
});
