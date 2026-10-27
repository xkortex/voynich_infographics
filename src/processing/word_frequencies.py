"""Build auditable word-family frequency comparisons from EVA IVTFF files.

Raw inputs stay local. Published vocabulary counts, mappings and provenance are
small text files; every plotted family can be traced to its original words.
"""

import argparse
import csv
from collections import Counter
import hashlib
import json
import random
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "ZL": ("Zandbergen–Landini 3b", "ZL3b-n.txt"),
    "IT": ("Takahashi / interlinear 2a", "IT2a-n.txt"),
    "VT": ("Voynichese / Takahashi 0e", "VT0e-n.txt"),
    "RF": ("Reference 1b · basic EVA", "RF1b-er.txt"),
}
BASIC = re.compile(r"^[a-vxyz]+$")
LOCUS = re.compile(r"^<(f[^.>]+)\.[^>]+>\s*(.*)")


def parse_words(text):
    """Keep marked words intact; never turn an uncertain span into a new word.

    IVTFF periods, commas (uncertain spaces), whitespace and drawing intrusions
    are boundaries. Other angle-bracket annotations are metadata, not words.
    Braces denote ligatures and stay literal in the unfiltered population.
    """
    counts = Counter()
    examples = {}
    for line in text.splitlines():
        match = LOCUS.match(line)
        if not match:
            continue
        folio, content = match.groups()
        content = content.replace("<->", ".")
        content = re.sub(r"<[^>]*>", "", content)
        for word in re.split(r"[.,\s]+", content):
            if word:
                counts[word] += 1
                examples.setdefault(word, folio)
    return counts, examples


def trim_middle(word, n):
    """Do not conflate distinct too-short words into one empty family."""
    return word[n:-n] if len(word) > 2 * n else "~short:" + word


def edit_neighbours(word):
    """All nonempty strings one Levenshtein edit away in basic EVA."""
    alphabet = "abcdefghijklmnopqrstuvxyz"
    for i in range(len(word)):
        if len(word) > 1:
            yield word[:i] + word[i + 1 :]
        for letter in alphabet:
            if letter != word[i]:
                yield word[:i] + letter + word[i + 1 :]
    for i in range(len(word) + 1):
        for letter in alphabet:
            yield word[:i] + letter + word[i:]


def collapse_rare(counts, threshold):
    """Map rare words directly to a strictly more frequent, non-rare neighbour.

    Distance is exactly one; no transitive chaining. Choose greatest original
    count, then lexical order. Unmatched rare words remain distinct.
    """
    targets = {word for word, count in counts.items() if count > threshold}
    mapping = {}
    for word, count in counts.items():
        choices = (
            targets.intersection(edit_neighbours(word)) if count <= threshold else set()
        )
        mapping[word] = min(choices, key=lambda w: (-counts[w], w)) if choices else word
    return mapping


def morfessor_families(counts, weight):
    """Fit independently per source; longest morph is a heuristic family key."""
    import morfessor

    random.seed(42)
    model = morfessor.BaselineModel(corpusweight=weight, use_skips=False)
    model.load_data([(count, word) for word, count in sorted(counts.items())])
    model.train_batch(algorithm="recursive", finish_threshold=0.01)
    segments = {word: list(model.viterbi_segment(word)[0]) for word in sorted(counts)}
    mapping = {word: max(parts, key=len) for word, parts in segments.items()}
    return mapping, segments


def write_json(path, value):
    """Keep each published text asset small; fail instead of silently bloating it."""
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(data.encode()) > 240_000:
        raise ValueError(f"Asset too large: {path}; reduce shard size")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def install_frequency_entry(site_dir):
    index = site_dir / "index.html"
    if not index.exists():
        return
    text = re.sub(
        r"<!-- WORD FREQUENCY ENTRY -->.*?<!-- END WORD FREQUENCY ENTRY -->\n?",
        "",
        index.read_text(),
        flags=re.S,
    )
    entry = """<!-- WORD FREQUENCY ENTRY -->
<article class="entry"><div style="padding:30px;background:#efe5d4;border:1px solid #d4c3a6;border-radius:8px"><p class="eyebrow">Words → families → frequency</p><h2 style="font-size:40px">How much does<br>the tail change?</h2><p>Four EVA sources. Fourteen treatments. Every family inspectable.</p></div><div><p class="eyebrow">Rank curves / frequency histograms</p><h2>Word frequency under transformations</h2><p>Compare counts and relative abundance across transcriptions, learned families, rare-word repairs, prefixes, suffixes and word middles.</p><a class="open" href="pages/word-frequencies/">Explore word frequencies →</a></div></article>
<!-- END WORD FREQUENCY ENTRY -->
"""
    index.write_text(
        text.replace('<section class="notes">', entry + '<section class="notes">', 1)
    )


def build(data_dir, site_dir):
    import morfessor

    page = site_dir / "pages/word-frequencies"
    out = page / "data"
    treatments = [("none", "Whole words · no transformation")]
    treatments += [
        (f"{side}{n}", f"{side.title()}-{n}")
        for side in ("prefix", "suffix")
        for n in (1, 2, 3)
    ]
    treatments += [(f"infix{n}", f"Middle · trim {n} each end") for n in (1, 2)]
    treatments += [(f"edit{n}", f"Edit distance 1 · rare count ≤ {n}") for n in (1, 2)]
    treatments += [
        (f"morf{weight}", f"Morfessor longest · α {weight}") for weight in (0.1, 1, 10)
    ]
    manifest = {
        "sources": [],
        "treatments": treatments,
        "seed": 42,
        "morfessor": morfessor.__version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parsing": "Period, comma, whitespace and <-> boundaries; other angle annotations removed. Marked tokens retained intact or excluded by population toggle.",
    }
    vt_text = (data_dir / SOURCES["VT"][1]).read_text(encoding="utf-8-sig")
    vt_pairs = set()
    for line in vt_text.splitlines():
        line_counts, line_examples = parse_words(line)
        vt_pairs.update((word, line_examples[word]) for word in line_counts)
    summaries = []
    for code, (label, filename) in SOURCES.items():
        path = data_dir / filename
        content = path.read_bytes()
        counts, examples = parse_words(content.decode("utf-8-sig"))
        words = sorted(counts)
        clean = Counter(
            {word: count for word, count in counts.items() if BASIC.fullmatch(word)}
        )
        vocabulary = [
            [word, counts[word], examples[word], (word, examples[word]) in vt_pairs]
            for word in words
        ]
        shards = []
        for start in range(0, len(words), 1000):
            name = f"{code}/vocab-{start // 1000}.json"
            write_json(out / name, vocabulary[start : start + 1000])
            shards.append(name)
        source = {
            "id": code,
            "label": label,
            "url": "https://www.voynich.nu/data/" + filename,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "tokens": sum(counts.values()),
            "types": len(words),
            "basic_tokens": sum(clean.values()),
            "basic_types": len(clean),
            "shards": shards,
            "maps": {},
        }
        for treatment, _ in treatments:
            mapping = {word: word for word in words}
            segments = None
            if treatment.startswith("prefix"):
                n = int(treatment[-1])
                mapping.update({w: w[:n] for w in clean})
            elif treatment.startswith("suffix"):
                n = int(treatment[-1])
                mapping.update({w: w[-n:] for w in clean})
            elif treatment.startswith("infix"):
                n = int(treatment[-1])
                mapping.update({w: trim_middle(w, n) for w in clean})
            elif treatment.startswith("edit"):
                mapping.update(collapse_rare(clean, int(treatment[-1])))
            elif treatment.startswith("morf"):
                learned, segments = morfessor_families(clean, float(treatment[4:]))
                mapping.update(learned)
            # Integer references avoid duplicating vocabulary text in every map.
            keys = sorted(set(mapping.values()))
            indices = {key: i for i, key in enumerate(keys)}
            name = f"{code}/{treatment}.json"
            write_json(
                out / name, {"keys": keys, "map": [indices[mapping[w]] for w in words]}
            )
            source["maps"][treatment] = name
            for population in ("basic", "all"):
                family_counts = Counter()
                for word in words:
                    if population == "all" or word in clean:
                        family_counts[mapping[word]] += counts[word]
                tokens = sum(family_counts.values())
                summaries.append(
                    {
                        "source": code,
                        "treatment": treatment,
                        "population": population,
                        "tokens": tokens,
                        "families": len(family_counts),
                        "singleton_families": sum(
                            count == 1 for count in family_counts.values()
                        ),
                        "top_10_token_percent": 100
                        * sum(sorted(family_counts.values(), reverse=True)[:10])
                        / tokens,
                    }
                )
            if segments:
                # Segmentation is audit data, not required for plotting.
                for start in range(0, len(words), 1000):
                    write_json(
                        out / f"{code}/{treatment}-segments-{start // 1000}.json",
                        [
                            [w, segments[w]]
                            for w in words[start : start + 1000]
                            if w in segments
                        ],
                    )
        manifest["sources"].append(source)
        print(
            f"{code}: {sum(counts.values()):,} tokens; {sum(clean.values()):,} basic-EVA tokens",
            flush=True,
        )
    manifest["training"] = {
        "algorithm": "recursive",
        "finish_threshold": 0.01,
        "use_skips": False,
        "decoder_addcount": 1.0,
        "decoder_maxlen": 30,
    }
    write_json(out / "manifest.json", manifest)
    with (out / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summaries)
    for extension in ("html", "css", "js"):
        target = "index.html" if extension == "html" else "chart." + extension
        (page / target).write_text(
            (
                Path(__file__).parent / "templates" / ("word_frequencies." + extension)
            ).read_text()
        )
    install_frequency_entry(site_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path, default=ROOT / "data/local/word-frequency"
    )
    parser.add_argument("--site-dir", type=Path, default=ROOT / "docs")
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download missing inputs from voynich.nu; raw files remain local",
    )
    args = parser.parse_args()
    if args.fetch:
        args.data_dir.mkdir(parents=True, exist_ok=True)
        for _, filename in SOURCES.values():
            path = args.data_dir / filename
            if not path.exists():
                with urllib.request.urlopen(
                    "https://www.voynich.nu/data/" + filename
                ) as response:
                    path.write_bytes(response.read())
    build(args.data_dir, args.site_dir)


if __name__ == "__main__":
    main()
