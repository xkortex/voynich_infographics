"""Shared command-line paths; no inputs or outputs are fetched implicitly."""
import argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def paths(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--data-dir', type=Path, default=ROOT/'data/local')
    p.add_argument('--output-dir', type=Path, default=ROOT/'generated')
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    return a.data_dir, a.output_dir
