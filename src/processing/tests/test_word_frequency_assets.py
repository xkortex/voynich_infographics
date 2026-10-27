"""Check the actual published mappings, not just tiny algorithm fixtures."""

from collections import Counter
import csv
import json
from pathlib import Path
import re
import unittest

DATA = Path(__file__).resolve().parents[3] / "docs/pages/word-frequencies/data"


@unittest.skipUnless(
    (DATA / "manifest.json").exists(), "Generated frequency page is not present"
)
class PublishedFrequencyTests(unittest.TestCase):
    def test_all_mappings_preserve_counts_and_match_saved_summaries(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        with (DATA / "summary.csv").open() as stream:
            summaries = {
                (row["source"], row["treatment"], row["population"]): row
                for row in csv.DictReader(stream)
            }
        for source in manifest["sources"]:
            vocabulary = [
                row
                for shard in source["shards"]
                for row in json.loads((DATA / shard).read_text())
            ]
            self.assertEqual(sum(row[1] for row in vocabulary), source["tokens"])
            self.assertEqual(len({row[0] for row in vocabulary}), len(vocabulary))
            for treatment, filename in source["maps"].items():
                mapping = json.loads((DATA / filename).read_text())
                self.assertEqual(len(mapping["map"]), len(vocabulary))
                self.assertTrue(
                    all(0 <= index < len(mapping["keys"]) for index in mapping["map"])
                )
                for population in ("basic", "all"):
                    counts = Counter()
                    for row, index in zip(vocabulary, mapping["map"]):
                        if population == "all" or re.fullmatch("[a-vxyz]+", row[0]):
                            counts[mapping["keys"][index]] += row[1]
                    saved = summaries[source["id"], treatment, population]
                    self.assertEqual(sum(counts.values()), int(saved["tokens"]))
                    self.assertEqual(
                        sum(counts.values()),
                        source["tokens" if population == "all" else "basic_tokens"],
                    )
                    self.assertEqual(len(counts), int(saved["families"]))
                    self.assertEqual(
                        sum(count == 1 for count in counts.values()),
                        int(saved["singleton_families"]),
                    )

    def test_saved_morfessor_segments_reconstruct_the_word_and_family(self):
        manifest = json.loads((DATA / "manifest.json").read_text())
        for source in manifest["sources"]:
            vocabulary = [
                row
                for shard in source["shards"]
                for row in json.loads((DATA / shard).read_text())
            ]
            for treatment in ("morf0.1", "morf1", "morf10"):
                mapping = json.loads((DATA / source["maps"][treatment]).read_text())
                keys = {
                    row[0]: mapping["keys"][index]
                    for row, index in zip(vocabulary, mapping["map"])
                }
                checked = set()
                for shard in sorted(
                    (DATA / source["id"]).glob(treatment + "-segments-*.json")
                ):
                    for word, segments in json.loads(shard.read_text()):
                        self.assertEqual("".join(segments), word)
                        self.assertEqual(max(segments, key=len), keys[word])
                        checked.add(word)
                self.assertEqual(len(checked), source["basic_types"])
