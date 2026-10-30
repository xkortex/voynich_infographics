# Character Markov transition explorer

Page: [`docs/pages/markov-transitions/`](../../docs/pages/markov-transitions/).
Generator: [`markov_transitions.py`](markov_transitions.py).
Browser source: [`templates/markov_transitions.js`](templates/markov_transitions.js).

## Reproduce

From the repository root, acquire the four EVA inputs as described in
[WORD_FREQUENCIES.md](WORD_FREQUENCIES.md). The existing symbol-frequency HTML
in `generated/` supplies the same vector glyph labels used elsewhere.

```sh
python3 src/processing/markov_transitions.py
python3 src/processing/assemble_site.py
python3 -m http.server 8000 --directory docs
```

The generator accepts `--data-dir` (default `data/local/word-frequency`) and
`--site-dir` (default `docs`). It never downloads raw inputs implicitly. Analysis
uses only the Python standard library. The browser has no external runtime,
font or chart-library dependency. Serve the page through HTTP, not `file:`.

Source files are ZL3b, IT2a, VT0e and RF1b basic EVA. These are related resources,
not independent witnesses: IT/VT share Takahashi ancestry and RF combines
readings. Acquisition URLs, exact SHA-256 input fingerprints and the generator
fingerprint accompany each published model. All assets are small UTF-8 text;
raw transcriptions and font/model binaries are not published by this generator.
Glyph labels reuse the atlas's existing EVA outlines and credits.

## Counting policy

One IVTFF text locus (line/label) is an independent boundary. Strip metadata in
angle brackets, treating `<->` drawing intrusions as word separators. Split on
periods, commas and whitespace. This treats uncertain spaces as boundaries.

Only complete `[a-vxyz]+` words are accepted. An alternative, unreadable marker,
extended code, ligature brace or other rejected token **ends the readable run**.
Never join the words on its two sides. Empty delimiters are ignored. Join
consecutive accepted words inside a run with exactly one ordinary space; do not
insert leading/trailing spaces, or transitions across loci. The policy differs
from folio-level statistics elsewhere and is deliberately stated on the page.

Letter mode uses individual EVA letters. Grouped mode uses longest matches
`cfh ckh cph cth ch sh`, with other letters separate. Space is a unit in both.
The model order refers to these units, not inferred phonemes.

For each readable run x[0]…x[n−1], count:

- Initial units: x[0].
- Initial pairs: x[0]→x[1], when n≥2, for second-order warm-up.
- First order: every x[i]→x[i+1].
- Second order: every (x[i],x[i+1])→x[i+2].

Sparse rows contain `[next_unit_index, positive_count]` pairs. The browser
normalizes over the entire observed row. First-order edges display
`count(previous,next) / Σ_next count(previous,next)`; second-order edges display
`count(a,b,next) / Σ_next count(a,b,next)`. No smoothing, interpolation or
fallback is applied. Zero-count destinations are not offered.

## Starting, stepping and stopping

Reset produces empty text and a START state. The first draw uses empirical
run-initial unit counts. In second order the second draw uses run-initial pair
counts conditioned on the chosen first unit. Later draws use the previous two
units. A transition (a,b)→c updates the displayed state to (b,c).

A context with no observed successor stops the generator. Undo or Reset can
recover. Observed run endings are **not a separate STOP state**; probabilities
are conditional on an observed successor, not a model of termination. There is
no automatic space or restart at a dead end.

Clicking a destination selects that unit deliberately. Clicking the current
state, pressing Enter in the diagram/page, or Next samples from the full positive-count distribution with the
browser's `Math.random()` and inverse cumulative sampling. Deterministic manual
choices are labelled separately from random draws. Each last-choice readout
records the context, count/total and order used for that choice.

Changing order preserves the already generated units and changes the next
conditional distribution. Earlier text was produced under its earlier choices;
it is not retrospectively resampled. Changing transcription or units resets the
text because the alphabet/model changed. Undo removes one appended unit and its
last-choice record. Copy uses ordinary spaces, independent of display settings.

The diagram is a focused outgoing-transition view, not a force-directed graph
of every possible context. The left state connects to destination units with
probability labels and square-root-scaled edge widths. By default it draws the
12 highest-probability destinations and reports their probability coverage.
Choose 6, 12, or all successors. The complete choice table is always available.
Neither visibility limit nor ranking changes normalization or random sampling.
Enter triggers one random draw even when a diagram node is focused; Space
activates that node as a deliberate choice. Held-key repeats are ignored.
Selectors, text fields, links, summaries and other native buttons retain normal
keyboard behavior. The Next button also accepts Enter without a duplicate draw.

Generated text is synthetic output from a low-order statistical model, not an
excerpt, translation, or evidence for a particular encoding hypothesis.

## Lexicon highlighting

The optional **Highlight lexicon words** mode (on by default) checks exact
whole-word spellings against the accepted lexicon of the selected transcription.
The same `text_runs` parsing policy constructs the lexicon, with occurrence
counts and the first observed source folio. Letter/grouped modes share that
source lexicon; grouping does not change the reconstructed word spelling.

A space or a model dead end completes a word. Completed matches receive a solid
highlight. A current unfinished word that happens to equal a lexicon entry gets
a dotted outline and is not counted as completed; extending it to a non-match
removes the highlight. No prefix/subword matching is performed. Undo, source
changes, and toggles recompute the display without changing the transition model
or generated units. Copy continues to use plain text with ordinary spaces.

Matches link to a source-folio exact-spelling candidate in Voynichese, with the
source occurrence count in the tooltip. A different live transcription may not
contain that spelling. Highlighting indicates corpus membership, not a meaningful
phrase or translation. Synthetic words absent from the lexicon are left plain.

Each source has a separate small `SOURCE-lexicon.json` containing
`[word, count, folio]` rows and input/generator fingerprints. It is fetched with
the model and cached per source. No raw corpus is published.

## Published schema and versioning

One JSON per source/unit mode contains the alphabet, unit frequencies, initial
counts, sparse first/second-order rows and totals. Both orders load together,
so switching order needs no new input or network request. Source and generator
hashes are repeated in each model and in `data/manifest.json`.

Assets have a 240,000-byte size cap. Presentation URLs carry content hashes;
data requests carry the analysis version to avoid mixed cached schemas. Raw
corpora remain ignored under `data/local/`.

## Checks

```sh
python3 -m unittest discover -s src/processing/tests -v
npm --prefix src/processing ci
npm --prefix src/processing run test:markov
```

Python fixtures check spaces, distinct first/second-order contexts, line and
unreadable-gap isolation, grouped units and terminal contexts. Every published
row is checked for positive unique successors, valid alphabet indices and
normalization, along with count and provenance invariants.

Browser-code tests exercise manual nodes, second-order warm-up and state shifts,
order switching without text loss, cumulative random-sampling boundaries,
current-state random clicks, dead ends, undo/reset, transcription reset, and
sampling a rare successor hidden by the diagram limit.
