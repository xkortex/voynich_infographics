# Voynich infographics

A collection of standalone, interactive Voynich manuscript charts and corpus comparisons.

## Site layout

The complete static site is in `docs/`. No build step, package installation, API keys, or external runtime dependencies are required.

```text
docs/
  index.html                     # Gallery / directory of all charts
  credits.html                   # Source and third-party licensing notes
  assets/                        # Shared styles and preview images
  pages/
    eva-frequencies/
      index.html
      downloads/                 # Original standalone HTML
    word-positions/
      index.html
      downloads/                 # Standalone HTML, PNG, SVG
    word-lengths/
      index.html
      downloads/                 # Standalone HTML, PNG, SVG, CSV
```

## Preview

From the repository root:

```sh
python3 -m http.server 8000 --directory docs
```

Open http://localhost:8000. All site links are relative, so the same directory works below a repository URL prefix.

## GitHub Pages

Configure this repository’s Pages publishing source to serve the `docs/` directory on the branch containing these files. The site is buildless. This setup does not itself push the repository or enable public hosting.

## Add another infographic

1. Create `docs/pages/<short-name>/index.html`.
2. Put downloadable copies/data under that page’s `downloads/` directory.
3. Add a preview under `docs/assets/` and an entry in `docs/index.html`.
4. Link back to `../../index.html`. Use relative URLs throughout.
5. Include the source, counting units, cleaning assumptions, and asset credits with the page.

## Included charts

- EVA symbol frequencies: grouped forms and individual EVA letter counts; sorting, linear/log bars, and CSV export.
- Word-position distributions: positional profiles, grouped/letter views, and independent/shared vertical scales.
- Word-length comparison: VMS, Forme of Cury, and Corpus orationum; line/histogram views and two EVA counting conventions.

The VMS charts use Zandbergen–Landini 3b. Different cleaning rules are documented within each chart. Comparison editions contain editorial material and OCR noise.

## Licensing

The repository’s MIT license applies to original site code. Third-party materials retain their own terms. In particular, Gabriel Landini’s EVA font-derived glyph outlines are **not** MIT-licensed; consult `docs/credits.html` and the linked source terms before reuse. The corpus text files are not included.

## Processing and provenance

All chart generators, the static-site assembler, and the auxiliary WMF script are in [`src/processing/`](src/processing/). Start with the [reproduction guide](src/processing/README.md), [source acquisition notes](src/processing/SOURCE_DATA.md), and [input fingerprints](src/processing/sources.json). Each chart links directly to its generator and these notes. Input corpora/font binaries are local-only and ignored by Git.

Compact, reviewable [derived baseline results](results/baseline/) are tracked separately from the ignored source corpora and build intermediates.
