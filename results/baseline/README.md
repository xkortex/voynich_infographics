# Derived baseline results

Compact text artifacts from the original chart inputs, regenerated with the checked-in processing scripts on 26 October 2026. No source corpus or font data is included.

- `counts.json`: per-symbol letter/grouped frequencies from eva_frequencies.py.
- `positions.json`: per-symbol positional-bin counts and totals from word_positions.py (15 bins).
- `length_stats.json`: full-edition and VMS summary statistics from word_lengths.py.
- `word_length_comparison.csv`: exact integer word-length counts and within-corpus percentages.
- `input_hashes.json`: SHA-256 fingerprints of the actual input bytes used for this rebuild.

See ../../src/processing/README.md for cleaning and counting rules and ../../src/processing/SOURCE_DATA.md for acquisition and rights notes. The corpus titles, not source filenames or host-specific paths, identify the text comparisons.

`sha256_bytes` in length_stats.json hashes original file bytes; `sha256_normalized_text` hashes UTF-8 re-encoding after Python read_text() normalizes line endings. sources.json and input_hashes.json always refer to the original bytes. Neither kind of hash establishes copyright permission.

To refresh these results, rebuild to generated/, run verify_outputs.py, and copy the five named text artifacts here. Inspect numerical differences before committing. Large text outputs, full corpora, PDF/font/image binaries and node_modules do not belong in this folder.
