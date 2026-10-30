# Vowel-like symbol discovery

The default view is now **blind exhaustive alternation search**, using grouped
EVA and a three-symbol candidate class. Sukhotin and the HMM remain comparisons.

This is a sensitivity experiment on distributional A/B classes. Neither class is
identified as phonetic vowels. The page links its code, data and primary papers.
It does not numerically reproduce an earlier published Voynich analysis.

## Build and inspect

Use Python 3.11+ and the pinned dependencies:

```sh
python3 -m pip install -r src/processing/requirements.txt
python3 src/processing/word_frequencies.py --fetch
python3 src/processing/vowel_discovery.py
python3 src/processing/assemble_site.py
python3 -m http.server 8000 --directory docs
```

The frequency generator acquires missing EVA sources only with `--fetch`. Other
source inputs and the existing frequency HTML must already be available; see
[SOURCE_DATA.md](SOURCE_DATA.md). `vowel_discovery.py` never downloads raw data.

Page: `http://127.0.0.1:8000/pages/vowel-discovery/`.

`--data-dir`, `--site-dir`, `--fit-words` (default 3000) and `--bootstraps`
(default 4) are explicit CLI settings. The on-page methods describe defaults;
actual sample sizes are displayed and all settings are saved in the manifest.
Models are cached only when generator hash, input hash and the two sample
settings match. No binary model or raw corpus is committed.

The generator publishes 44 scenario JSONs, one manifest and a small existing
vector-glyph mapping. Each asset is capped at 240,000 bytes. The browser needs
no external library, font, or service. Run it through HTTP, not a `file:` URL.

## Inputs and representations

- ZL3b, IT2a, VT0e and RF1b basic EVA use the four locally acquired inputs from
  the [word frequency experiment](WORD_FREQUENCIES.md). They are related
  resources, not independent witnesses. Preserve original word order; accept
  complete basic-EVA words only and do not resolve alternative readings.
- Forme and Orationum reuse the word-length chart's full-edition tokenization,
  Gutenberg-wrapper removal, page-marker removal and line-end dehyphenation.
  Editorial material and OCR noise remain. Lowercase Unicode letters stay
  distinct, including accents, historical letters and ligatures. Apostrophes
  do not contribute symbols. No modern spelling normalization is performed.
- Each Voynich source has letter/grouped-unit modes; the other two use letters.
  Grouping is longest-match `cfh ckh cph cth ch sh`, then individual EVA letters.
- Whole and interior scopes apply to every source. Interior scope removes the
  first and last **current units** after the control transformation, dropping
  empty results. It never joins across source word boundaries.
- Original and within-word shuffle controls apply to every source. Shuffle
  independently permutes each word occurrence, preserving its unit multiset
  and length. A seeded random stream makes it reproducible.
- Comparison corpora additionally have a vowel-deleted control: remove a/e/i/o/u,
  their accented forms, and æ/œ. y remains. This is an orthographic deletion
  experiment, not an authentic abjad or a contextual phonetic annotation of
  historical i/u, semivowels, or vowel sequences.

Input SHA-256 hashes, Python/NumPy versions, seed and generator SHA-256 are in
`docs/pages/vowel-discovery/data/manifest.json`. Each dataset repeats the run
and input hashes. The generator reads the original local inputs, not an
unrecorded live transcription.

## Algorithms

**Blind fixed-size alternation search.** For k = 1, 2, 3, 4, enumerate every
subset of k observed units. For a candidate A, count directed within-word pairs
with exactly one endpoint in A. Everything else is B. Maximize this count and
divide by all within-word pairs (including self-pairs) for the alternation rate.
There are no vowel labels, seed symbols or frequency cutoffs in this search.
The minimum-count UI setting is visibility-only.

The implementation uses the equivalent weighted cut formula: symmetrize pairs
into M with diagonal zero, then score(A) = sum of row sums for members of A
minus twice the sum of M[i,j] over unordered pairs inside A. This is an exact
integer objective. Save the top eight sets ordered by score descending and
lexical subset order, with the total number of exactly tied optima and total
candidate count. The small candidate class is A; there is no seed-based flip.

The search is repeated independently for every source, control and block
resample. Blind-search stability bars use the first lexical optimum of the
selected k in each resample, with unobserved symbols omitted from that symbol's
denominator. These bars are sensitive to ties and do not average all optima.

On the supplied ZL grouped whole-word native input, the unique best k=3 set is
`{a,e,o}` (85,961 / 130,287 pairs; 65.9781866%), and k=4 is `{a,e,o,y}`
(94,974 / 130,287; 72.8959912%). This verifies the earlier candidate-nucleus
result on these inputs. Individual EVA letters give a different optimum
because `ch`, `sh` and gallows composites are split. These are in-sample maxima,
not held-out accuracy or a discovery of phonetic values. More members and more
candidate sets change the optimization problem; scores across k are not a
penalty-adjusted model comparison.

The candidate cards show best k=3 and k=4 results, and the ranked table follows
the selected k. “Use set” applies any displayed candidate to the editable
assignments; the saved fitted columns and comparison grid still show the
optimum. Reset restores the selected method's optimum. CSV files include k,
blind assignments and bootstrap numerators/denominators as well as the other
methods. Presentation assets are content-versioned; data requests carry the
analysis version to prevent a stale schema mixing with a new interface.


**Sukhotin.** Following [Mayer (2010), §3.2](https://aclanthology.org/W10-2208/),
symmetrize directed within-word bigram counts, zero the diagonal, and initialize
scores as contact sums. Select the largest positive score, assign that symbol
to A, and subtract twice its contacts from all remaining scores. Do not select
an assigned symbol again. Stop when no positive score remains. Ties follow the
sorted symbol order. The first selected symbol is the contact-frequency seed.
Symbols with no observations are unassigned. Self-contacts remain in the
published directed pair matrix but are excluded from Sukhotin fitting.

**Two-state HMM.** A categorical-emission HMM uses separate word starts, shared
start/transition/emission parameters and no boundary symbol. Scaled
forward/backward Baum–Welch updates expected counts. Repeated word occurrences
weight the likelihood; grouping identical sequences only avoids redundant work.
Use Dirichlet(2) random initialization, seed 20261029 plus restart number, up to
25 iterations, relative likelihood improvement tolerance 1e-5, and a numerical
pseudocount of 1e-8 in updates. No known vowel labels enter fitting.

Fit at most 3,000 whole sequences selected at evenly spaced positions across
the scenario. Exclude sequences longer than 30 units from HMM fitting, not from
Sukhotin, counts or the contact display. Pick the greatest training likelihood
of three starts. These likelihoods are comparable **only within that sample**.

Because hidden state names are arbitrary, orient A to the state accounting for
at least half the expected occurrences of Sukhotin's seed. Assign other symbols
by their expected fraction of occurrences in that state (threshold ≥ 0.5).
Unseen symbols remain unassigned. The displayed occupancy is a fitted state
membership, not a calibrated probability of being a vowel. HMM splits can
capture initial/final position or other contextual distinctions.

For context on using unsupervised methods on Voynich, see
[Reddy & Knight (2011)](https://aclanthology.org/W11-1511/). This experiment uses
EVA inputs and independent words, and should not be described as reproducing
their corpus, representation or HMM setup.

## Sensitivity measures

Four block-bootstrap runs sample complete source documents with replacement.
Voynich documents are folios; comparison documents are artificial contiguous
200-word blocks. Sukhotin uses the complete resample. Each bootstrap HMM fits
at most 1,000 evenly spaced sequences with one seeded initialization. Its A/B
labels align to the full-fit seed if observed, otherwise to weighted full-fit
assignment agreement. Sukhotin retains its algorithm-selected set.

Stability bars show A assignments / runs where the symbol was observed. These
are not confidence intervals. HMM resampling sensitivity includes initialization
variation; the separate three-start bar exposes full-sample fitting variation.
A symbol unseen by every relevant run is blank. Four runs give a coarse
diagnostic; low-count symbols require particular care.

A second grid compares the selected method across source baselines, interior
scope, shuffle and alternative grouping (Voynich), or the five native/interior/
shuffle/deletion conditions (comparison corpora). A is oriented per fit; seeds
are in cell tooltips. Different seeds can change or invert partitions. There
is no pooled cross-transcription "vowel probability". Missing units are blank,
including when a grouped sign is absent in a letter representation.

## Interactive views

- The stability table has glyph labels, blind-search and other full-fit assignments, HMM occupancy,
  block-resampling bars, initialization sensitivity and editable A/B/unknown
  assignments. The current editing method is separate from the fitted results.
- The directed matrix offers row-normalized next-symbol probabilities or log2
  lift over the following-symbol marginal. Zero observed counts have undefined
  lift and are blank. Probability opacity is square-root-scaled for visibility;
  lift color intensity saturates at ±4 bits. Exact hover values are not clipped.
  No spaces or cross-word pairs are added.
- Cross-class adjacency is divided by **all** within-word pairs. The fraction
  with both symbols assigned is shown separately. The `2p(A)p(B)` reference
  uses symbol-token shares and is only an independence diagnostic; direct
  within-word shuffle is the more relevant control. No significance claim is
  attached to either value.
- The first 120 retained words are colored using current assignments. For
  transformed controls, the displayed units are transformed, while hover text
  retains the original word. Voynich links use the original spelling and an
  observed source folio. They are candidates: the live Voynichese transcription
  may disagree. These are spelling highlights, not unique occurrence IDs.
- Known comparison vowel letters remain hidden until explicitly revealed.
  The revealed check reports token-weighted precision of A against reference
  vowel letters and reference-vowel recall. Unassigned vowels count as misses.
  Deleted-vowel recall is undefined, not zero or perfect.
- A CSV download includes all symbols, original fitted results, resampling
  numerators/denominators and the user's current assignment. Minimum count only
  changes visibility; it never changes fitting or summary totals.

## Verification

```sh
python3 -m unittest discover -s src/processing/tests -v
npm --prefix src/processing ci
npm --prefix src/processing run test:vowels
```

Tests include the published German Sukhotin toy example, independent exhaustive
hidden-state enumeration against forward/backward expected counts, EM likelihood
monotonicity on an alternating toy corpus, deterministic seeded fitting, word
boundary isolation, exact shuffle/deletion invariants, and all 44 published
assets' count and probability consistency. Browser-code tests cover loading,
comparison grids, editing/reset, original-word links, hidden reference labels,
deleted-vowel controls, and empty count filters.
