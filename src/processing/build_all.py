"""Run the infographic generators in order, then optionally assemble the site."""

import argparse
import subprocess
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    """Parse arguments and run this command explicitly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated")
    parser.add_argument(
        "--skip-png",
        action="store_true",
        help="Generate HTML/SVG/data only; do not assemble docs/",
    )
    parser.add_argument(
        "--xml-dir",
        type=Path,
        help="Also rebuild the reading edition from Voynichese XML",
    )
    parser.add_argument(
        "--structural-statistics",
        action="store_true",
        help="Also recompute the WMF character/trigram comparison",
    )
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for script in ["eva_frequencies.py", "word_positions.py", "word_lengths.py"]:
        subprocess.run(
            [
                sys.executable,
                str(HERE / script),
                "--data-dir",
                str(arguments.data_dir),
                "--output-dir",
                str(arguments.output_dir),
            ],
            check=True,
        )
    inputs = {
        name: hashlib.sha256((arguments.data_dir / name).read_bytes()).hexdigest()
        for name in [
            "transcription.txt",
            "EVA2.ttf",
            "forme_of_cury.txt",
            "orationum_ocr.txt",
        ]
    }
    (arguments.output_dir / "input_hashes.json").write_text(
        json.dumps(inputs, indent=2) + "\n"
    )
    if not arguments.skip_png:
        subprocess.run(
            [
                "node",
                str(HERE / "render_pngs.cjs"),
                "--output-dir",
                str(arguments.output_dir),
            ],
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(HERE / "assemble_site.py"),
                "--artifacts",
                str(arguments.output_dir),
            ],
            check=True,
        )

    if arguments.xml_dir and not arguments.skip_png:
        subprocess.run(
            [
                sys.executable,
                str(HERE / "reading_text.py"),
                "--xml-dir",
                str(arguments.xml_dir),
                "--font",
                str(arguments.data_dir / "EVA2.ttf"),
            ],
            check=True,
        )

    if arguments.structural_statistics and not arguments.skip_png:
        subprocess.run(
            [
                sys.executable,
                str(HERE / "structural_statistics.py"),
                "--vms",
                str(arguments.data_dir / "transcription.txt"),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
