"""Check historical aggregates after rebuilding with the original chart inputs."""

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from config import ROOT

EXPECTED_SYMBOL_TOTALS = {"groups": 173512, "letters": 193266}
EXPECTED_POSITION_TOTALS = {"groups": 169172, "letters": 188466}
EXPECTED_WORD_TOTALS = {
    "Forme of Cury": 43765,
    "Corpus orationum": 104081,
    "VMS · grouped EVA": 37126,
}


def check_totals(output_dir):
    """Ensure each independent counting stage still matches the historical baseline."""
    counts = json.loads((output_dir / "counts.json").read_text())
    for mode, expected in EXPECTED_SYMBOL_TOTALS.items():
        actual = sum(item["count"] for item in counts[mode])
        assert actual == expected, f"{mode} symbol total: {actual} != {expected}"
    positions = json.loads((output_dir / "positions.json").read_text())
    for mode, expected in EXPECTED_POSITION_TOTALS.items():
        assert positions[mode]["total"] == expected, f"{mode} position total differs"
        assert sum(map(sum, positions[mode]["hist"].values())) == expected
    summaries = json.loads((output_dir / "length_stats.json").read_text())
    for corpus, expected in EXPECTED_WORD_TOTALS.items():
        assert summaries[corpus]["tokens"] == expected, f"{corpus} word total differs"


def check_percentage_sums(csv_path):
    """Each corpus distribution must be normalized independently to 100 percent."""
    totals = defaultdict(float)
    with csv_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            totals[row["corpus"]] += float(row["percent_of_words"])
    for corpus, total in totals.items():
        assert math.isclose(
            total, 100, abs_tol=1e-6
        ), f"{corpus} percentages sum to {total}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated")
    arguments = parser.parse_args()
    check_totals(arguments.output_dir)
    check_percentage_sums(arguments.output_dir / "word_length_comparison.csv")
    print(
        "PASS: all historical totals, position histograms, and normalized distributions"
    )


if __name__ == "__main__":
    main()
