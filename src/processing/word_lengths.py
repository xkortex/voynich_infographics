"""Compare word-length frequencies in VMS, Forme of Cury and Orationum."""

import csv
import hashlib
import html
import json
import re
import statistics
import unicodedata
from collections import Counter
from pathlib import Path
from config import paths, read_template
from eva import readable_words, tokenize

CORPUS_COLORS = ["#187e83", "#d36b28", "#8159a5"]
TAIL_BIN = 25


def edition_words(text, remove_gutenberg_wrapper=False):
    """Apply the historical full-edition cleaning, without filtering commentary."""
    if remove_gutenberg_wrapper:
        text = re.split(r"\*\*\* START OF .*?\*\*\*", text, maxsplit=1)[-1]
        text = re.split(r"\*\*\* END OF ", text, maxsplit=1)[0]
    text = re.sub(r"^\s*===== PDF PAGE \d+ =====\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*Digitized by Google\s*$", "", text, flags=re.M | re.I)
    text = re.sub(r"([^\W\d_])-\s*\n\s*([^\W\d_])", r"\1\2", text)
    text = unicodedata.normalize("NFC", text)
    words = re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)*", text)
    return words


def edition_word_lengths(text, remove_gutenberg_wrapper=False):
    """Count alphabetic characters with the shared full-edition tokenization."""
    return [
        sum(character.isalpha() for character in word)
        for word in edition_words(text, remove_gutenberg_wrapper)
    ]


def summarize_lengths(lengths):
    """Describe repeated occurrences, using the historical first mode on ties."""
    return {
        "tokens": len(lengths),
        "mean": statistics.mean(lengths),
        "median": statistics.median(lengths),
        "mode": Counter(lengths).most_common(1)[0][0],
    }


def load_distributions(data_dir):
    distributions = {}
    summaries = {}
    editions = {
        "Forme of Cury": data_dir / "forme_of_cury.txt",
        "Corpus orationum": data_dir / "orationum_ocr.txt",
    }
    for name, path in editions.items():
        original = path.read_text()
        lengths = edition_word_lengths(original, name == "Forme of Cury")
        distributions[name] = Counter(lengths)
        summaries[name] = {
            **summarize_lengths(lengths),
            "sha256_normalized_text": hashlib.sha256(original.encode()).hexdigest(),
            "sha256_bytes": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    words = readable_words((data_dir / "transcription.txt").read_text())
    for name, mode in [
        ("VMS · grouped EVA", "groups"),
        ("VMS · EVA letters", "letters"),
    ]:
        lengths = [len(tokenize(word, mode)) for word in words]
        distributions[name] = Counter(lengths)
        summaries[name] = summarize_lengths(lengths)
    return distributions, summaries


def write_distribution_csv(path, distributions):
    """Keep every exact integer length, including zeros; only the chart bins 25+."""
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["corpus", "word_length", "count", "percent_of_words"])
        for name, counts in distributions.items():
            for length in range(1, max(counts) + 1):
                writer.writerow(
                    [
                        name,
                        length,
                        counts[length],
                        f"{100 * counts[length] / sum(counts.values()):.8f}",
                    ]
                )


def render_length_chart(names, summaries, distributions, style, ceiling):
    width = 1200
    height = 850
    x = 90
    y = 220
    plot_width = 1060
    plot_height = 390
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img"><title>Word-length distributions: VMS, Forme of Cury and Corpus orationum</title><rect width="1200" height="850" fill="#fffdf7"/><style>text{{font-family:system-ui,sans-serif;fill:#263c3a}}.muted{{fill:#65736e;font-size:13px}}.tick{{font-size:12px}}</style><text x="50" y="57" font-family="Georgia,serif" font-size="36">How long are the words?</text><text x="50" y="88" class="muted">VMS vs. Forme of Cury vs. Corpus orationum · word occurrences, normalized within each corpus</text>'
    ]
    for i, name in enumerate(names):
        summary = summaries[name]
        legend_x = 50 + i * 385
        svg_parts += [
            f'<rect x="{legend_x}" y="118" width="13" height="13" fill="{CORPUS_COLORS[i]}"/><text x="{legend_x + 23}" y="130" font-size="17">{html.escape(name)}</text>',
            f"""<text x="{legend_x}" y="156" class="muted">{summary['tokens']:,} words · mean {summary['mean']:.2f} · median {summary['median']:g} · mode {summary['mode']}</text>""",
        ]
    for tick in range(0, ceiling + 1, 5):
        yy = y + plot_height - tick / ceiling * plot_height
        svg_parts.append(
            f'<line x1="{x}" x2="{x + plot_width}" y1="{yy}" y2="{yy}" stroke="#dce2d9"/><text x="{x - 13}" y="{yy + 4}" text-anchor="end" class="tick">{tick}%</text>'
        )
    svg_parts.append(
        f'<text x="{x}" y="{y - 20}" class="muted">Share of word occurrences</text>'
    )
    step = plot_width / TAIL_BIN
    for k in range(1, TAIL_BIN + 1):
        xx = x + (k - 0.5) * step
        svg_parts.append(
            f"""<text x="{xx}" y="{y + plot_height + 23}" text-anchor="middle" class="tick">{(k if k < TAIL_BIN else '25+')}</text>"""
        )
    for i, name in enumerate(names):
        length_counts = distributions[name]
        word_count = sum(length_counts.values())
        values = [
            100
            * (
                length_counts[k]
                if k < TAIL_BIN
                else sum((v for (j, v) in length_counts.items() if j >= TAIL_BIN))
            )
            / word_count
            for k in range(1, TAIL_BIN + 1)
        ]
        points = []
        for k, v in enumerate(values):
            xx = x + (k + 0.5) * step
            yy = y + plot_height - v / ceiling * plot_height
            points.append(f"{xx:.2f},{yy:.2f}")
            tooltip = html.escape(
                f"{name} | length {(k + 1 if k + 1 < 25 else '25+')}: {v:.3f}%"
            )
            if style == "line":
                svg_parts.append(
                    f'<circle cx="{xx}" cy="{yy}" r="3.5" fill="{CORPUS_COLORS[i]}"><title>{tooltip}</title></circle>'
                )
            else:
                bar_width = step * 0.25
                svg_parts.append(
                    f'<rect x="{xx - step * 0.375 + i * bar_width}" y="{yy}" width="{bar_width - 1}" height="{y + plot_height - yy}" fill="{CORPUS_COLORS[i]}"><title>{tooltip}</title></rect>'
                )
        if style == "line":
            svg_parts.append(
                f"""<polyline points="{' '.join(points)}" fill="none" stroke="{CORPUS_COLORS[i]}" stroke-width="2.7"/>"""
            )
    svg_parts.extend(
        [
            f'<text x="{x + plot_width / 2}" y="{y + plot_height + 54}" text-anchor="middle" font-size="15">Word length (letters / EVA units)</text>',
            '<text x="50" y="706" class="muted">Full-edition comparison: Forme includes introduction, notes, glossary and appendices; Orationum includes editorial apparatus.</text>',
            '<text x="50" y="730" class="muted">OCR noise is retained; page markers and “Digitized by Google” are removed. Gutenberg wrapper removed; line-end hyphens joined.</text>',
            '<text x="50" y="754" class="muted">Latin/English: Unicode letters counted; internal apostrophes do not add length. Other punctuation splits words; Roman numerals remain.</text>',
            '<text x="50" y="778" class="muted">VMS: ZL3b text loci; uncertain words omitted. Grouped EVA treats ch, sh, cfh, ckh, cph, cth as one unit; iin remains three.</text>',
            '<text x="50" y="802" class="muted">Repeated word occurrences are counted. Each corpus sums to 100%. Last bin combines lengths ≥25; CSV retains every exact length.</text>',
            "</svg>",
        ]
    )
    return "".join(svg_parts)


def main():
    data_dir, output_dir = paths(__doc__)
    distributions, summaries = load_distributions(data_dir)
    write_distribution_csv(output_dir / "word_length_comparison.csv", distributions)
    peak = max(
        100 * count / sum(counts.values())
        for counts in distributions.values()
        for count in counts.values()
    )
    ceiling = int(peak // 5 + 1) * 5
    views = {}
    for mode in ["grouped", "letters"]:
        names = [
            "VMS · grouped EVA" if mode == "grouped" else "VMS · EVA letters",
            "Forme of Cury",
            "Corpus orationum",
        ]
        for style in ["line", "bars"]:
            views[mode + "_" + style] = render_length_chart(
                names, summaries, distributions, style, ceiling
            )
    (output_dir / "word_length_comparison.svg").write_text(views["grouped_line"])
    page = read_template("word_lengths.html")
    page = page.replace("DEFAULT", views["grouped_line"]).replace(
        "DATA", json.dumps(views)
    )
    (output_dir / "word_length_comparison.html").write_text(page)
    (output_dir / "length_stats.json").write_text(json.dumps(summaries, indent=2))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
