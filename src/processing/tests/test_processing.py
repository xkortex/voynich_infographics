"""Small regression cases for the choices that affect the published statistics."""

import ast
import contextlib
import importlib
import io
from pathlib import Path
import sys
import unittest
from collections import Counter

PROCESSING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROCESSING_DIR))

from eva import readable_spans, readable_words, tokenize
from word_positions import BIN_COUNT, count_positions
from wmf_word_lengths import is_tamil, summarize


class EvaParsingTests(unittest.TestCase):
    def test_grouped_forms_use_longest_match(self):
        self.assertEqual(tokenize("cthiinsh"), ["cth", "i", "i", "n", "sh"])
        self.assertEqual(tokenize("cth", "letters"), ["c", "t", "h"])

    def test_word_and_span_cleaning_are_intentionally_different(self):
        transcription = "<f1r.1,@P0> daiin.cho[a:o]l.shey\n"
        self.assertEqual(readable_words(transcription), ["daiin", "shey"])
        segments, loci, alternatives, rare = readable_spans(transcription)
        self.assertEqual(segments, ["daiin", "cho", "l", "shey"])
        self.assertEqual((loci, alternatives, rare), (1, 1, 0))

    def test_headers_and_comments_are_not_text(self):
        transcription = "# commentary\n<f1r> <! header>\n<f1r.1,@P0> <%>daiin\n"
        self.assertEqual(readable_words(transcription), ["daiin"])


class PositionTests(unittest.TestCase):
    def test_endpoints_and_single_token_midpoint(self):
        counts, histograms = count_positions(["ao", "y"], "groups")
        self.assertEqual(counts, Counter(a=1, o=1, y=1))
        self.assertEqual(histograms["a"][0], 1)
        self.assertEqual(histograms["o"][-1], 1)
        self.assertEqual(histograms["y"][BIN_COUNT // 2], 1)
        self.assertEqual(sum(map(sum, histograms.values())), 3)


class WmfTests(unittest.TestCase):
    def test_tamil_exclusion_does_not_match_similar_language_names(self):
        for language in ["ta", "tam", "Tamil", "ta-IN", "tamil_train"]:
            self.assertTrue(is_tamil(language))
        for language in ["tatar", "talysh", "taq", "data"]:
            self.assertFalse(is_tamil(language))

    def test_weighted_median_modes_and_population_deviation(self):
        result = summarize(Counter({1: 2, 3: 2}))
        self.assertEqual(result["words"], 4)
        self.assertEqual(result["median"], 2)
        self.assertEqual(result["modes"], [1, 3])
        self.assertEqual(result["stddev_population"], 1)
        self.assertEqual(result["pct_length_1_2"], 50)


class ImportSafetyTests(unittest.TestCase):
    def test_commands_do_not_parse_arguments_or_print_on_import(self):
        # An import should work even with argv that none of our CLIs recognize.
        original_arguments = sys.argv
        try:
            sys.argv = ["test", "--not-a-cli-invocation"]
            for name in [
                "assemble_site",
                "build_all",
                "check_sources",
                "eva_frequencies",
                "fetch_sources",
                "provenance",
                "verify_outputs",
                "word_lengths",
                "word_positions",
                "wmf_word_lengths",
                "ocr_fullres_mac",
            ]:
                with self.subTest(module=name), contextlib.redirect_stdout(
                    io.StringIO()
                ) as output:
                    importlib.reload(importlib.import_module(name))
                    self.assertEqual(output.getvalue(), "")
        finally:
            sys.argv = original_arguments


if __name__ == "__main__":
    unittest.main()
