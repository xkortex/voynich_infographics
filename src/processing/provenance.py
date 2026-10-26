"""Attach the code → methodology → source-data trail to each static chart."""

import json
import re
from config import read_template

REPOSITORY_FILES = "https://github.com/xkortex/voynich_infographics/blob/main/"
CHARTS = {
    "eva-frequencies": ("eva_frequencies.py", "voynich_eva_frequency"),
    "word-positions": ("word_positions.py", "voynich_eva_word_positions"),
    "word-lengths": ("word_lengths.py", "word_length_comparison"),
}


def shared_links():
    """Links shared by the chart trail and the site-wide methodology page."""
    return (
        f'<a href="{REPOSITORY_FILES}src/processing/README.md">Reproduce these charts</a> · '
        f'<a href="{REPOSITORY_FILES}src/processing/SOURCE_DATA.md">Source acquisition &amp; rights</a>'
    )


def insert_chart_trail(chart_path, script_name):
    """Replace an existing trail, so repeated assembly never duplicates it."""
    document = chart_path.read_text()
    document = re.sub(
        r'<aside class="processing-provenance".*?</aside>', "", document, flags=re.S
    )
    trail = read_template("chart_provenance.html")
    trail = trail.replace(
        "SCRIPT_URL", REPOSITORY_FILES + "src/processing/" + script_name
    )
    trail = trail.replace("SHARED_LINKS", shared_links())
    closing_main = document.rfind("</main>")
    insertion = closing_main + len("</main>") if closing_main >= 0 else len(document)
    chart_path.write_text(document[:insertion] + trail + document[insertion:])


def insert_gallery_trail(page_path):
    """Add a methodology link to the index or credits, once."""
    document = page_path.read_text()
    if 'class="site-provenance"' in document:
        return
    trail = (
        '<section class="site-provenance notes"><h3>Follow the analysis</h3><p>'
        + shared_links()
        + ' · <a href="provenance.html">Methods &amp; limitations</a></p></section>'
    )
    closing_main = document.rfind("</main>")
    page_path.write_text(document[:closing_main] + trail + document[closing_main:])


def write_provenance_page(site_dir):
    """Render the human-readable explanation of methods and remaining source gaps."""
    chart_links = "".join(
        f'<li><a href="pages/{slug}/">{slug}</a> → '
        f'<a href="{REPOSITORY_FILES}src/processing/{script}">{script}</a></li>'
        for slug, (script, _) in CHARTS.items()
    )
    document = read_template("provenance_page.html")
    document = document.replace("SHARED_LINKS", shared_links()).replace(
        "CHART_LINKS", chart_links
    )
    (site_dir / "provenance.html").write_text(document)


def annotate(repository_dir, artifacts_dir=None):
    """Attach trails and publish input fingerprints, never the input corpus bytes.

    artifacts_dir is accepted for compatibility with existing assembly commands;
    all provenance comes from the tracked source manifest and chart definitions.
    """
    site_dir = repository_dir / "docs"
    for slug, (script_name, artifact_name) in CHARTS.items():
        chart_dir = site_dir / "pages" / slug
        for chart_path in [
            chart_dir / "index.html",
            chart_dir / "downloads" / (artifact_name + ".html"),
        ]:
            insert_chart_trail(chart_path, script_name)
    for filename in ["index.html", "credits.html"]:
        insert_gallery_trail(site_dir / filename)
    manifest = json.loads((repository_dir / "src/processing/sources.json").read_text())
    (site_dir / "assets/input-fingerprints.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    write_provenance_page(site_dir)
