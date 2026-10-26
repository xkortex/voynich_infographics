# Voynich infographics

A collection of standalone, interactive Voynich manuscript charts and corpus comparisons.

## AI Usage Disclaimer

🙋 Hi there, human here. This is, like many folks suddenly entering this space, a passion project for me. I would not have the time or mental energy to dig in as deeply as I can now without generative AI assistance. My chops are in data science and scientific research, and I've been hacking on ML since before Siraj got cancelled, so I am well aware of the limitations and hazards of GenAI. My goal here is to not use AI to come up with any conclusions or generate any graphics directly, rather I am creating scrutable tooling and pipelines with coding assistance, that process the data in a fully deterministic and reproducible way. I understand genAI usage in the broad field of scientific research is quite contentious, and particularly the genre of vibeslop Voynich "theories" is a blight on this topic. I try to review as much of the output as I can, but again, passion project. If I find something particularly juicy, rest assured I'll be pursuing the full peer-reviewed publication process. 

If you see an error, hallucination, or other troubling output, please submit an Issue. I'm not accepting issues of the nature "I can't get it to run" (skill issue) or PRs unless it's something my stretched-thin attention can find value in immediately. No slop. I barely have spoons as is. 


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
