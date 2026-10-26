"""Build a reflowable reading edition from the Voynichese Project XML.

The XML, not ZL3b, defines text and word order here. Geometry is not used to
invent paragraph or line boundaries. This is a reading edition, not a facsimile.
"""

import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

from config import ROOT, TEMPLATE_DIR, read_template

COPYRIGHT = "Copyright (C) 2014 The Voynichese Project"
SOURCE_URL = "https://github.com/voynichese/voynichese"


def folio_sort_key(name):
    match = re.fullmatch(r"f(\d+)([rv])(\d*)", name)
    if match is None:
        raise ValueError(f"Unrecognized folio name: {name}")
    number, side, panel = match.groups()
    return int(number), side, int(panel or 0)


def viewer_link(folio, word=None):
    """The viewer supports exact-spelling queries, not unique occurrence IDs.

    Its trailing numeric fragment is a scroll offset, NOT an XML word index.
    A repeated spelling is highlighted at every occurrence on the selected folio.
    """
    fragment = f"/{folio}"
    if word is not None:
        fragment += "/exa:" + quote(word, safe="")
    return "https://www.voynichese.com/#" + fragment


def read_folios(xml_dir):
    folios = []
    fingerprints = {}
    for path in xml_dir.glob("*.xml"):
        original = path.read_bytes()
        if b"Apache License, Version 2.0" not in original:
            raise ValueError(f"Missing expected source license notice: {path.name}")
        root = ET.fromstring(original)
        name = root.attrib["name"]
        words = []
        for element in root.findall("word"):
            word = element.text or ""
            if not re.fullmatch(r"[a-z]+", word):
                raise ValueError(
                    f"Unsupported transcription text: {path.name}: {word!r}"
                )
            words.append({"index": int(element.attrib["index"]), "eva": word})
        indices = [word["index"] for word in words]
        if len(set(indices)) != len(indices):
            raise ValueError(f"Duplicate word indices in {path.name}")
        if len(words) != int(root.attrib["wordCount"]):
            raise ValueError(f"Word-count header mismatch in {path.name}")
        folios.append({"folio": name, "words": words})
        fingerprints[path.name] = hashlib.sha256(original).hexdigest()
    folios.sort(key=lambda folio: folio_sort_key(folio["folio"]))
    if not folios:
        raise ValueError(f"No folio XML found in {xml_dir}")
    return folios, fingerprints


def extract_glyphs(font_path):
    """Share font-derived outlines as small text data; do not bundle a font binary."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    glyphs = {}
    with TTFont(font_path) as font:
        glyph_set = font.getGlyphSet()
        character_map = font.getBestCmap()
        for character in "abcdefghijklmnopqrstuvxyzFKPST":
            glyph = glyph_set[character_map[ord(character)]]
            pen = SVGPathPen(glyph_set)
            glyph.draw(pen)
            glyphs[character] = {"path": pen.getCommands(), "advance": glyph.width}
    return glyphs


def install_gallery_entry(site_dir):
    """Idempotent so either rebuilding the gallery or just the reader is safe."""
    index_path = site_dir / "index.html"
    if not index_path.exists():
        return
    page = index_path.read_text()
    page = re.sub(
        r"<!-- READER ENTRY -->.*?<!-- END READER ENTRY -->", "", page, flags=re.S
    )
    entry = read_template("reading_gallery_entry.html")
    page = page.replace('<section class="notes">', entry + '<section class="notes">', 1)
    index_path.write_text(page)


def build_reader(xml_dir, font_path, site_dir):
    folios, fingerprints = read_folios(xml_dir)
    reader_dir = site_dir / "pages/reading-text"
    data_dir = reader_dir / "folios"
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for folio in folios:
        name = folio["folio"]
        (data_dir / f"{name}.json").write_text(
            json.dumps(folio, separators=(",", ":")) + "\n"
        )
        manifest.append({"folio": name, "words": len(folio["words"])})
    (reader_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (reader_dir / "glyphs.json").write_text(
        json.dumps(extract_glyphs(font_path), separators=(",", ":")) + "\n"
    )
    options = "".join(
        f'<option value="{item["folio"]}">{item["folio"]}</option>' for item in manifest
    )
    sections = "".join(
        f'<section class="folio" id="{item["folio"]}" data-folio="{item["folio"]}">'
        f'<header class="folio-heading"><h2>{item["folio"]}</h2>'
        f'<a href="{viewer_link(item["folio"])}" target="_blank" rel="noopener">View manuscript ↗</a></header>'
        f'<p class="folio-placeholder">{item["words"]:,} words · <button class="load-folio" type="button">Load folio</button></p>'
        "</section>"
        for item in manifest
    )
    page = read_template("reading_text.html")
    for key, value in {
        "READER_STYLE_VERSION": hashlib.sha256((TEMPLATE_DIR / "reading_text.css").read_bytes()).hexdigest()[:12],
        "READER_SCRIPT_VERSION": hashlib.sha256((TEMPLATE_DIR / "reading_text.js").read_bytes()).hexdigest()[:12],
        "FOLIO_OPTIONS": options,
        "FOLIO_SECTIONS": sections,
        "FOLIO_COUNT": str(len(folios)),
        "WORD_COUNT": f'{sum(len(folio["words"]) for folio in folios):,}',
    }.items():
        page = page.replace(key, value)
    (reader_dir / "index.html").write_text(page)
    for extension in ["css", "js"]:
        shutil.copy2(
            TEMPLATE_DIR / f"reading_text.{extension}",
            reader_dir / f"reader.{extension}",
        )
    notice = read_template("reading_NOTICE.txt")
    (reader_dir / "NOTICE.txt").write_text(notice)
    shutil.copy2(TEMPLATE_DIR / "APACHE-2.0.txt", reader_dir / "APACHE-2.0.txt")
    (reader_dir / "source-manifest.json").write_text(
        json.dumps(
            {
                "source": SOURCE_URL,
                "source_archive_url": "https://www.voynichese.com/1/data/folio/voynichese_data.zip",
                "copyright": COPYRIGHT,
                "license": "Apache-2.0 (notice in each supplied XML)",
                "transformation": "Keep XML word order and indices; omit image coordinates; group by folio. No normalization or uncertain-word filtering.",
                "xml_sha256": dict(sorted(fingerprints.items())),
                "font_sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
                "viewer_links": "#/FOLIO/exa:EVA highlights exact spelling; numeric fragments are scroll offsets, not word IDs.",
                "notices": "NOTICE.txt; APACHE-2.0.txt; existing site glyph rights caveat",
            },
            indent=2,
        )
        + "\n"
    )
    install_gallery_entry(site_dir)
    print(
        f"Reader: {len(folios)} folios, {sum(len(folio['words']) for folio in folios):,} words"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path, default=ROOT / "data/local/EVA2.ttf")
    parser.add_argument("--site-dir", type=Path, default=ROOT / "docs")
    arguments = parser.parse_args()
    build_reader(arguments.xml_dir, arguments.font, arguments.site_dir)


if __name__ == "__main__":
    main()
