"""Explore two distributional symbol classes, without assuming either is vowels.

Sukhotin uses symmetrized within-word contacts with a zero diagonal. The HMM
uses scaled forward/backward EM on independent words; no boundary symbol and
no known vowel labels are used in fitting. Publish only small derived assets.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import unicodedata

from config import ROOT
from eva import tokenize
from word_frequencies import SOURCES, LOCUS, BASIC
from word_lengths import edition_words
from word_positions import load_glyphs

SEED = 20261029
VOWELS = set("aeiou")


def is_reference_vowel(symbol):
    """An orthographic reference, not a phonetic annotation of historical text."""
    if symbol in ("æ", "œ"):
        return True
    return unicodedata.normalize("NFD", symbol)[0] in VOWELS


def read_sources(data_dir):
    sources = {}
    for code, (label, filename) in SOURCES.items():
        path = data_dir / "word-frequency" / filename
        docs = defaultdict(list)
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = LOCUS.match(line)
            if not match:
                continue
            folio, content = match.groups()
            content = re.sub(r"<[^>]*>", "", content.replace("<->", "."))
            for word in re.split(r"[.,\s]+", content):
                if BASIC.fullmatch(word):
                    docs[folio].append(word)
        sources[code] = {
            "label": label,
            "vms": True,
            "documents": list(docs.values()),
            "folios": list(docs),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "url": "https://www.voynich.nu/data/" + filename,
        }
    for code, filename, label in [
        ("forme", "forme_of_cury.txt", "English · Forme of Cury"),
        ("orationum", "orationum_ocr.txt", "Latin · Corpus orationum"),
    ]:
        path = data_dir / filename
        words = [
            "".join(c for c in word.lower() if c.isalpha())
            for word in edition_words(path.read_text(), code == "forme")
        ]
        sources[code] = {
            "label": label,
            "vms": False,
            "documents": [words[i : i + 200] for i in range(0, len(words), 200)],
            "folios": [],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "url": (
                "https://www.gutenberg.org/cache/epub/8102/pg8102.txt"
                if code == "forme"
                else "https://azbyka.ru/otechnik/assets/uploads/CCSL/CCSL_160_Corpus_orationum_A-C.pdf"
            ),
        }
    return sources


def prepare(source, mode, scope, control):
    rng = random.Random(SEED)
    documents = []
    examples = []
    dropped = 0
    for index, words in enumerate(source["documents"]):
        doc = []
        for word in words:
            symbols = tokenize(word, mode) if source["vms"] else list(word)
            if control == "deleted":
                symbols = [
                    symbol for symbol in symbols if not is_reference_vowel(symbol)
                ]
            if control == "shuffle":
                rng.shuffle(symbols)
            if scope == "interior":
                symbols = symbols[1:-1]
            if not symbols:
                dropped += 1
                continue
            doc.append(symbols)
            if len(examples) < 120:
                examples.append(
                    {
                        "original": word,
                        "symbols": symbols,
                        "folio": source["folios"][index] if source["vms"] else None,
                    }
                )
        if doc:
            documents.append(doc)
    return documents, examples, dropped


def pair_counts(sequences, symbols):
    import numpy as np

    index = {symbol: i for i, symbol in enumerate(symbols)}
    counts = np.zeros(len(symbols), dtype=np.int64)
    pairs = np.zeros((len(symbols), len(symbols)), dtype=np.int64)
    for sequence in sequences:
        ids = [index[symbol] for symbol in sequence]
        for item in ids:
            counts[item] += 1
        for left, right in zip(ids, ids[1:]):
            pairs[left, right] += 1
    return counts, pairs


def sukhotin(pairs):
    """Mayer (2010) §3.2: symmetrized contacts; diagonal excluded; lexical ties."""
    import numpy as np

    contacts = (pairs + pairs.T).astype(float)
    np.fill_diagonal(contacts, 0)
    scores = contacts.sum(axis=1)
    chosen = []
    while len(scores) and np.max(scores) > 0:
        selected = int(np.argmax(scores))
        chosen.append(selected)
        scores -= 2 * contacts[:, selected]
        scores[chosen] = -np.inf
    return chosen


def evenly_sample(sequences, limit):
    """Deterministic spread across the text, preserving whole sequences."""
    eligible = [sequence for sequence in sequences if 1 <= len(sequence) <= 30]
    if len(eligible) <= limit:
        return eligible
    return [eligible[int(i * len(eligible) / limit)] for i in range(limit)]


def hmm_groups(sequences, symbols):
    import numpy as np

    ids = {symbol: i for i, symbol in enumerate(symbols)}
    groups = defaultdict(Counter)
    for sequence in sequences:
        groups[len(sequence)][tuple(ids[symbol] for symbol in sequence)] += 1
    return [
        (
            np.array(list(counts), dtype=int),
            np.array(list(counts.values()), dtype=float),
        )
        for counts in groups.values()
    ]


def expectation(groups, start, transition, emission):
    """Scaled forward/backward; weighted unique words avoid repeated work."""
    import numpy as np

    starts = np.zeros(2)
    transitions = np.zeros((2, 2))
    emissions = np.zeros_like(emission)
    likelihood = 0.0
    for observations, weight in groups:
        size, length = observations.shape
        alpha = np.zeros((size, length, 2))
        scales = np.zeros((size, length))
        alpha[:, 0, :] = start * emission[:, observations[:, 0]].T
        scales[:, 0] = alpha[:, 0, :].sum(axis=1)
        alpha[:, 0, :] /= scales[:, 0, None]
        for t in range(1, length):
            alpha[:, t, :] = (alpha[:, t - 1, :] @ transition) * emission[
                :, observations[:, t]
            ].T
            scales[:, t] = alpha[:, t, :].sum(axis=1)
            alpha[:, t, :] /= scales[:, t, None]
        likelihood += float((np.log(scales).sum(axis=1) * weight).sum())
        beta = np.ones((size, length, 2))
        for t in range(length - 2, -1, -1):
            beta[:, t, :] = (
                (emission[:, observations[:, t + 1]].T * beta[:, t + 1, :])
                @ transition.T
            ) / scales[:, t + 1, None]
        gamma = alpha * beta
        gamma /= gamma.sum(axis=2, keepdims=True)
        starts += (gamma[:, 0, :] * weight[:, None]).sum(axis=0)
        for state in range(2):
            np.add.at(
                emissions[state],
                observations.ravel(),
                (gamma[:, :, state] * weight[:, None]).ravel(),
            )
        for t in range(length - 1):
            xi = (
                alpha[:, t, :, None]
                * transition
                * (emission[:, observations[:, t + 1]].T * beta[:, t + 1, :])[
                    :, None, :
                ]
            )
            xi /= xi.sum(axis=(1, 2))[:, None, None]
            transitions += (xi * weight[:, None, None]).sum(axis=0)
    return likelihood, starts, transitions, emissions


def fit_hmm(sequences, symbols, anchor, seed, epochs=25):
    import numpy as np

    rng = np.random.default_rng(seed)
    groups = hmm_groups(sequences, symbols)
    if not groups:
        return {
            "probabilities": [None] * len(symbols),
            "likelihood": None,
            "iterations": 0,
            "trace": [],
        }
    start = rng.dirichlet([2, 2])
    transition = np.vstack([rng.dirichlet([2, 2]) for _ in range(2)])
    emission = np.vstack([rng.dirichlet(np.ones(len(symbols)) * 2) for _ in range(2)])
    trace = []
    for _ in range(epochs):
        likelihood, starts, transitions, emissions = expectation(
            groups, start, transition, emission
        )
        trace.append(likelihood)
        start = starts + 1e-8
        start /= start.sum()
        transition = transitions + 1e-8
        transition /= transition.sum(axis=1, keepdims=True)
        emission = emissions + 1e-8
        emission /= emission.sum(axis=1, keepdims=True)
        if len(trace) > 1 and abs(trace[-1] - trace[-2]) < 1e-5 * max(
            1, abs(trace[-2])
        ):
            break
    likelihood, _, _, emissions = expectation(groups, start, transition, emission)
    totals = emissions.sum(axis=0)
    probability = np.divide(
        emissions[0], totals, out=np.full(len(symbols), 0.5), where=totals > 0
    )
    if probability[anchor] < 0.5:
        probability = 1 - probability
    return {
        "probabilities": [
            round(float(p), 6) if total > 0 else None
            for p, total in zip(probability, totals)
        ],
        "likelihood": likelihood,
        "iterations": len(trace),
        "trace": trace + [likelihood],
    }


def model_run(sequences, symbols, seed, limit, restarts):
    import numpy as np

    counts, pairs = pair_counts(sequences, symbols)
    selected = sukhotin(pairs)
    anchor = selected[0] if selected else int(np.argmax(counts))
    sample = evenly_sample(sequences, limit)
    fits = [fit_hmm(sample, symbols, anchor, seed + i) for i in range(restarts)]
    best = max(
        fits,
        key=lambda fit: fit["likelihood"] if fit["likelihood"] is not None else -np.inf,
    )
    return {
        "sukhotin": [
            i in selected if counts[i] > 0 else None for i in range(len(symbols))
        ],
        "seed_symbol": symbols[anchor],
        "hmm": best["probabilities"],
        "fit_words": len(sample),
        "omitted_long_words": sum(len(word) > 30 for word in sequences),
        "hmm_fit": {
            "likelihood": best["likelihood"],
            "iterations": best["iterations"],
            "restart_likelihoods": [fit["likelihood"] for fit in fits],
        },
        "restart_A_fraction": [
            (
                sum(
                    fit["probabilities"][i] >= 0.5
                    for fit in fits
                    if fit["probabilities"][i] is not None
                )
                / sum(fit["probabilities"][i] is not None for fit in fits)
                if any(fit["probabilities"][i] is not None for fit in fits)
                else None
            )
            for i in range(len(symbols))
        ],
    }


def scenario(source, mode, scope, control, bootstraps=4, fit_words=3000):
    documents, examples, dropped = prepare(source, mode, scope, control)
    sequences = [word for doc in documents for word in doc]
    symbols = sorted({symbol for word in sequences for symbol in word})
    counts, pairs = pair_counts(sequences, symbols)
    result = model_run(sequences, symbols, SEED, fit_words, 3)
    samples = []
    rng = random.Random(SEED)
    for iteration in range(bootstraps):
        docs = rng.choices(documents, k=len(documents))
        words = [word for doc in docs for word in doc]
        run = model_run(words, symbols, SEED + 100 + iteration, 1000, 1)
        # HMM state labels are arbitrary. Align to the full fit's anchor if it
        # was present, otherwise choose the orientation matching its assignments.
        full_anchor = symbols.index(result["seed_symbol"])
        p = run["hmm"]
        if p[full_anchor] is not None:
            if p[full_anchor] < 0.5:
                run["hmm"] = [None if x is None else 1 - x for x in p]
        else:
            overlap = sum(
                counts[i] * (int(p[i] >= 0.5) == int(result["hmm"][i] >= 0.5))
                for i in range(len(symbols))
                if p[i] is not None and result["hmm"][i] is not None
            )
            observed = sum(
                counts[i]
                for i in range(len(symbols))
                if p[i] is not None and result["hmm"][i] is not None
            )
            if overlap < observed / 2:
                run["hmm"] = [None if x is None else 1 - x for x in p]
        samples.append(run)
    result["bootstrap"] = {}
    for method in ("sukhotin", "hmm"):
        result["bootstrap"][method] = [
            {
                "A": sum(
                    run[method][i] >= (0.5 if method == "hmm" else 1)
                    for run in samples
                    if run[method][i] is not None
                ),
                "n": sum(run[method][i] is not None for run in samples),
            }
            for i in range(len(symbols))
        ]
    return {
        "symbols": symbols,
        "counts": counts.tolist(),
        "pairs": pairs.tolist(),
        "examples": examples,
        "words": len(sequences),
        "dropped_words": dropped,
        "document_count": len(documents),
        **result,
    }


def write_json(path, value):
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    if len(content.encode()) > 240000:
        raise ValueError(f"Asset too large: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def install_vowel_entry(site_dir):
    path = site_dir / "index.html"
    if not path.exists():
        return
    text = re.sub(
        r"<!-- VOWEL ENTRY -->.*?<!-- END VOWEL ENTRY -->\n?",
        "",
        path.read_text(),
        flags=re.S,
    )
    entry = """<!-- VOWEL ENTRY -->
<article class="entry"><div style="padding:30px;background:#e6ece7;border:1px solid #bdcbc2;border-radius:8px"><p class="eyebrow">Distributional classes / controlled experiments</p><h2 style="font-size:40px">Which signs<br>behave like vowels?</h2><p>Two methods. Shuffled and vowel-deleted controls. No assumed decipherment.</p></div><div><p class="eyebrow">Stability → neighbors → actual words</p><h2>Vowel-like symbol discovery</h2><p>Compare inferred classes across transcriptions, grouping and word interiors, inspect resampling stability, and test your own assignments.</p><a class="open" href="pages/vowel-discovery/">Explore candidate classes →</a></div></article>
<!-- END VOWEL ENTRY -->
"""
    path.write_text(
        text.replace('<section class="notes">', entry + '<section class="notes">', 1)
    )


def main():
    import numpy as np

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/local")
    parser.add_argument("--site-dir", type=Path, default=ROOT / "docs")
    parser.add_argument("--fit-words", type=int, default=3000)
    parser.add_argument("--bootstraps", type=int, default=4)
    args = parser.parse_args()
    page = args.site_dir / "pages/vowel-discovery"
    sources = read_sources(args.data_dir)
    manifest = {
        "seed": SEED,
        "fit_words": args.fit_words,
        "bootstrap_fit_words": 1000,
        "bootstraps": args.bootstraps,
        "restarts": 3,
        "max_word_units": 30,
        "max_epochs": 25,
        "numpy": np.__version__,
        "python": sys.version.split()[0],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sources": [],
        "scenarios": [],
    }
    for code, source in sources.items():
        manifest["sources"].append(
            {
                key: value
                for key, value in {"id": code, **source}.items()
                if key not in ("documents", "folios")
            }
        )
        modes = ("letters", "groups") if source["vms"] else ("letters",)
        controls = (
            ("native", "shuffle") if source["vms"] else ("native", "shuffle", "deleted")
        )
        for mode in modes:
            for scope in ("whole", "interior"):
                for control in controls:
                    name = "-".join((code, mode, scope, control))
                    target = page / "data" / f"{name}.json"
                    if target.exists():
                        saved = json.loads(target.read_text())
                        if (
                            saved.get("run_hash") == manifest["script_sha256"]
                            and saved.get("input_hash") == source["sha256"]
                            and saved.get("settings")
                            == [args.fit_words, args.bootstraps]
                        ):
                            print("Cached " + name, flush=True)
                        else:
                            saved = None
                    else:
                        saved = None
                    if saved is None:
                        saved = scenario(
                            source,
                            mode,
                            scope,
                            control,
                            args.bootstraps,
                            args.fit_words,
                        )
                        saved.update(
                            run_hash=manifest["script_sha256"],
                            input_hash=source["sha256"],
                            settings=[args.fit_words, args.bootstraps],
                        )
                        write_json(target, saved)
                        print(
                            f'{name}: {saved["words"]:,} words; A seed {saved["seed_symbol"]}',
                            flush=True,
                        )
                    manifest["scenarios"].append(
                        {
                            "id": name,
                            "source": code,
                            "mode": mode,
                            "scope": scope,
                            "control": control,
                            "file": target.name,
                        }
                    )
    write_json(page / "data/manifest.json", manifest)
    write_json(
        page / "data/glyphs.json",
        load_glyphs((ROOT / "generated/voynich_eva_frequency.html").read_text()),
    )
    for extension in ("html", "js", "css"):
        destination = "index.html" if extension == "html" else "explorer." + extension
        (page / destination).write_text(
            (
                Path(__file__).parent / "templates" / ("vowel_discovery." + extension)
            ).read_text()
        )
    install_vowel_entry(args.site_dir)


if __name__ == "__main__":
    main()
