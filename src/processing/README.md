# Processing and reproducibility

The generators are organized into importable functions with explicit inputs and outputs. Numerical cleaning and counting rules are preserved. Page presentation lives in readable HTML, CSS and JavaScript templates; builds embed those files so the delivered charts remain standalone. `ocr_fullres_mac.py` is the user-identified historical OCR script, preserved unchanged.

## From input to chart

| Chart | Processing | Inputs | Outputs |
|---|---|---|---|
| EVA frequencies | `eva_frequencies.py` | ZL3b text + EVA2 font | HTML, counts.json; glyph paths embedded in HTML |
| Word positions | `word_positions.py` | ZL3b + frequency HTML for glyphs | HTML, SVG, positions.json |
| Word lengths | `word_lengths.py` | ZL3b + Forme + Orationum OCR | HTML, SVG, CSV, length_stats.json |
| Raster export | `render_pngs.cjs` | Two SVGs | PNG previews/downloads |
| Static gallery | `assemble_site.py`, `provenance.py` | Generated artifacts | docs/ pages, previews, downloads, provenance links |
| Orationum OCR | `ocr_fullres_mac.py` | Authorized source PDF; Poppler + Tesseract | Per-page cache and full OCR text |
| WMF auxiliary analysis | `wmf_word_lengths.py` | WMF wmf.csv | Per-language summary and distribution CSVs; Tamil excluded |

WMF results are not an input to any of the three current charts. Source-data instructions and rights caveats are in [SOURCE_DATA.md](SOURCE_DATA.md); exact original input-byte hashes are in [sources.json](sources.json).

## Rebuild

Run from the repository root. Requires Python 3.10+ (3.12 recommended), Node.js compatible with Sharp 0.35.5, and the locally acquired inputs. Python and Node packages are required **only to rebuild**, not to view the website.

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r src/processing/requirements.txt
npm --prefix src/processing install
python3 src/processing/check_sources.py --data-dir data/local
python3 src/processing/build_all.py --data-dir data/local
```

`build_all.py` runs the three chart generators in order, rasterizes PNGs, and assembles `docs/`. It writes input hashes for that run to `generated/input_hashes.json`. It does not fetch data or publish anything. `check_sources.py` exits nonzero for a missing or differing input; a different upstream byte version may still produce the same aggregate counts (for example, different newlines). Inspect differences rather than assuming equivalence.

For HTML/SVG/data only, without the Node step or updating docs/: `python3 src/processing/build_all.py --skip-png`. Individual Python generators accept `--data-dir` and `--output-dir`. `assemble_site.py --artifacts generated` updates the gallery from a complete set of artifacts, including PNGs. These paths may point outside the repo. Ignore rules keep data/local, generated and package installations out of Git.

To re-annotate existing pages without changing the charts, call `annotate(repo_path, artifact_path)` from `provenance.py`; normal assembly already does this.

## Methodology

### EVA frequencies

Read ZL3b IVTFF text loci (not page headers or comments). Strip angle-bracket annotations, replace complete bracketed alternative spans and extended @number; signs with separators, remove curly ligature braces but retain contents, normalize case, and count readable basic-EVA segments. Default grouped forms use longest-match segmentation of cfh, ckh, cph, cth, ch, sh; remaining letters count separately. Thus cth is one grouped token and iin remains three. All 25 font letter codes a–v, x–z are listed, even at zero. Totals: **193,266 EVA letters / 173,512 grouped tokens** from 5,385 loci.

### Positions and word lengths

Remove angle annotations; split words at periods, commas, whitespace, hyphens and equals signs; strip curly braces. Retain only words entirely matching basic EVA. This rejects a whole word containing alternatives, extended codes or unreadables, instead of keeping its readable parts. **37,126 VMS word occurrences** remain, containing **188,466 letters / 169,172 grouped tokens**.

Position = token index / (token count − 1), binned into 15 intervals. Single-token words go in the middle. Repeated words count repeatedly. Own-peak scaling compares shape, while shared scaling compares absolute bin counts; color expresses overall token share. Small word lengths create discrete positional spikes, so these curves are not smoothed estimates of a continuous process.

For the comparison editions, remove Gutenberg wrapper, PDF page markers and standalone Google digitization lines; join letter-hyphen-newline-letter wraps; normalize NFC. Tokenize Unicode alphabetic-like runs with optional internal apostrophes; only alphabetic characters add length. Keep editorial content, abbreviations and OCR noise. Expected counts: **43,765 Forme words**, mean **4.1451616589**; **104,081 Orationum words**, mean **5.7214669344**. CSV preserves exact lengths; chart tail is 25+. VMS grouped mean is **4.5566988095**, letter mean **5.0763885148**.

### WMF

The WMF script streams only wmf.csv when given its directory, uses the language and text columns, and excludes ta/tam/Tamil labels. It computes mean, median, all tied modes, population SD, and shares at 1–2, 4–6, 8+, 10+. It omits zero-letter matches. It uses the earlier alphabetic-run convention, not language-specific word segmentation. Unspaced scripts and combining marks need special interpretation. The validated historical run contained **339 retained language groups** and excluded **1,791 Tamil rows**.

## Verification

`python3 src/processing/verify_outputs.py --output-dir generated` checks the expected original counts. If intentionally using different input versions, a failed historical-count check does not mean the algorithm is broken; record and inspect the change. SVG/HTML content is reproducible under the same inputs; PNG text rasterization can vary with the host fonts/rendering libraries.

## Limits and licensing

These are operational transcription/orthography counts, not linguistic character counts or a decipherment. Full-edition comparison texts mix genres and editorial content. No corpus or font binary is bundled. The Orationum source PDF URL and original OCR script have now been identified by the user; the remaining run-level gaps are listed in SOURCE_DATA.md. The MIT license on original code does not license source corpora or third-party EVA glyph artwork. Refer to SOURCE_DATA.md and the original rights notices.

## Reading and editing the code

- `eva.py` defines the shared alphabet, longest-match tokenizer, and the two deliberately different uncertainty policies.
- `eva_frequencies.py` counts symbols and converts font glyphs to paths.
- `word_positions.py` separates position counting from SVG rendering.
- `word_lengths.py` separates edition cleaning, statistics, CSV export, and chart rendering.
- `templates/` contains the HTML, CSS, and browser-side JavaScript. `config.read_template()` expands local includes at build time; it adds no runtime downloads.
- `assemble_site.py` copies chart downloads, draws the frequency preview, and builds the gallery.
- `provenance.py` attaches the analysis trail and writes the methods page.
- CLI modules use `main()` guards: importing them does not launch processing or parse arguments.

Run focused regression tests after installing the Python dependencies:

```sh
python3 -m unittest discover -s src/processing/tests -v
python3 src/processing/verify_outputs.py
npm --prefix src/processing ci
npm --prefix src/processing run test:reader
```

The readability refactor was checked against the original generated data: JSON values match, and CSV, SVG and PNG outputs are byte-identical. HTML/CSS/JavaScript source whitespace is now formatted for reading. The original OCR script is already written in conventional functions and is kept unchanged to preserve its recorded source fingerprint.

## Reader generation

`reading_text.py` parses the separately supplied Voynichese XML, validates counts and word indices, and emits small per-folio text files plus a source-hash manifest. It does not use the analysis cleaning or ZL3b text. `templates/reading_text.{html,css,js}` implement continuous loading, glyph rendering, folio navigation and printing. The raw XML’s original order is kept; the reader does not invent line/paragraph boundaries from image coordinates. Its license/notice is separate from both the site’s MIT code and the glyph artwork terms. See SOURCE_DATA.md for provenance and the remaining acquisition gap.

The reader supports shareable folio fragments (`#f111r`) and exact local word fragments (`#f1r-word-0`, using the XML word index). Navigation waits for the destination and keeps it aligned while preceding folios load; manual scrolling releases that alignment. Browser back/forward restores previous destinations.

EVA search reads the same per-folio JSON files, including folios not yet displayed. It supports case-insensitive substring or whole-word/phrase matching, context links, highlights, and previous/next results. Phrases never cross folio boundaries. The browser regression suite exercises delayed loading, competing jumps, word fragments, history, and search without requiring the source corpora.

## Linked structural statistics

`structural_statistics.py` computes the new conditional-entropy, pair-matrix and word-trigram comparison against WMF (excluding Tamil). See [STRUCTURAL_STATISTICS.md](STRUCTURAL_STATISTICS.md) for exact definitions, sample limits, boundary handling, shuffle baseline, and paper attribution. All three interactive plots live on one page; the two character-pair views share a comparison selection. The page links back to its script, run hashes, and small derived data files.
