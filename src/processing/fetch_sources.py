"""Fetch public text inputs to an ignored local folder, never to the website."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from config import ROOT

PUBLIC_TEXT_URLS = {
    "zl3b": "https://voynich.nu/data/ZL3b-n.txt",
    "forme": "https://www.gutenberg.org/cache/epub/8102/pg8102.txt",
}


def download_source(source, url, data_dir):
    """Keep existing files; report differing upstream bytes rather than concealing them."""
    destination = data_dir / source["local_filename"]
    if destination.exists():
        print(f"Kept existing {destination}")
        return
    request = urllib.request.Request(
        url, headers={"User-Agent": "voynich-infographics source acquisition"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        download_bytes = response.read()
    destination.write_bytes(download_bytes)
    actual_hash = hashlib.sha256(download_bytes).hexdigest()
    status = (
        "historical match"
        if actual_hash == source["sha256"]
        else "DIFFERS from historical bytes; inspect before rebuilding"
    )
    print(f"{destination} SHA-256 {actual_hash} ({status})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/local")
    parser.add_argument(
        "--vms-mirror",
        action="store_true",
        help="Explicitly use the documented GitHub mirror instead of voynich.nu",
    )
    arguments = parser.parse_args()
    arguments.data_dir.mkdir(parents=True, exist_ok=True)
    sources = json.loads(Path(__file__).with_name("sources.json").read_text())["inputs"]
    for source_id, primary_url in PUBLIC_TEXT_URLS.items():
        source = next(item for item in sources if item["id"] == source_id)
        url = (
            source["retrieved_mirror"]
            if source_id == "zl3b" and arguments.vms_mirror
            else primary_url
        )
        download_source(source, url, arguments.data_dir)
    print(
        "Obtain EVA2.ttf manually under its source terms. "
        "Supply your own authorized Orationum OCR; see SOURCE_DATA.md."
    )


if __name__ == "__main__":
    main()
