from pathlib import Path
import shutil,json,re
import argparse
repo=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description='Assemble docs/ from generated infographic artifacts')
p.add_argument('--artifacts',type=Path,default=repo/'generated')
source=p.parse_args().artifacts
site=repo/'docs'
(site/'assets').mkdir(parents=True,exist_ok=True)
items=[('eva-frequencies','EVA symbol frequencies','How often does each sign occur?','Compare glyph counts, sort the alphabet, and switch between individual EVA letters and grouped forms.','voynich_eva_frequency',None),('word-positions','Where symbols occur within words','Beginning, middle, or end?','Small area charts reveal each sign’s positional profile. Compare grouped forms or individual EVA letters on independent or shared scales.','voynich_eva_word_positions','voynich_eva_word_positions.png'),('word-lengths','Word lengths across corpora','VMS, Forme of Cury, and Orationum','Compare normalized word-length distributions, switch between lines and histograms, and inspect the effect of EVA segmentation.','word_length_comparison','word_length_comparison.png')]
navstyle='''<style>.atlas-nav{box-sizing:border-box;display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding:12px 24px;background:#203c37;color:#fffdf6;font:14px/1.5 system-ui,sans-serif!important;max-width:none!important;margin:0!important}.atlas-nav a{color:#fffdf6!important;text-decoration:none}.atlas-nav a:hover{text-decoration:underline}.atlas-nav .atlas-links{margin-left:auto;display:flex;gap:16px;flex-wrap:wrap}@media print{.atlas-nav{display:none!important}}</style>'''
for slug,title,kicker,desc,stem,preview in items:
 folder=site/'pages'/slug;dl=folder/'downloads';dl.mkdir(parents=True,exist_ok=True)
 original=(source/(stem+'.html')).read_text()
 nav=navstyle+f'<nav class="atlas-nav" aria-label="Atlas navigation"><a href="../../index.html">← Voynich infographics</a><span class="atlas-links"><a href="downloads/{stem}.html" download>Standalone HTML ↓</a>'
 for ext in ['png','svg','csv']:
  p=source/(stem+'.'+ext)
  if p.exists():
   shutil.copy2(p,dl/p.name);nav+=f'<a href="downloads/{p.name}" download>{ext.upper()} ↓</a>'
 nav+='</span></nav>'
 if slug=='word-lengths':
  # Its companion CSV carries an additional suffix.
  p=source/'word_length_comparison.csv'
  if not (dl/p.name).exists():shutil.copy2(p,dl/p.name)
 # Insert after CSS so existing standalone stylesheet selectors remain intact.
 original=original.replace('<main',nav+'<main',1) if slug!='word-lengths' else original.replace('<nav id="controls"',nav+'<nav id="controls"',1)
 # word-position standalone has controls before main: place global navigation before those controls.
 if slug=='word-positions':
  original=original.replace(nav+'<main','<main',1).replace('<nav id="controls"',nav+'<nav id="controls"',1)
 (folder/'index.html').write_text(original)
 shutil.copy2(source/(stem+'.html'),dl/(stem+'.html'))
 if preview:shutil.copy2(source/preview,site/'assets'/preview)
# A vector preview for the frequency chart, using the embedded reference data.
freq=json.loads(re.search(r'<script id="reference" type="application/json">(.*?)</script>',(source/'voynich_eva_frequency.html').read_text(),re.S)[1])['groups']
freq=sorted(freq,key=lambda r:-r['count'])[:9];maximum=max(x['count'] for x in freq)
svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 410"><rect width="700" height="410" fill="#fffdf7"/><text x="36" y="50" font-family="Georgia,serif" font-size="27" fill="#253d38">The most frequent EVA forms</text>'
for i,row in enumerate(freq):
 y=76+i*34;svg+=f'<text x="36" y="{y+19}" font-family="monospace" font-size="17" fill="#253d38">{row["symbol"]}</text><rect x="83" y="{y}" width="{row["count"]/maximum*470}" height="22" rx="3" fill="#277b72"/><text x="650" y="{y+18}" font-family="system-ui,sans-serif" font-size="14" text-anchor="end" fill="#62716c">{row["count"]:,}</text>'
svg+='</svg>'; (site/'assets/eva-frequency-preview.svg').write_text(svg)
css='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f3eb;color:#243c36;font:17px/1.65 system-ui,sans-serif}a{color:#216f63;text-underline-offset:4px}a:focus-visible{outline:3px solid #cc7836;outline-offset:5px}header,main,footer{max-width:1140px;margin:auto;padding:28px}.masthead{display:flex;justify-content:space-between;border-bottom:1px solid #cbd4c8;font-size:14px}.masthead a{color:inherit}.eyebrow{text-transform:uppercase;font-size:12px;letter-spacing:.18em;color:#527269;font-weight:700}.intro{padding:55px 0 30px;max-width:850px}h1{font:clamp(44px,7vw,78px)/1.1 Georgia,serif;margin:14px 0 24px;font-weight:400;letter-spacing:-.035em}h2{font:32px/1.2 Georgia,serif;margin:10px 0 16px}h3{font:24px Georgia,serif}.intro p{font-size:20px;color:#5e7068;max-width:760px}.entry{display:grid;grid-template-columns:1.1fr 1fr;gap:40px;align-items:center;padding:40px 0;border-top:1px solid #cbd4c8}.entry p{color:#5e7068}.preview{background:#fffdf7;border:1px solid #dbe0d4;border-radius:8px;overflow:hidden;display:block;height:295px}.preview img{display:block;width:100%;height:100%;object-fit:cover;object-position:top}.entry:last-child .preview img{object-fit:contain}.open{display:inline-block;background:#244f45;color:white;padding:10px 20px;border-radius:5px;text-decoration:none}.open:hover{background:#35705f}.download{font-size:14px;margin-top:16px}.notes{background:#e9eee4;border-radius:8px;padding:28px;margin:26px 0 10px}.notes p{max-width:900px;color:#52665d}footer{font-size:13px;border-top:1px solid #cbd4c8;color:#63726a;margin-top:35px;padding-bottom:45px}@media(max-width:700px){header,main,footer{padding:20px}.intro{padding:30px 0 18px}.entry{grid-template-columns:1fr;gap:20px}.preview{height:260px}.intro p{font-size:18px}.masthead{gap:16px;flex-wrap:wrap}}'''
(site/'assets/site.css').write_text(css)
entries=[]
for i,(slug,title,kicker,desc,stem,preview) in enumerate(items,1):
 image=preview or 'eva-frequency-preview.svg'
 entries.append(f'<article class="entry"><a class="preview" href="pages/{slug}/" aria-label="Open {title}"><img src="assets/{image}" alt="Preview of {title}" {"loading=lazy" if i>1 else ""}></a><div><div class="eyebrow">0{i} / {kicker}</div><h2>{title}</h2><p>{desc}</p><a class="open" href="pages/{slug}/">Explore chart →</a><p class="download"><a href="pages/{slug}/downloads/{stem}.html" download>Download standalone HTML</a></p></div></article>')
index='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Interactive visual references for the Voynich manuscript: EVA frequencies, word positions, and corpus word-length comparisons."><title>Voynich infographics</title><link rel="stylesheet" href="assets/site.css"><header><div class="masthead"><span>VOYNICH INFOGRAPHICS</span><a href="https://github.com/xkortex/voynich_infographics">Source on GitHub ↗</a></div><div class="intro"><div class="eyebrow">A visual notebook for an undeciphered manuscript</div><h1>Explore the patterns<br>in the script.</h1><p>Interactive charts for looking closely at the Voynich manuscript—its signs, their positions, and the shapes of its words. Every chart also works as a standalone download.</p></div></header><main>'''+''.join(entries)+'''<section class="notes"><h3>Read the patterns with their assumptions.</h3><p>EVA is a transliteration system, not a decipherment. Grouping signs changes the units being counted. Each chart explains its segmentation and cleaning rules; counts can differ between charts when uncertain words are excluded differently.</p><p>The VMS charts use Zandbergen–Landini 3b. The word-length comparison uses the supplied full editions of <i>Forme of Cury</i> and <i>Corpus orationum</i>, including editorial material and OCR noise. These charts are exploratory references.</p></section></main><footer>Created by Mike McDermott · Data and glyph credits accompany each chart. <a href="credits.html">Sources &amp; licensing</a></footer></html>'''
(site/'index.html').write_text(index)
(site/'credits.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sources &amp; licensing · Voynich infographics</title><link rel="stylesheet" href="assets/site.css"><main><a href="index.html">← All infographics</a><h1>Sources &amp; licensing</h1><p>Site code is covered by the repository’s MIT license. Third-party data and glyph artwork retain their own terms and are not relicensed by that license.</p><h2>Voynich data</h2><p>René Zandbergen and Gabriel Landini, ZL3b transliteration, 13 May 2025. The transliteration is offered as CC0. See <a href="https://voynich.nu/transcr.html">transliteration documentation</a>. Exact source links and cleaning decisions appear in each chart.</p><h2>Glyph artwork</h2><p>Glyph outlines are derived from Gabriel Landini’s EVA2 font (2025). The font and derived outlines are third-party copyrighted artwork, separate from the MIT-licensed site code. The source describes private use and restricts commercial use; see <a href="https://voynich.nu/roadmap.html">the font credits and terms</a>. This project does not grant additional rights to the glyph artwork.</p><h2>Comparison texts</h2><p>The word-length comparison uses Project Gutenberg ebook 8102, <i>The Forme of Cury</i>, and user-supplied OCR from <i>Corpus orationum</i>, CCSL 160 (A–C). Only aggregate word-length counts and chart graphics are included here; the supplied text files are not redistributed.</p></main></html>''')
(site/'.nojekyll').touch()

from provenance import annotate
annotate(repo, source)
print('Site assembled with provenance:',site)
