# Word frequency sensitivity experiment

Page: [`docs/pages/word-frequencies/`](../../docs/pages/word-frequencies/).
Generator: [`word_frequencies.py`](word_frequencies.py). Browser source:
[`templates/word_frequencies.js`](templates/word_frequencies.js).

## Reproduce

From the repository root, using Python 3.10 or newer:

```sh
python3 -m pip install -r src/processing/requirements.txt
python3 src/processing/word_frequencies.py --fetch
python3 -m http.server 8000 --directory docs
```

Open `http://127.0.0.1:8000/pages/word-frequencies/`. Downloads happen only with
`--fetch`, and only for missing inputs. Files stay in ignored
`data/local/word-frequency/`. To use separately acquired files, pass `--data-dir`.
The manifest records the exact bytes, SHA-256 hashes, source URLs, script hash,
Morfessor version, seed and training parameters. It does not silently replace
an existing input. Delete or move a local input explicitly before reacquiring it.

Inputs come from the [Voynich.nu resource table](https://www.voynich.nu/transcr.html):

| Code | File | Representation |
|---|---|---|
| ZL | `https://www.voynich.nu/data/ZL3b-n.txt` | Zandbergen–Landini, EVA |
| IT | `https://www.voynich.nu/data/IT2a-n.txt` | Takahashi extracted from interlinear, EVA-T |
| VT | `https://www.voynich.nu/data/VT0e-n.txt` | Voynichese browser transcription, EVA-T |
| RF | `https://www.voynich.nu/data/RF1b-er.txt` | Combined reference, basic EVA |

These are four related resources, not independent witnesses. FG, CD and GC use
other alphabets and are outside this first EVA comparison. RF basic EVA is the
site's approximation/conversion, not its full extended representation. Coverage,
word boundaries and uncertainty differ; no common-locus restriction is applied.
The source site describes transliterations as CC0 in its
[licensing notes](https://www.voynich.nu/roadmap.html#licences).
No raw inputs or model binaries are committed by this generator.

## Population and treatments

The baseline is **no word transformation after IVTFF parsing**. Headers and
angle-bracket metadata are not words. Periods, commas (uncertain spaces),
whitespace and drawing intrusions `<->` are boundaries. Alternative readings,
question marks, extended codes and ligature braces are retained literally in
marked tokens. We never extract apparent readable fragments from these tokens.

The default population contains only complete basic-EVA words (`[a-vxyz]+`).
The all-token population includes marked tokens but leaves them unchanged under
every treatment. Counts and filtering are identical across treatments for each
population. Both populations and all transformations preserve total token mass.
“No processing” does not imply uncertainty has been resolved.

Fourteen transformations are precomputed separately for each source:

- Whole-word identity.
- Prefix-1/2/3 and suffix-1/2/3: retain that many EVA letters, shorter words intact.
- Middle-1/2: remove that many letters from **each** end. Words of length ≤ 2n
  retain separate `~short:WORD` identities; they never become a shared empty word.
- Rare-word collapse at original count ≤ 1 or ≤ 2. Move only to a word above
  the threshold at exactly one Levenshtein insertion, deletion or substitution.
  Choose highest original frequency, then lexical order. No chaining; no common
  word merging. Anagrams/transpositions are not a one-edit match by definition.
- Morfessor Baseline 2.0.6 with corpus weights 0.1, 1, 10. Train on sorted
  `(token_count, word)` records, seed 42, `use_skips=False`, recursive batch
  training, finish threshold 0.01. Decode with default Viterbi addcount 1.0,
  max segment length 30. Family = longest segment, leftmost on ties, consistent
  with the earlier four-corpus experiment. We do not count morph tokens, or
  assert that the selected segments are linguistic stems. Corpus weight trades
  off lexicon and corpus costs; see the
  [Morfessor documentation](https://morfessor.readthedocs.io/en/latest/cmdtools.html).

Truncation counts transliteration letters, not grouped Voynich glyphs. A smaller
vocabulary or heavier head is partly guaranteed by pooling identities; it does
not on its own support an encoding hypothesis.

## Measures and audit trail

The rank curve plots family token count, or `100 × count / source tokens`,
against independently assigned rank (count descending, lexical tie breaks).
The exact frequency-of-frequencies histogram plots `k` against the number of
families occurring k times, or that number divided by all families × 100.
There are no hidden histogram bins. Logarithmic axes are optional.

The interface compares at most six source × treatment combinations. It shows
all family ranks in the line paths; focusable/hoverable markers sample long
tails to avoid thousands of keyboard stops. The table contains every family,
with a member-spelling filter, 30-row pagination and complete CSV export.
Summary statistics are also saved as `data/summary.csv` for both populations.

Each source vocabulary is split into small JSON shards of
`[word, token_count, example_folio, spelling_verified_in_VT]`.
Treatment files contain family keys and integer mappings parallel to that
vocabulary. Segmentation shards preserve Morfessor's actual decoded segments.
Each asset is capped at 240,000 bytes; no dependency is fetched by the browser.

Links use **original words**, not transformed keys. The example is a folio
where that spelling occurs in the selected source. Verification checks whether
the exact spelling also occurs on that folio in the downloaded VT transcription;
it is not a guarantee about a future live Voynichese version. Unverified links
are labelled candidates, and marked tokens link only to the folio. Voynichese
highlights a spelling on the folio rather than identifying a unique occurrence.

## Checks

```sh
python3 -m unittest discover -s src/processing/tests -v
npm --prefix src/processing ci
npm --prefix src/processing run test:frequencies
```

Python fixtures exercise parsing, mass conservation, edit thresholds/ties and
short middles. Browser-code tests cover relative/count views, literal-token
population, family membership links, filtering and dependency-load failure.
Generated-data audits check every map index, both population totals and
segmentation reconstruction for every source and treatment.
