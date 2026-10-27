"""Meaningful invariants for the word-family frequency experiment."""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from word_frequencies import parse_words, collapse_rare, trim_middle, morfessor_families


class WordFrequencyTests(unittest.TestCase):
    def test_metadata_is_not_text_and_marked_words_are_not_fragmented(self):
        counts, examples = parse_words("""# comment
<f1r> <! $Q=A>
<f1r.1,@P0> <%>daiin.[ch:sh]ol.cho?y.abc<->def<$>
<f2v.1,+P0> daiin,or<!remark>
""")
        self.assertEqual(
            counts,
            Counter(
                {"daiin": 2, "[ch:sh]ol": 1, "cho?y": 1, "abc": 1, "def": 1, "or": 1}
            ),
        )
        self.assertEqual(examples["daiin"], "f1r")

    def test_rare_collapse_uses_original_counts_and_no_chaining(self):
        counts = Counter({"dain": 1, "daiin": 8, "dan": 9, "din": 1, "d": 1, "x": 1})
        mapping = collapse_rare(counts, 1)
        self.assertEqual(mapping["dain"], "dan")
        self.assertEqual(mapping["din"], "dan")
        self.assertEqual(mapping["d"], "d")  # Cannot follow a rare intermediary.
        self.assertEqual(mapping["daiin"], "daiin")
        self.assertEqual(mapping["x"], "x")
        aggregated = Counter()
        for word, count in counts.items():
            aggregated[mapping[word]] += count
        self.assertEqual(sum(aggregated.values()), sum(counts.values()))

    def test_edit_ties_are_lexical_and_transposition_is_two_edits(self):
        counts = Counter({"bat": 1, "cat": 5, "hat": 5, "ab": 1, "ba": 8})
        mapping = collapse_rare(counts, 1)
        self.assertEqual(mapping["bat"], "ba")  # Most frequent eligible target.
        self.assertEqual(
            collapse_rare(Counter({"bat": 1, "cat": 5, "hat": 5}), 1)["bat"], "cat"
        )
        self.assertEqual(mapping["ab"], "ab")

    def test_infix_short_words_never_form_an_empty_superfamily(self):
        self.assertEqual(trim_middle("daiin", 1), "aii")
        self.assertEqual(trim_middle("daiin", 2), "i")
        self.assertNotEqual(trim_middle("ab", 1), trim_middle("cd", 1))
        self.assertEqual(trim_middle("a", 2), "~short:a")


if __name__ == "__main__":
    unittest.main()
