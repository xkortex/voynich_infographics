"""Count first/second-order EVA transitions including observed word spaces.

Each IVTFF text locus is independent. An unreadable/extended/alternative word
breaks the run rather than creating an invented connection across the gap.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from config import ROOT
from eva import tokenize
from word_frequencies import SOURCES, BASIC, LOCUS
from word_positions import load_glyphs


def text_runs(text, mode):
    """Yield unit sequences with one space between consecutive complete words."""
    for line in text.splitlines():
        match = LOCUS.match(line)
        if not match:
            continue
        content = re.sub(r"<[^>]*>", "", match.group(2).replace("<->", "."))
        run = []
        for word in re.split(r"[.,\s]+", content):
            if not word:
                continue
            if not BASIC.fullmatch(word):
                if run:
                    yield run
                    run = []
                continue
            if run:
                run.append(" ")
            run.extend(tokenize(word, mode))
        if run:
            yield run


def lexicon_counts(text):
    """Count whole accepted words, with a source-folio spelling example."""
    counts = Counter()
    folios = {}
    for line in text.splitlines():
        match = LOCUS.match(line)
        if not match:
            continue
        for run in text_runs(line, "letters"):
            for word in "".join(run).split(" "):
                counts[word] += 1
                folios.setdefault(word, match.group(1))
    return [[word, count, folios[word]] for word, count in sorted(counts.items())]


def transition_counts(runs):
    """Sparse integer counts; normalize only over observed successors in the UI."""
    runs = [run for run in runs if run]
    alphabet = sorted({unit for run in runs for unit in run})
    ids = {unit: i for i, unit in enumerate(alphabet)}
    starts = Counter()
    start_pairs = defaultdict(Counter)
    first = defaultdict(Counter)
    second = defaultdict(Counter)
    frequencies = Counter()
    for run in runs:
        values = [ids[unit] for unit in run]
        if not values:
            continue
        starts[values[0]] += 1
        frequencies.update(values)
        if len(values) > 1:
            start_pairs[values[0]][values[1]] += 1
        for a, b in zip(values, values[1:]):
            first[a][b] += 1
        for a, b, c in zip(values, values[1:], values[2:]):
            second[(a, b)][c] += 1
    rows = lambda counts: [
        [int(unit), int(count)] for unit, count in sorted(counts.items())
    ]
    return {
        "alphabet": alphabet,
        "starts": rows(starts),
        "start_pairs": {str(a): rows(row) for a, row in sorted(start_pairs.items())},
        "first": {str(a): rows(row) for a, row in sorted(first.items())},
        "second": {f"{a},{b}": rows(row) for (a, b), row in sorted(second.items())},
        "frequencies": [frequencies[i] for i in range(len(alphabet))],
        "runs": len(runs),
        "units": sum(frequencies.values()),
        "first_total": sum(sum(row.values()) for row in first.values()),
        "second_total": sum(sum(row.values()) for row in second.values()),
    }


def write_json(path, value):
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(content.encode()) > 240000:
        raise ValueError(f"Asset too large: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def install_markov_entry(site_dir):
    path = site_dir / "index.html"
    if not path.exists():
        return
    text = re.sub(
        r"<!-- MARKOV ENTRY -->.*?<!-- END MARKOV ENTRY -->\n?",
        "",
        path.read_text(),
        flags=re.S,
    )
    entry = """<!-- MARKOV ENTRY -->
<article class="entry"><div style="padding:30px;background:#e5eaf0;border:1px solid #c2ccd5;border-radius:8px"><p class="eyebrow">Context → probability → next sign</p><h2 style="font-size:40px">Follow the<br>next character.</h2><p>Characters and spaces. First or second order. Step through the model.</p></div><div><p class="eyebrow">Interactive Markov transitions</p><h2>Spell with a transition model</h2><p>Inspect outgoing probabilities, choose a sign or sample the next one, and compare four transcriptions with spaces included.</p><a class="open" href="pages/markov-transitions/">Explore the Markov diagram →</a></div></article>
<!-- END MARKOV ENTRY -->
"""
    path.write_text(
        text.replace('<section class="notes">', entry + '<section class="notes">', 1)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=ROOT / "data/local/word-frequency"
    )
    parser.add_argument("--site-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    page = args.site_dir / "pages/markov-transitions"
    manifest = {
        "sources": [],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "boundaries": "One space between readable words inside a locus; no transition across locus boundaries or rejected words.",
    }
    for code, (label, filename) in SOURCES.items():
        path = args.data_dir / filename
        source = {
            "id": code,
            "label": label,
            "url": "https://www.voynich.nu/data/" + filename,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "files": {},
        }
        source["lexicon"] = f"{code}-lexicon.json"
        words = lexicon_counts(path.read_text(encoding="utf-8-sig"))
        source["lexicon_types"] = len(words)
        write_json(
            page / "data" / source["lexicon"],
            {
                "words": words,
                "source": code,
                "input_sha256": source["sha256"],
                "script_sha256": manifest["script_sha256"],
            },
        )
        for mode in ("letters", "groups"):
            data = transition_counts(
                text_runs(path.read_text(encoding="utf-8-sig"), mode)
            )
            data.update(
                source=code,
                mode=mode,
                input_sha256=source["sha256"],
                script_sha256=manifest["script_sha256"],
            )
            name = f"{code}-{mode}.json"
            write_json(page / "data" / name, data)
            source["files"][mode] = name
            print(
                f'{code} {mode}: {data["runs"]:,} runs; {data["first_total"]:,} pairs; {data["second_total"]:,} triples'
            )
        manifest["sources"].append(source)
    write_json(page / "data/manifest.json", manifest)
    write_json(
        page / "data/glyphs.json",
        load_glyphs((ROOT / "generated/voynich_eva_frequency.html").read_text()),
    )
    templates = Path(__file__).parent / "templates"
    for extension in ("html", "js", "css"):
        content = (templates / ("markov_transitions." + extension)).read_text()
        if extension == "html":
            for asset in ("js", "css"):
                digest = hashlib.sha256(
                    (templates / ("markov_transitions." + asset)).read_bytes()
                ).hexdigest()[:12]
                attributes = f'?v={digest}"'
                if asset == "js":
                    attributes += f' data-version="{manifest["script_sha256"]}"'
                content = content.replace(
                    f'explorer.{asset}"', f"explorer.{asset}" + attributes
                )
        (
            page / ("index.html" if extension == "html" else "explorer." + extension)
        ).write_text(content)
    install_markov_entry(args.site_dir)


if __name__ == "__main__":
    main()
