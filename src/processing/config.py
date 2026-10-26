"""Command-line defaults and presentation templates shared by the generators."""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = Path(__file__).with_name("templates")


def paths(description):
    """Parse explicit local input/output paths; never download inputs implicitly."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated")
    arguments = parser.parse_args()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    return arguments.data_dir, arguments.output_dir


def read_template(filename):
    """Read a checked-in presentation template, independent of the working directory."""
    template = (TEMPLATE_DIR / filename).read_text(encoding="utf-8")
    return re.sub(
        r"\{\{ include:([\w.-]+) \}\}",
        lambda match: (TEMPLATE_DIR / match.group(1)).read_text(encoding="utf-8"),
        template,
    )
