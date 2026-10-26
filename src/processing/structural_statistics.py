"""Recompute character-pair and word-trigram statistics for the explorable page.

WMF is processed by its contiguous language blocks, never concatenating articles.
VMS uses readable ZL3b paragraph loci, grouped by folio. This is a new analysis,
not a numerical reproduction of the Bowern–Lindemann paper's corpus.
"""

import argparse
from collections import Counter
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import shutil
import unicodedata

from config import ROOT, TEMPLATE_DIR, read_template
from eva import readable_words, tokenize
from wmf_word_lengths import is_tamil

MODES = ("native", "prefix3", "suffix3")
SHUFFLE_SEED = 20261026


def normalize_words(text):
    """NFC + lowercase; keep Unicode letters and attached combining marks.

    Other characters become separators. No dictionary filter, transliteration,
    diacritic stripping or linguistic word segmentation is performed.
    """
    text = unicodedata.normalize("NFC", text.lower())
    words = []
    word = []
    for character in text:
        category = unicodedata.category(character)
        if category.startswith("L") or (category.startswith("M") and word):
            word.append(character)
        elif word:
            words.append("".join(word))
            word = []
    if word:
        words.append("".join(word))
    return words


def sample_documents(documents, maximum_words):
    sampled = []
    remaining = maximum_words
    for words in documents:
        if not remaining:
            break
        kept = words[:remaining]
        if kept:
            sampled.append(kept)
            remaining -= len(kept)
    return sampled


def repeated_trigrams(documents, mode="native"):
    """Occurrence-weighted coverage: sum(c for c >= 2) / all word windows.

    Prefix/suffix mappings are deliberately many-to-one. They create collisions
    even in shuffled text, so increased coverage is not proof of morphology.
    """
    counts = Counter()
    for words in documents:
        if mode == "prefix3":
            words = [word[:3] for word in words]
        elif mode == "suffix3":
            words = [word[-3:] for word in words]
        elif mode != "native":
            raise ValueError(f"Unknown trigram representation: {mode}")
        counts.update(zip(words, words[1:], words[2:]))
    total = sum(counts.values())
    repeated = sum(count for count in counts.values() if count >= 2)
    return {
        "windows": total,
        "repeated_occurrences": repeated,
        "distinct_types": len(counts),
        "repeated_types": sum(count >= 2 for count in counts.values()),
        "percent": 100 * repeated / total if total else None,
    }


def character_pairs(documents, maximum_units, grouped=False, boundaries=True):
    """Adjacent pairs with or without word-space symbols; reset at each document.

    Turning spaces off joins words within the document, making boundary effects
    inspectable. It does not create edges between different source documents.
    """
    pairs = Counter()
    characters = Counter()
    remaining = maximum_units
    for words in documents:
        sequence = []
        for index, word in enumerate(words):
            if index and boundaries:
                sequence.append(" ")
            sequence.extend(tokenize(word) if grouped else word)
        kept = sequence[:remaining]
        characters.update(kept)
        pairs.update(zip(kept, kept[1:]))
        remaining -= len(kept)
        if not remaining:
            break
    outgoing = Counter()
    for (previous, following), count in pairs.items():
        outgoing[previous] += count
    total = sum(pairs.values())
    h2 = (
        -sum(
            count / total * math.log2(count / outgoing[previous])
            for (previous, _), count in pairs.items()
        )
        if total
        else 0.0
    )
    units = sum(characters.values())
    h1 = (
        -sum(count / units * math.log2(count / units) for count in characters.values())
        if units
        else 0.0
    )
    return {
        "alphabet": len(characters),
        "units": units,
        "pair_count": total,
        "h1": h1,
        "h2": h2,
        "characters": characters,
        "pairs": pairs,
        "outgoing": outgoing,
    }


def matrix_payload(statistics, top_symbols):
    """Publish only a small visible submatrix, keeping full row denominators."""
    symbols = [
        symbol for symbol, _ in statistics["characters"].most_common(top_symbols)
    ]
    matrix = [
        [statistics["pairs"][(left, right)] for right in symbols] for left in symbols
    ]
    return {
        "symbols": symbols,
        "counts": matrix,
        "outgoing": [statistics["outgoing"][symbol] for symbol in symbols],
        "pair_count": statistics["pair_count"],
        "shown_pair_count": sum(map(sum, matrix)),
        "full_alphabet": statistics["alphabet"],
    }


def analyze_documents(identifier, label, kind, documents, options, grouped=False):
    count = sum(map(len, documents))
    randomizer = random.Random(SHUFFLE_SEED)
    shuffled = []
    for words in documents:
        copy = words.copy()
        randomizer.shuffle(copy)
        shuffled.append(copy)
    row = {
        "id": identifier,
        "label": label,
        "kind": kind,
        "words": count,
        "documents": len(documents),
        "limited": count < options.max_words,
    }
    for mode in MODES:
        row[mode] = repeated_trigrams(documents, mode)
        row[mode + "_shuffled"] = repeated_trigrams(shuffled, mode)
    matrices = {}
    for boundary_mode in ["spaces", "joined"]:
        statistics = character_pairs(
            documents, options.max_units, grouped, boundary_mode == "spaces"
        )
        row[boundary_mode] = {
            name: statistics[name]
            for name in ["alphabet", "units", "pair_count", "h1", "h2"]
        }
        matrices[boundary_mode] = matrix_payload(statistics, options.matrix_size)
    filename = identifier + ".json"
    row["matrix_file"] = "pairs/" + filename
    matrices["statistics"] = row.copy()
    (options.output_dir / "pairs" / filename).write_text(
        json.dumps(matrices, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    return row


def vms_documents(path):
    """Paragraph text only, including line-final paragraph loci; exclude labels."""
    documents = []
    current = []
    for line in path.read_text().splitlines():
        if re.match(r"^<f[^.>]+>", line):
            if current:
                documents.append(current)
            current = []
        match = re.match(r"^<f[^>]*\.[^>]*,[^>]*P[^>]*>", line)
        if match:
            current.extend(readable_words(line))
    if current:
        documents.append(current)
    return documents


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scatter_summary(row):
    """Small scatter dataset; full statistics live alongside each matrix."""
    compact = row.copy()
    for mode in MODES:
        for key in [mode, mode + "_shuffled"]:
            compact[key] = {"percent": row[key]["percent"]}
    return compact


def build_statistics(options):
    options.output_dir.mkdir(parents=True, exist_ok=True)
    (options.output_dir / "pairs").mkdir(exist_ok=True)
    rows = []
    csv.field_size_limit(100_000_000)
    excluded = 0
    seen = set()
    with options.wmf.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for language, records in itertools.groupby(
            reader, key=lambda record: record["language"].strip().lower()
        ):
            if language in seen:
                raise ValueError(f"WMF language blocks are not contiguous: {language}")
            seen.add(language)
            if is_tamil(language):
                excluded += sum(1 for _ in records)
                continue
            documents = []
            remaining = options.max_words
            for record in records:
                if remaining:
                    words = normalize_words(record["text"])[:remaining]
                    if words:
                        documents.append(words)
                        remaining -= len(words)
            identifier = "wmf-" + language
            if not re.fullmatch(r"[a-z0-9_-]+", identifier):
                raise ValueError(f"Unsafe language code: {language}")
            if documents:
                rows.append(
                    analyze_documents(identifier, language, "wmf", documents, options)
                )
            if len(rows) % 25 == 0:
                print(f"Analyzed {len(rows)} WMF languages", flush=True)
    sampled_vms = sample_documents(vms_documents(options.vms), options.max_words)
    rows.append(
        analyze_documents("vms-eva", "VMS · EVA letters", "vms", sampled_vms, options)
    )
    rows.append(
        analyze_documents(
            "vms-groups", "VMS · grouped EVA", "vms", sampled_vms, options, grouped=True
        )
    )
    # Main scatter data stays small; counts remain inspectable in per-language files.
    (options.output_dir / "summary.json").write_text(
        json.dumps(
            [scatter_summary(row) for row in rows],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
    )
    fields = [
        "id",
        "label",
        "words",
        "documents",
        "alphabet",
        "h1",
        "h2",
        "native_pct",
        "prefix3_pct",
        "suffix3_pct",
        "native_shuffle_pct",
        "prefix3_shuffle_pct",
        "suffix3_shuffle_pct",
    ]
    with (options.output_dir / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **{key: row[key] for key in ["id", "label", "words", "documents"]},
                    **{key: row["spaces"][key] for key in ["alphabet", "h1", "h2"]},
                    **{mode + "_pct": row[mode]["percent"] for mode in MODES},
                    **{
                        mode + "_shuffle_pct": row[mode + "_shuffled"]["percent"]
                        for mode in MODES
                    },
                }
            )
    metadata = {
        "wmf_sha256": file_hash(options.wmf),
        "vms_sha256": file_hash(options.vms),
        "wmf_languages": sum(row["kind"] == "wmf" for row in rows),
        "excluded_tamil_rows": excluded,
        "max_words": options.max_words,
        "max_character_units": options.max_units,
        "matrix_size": options.matrix_size,
        "shuffle_seed": SHUFFLE_SEED,
        "sampling": "First up to max_words tokens in source order; source documents never bridged. Pair sequences capped at max_units separately per boundary/representation mode.",
        "normalization": "WMF text field only, lowercase then NFC; Unicode letters and attached marks; other characters split tokens. VMS readable basic-EVA paragraph words, grouped by folio. Omitted uncertain words close gaps between retained words.",
        "entropy": "Plug-in H(next | previous) = -sum_ab p(ab) log2(count(ab)/outgoing(a)); spaces included by default. No bias correction. Joined view removes spaces within documents.",
        "trigram": "Three WORD windows. Repeated occurrence coverage = sum counts >=2 / all windows. Prefix3/suffix3 map each word to first/last 3 Unicode codepoints, retaining shorter words. VMS grouped view uses identical word-string trigram mappings.",
        "shuffle": "One within-document shuffle preserving words/frequencies; descriptive collision baseline, not a significance test.",
        "source_paper": "https://doi.org/10.1146/annurev-linguistics-011619-030613",
        "paper_relationship": "New WMF/ZL computation inspired by figures 4 and 6, not a reproduction of published values. Trigram experiment is separate from the paper.",
    }
    (options.output_dir / "methods.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "languages": metadata["wmf_languages"],
                "excluded_tamil_rows": excluded,
                "vms": [row for row in rows if row["kind"] == "vms"],
            },
            indent=2,
        )
    )


def install_structural_entry(site_dir):
    """Keep the gallery link when other charts are rebuilt."""
    index = site_dir / "index.html"
    if not index.exists():
        return
    page = index.read_text()
    page = re.sub(
        r"<!-- STRUCTURAL ENTRY -->.*?<!-- END STRUCTURAL ENTRY -->",
        "",
        page,
        flags=re.S,
    )
    page = page.replace(
        '<section class="notes">',
        read_template("structural_gallery_entry.html") + '<section class="notes">',
        1,
    )
    index.write_text(page)


def build_page(output_dir):
    """Presentation rebuild does not rescan the 603 MB WMF corpus."""
    page_dir = output_dir.parent
    page_dir.mkdir(parents=True, exist_ok=True)
    methods = json.loads((output_dir / "methods.json").read_text())
    page = read_template("structural_statistics.html")
    for placeholder, value in {
        "WMF_COUNT": str(methods["wmf_languages"]),
        "WORD_LIMIT": f'{methods["max_words"]:,}',
        "UNIT_LIMIT": f'{methods["max_character_units"]:,}',
        "MATRIX_LIMIT": str(methods["matrix_size"]),
    }.items():
        page = page.replace(placeholder, value)
    (page_dir / "index.html").write_text(page)
    for extension in ["css", "js"]:
        shutil.copy2(
            TEMPLATE_DIR / f"structural_statistics.{extension}",
            page_dir / f"statistics.{extension}",
        )
    site_dir = page_dir.parents[1]
    install_structural_entry(site_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wmf", type=Path, default=Path.home() / "bots/ChatGPT/corpora/wmf/wmf.csv"
    )
    parser.add_argument(
        "--vms", type=Path, default=ROOT / "data/local/transcription.txt"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs/pages/structural-statistics/data",
    )
    parser.add_argument("--max-words", type=int, default=32000)
    parser.add_argument("--max-units", type=int, default=200000)
    parser.add_argument("--matrix-size", type=int, default=28)
    parser.add_argument(
        "--page-only",
        action="store_true",
        help="Refresh HTML/CSS/JS without recomputing statistics",
    )
    options = parser.parse_args()
    if options.max_words < 3 or options.max_units < 2 or options.matrix_size < 1:
        parser.error(
            "Positive sample limits are required (at least 3 words / 2 character units)"
        )
    if not options.page_only:
        build_statistics(options)
    build_page(options.output_dir)


if __name__ == "__main__":
    main()
