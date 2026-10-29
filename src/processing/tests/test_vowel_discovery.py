"""Independent numerical and corpus invariants for the vowel-class experiment."""

from collections import Counter
import itertools
import json
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vowel_discovery import (
    pair_counts,
    sukhotin,
    expectation,
    fit_hmm,
    hmm_groups,
    prepare,
    is_reference_vowel,
)


class VowelDiscoveryTests(unittest.TestCase):
    def test_published_sukhotin_toy_example(self):
        words = [
            list(word)
            for word in ["saat", "salat", "tal", "last", "stall", "lese", "seele"]
        ]
        symbols = sorted({symbol for word in words for symbol in word})
        counts, pairs = pair_counts(words, symbols)
        self.assertEqual([symbols[i] for i in sukhotin(pairs)], ["a", "e"])
        self.assertEqual(int(pairs.sum()), sum(len(word) - 1 for word in words))
        self.assertEqual(int(counts.sum()), sum(map(len, words)))

    def test_forward_backward_matches_exhaustive_hidden_state_paths(self):
        start = np.array([0.6, 0.4])
        transition = np.array([[0.7, 0.3], [0.2, 0.8]])
        emission = np.array([[0.8, 0.2], [0.1, 0.9]])
        observations = [0, 1, 0]
        likelihood, starts, transitions, emissions = expectation(
            [(np.array([observations]), np.array([2.0]))], start, transition, emission
        )
        paths = []
        for states in itertools.product(range(2), repeat=3):
            p = start[states[0]] * emission[states[0], observations[0]]
            for i in range(1, 3):
                p *= (
                    transition[states[i - 1], states[i]]
                    * emission[states[i], observations[i]]
                )
            paths.append((states, p))
        total = sum(p for _, p in paths)
        self.assertAlmostEqual(likelihood, 2 * np.log(total), places=10)
        expected_starts = np.zeros(2)
        expected_transitions = np.zeros((2, 2))
        expected_emissions = np.zeros((2, 2))
        for states, p in paths:
            weight = 2 * p / total
            expected_starts[states[0]] += weight
            for state, obs in zip(states, observations):
                expected_emissions[state, obs] += weight
            for a, b in zip(states, states[1:]):
                expected_transitions[a, b] += weight
        np.testing.assert_allclose(starts, expected_starts)
        np.testing.assert_allclose(transitions, expected_transitions)
        np.testing.assert_allclose(emissions, expected_emissions)

    def test_hmm_recovers_toy_alternation_and_em_does_not_decrease(self):
        words = [list("baba")] * 30 + [list("kaka")] * 30
        fit = fit_hmm(words, list("abk"), 0, 42)
        self.assertGreater(fit["probabilities"][0], 0.95)
        self.assertLess(fit["probabilities"][1], 0.05)
        self.assertLess(fit["probabilities"][2], 0.05)
        self.assertTrue(
            all(b >= a - 1e-6 for a, b in zip(fit["trace"], fit["trace"][1:]))
        )
        self.assertEqual(fit, fit_hmm(words, list("abk"), 0, 42))

    def test_word_resets_never_create_cross_word_pairs(self):
        counts, pairs = pair_counts([list("a"), list("b")], list("ab"))
        self.assertEqual(int(pairs.sum()), 0)
        groups = hmm_groups([list("a"), list("b")], list("ab"))
        _, starts, transitions, emissions = expectation(
            groups, np.array([0.5, 0.5]), np.ones((2, 2)) * 0.5, np.ones((2, 2)) * 0.5
        )
        self.assertEqual(transitions.sum(), 0)
        self.assertAlmostEqual(starts.sum(), 2)
        self.assertAlmostEqual(emissions.sum(), 2)

    def test_controls_preserve_multisets_and_trim_grouped_units(self):
        source = {
            "vms": True,
            "documents": [["chody", "shaiin", "a"]],
            "folios": ["f1r"],
        }
        native, _, _ = prepare(source, "groups", "whole", "native")
        shuffled, _, _ = prepare(source, "groups", "whole", "shuffle")
        self.assertEqual(
            [Counter(word) for word in native[0]],
            [Counter(word) for word in shuffled[0]],
        )
        inside, _, dropped = prepare(source, "groups", "interior", "native")
        self.assertEqual(inside[0][0], ["o", "d"])
        self.assertEqual(dropped, 1)
        comparison = {"vms": False, "documents": [["café", "æon", "a"]], "folios": []}
        deleted, _, dropped = prepare(comparison, "letters", "whole", "deleted")
        self.assertEqual(deleted, [[["c", "f"], ["n"]]])
        self.assertEqual(dropped, 1)
        self.assertFalse(
            any(
                is_reference_vowel(symbol)
                for doc in deleted
                for word in doc
                for symbol in word
            )
        )


DATA = Path(__file__).resolve().parents[3] / "docs/pages/vowel-discovery/data"


@unittest.skipUnless(
    (DATA / "manifest.json").exists(), "Generated explorer not present"
)
class VowelAssetsTests(unittest.TestCase):
    def test_all_published_scenarios_have_consistent_counts_and_models(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual(len(manifest["scenarios"]), 44)
        for item in manifest["scenarios"]:
            data = json.loads((DATA / item["file"]).read_text())
            n = len(data["symbols"])
            self.assertEqual(len(set(data["symbols"])), n)
            self.assertEqual(len(data["pairs"]), n)
            self.assertTrue(all(len(row) == n for row in data["pairs"]))
            self.assertEqual(
                sum(data["counts"]) - data["words"], sum(map(sum, data["pairs"]))
            )
            self.assertEqual(data["run_hash"], manifest["script_sha256"])
            for method in ("hmm", "sukhotin"):
                self.assertEqual(len(data[method]), n)
                for value in data[method]:
                    self.assertTrue(value is None or 0 <= value <= 1)
                for value in data["bootstrap"][method]:
                    self.assertTrue(
                        0 <= value["A"] <= value["n"] <= manifest["bootstraps"]
                    )
            if item["control"] == "deleted":
                self.assertFalse(any(is_reference_vowel(s) for s in data["symbols"]))
            for example in data["examples"]:
                self.assertTrue(all(s in data["symbols"] for s in example["symbols"]))
