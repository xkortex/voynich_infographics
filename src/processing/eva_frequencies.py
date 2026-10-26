"""Generate EVA frequencies, embedded glyph paths, and the standalone HTML chart."""

import hashlib
import json
from collections import Counter
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from config import paths, read_template
from eva import LETTERS, GROUPED_FORMS, readable_spans, tokenize


def render_glyph(token, glyph_set, character_map):
    connected_form = {
        "sh": "Sh",
        "cfh": "cFh",
        "ckh": "cKh",
        "cph": "cPh",
        "cth": "cTh",
    }.get(token, token)
    path_pen = SVGPathPen(glyph_set)
    advance = 0
    for character in connected_form:
        font_glyph = glyph_set[character_map[ord(character)]]
        font_glyph.draw(TransformPen(path_pen, (1, 0, 0, 1, advance, 0)))
        advance += font_glyph.width
    return (
        '<svg aria-hidden="true" viewBox="-250 -150 '
        + str(advance + 500)
        + ' 1900"><g transform="translate(0 1200) scale(1 -1)"><path d="'
        + path_pen.getCommands()
        + '"/></g></svg>'
    )


def render_rows(mode, frequencies, glyphs):
    ordered_symbols = sorted(
        frequencies[mode], key=lambda x: (-x["count"], x["symbol"])
    )
    total = sum((x["count"] for x in ordered_symbols))
    maximum_count = max((x["count"] for x in ordered_symbols))
    return "".join(
        (
            f"""<tr><th scope="row"><span class="glyph">{glyphs[item['symbol']]}</span><code>{item['symbol']}</code></th><td><div class="track"><div class="bar" style="width:{item['count'] / maximum_count * 100}%"></div></div></td><td class="num">{item['count']:,}</td><td class="num">{item['count'] / total * 100:.3f}%</td></tr>"""
            for item in ordered_symbols
        )
    )


def count_symbols(segments):
    """Count readable spans under both segmentation conventions."""
    return {
        "letters": Counter("".join(segments)),
        "groups": Counter(token for segment in segments for token in tokenize(segment)),
    }


def main():
    data_dir, output_dir = paths(__doc__)
    transcription_path = data_dir / "transcription.txt"
    segments, locus_count, alternative_count, rare_count = readable_spans(
        transcription_path.read_text()
    )
    counts = count_symbols(segments)
    all_symbols = LETTERS + GROUPED_FORMS
    with TTFont(data_dir / "EVA2.ttf") as font:
        glyph_set = font.getGlyphSet()
        character_map = font.getBestCmap()
        glyphs = {
            symbol: render_glyph(symbol, glyph_set, character_map)
            for symbol in all_symbols
        }
    frequencies = {
        mode: [
            {"symbol": symbol, "count": counter.get(symbol, 0)}
            for symbol in (LETTERS if mode == "letters" else all_symbols)
        ]
        for mode, counter in counts.items()
    }
    replacements = {
        "TOTAL": f"{sum(counts['groups'].values()):,}",
        "LINES": str(locus_count),
        "ROWS": render_rows("groups", frequencies, glyphs),
        "ALT": str(alternative_count),
        "RARE": str(rare_count),
        "HASH": hashlib.sha256(transcription_path.read_bytes()).hexdigest(),
        "DATA": json.dumps(frequencies),
        "GLYPHS": json.dumps(glyphs),
    }
    page = read_template("eva_frequencies.html")
    for placeholder, value in replacements.items():
        page = page.replace(placeholder, value)
    (output_dir / "voynich_eva_frequency.html").write_text(page)
    (output_dir / "counts.json").write_text(json.dumps(frequencies))
    print(
        f"EVA frequencies: {locus_count:,} loci; "
        f"{sum(counts['letters'].values()):,} letters; "
        f"{sum(counts['groups'].values()):,} grouped tokens"
    )


if __name__ == "__main__":
    main()
