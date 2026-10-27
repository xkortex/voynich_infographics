"""Check comparison tokenization and within-word Unicode letter positions."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from word_positions import edition_positions
from word_lengths import edition_word_lengths


class ComparisonPositionTests(unittest.TestCase):
    def test_historical_letters_accents_and_apostrophes(self):
        text = "Þe café l'amour æon"
        result = edition_positions(text)
        stats = result["statistics"]["letters"]
        self.assertEqual(result["word_count"], 4)
        self.assertEqual(stats["total"], sum(edition_word_lengths(text)))
        self.assertEqual(stats["counts"]["þ"], 1)
        self.assertEqual(stats["hist"]["þ"][0], 1)
        self.assertEqual(stats["counts"]["é"], 1)
        self.assertEqual(stats["hist"]["é"][-1], 1)
        self.assertNotIn("'", stats["counts"])
        self.assertEqual(
            sum(sum(bins) for bins in stats["hist"].values()), stats["total"]
        )

    def test_wrapper_ocr_cleaning_and_single_letter_midpoint(self):
        text = "preface\n*** START OF TEST ***\na\n===== PDF PAGE 1 =====\nam-\nor\nDigitized by Google\n*** END OF TEST ***\nfooter"
        result = edition_positions(text, True)
        self.assertEqual(result["word_count"], 2)
        self.assertEqual(result["statistics"]["letters"]["total"], 5)
        self.assertEqual(result["statistics"]["letters"]["hist"]["a"][7], 1)
