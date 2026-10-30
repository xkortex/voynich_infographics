"""Boundary and normalization invariants for the displayed Markov models."""

from pathlib import Path
import sys
import json
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from markov_transitions import text_runs, transition_counts, lexicon_counts


class MarkovTests(unittest.TestCase):
    def test_spaces_are_observed_units_and_context_order_matters(self):
        runs = [list("a b"), list("a c"), list("a b")]
        data = transition_counts(runs)
        index = {unit: i for i, unit in enumerate(data["alphabet"])}
        a, space, b, c = [index[x] for x in ("a", " ", "b", "c")]
        self.assertEqual(data["starts"], [[a, 3]])
        self.assertEqual(data["first"][str(a)], [[space, 3]])
        self.assertEqual(data["first"][str(space)], [[b, 2], [c, 1]])
        self.assertEqual(data["second"][f"{a},{space}"], [[b, 2], [c, 1]])
        self.assertNotIn(f"{space},{a}", data["second"])
        self.assertEqual(data["start_pairs"][str(a)], [[space, 3]])
        self.assertEqual(data["first_total"], 6)
        self.assertEqual(data["second_total"], 3)

    def test_loci_and_unknown_words_break_runs_without_invented_spaces(self):
        text = """# not text
<f1r> <! $Q=A>
<f1r.1,@P0> <%>a.b.cho?y.c.d<$>
<f1r.2,+P0> e.f
<f1r.3,+P0> g.@123;.h
"""
        runs = list(text_runs(text, "letters"))
        self.assertEqual(runs, [list("a b"), list("c d"), list("e f"), ["g"], ["h"]])
        data = transition_counts(runs)
        ids = {u: i for i, u in enumerate(data["alphabet"])}
        self.assertNotIn(str(ids["b"]), data["first"])
        self.assertEqual(data["frequencies"][ids[" "]], 3)

    def test_grouped_mode_does_not_split_composites(self):
        text = "<f1r.1,@P0> chody.shaiin"
        grouped = list(text_runs(text, "groups"))
        self.assertEqual(
            grouped, [["ch", "o", "d", "y", " ", "sh", "a", "i", "i", "n"]]
        )
        letters = list(text_runs(text, "letters"))
        self.assertEqual("".join(letters[0]), "chody shaiin")
        self.assertEqual("".join(grouped[0]), "chody shaiin")

    def test_lexicon_counts_complete_source_words_and_folio_examples(self):
        text = "<f1r.1,@P0> daiin.chody.cho?y\n<f2v.1,@P0> daiin.shaiin"
        words = {word: (count, folio) for word, count, folio in lexicon_counts(text)}
        self.assertEqual(
            words, {"daiin": (2, "f1r"), "chody": (1, "f1r"), "shaiin": (1, "f2v")}
        )
        self.assertNotIn("cho", words)

    def test_no_fictional_successor_or_empty_run_start(self):
        data = transition_counts([[], ["a"], ["b"]])
        self.assertEqual(data["runs"], 2)
        self.assertEqual(data["first"], {})
        self.assertEqual(data["second"], {})
        self.assertEqual(data["start_pairs"], {})


DATA = Path(__file__).resolve().parents[3] / "docs/pages/markov-transitions/data"


@unittest.skipUnless((DATA / "manifest.json").exists(), "Generated model assets absent")
class MarkovAssetsTests(unittest.TestCase):
    def test_all_published_sparse_rows_are_positive_and_normalize(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual(len(manifest["sources"]), 4)
        for source in manifest["sources"]:
            vocabulary = json.loads((DATA / source["lexicon"]).read_text())
            self.assertEqual(vocabulary["input_sha256"], source["sha256"])
            self.assertEqual(vocabulary["script_sha256"], manifest["script_sha256"])
            self.assertEqual(len(vocabulary["words"]), source["lexicon_types"])
            self.assertEqual(
                len(vocabulary["words"]), len({row[0] for row in vocabulary["words"]})
            )
            self.assertTrue(
                all(
                    count > 0 and folio.startswith("f")
                    for _, count, folio in vocabulary["words"]
                )
            )
            for file in source["files"].values():
                model = json.loads((DATA / file).read_text())
                n = len(model["alphabet"])
                self.assertIn(" ", model["alphabet"])
                self.assertEqual(sum(model["frequencies"]), model["units"])
                self.assertEqual(
                    sum(count for _, count in model["starts"]), model["runs"]
                )
                self.assertEqual(model["first_total"], model["units"] - model["runs"])
                self.assertEqual(
                    model["first_total"],
                    sum(count for row in model["first"].values() for _, count in row),
                )
                self.assertEqual(
                    model["second_total"],
                    sum(count for row in model["second"].values() for _, count in row),
                )
                self.assertEqual(model["script_sha256"], manifest["script_sha256"])
                self.assertEqual(model["input_sha256"], source["sha256"])
                for field in ("first", "second", "start_pairs"):
                    for row in model[field].values():
                        self.assertEqual(len(row), len({unit for unit, _ in row}))
                        total = sum(count for _, count in row)
                        self.assertTrue(
                            all(0 <= unit < n and count > 0 for unit, count in row)
                        )
                        self.assertAlmostEqual(
                            sum(count / total for _, count in row), 1
                        )
