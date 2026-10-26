#!/usr/bin/env python3
"""Word-occurrence length distributions for UTF-8 multilingual corpora.
Python 3.9+; standard library only. Run --help for input options.
"""

import argparse
import csv
import gzip
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

LETTERS = r"[^\W\d_]"
TOKEN = re.compile(LETTERS + r"+(?:['’]" + LETTERS + r"+)*")


def is_tamil(value):
    """Match Tamil names/codes, including ta-IN, tam_Taml, tamil_train."""
    parts = re.split(r"[^a-z0-9]+", str(value).casefold())
    return any(p in {"ta", "tam", "tamil"} for p in parts)


def clean(text, join_hyphens=True):
    # Match the cleaning used for the earlier full-edition comparisons.
    text = re.split(r"\*\*\* START OF .*?\*\*\*", text, maxsplit=1)[-1]
    text = re.split(r"\*\*\* END OF ", text, maxsplit=1)[0]
    text = re.sub(r"^\s*===== PDF PAGE \d+ =====\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*Digitized by Google\s*$", "", text, flags=re.M | re.I)
    if join_hyphens:
        text = re.sub(r"(" + LETTERS + r")-\s*\n\s*(" + LETTERS + r")", r"\1\2", text)
    return unicodedata.normalize("NFC", text)


def lengths(text, join_hyphens=True):
    for match in TOKEN.finditer(clean(text, join_hyphens)):
        # Apostrophes are internal to a token but contribute zero length.
        length = sum(c.isalpha() for c in match.group())
        if length:
            yield length


def summarize(counts):
    n = sum(counts.values())
    if not n:
        return dict(
            words=0,
            mean=None,
            median=None,
            modes=[],
            stddev_population=None,
            pct_length_1_2=None,
            pct_length_4_6=None,
            pct_length_8_plus=None,
            pct_length_10_plus=None,
        )
    mean = sum(k * v for k, v in counts.items()) / n
    variance = sum(v * (k - mean) ** 2 for k, v in counts.items()) / n
    ranks = ((n - 1) // 2, n // 2)
    middle = []
    running = 0
    for k, v in sorted(counts.items()):
        for rank in ranks:
            if running <= rank < running + v:
                middle.append(k)
        running += v
    peak = max(counts.values())
    pct = lambda condition: 100 * sum(v for k, v in counts.items() if condition(k)) / n
    return dict(
        words=n,
        mean=mean,
        median=sum(middle) / 2,
        modes=[k for k, v in sorted(counts.items()) if v == peak],
        stddev_population=math.sqrt(variance),
        pct_length_1_2=pct(lambda k: 1 <= k <= 2),
        pct_length_4_6=pct(lambda k: 4 <= k <= 6),
        pct_length_8_plus=pct(lambda k: k >= 8),
        pct_length_10_plus=pct(lambda k: k >= 10),
    )


def open_text(path):
    return (gzip.open if path.suffix.lower() == ".gz" else open)(
        path, "rt", encoding="utf-8-sig", errors="strict", newline=""
    )


def format_of(path, override):
    if override != "auto":
        return override
    name = (
        path.name.lower().removesuffix(".gz")
        if sys.version_info >= (3, 9)
        else path.name.lower()
    )
    for extension in ("txt", "csv", "tsv", "jsonl"):
        if name.endswith("." + extension):
            return extension
    return None


def text_language(path, root, source):
    relative = path.relative_to(root) if root.is_dir() else Path(path.name)
    filename = relative.name
    if filename.lower().endswith(".gz"):
        filename = filename[:-3]
    stem = Path(filename).stem
    if source == "parent":
        return path.parent.name
    if source == "filename":
        return stem
    return relative.parts[0] if len(relative.parts) > 1 else stem


def records(path, fmt, args):
    """Yield (language, text, occurrence weight, record location)."""
    with open_text(path) as stream:
        if fmt == "txt":
            yield text_language(
                path, args.input, args.language_from
            ), stream.read(), 1, "file"
            return
        if fmt in {"csv", "tsv"}:
            reader = csv.DictReader(stream, delimiter="\t" if fmt == "tsv" else ",")
            required = {args.language_column, args.text_column}
            if args.count_column:
                required.add(args.count_column)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing columns {sorted(missing)}")
            iterator = ((i, row) for i, row in enumerate(reader, 2))
        else:
            iterator = (
                (i, json.loads(line))
                for i, line in enumerate(stream, 1)
                if line.strip()
            )
        for i, row in iterator:
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{i}: expected an object/row")
            if any(key not in row for key in (args.language_column, args.text_column)):
                raise ValueError(f"{path}:{i}: missing language or text field")
            language, text = row[args.language_column], row[args.text_column]
            if (
                not isinstance(language, str)
                or not language.strip()
                or not isinstance(text, str)
            ):
                raise ValueError(
                    f"{path}:{i}: language must be nonempty text; text must be a string"
                )
            weight = 1
            if args.count_column:
                value = row.get(args.count_column)
                if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
                    raise ValueError(
                        f"{path}:{i}: count must be a nonnegative integer, got {value!r}"
                    )
                weight = int(value)
            yield language.strip(), text, weight, f"record {i}"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 wmf_word_lengths.py /path/to/WMF --out results
  python3 wmf_word_lengths.py corpus.csv --text-column text --language-column language
  python3 wmf_word_lengths.py words.tsv --text-column word --count-column count

Text files: default grouping uses the first directory beneath INPUT, or the filename
stem for flat input. Use --language-from parent/filename to change it.
CSV/TSV/JSONL: language and text come from fields; defaults: language, text.
No language detection is performed. Tamil exclusion requires language labels or paths.
""",
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=Path.home() / "bots/ChatGPT/corpora/wmf",
        help="File or directory (default: ~/bots/ChatGPT/corpora/wmf)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "bots/ChatGPT/voynich/runs/wmf_word_lengths",
    )
    parser.add_argument(
        "--format", choices=["auto", "txt", "csv", "tsv", "jsonl"], default="auto"
    )
    parser.add_argument(
        "--language-from",
        choices=["first-directory", "parent", "filename"],
        default="first-directory",
    )
    parser.add_argument("--language-column", default="language")
    parser.add_argument("--text-column", default="text")
    parser.add_argument(
        "--count-column", help="Optional integer occurrence count (word-list inputs)"
    )
    parser.add_argument("--no-join-line-hyphens", action="store_true")
    args = parser.parse_args()
    args.input = args.input.expanduser().resolve()
    # WMF's top-level CSV is the corpus; derived analysis tables are not inputs.
    if args.input.is_dir() and (args.input / "wmf.csv").is_file():
        args.input = args.input / "wmf.csv"
        print(f"Using WMF corpus: {args.input}", flush=True)
    csv.field_size_limit(100_000_000)
    args.out = args.out.expanduser().resolve()
    if not args.input.exists():
        parser.error(f"input not found: {args.input}")
    if args.input == args.out or args.out in args.input.parents:
        parser.error("output must not equal or contain the input path")
    candidates = sorted(args.input.rglob("*")) if args.input.is_dir() else [args.input]
    files = [
        p
        for p in candidates
        if p.is_file() and args.out not in p.parents and format_of(p, args.format)
    ]
    if not files:
        parser.error(
            "no supported input files (.txt, .csv, .tsv, .jsonl; optionally .gz)"
        )
    counts = defaultdict(Counter)
    audit = []
    excluded_records = excluded_files = read_records = 0
    try:
        for path in files:
            relative = (
                path.relative_to(args.input) if args.input.is_dir() else Path(path.name)
            )
            # Check all relative components, without inheriting incidental ancestor names.
            if any(is_tamil(part) for part in relative.parts) or (
                not args.input.is_dir() and is_tamil(path.parent.name)
            ):
                excluded_files += 1
                audit.append({"file": str(path), "status": "excluded_tamil_path"})
                continue
            record_count = tamil_rows = word_count = 0
            for language, text, weight, location in records(
                path, format_of(path, args.format), args
            ):
                record_count += 1
                if record_count % 50000 == 0:
                    print(
                        f"Read {record_count:,} rows from {path.name}…",
                        file=sys.stderr,
                        flush=True,
                    )
                if is_tamil(language):
                    tamil_rows += 1
                    continue
                c = Counter(lengths(text, not args.no_join_line_hyphens))
                # Keep language labels case-insensitive; aliases other than Tamil are not merged.
                counts[language.casefold()].update(
                    {k: v * weight for k, v in c.items()}
                )
                word_count += sum(c.values()) * weight
            excluded_records += tamil_rows
            read_records += record_count
            audit.append(
                {
                    "file": str(path),
                    "status": "processed",
                    "records": record_count,
                    "excluded_tamil_records": tamil_rows,
                    "counted_word_occurrences": word_count,
                }
            )
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        parser.exit(1, f"Input error: {exc}\nNo new result files were written.\n")
    if not counts or not any(sum(c.values()) for c in counts.values()):
        parser.error("no words remained after exclusions and tokenization")
    args.out.mkdir(parents=True, exist_ok=True)
    fields = ["language"] + list(summarize(Counter()))
    with open(args.out / "summary.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for language, c in sorted(counts.items()):
            result = summarize(c)
            result["modes"] = ";".join(map(str, result["modes"]))
            writer.writerow({"language": language, **result})
    with open(
        args.out / "word_length_distribution.csv", "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["language", "word_length", "count", "percent_of_words"])
        for language, c in sorted(counts.items()):
            n = sum(c.values())
            for k in range(1, max(c, default=0) + 1):
                writer.writerow([language, k, c[k], 100 * c[k] / n if n else 0])
    metadata = {
        "input": str(args.input),
        "files_found": len(files),
        "excluded_tamil_files": excluded_files,
        "excluded_tamil_records": excluded_records,
        "records_read": read_records,
        "language_groups": len(counts),
        "arguments": {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        },
        "method": "Repeated word occurrences; Unicode alphabetic runs with internal apostrophes; NFC; letters only contribute to length. No dictionary filtering, OCR correction, language detection or word segmentation for unspaced scripts. Roman numerals retained. Standard deviation uses population denominator N. Tamil excluded by path components or language values ta/tam/tamil, including delimited locale/split suffixes. Languages are lowercased but aliases are otherwise not merged. Text files are loaded one at a time; table/JSONL records are streamed.",
        "files": audit,
    }
    (args.out / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(counts)} language groups to {args.out}")
    print(
        f"Tamil excluded: {excluded_files} files, {excluded_records} labeled records."
    )
    if not excluded_files and not excluded_records:
        print(
            "NOTICE: No Tamil labels matched. Check paths/metadata; content language is not detected."
        )
    print("summary.csv | word_length_distribution.csv | run_metadata.json")


if __name__ == "__main__":
    main()
