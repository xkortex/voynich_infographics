"""Assemble the buildless gallery from standalone chart artifacts."""

import argparse
import json
import re
import shutil
from pathlib import Path
from config import ROOT, read_template
from provenance import annotate
from reading_text import install_gallery_entry
from structural_statistics import install_structural_entry
from word_frequencies import install_frequency_entry

CHARTS = [
    (
        "eva-frequencies",
        "EVA symbol frequencies",
        "How often does each sign occur?",
        "Compare glyph counts, sort the alphabet, and switch between individual EVA letters and grouped forms.",
        "voynich_eva_frequency",
        None,
    ),
    (
        "word-positions",
        "Where symbols occur within words",
        "Beginning, middle, or end?",
        "Small area charts reveal each sign’s positional profile. Compare grouped forms or individual EVA letters on independent or shared scales.",
        "voynich_eva_word_positions",
        "voynich_eva_word_positions.png",
    ),
    (
        "word-lengths",
        "Word lengths across corpora",
        "VMS, Forme of Cury, and Orationum",
        "Compare normalized word-length distributions, switch between lines and histograms, and inspect the effect of EVA segmentation.",
        "word_length_comparison",
        "word_length_comparison.png",
    ),
]


def copy_chart_pages(site_dir, artifacts_dir, charts, navigation_style):
    """Copy standalone charts and downloads, then add shared navigation."""
    for slug, title, kicker, description, artifact_name, preview in charts:
        page_dir = site_dir / "pages" / slug
        downloads_dir = page_dir / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        chart_html = (artifacts_dir / (artifact_name + ".html")).read_text()
        nav = (
            navigation_style
            + f'<nav class="atlas-nav" aria-label="Atlas navigation"><a href="../../index.html">← Voynich infographics</a><span class="atlas-links"><a href="downloads/{artifact_name}.html" download>Standalone HTML ↓</a>'
        )
        for ext in ["png", "svg", "csv"]:
            artifact_path = artifacts_dir / (artifact_name + "." + ext)
            if artifact_path.exists():
                shutil.copy2(artifact_path, downloads_dir / artifact_path.name)
                nav += f'<a href="downloads/{artifact_path.name}" download>{ext.upper()} ↓</a>'
        nav += "</span></nav>"
        # Position/length charts put controls before <main>; frequency controls
        # are inside <main>. Insert the site navigation above either layout.
        anchor = (
            '<nav id="controls"'
            if slug in {"word-positions", "word-lengths"}
            else "<main"
        )
        chart_html = chart_html.replace(anchor, nav + anchor, 1)
        (page_dir / "index.html").write_text(chart_html)
        shutil.copy2(
            artifacts_dir / (artifact_name + ".html"),
            downloads_dir / (artifact_name + ".html"),
        )
        if preview:
            shutil.copy2(artifacts_dir / preview, site_dir / "assets" / preview)


def build_frequency_preview(site_dir, artifacts_dir):
    """Generate the small vector frequency preview for the gallery."""
    frequencies = json.loads(
        re.search(
            '<script id="reference" type="application/json">(.*?)</script>',
            (artifacts_dir / "voynich_eva_frequency.html").read_text(),
            re.S,
        )[1]
    )["groups"]
    frequencies = sorted(frequencies, key=lambda r: -r["count"])[:9]
    maximum_count = max((x["count"] for x in frequencies))
    preview_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 410"><rect width="700" height="410" fill="#fffdf7"/><text x="36" y="50" font-family="Georgia,serif" font-size="27" fill="#253d38">The most frequent EVA forms</text>'
    for chart_number, row in enumerate(frequencies):
        y = 76 + chart_number * 34
        preview_svg += f"""<text x="36" y="{y + 19}" font-family="monospace" font-size="17" fill="#253d38">{row['symbol']}</text><rect x="83" y="{y}" width="{row['count'] / maximum_count * 470}" height="22" rx="3" fill="#277b72"/><text x="650" y="{y + 18}" font-family="system-ui,sans-serif" font-size="14" text-anchor="end" fill="#62716c">{row['count']:,}</text>"""
    preview_svg += "</svg>"
    (site_dir / "assets/eva-frequency-preview.svg").write_text(preview_svg)


def build_gallery_pages(site_dir, charts):
    """Write the gallery, shared CSS, credits, and GitHub Pages marker."""
    stylesheet = read_template("gallery.css")
    (site_dir / "assets/site.css").write_text(stylesheet)
    entries = []
    for chart_number, (
        slug,
        title,
        kicker,
        description,
        artifact_name,
        preview,
    ) in enumerate(charts, 1):
        image = preview or "eva-frequency-preview.svg"
        entries.append(
            f"""<article class="entry"><a class="preview" href="pages/{slug}/" aria-label="Open {title}"><img src="assets/{image}" alt="Preview of {title}" {('loading=lazy' if chart_number > 1 else '')}></a><div><div class="eyebrow">0{chart_number} / {kicker}</div><h2>{title}</h2><p>{description}</p><a class="open" href="pages/{slug}/">Explore chart →</a><p class="download"><a href="pages/{slug}/downloads/{artifact_name}.html" download>Download standalone HTML</a></p></div></article>"""
        )
    gallery_html = (
        read_template("gallery_intro.html")
        + "".join(entries)
        + read_template("gallery_footer.html")
    )
    (site_dir / "index.html").write_text(gallery_html)
    (site_dir / "credits.html").write_text(read_template("credits.html"))
    (site_dir / ".nojekyll").touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "generated")
    artifacts_dir = parser.parse_args().artifacts
    site_dir = ROOT / "docs"
    (site_dir / "assets").mkdir(parents=True, exist_ok=True)
    copy_chart_pages(site_dir, artifacts_dir, CHARTS, read_template("navigation.html"))
    build_frequency_preview(site_dir, artifacts_dir)
    build_gallery_pages(site_dir, CHARTS)
    annotate(ROOT, artifacts_dir)
    if (site_dir / "pages/reading-text/index.html").exists():
        install_gallery_entry(site_dir)
    if (site_dir / "pages/structural-statistics/index.html").exists():
        install_structural_entry(site_dir)
    if (site_dir / "pages/word-frequencies/index.html").exists():
        install_frequency_entry(site_dir)
    print("Site assembled with provenance:", site_dir)


if __name__ == "__main__":
    main()
