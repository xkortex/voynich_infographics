"""Independent small examples for entropy and repeated-window definitions."""

import math
import contextlib
import io
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from structural_statistics import (
    character_pairs,
    normalize_words,
    repeated_trigrams,
    sample_documents,
)

from structural_statistics import build_statistics


class PairStatisticsTests(unittest.TestCase):
    def test_deterministic_next_character_has_zero_entropy(self):
        result = character_pairs([["ababab"]], 100, boundaries=False)
        self.assertEqual(result["h2"], 0)
        self.assertEqual(result["pair_count"], 5)

    def test_two_equally_likely_followers_give_one_bit(self):
        result = character_pairs([["aa"], ["ab"], ["ba"], ["bb"]], 100)
        self.assertAlmostEqual(result["h2"], 1)

    def test_documents_do_not_create_extra_pairs(self):
        result = character_pairs([["aa"], ["bb"]], 100, boundaries=False)
        self.assertEqual(result["pair_count"], 2)
        self.assertNotIn(("a", "b"), result["pairs"])

    def test_explicit_space_symbol_and_unit_cap(self):
        result = character_pairs([["ab", "cd"]], 4)
        self.assertEqual(result["units"], 4)
        self.assertEqual(result["pair_count"], 3)
        self.assertEqual(result["pairs"][("b", " ")], 1)
        self.assertEqual(result["pairs"][(" ", "c")], 1)


class TrigramCoverageTests(unittest.TestCase):
    def test_every_repeated_occurrence_counts_including_first(self):
        result = repeated_trigrams([["a", "b", "c", "a", "b", "c"]])
        self.assertEqual(result["windows"], 4)
        self.assertEqual(result["repeated_occurrences"], 2)
        self.assertEqual(result["percent"], 50)

    def test_prefix_and_suffix_mappings_are_not_deletions(self):
        prefix_words = [["abcx", "defx", "ghix", "abcy", "defy", "ghiy"]]
        suffix_words = [["xabc", "xdef", "xghi", "yabc", "ydef", "yghi"]]
        self.assertEqual(repeated_trigrams(prefix_words)["percent"], 0)
        self.assertEqual(repeated_trigrams(prefix_words, "prefix3")["percent"], 50)
        self.assertEqual(repeated_trigrams(suffix_words, "suffix3")["percent"], 50)

    def test_document_boundary_is_not_a_trigram(self):
        result = repeated_trigrams([["a", "b"], ["c", "a", "b", "c"]])
        self.assertEqual(result["windows"], 2)
        self.assertEqual(result["percent"], 0)

    def test_empty_window_set_is_not_reported_as_zero_percent(self):
        self.assertIsNone(repeated_trigrams([["a", "b"]])["percent"])

    def test_sample_cap_keeps_a_partial_final_document(self):
        self.assertEqual(
            sample_documents([["a", "b"], ["c", "d", "e"]], 4), [["a", "b"], ["c", "d"]]
        )

    def test_unicode_marks_stay_attached_but_digits_separate(self):
        self.assertEqual(normalize_words("A\u0301 Z9 हिंदी"), ["á", "z", "हिंदी"])


class PipelineFixtureTests(unittest.TestCase):
    def test_saved_counts_and_compact_summary_agree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wmf = root / "wmf.csv"
            wmf.write_text(
                'language,text\nen,"a b c a b c"\nta,"ignored Tamil words"\n'
            )
            vms = root / "vms.txt"
            vms.write_text("<f1r> <! $L=A>\n<f1r.1,@P0> a.b.c.a.b.c\n")
            output = root / "data"
            options = SimpleNamespace(
                wmf=wmf,
                vms=vms,
                output_dir=output,
                max_words=6,
                max_units=100,
                matrix_size=3,
            )
            with contextlib.redirect_stdout(io.StringIO()):
                build_statistics(options)
            summary = json.loads((output / "summary.json").read_text())
            methods = json.loads((output / "methods.json").read_text())
            self.assertEqual(methods["wmf_languages"], 1)
            self.assertEqual(methods["excluded_tamil_rows"], 1)
            self.assertEqual(len(summary), 3)
            for row in summary:
                self.assertEqual(row["native"]["percent"], 50)
                self.assertEqual(set(row["native"]), {"percent"})
                detail = json.loads((output / row["matrix_file"]).read_text())
                self.assertEqual(
                    detail["statistics"]["native"]["repeated_occurrences"], 2
                )


if __name__ == "__main__":
    unittest.main()
