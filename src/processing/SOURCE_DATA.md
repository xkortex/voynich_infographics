# Obtaining the inputs; provenance and rights

Input texts and the font binary are **not hosted in this repository**. Put authorized local copies in `data/local/`, which is ignored by Git, or use `--data-dir /another/private/folder`. `sources.json` records the exact original file-byte SHA-256 hashes and sizes, not the texts themselves. File hashes identify bytes; they do not prove a license or source chain.

The reading edition is a separate exception: its small Apache-attributed derived per-folio text files are published for continuous reading; see section 6.

## 1. Zandbergen–Landini VMS transliteration

- Primary documentation: https://voynich.nu/transcr.html
- Input: https://voynich.nu/data/ZL3b-n.txt (ZL3b, 13 May 2025)
- Exact copy originally retrieved from: https://raw.githubusercontent.com/Aspect-Research/voynich-autoexploration/master/data/transcriptions/eva_zl3b.txt
- Save as `transcription.txt`.
- voynich.nu states that its transliterations are CC0: https://voynich.nu/roadmap.html#licences . See the page’s licences/copyright section if the anchor changes. This applies to the transliteration, not automatically to fonts or scan imagery.

## 2. EVA glyph artwork

- Gabriel Landini, EVA2.ttf (2025): https://voynich.nu/Fonts/EVA2.ttf
- Source credit and terms: https://voynich.nu/roadmap.html
- Save an authorized local copy as `EVA2.ttf`.

The existing charts contain paths derived from this font. The source states permission for display on that site or private use and discusses commercial restrictions; this is **not a clear general redistribution license** for another public site. No font binary is bundled here. Do not interpret the site’s MIT license, attribution, or noncommercial intent as proof of permission for derived glyph redistribution. Public reuse of those outlines remains a rights question to resolve with the relevant rights holder/source, or replace them with independently licensed artwork. This documentation records the issue; it does not establish clearance.

## 3. Forme of Cury

- Samuel Pegge edition, Project Gutenberg ebook **8102**: https://www.gutenberg.org/ebooks/8102
- Plain text: https://www.gutenberg.org/cache/epub/8102/pg8102.txt
- Save as `forme_of_cury.txt`.
- Gutenberg lists the ebook as public domain in the USA. The ebook includes its own terms and a reminder to check local law outside the USA. Retain the source notice in your private input. We publish aggregate statistics, not the ebook file.

## 4. Corpus orationum, CCSL 160, A–C

- Source scan URL (confirmed by user on 26 October 2026): https://azbyka.ru/otechnik/assets/uploads/CCSL/CCSL_160_Corpus_orationum_A-C.pdf
- Input used: user-supplied `CCSL_160_Corpus_orationum_A-C_fullres_ocr.txt`.
- Save as `orationum_ocr.txt`.
- The user confirms (26 October 2026) that an assistant-provided script produced the OCR using **Tesseract and Poppler**.
- The user supplied the identified script, preserved unchanged as [`ocr_fullres_mac.py`](ocr_fullres_mac.py). Its SHA-256 is recorded in sources.json.
- Its defaults are: all PDF pages, **400 DPI**, grayscale PNG rendering through `pdftoppm`, **lat+fra+eng**, Tesseract **OEM 1 / PSM 3**, two workers and OMP_THREAD_LIMIT=1. Page results are cached and reused unless `--force` is passed.
- These defaults are known from the script, not a surviving run log. The actual invocation/overrides, source PDF hash and installed Poppler/Tesseract/language-model versions are still unrecorded. Cached pages can originate from earlier settings; use a fresh workdir or `--force` after changing settings.
- Example reproducing the script’s defaults with explicit options (not a claim to recover the original command):

  ```sh
  python3 src/processing/ocr_fullres_mac.py /private/path/CCSL_160_Corpus_orationum_A-C.pdf --dpi 400 --workers 2 --lang lat+fra+eng --psm 3 --output data/local/orationum_ocr.txt --workdir /private/path/ocr_pages
  ```

- Install Poppler, Tesseract and the Latin/French/English language data separately. On macOS the script suggests `brew install poppler tesseract tesseract-lang`. Record their versions and PDF hash with new OCR runs. Fresh OCR may differ from the existing input fingerprint even with the same defaults.
- Obtain the edition/scan through an authorized library, publisher or other source. We have not established permission to mirror the modern edition, scan, OCR or editorial apparatus. OCR tool licensing does not grant rights in the input book. No original text is redistributed here.

## 5. WMF (auxiliary analysis)

- Wikipedia Multilingual Fragments, Carlos Quesada: https://doi.org/10.5281/zenodo.15696122
- Obtain the dataset from its record and use the extracted `wmf.csv`, not the derived TF-IDF/ngram tables.
- The bundled dataset README states CC BY-SA 4.0. This note records that assertion; inspect the actual record and attribution/share-alike terms before redistributing data. WMF itself is not included here and is not an input to the three existing charts.
- Example local run: `python3 src/processing/wmf_word_lengths.py "$HOME/bots/ChatGPT/corpora/wmf" --out generated/wmf`.

## Optional download helper

```sh
python3 src/processing/fetch_sources.py --data-dir data/local
# If the primary VMS download is unavailable, explicitly select the recorded mirror:
python3 src/processing/fetch_sources.py --data-dir data/local --vms-mirror
python3 src/processing/check_sources.py --data-dir data/local
```

The helper fetches only the public VMS text and Gutenberg text; it does not fetch a font, Orationum, or WMF. It preserves existing inputs and prints a warning for bytes that differ from the original hashes. A failure is reported rather than silently switching sources. Upstream content and line endings can change; keep the printed hashes with your analysis.

## 6. Voynichese reading edition XML

The user supplied `voynichese_enhanced_transcription/` (225 XML folios). Every input file carries “Copyright (C) 2014 The Voynichese Project” and an Apache License 2.0 notice. The new reading page publishes a transformed edition with attribution and the license; it is a deliberate exception to the analysis workflow’s local-only text policy. No original XML or image geometry is committed.

Project: https://github.com/voynichese/voynichese . Transcription credits: https://github.com/voynichese/voynichese/blob/wiki/CreditsAndCopyright.md (including Takeshi Takahashi and Jorge Stolfi). The project documents its Apache-2.0 enhanced transcription download at https://www.voynichese.com/1/data/folio/voynichese_data.zip (see https://github.com/voynichese/voynichese/blob/wiki/DataSets.md). On 26 October 2026 all 225 XML files in that archive were verified byte-for-byte against the supplied local files. The archive SHA-256 was `402d99ca8191ae53a4f25912ee0af0a7e6b6d9a3714b2beaf86404a27d5b7ad5`. Compare file hashes in `docs/pages/reading-text/source-manifest.json` to identify this exact edition.

Word links use the live viewer’s `#/FOLIO/exa:EVA` fragment syntax, verified against its parser and a live f1r/fachys link on 26 October 2026. The final numeric fragment means page scroll offset, not the XML word index. The query selects all exact-spelling matches on a folio, not a unique occurrence.

## Word frequency comparison inputs

The additional IT2a, VT0e and RF1b basic-EVA inputs are acquired directly from Voynich.nu and kept local. ZL3b is the same resource used by the earlier charts. See [WORD_FREQUENCIES.md](WORD_FREQUENCIES.md) for exact acquisition URLs, related-source limitations and raw/derived separation; the published page includes SHA-256 fingerprints for every input.
