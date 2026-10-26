"""Compare local input bytes with the fingerprints used for the original charts."""

import argparse
import hashlib
import json
from config import ROOT
from pathlib import Path


def check_input(data_dir, source):
    """Print one source check and return whether the original bytes are present."""
    path = data_dir / source["local_filename"]
    actual_hash = (
        hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    )
    matches = actual_hash == source["sha256"]
    status = "MATCH" if matches else "MISSING" if actual_hash is None else "DIFFERENT"
    print(f"{status} {source['local_filename']}")
    if actual_hash and not matches:
        print(f"  actual SHA-256: {actual_hash}")
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/local")
    arguments = parser.parse_args()
    sources = json.loads(Path(__file__).with_name("sources.json").read_text())["inputs"]
    # Evaluate every check, even when an earlier source is missing.
    checks = [check_input(arguments.data_dir, source) for source in sources]
    raise SystemExit(0 if all(checks) else 1)


if __name__ == "__main__":
    main()
