# Character pairs and word triples

This page combines three newly computed graphics: (1) h₂ versus observed character inventory; (2) two linked pair matrices; (3) exact repeated-word-trigram coverage versus prefix-3 or suffix-3 coverage. The first two describe the same pair counts. They are inspired by figures 4 and 6 of Bowern & Lindemann (2021), not reproductions of that paper’s data or values. The trigram analysis is separate, following the exploratory repeated-window definition confirmed by the project owner.

## Recompute or edit

```sh
python3 src/processing/structural_statistics.py \
  --wmf "$HOME/bots/ChatGPT/corpora/wmf/wmf.csv" \
  --vms data/local/transcription.txt

# Presentation-only changes do not need another WMF scan:
python3 src/processing/structural_statistics.py --page-only
```

The script writes `docs/pages/structural-statistics/`. `data/summary.csv` has flat summary values. `data/summary.json` is the compact scatter dataset. Each `data/pairs/<corpus>.json` has both boundary-mode matrices and complete per-corpus summary counts under `statistics`. `data/methods.json` records input-byte hashes, sample limits, normalization and seed. No corpus text is emitted. Inputs remain outside Git. `build_all.py --structural-statistics` optionally includes this analysis; ordinary gallery rebuilds retain the link without recomputing it.

## Sampling and normalization

- WMF: `text` only, one row/fragment per document; language blocks must be contiguous. Exclude Tamil labels using the existing `is_tamil` function. All 339 remaining language samples are included.
- Per language, take the first up to **32,000 words** in source order, including a partial final fragment if necessary. The first-sample choice is deterministic, not randomized; do not assume it is representative of an entire language. Under-length samples are flagged.
- WMF normalization: lowercase, then NFC. Unicode letters and attached combining marks stay in tokens. Everything else separates tokens. No linguistic word segmenter is applied; languages without consistent word spaces need separate interpretation. Prefix/suffix counts are codepoints, not grapheme clusters.
- VMS: ZL3b `P` paragraph loci only; group by folio, excluding labels. The existing readable-word parser omits uncertain/extended words. **Omissions close gaps**, so surviving words become neighbors in the cleaned sequence. These windows are not assertions of original adjacency across an omitted word. The paper used different transcriptions and samples.
- Reset sequences at WMF document/fragment boundaries and VMS folio boundaries. Never create a cross-document bigram or three-word window. VMS physical line breaks are not interpreted as sentence boundaries.

## Character statistics

For each view, cap the sequence at **200,000 units**. In the default view words are separated by one literal space, counted as a symbol. The alternate view deletes spaces within documents, thereby joining neighboring words; document resets still apply. VMS may use individual EVA letters or longest-match cfh/ckh/cph/cth/ch/sh groups. This changes entropy units; it does not change the EVA word strings in the third graphic.

For pair counts c(a,b), outgoing(a)=Σ_b c(a,b), and N=Σ_ab c(a,b):

`h2 = -Σ_ab [c(a,b)/N] × log2[c(a,b)/outgoing(a)]`

Zero cells contribute zero. This is a plug-in estimate without smoothing or finite-sample correction. H1 is also recorded from individual-unit frequencies. The observed inventory includes all characters in the capped sample, including rare foreign-script loanwords and spaces where enabled; it is not a phoneme inventory or a filtered native alphabet. This explains the difference from a paper-style inventory plot.

The displayed matrix shows at most **28 symbols**, ordered by marginal frequency independently for each corpus. It uses the full outgoing counts and N for probabilities; cropping therefore does not renormalize rows. Measures are conditional probability c(a,b)/outgoing(a), joint pair frequency c(a,b)/N, and contribution `-[c(a,b)/N] log2[c(a,b)/outgoing(a)]`. Both panels use identical fixed color scales; joint/contribution views label clipping thresholds. Every matrix cell exposes its exact count and probabilities. Tab into a matrix, then use arrow keys to move between cells.

## Word-trigram coverage

A trigram is a window of **three words**, not three characters. Count overlapping windows within each document. For each distinct triple with frequency c, coverage is:

`100 × Σ_{triples with c≥2} c / Σ_{all triples} c`

This counts every occurrence of a repeated triple, including its first occurrence. It is not the share of distinct trigram types that repeat, or the share of occurrences after subtracting one per type. Numerators, denominators and type counts are all retained in each corpus’s full statistics.

`native`: original normalized word strings.

`prefix3`: replace every word with `word[:3]`.

`suffix3`: replace every word with `word[-3:]`.

Shorter words stay unchanged. There are no character edits, search-based alignments, or learned repairs. These are many-to-one mappings; they can only preserve or raise repeated-window coverage. Higher coverage after mapping is not by itself evidence for morphology or meaningful syntax.

Shuffle words independently within each source document with seed **20261026**, using the same shuffled order for all three mappings. This preserves words, frequencies and document lengths and provides a descriptive collision baseline. It is one shuffle, not a confidence interval or significance test.

## Baseline from this run

| VMS EVA paragraph sample | Value |
|---|---:|
| Words / folio documents | 32,000 / 204 |
| Three-word windows | 31,592 |
| Repeated native occurrences | 326 (1.0319%) |
| Prefix-3 repeated occurrences | 7,679 (24.3068%) |
| Suffix-3 repeated occurrences | 11,974 (37.9020%) |
| Shuffled prefix-3 coverage | 20.4799% |
| Shuffled suffix-3 coverage | 35.8350% |
| Letter h₂, with spaces | 2.11133 bits |
| Grouped-form h₂, with spaces | 2.23895 bits |

In this run the VMS letter sample is below all 339 WMF samples on native three-word coverage and on character h₂. This is a description of these samples and these tokenization rules, not a universal test of language, a script identification, or a decipherment. Genre, Wikipedia duplication/boilerplate, sample selection, sparse inventories and orthography remain confounds.

## References and rights

- Bowern, Claire L. & Luke Lindemann. 2021. *The Linguistics of the Voynich Manuscript*. Annual Review of Linguistics 7:285–308. https://doi.org/10.1146/annurev-linguistics-011619-030613 . Figures 4 and 6 motivate the pair-based views. No published image or paper text is distributed.
- Lindemann, Luke & Claire Bowern. 2020. *Character Entropy in Modern and Historical Texts: Comparison Metrics for an Undeciphered Manuscript*. https://arxiv.org/abs/2010.14697 . Additional explanation of conditional entropy and bigram matrices.
- Carlos Quesada, *Wikipedia Multilingual Fragments*: https://doi.org/10.5281/zenodo.15696122 . The bundled README states CC BY-SA 4.0. Aggregate counts here are derived from that dataset; keep this attribution and consult upstream terms when reusing them.
- René Zandbergen & Gabriel Landini, ZL3b-n.txt: https://voynich.nu/data/ZL3b-n.txt . Transliterations offered as CC0 by voynich.nu. Exact bytes are fingerprinted in the run configuration.
