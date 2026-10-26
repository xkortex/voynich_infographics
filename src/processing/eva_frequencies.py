"""Generate eva frequencies artifacts. See README.md."""
import re,json,html,hashlib
from collections import Counter
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from pathlib import Path
from config import paths
data_dir, output_dir = paths(__doc__)
raw=(data_dir/'transcription.txt').read_text()
segments=[]; lines=0; alternatives=0; rare=0
for line in raw.splitlines():
 m=re.match(r'^<f[^>]*\.[^>]*>\s*(.*)',line)
 if not m: continue
 lines+=1; s=m[1]
 s=re.sub(r'<[^>]*>',' ',s)
 alternatives+=len(re.findall(r'\[[^\]]*\]',s));s=re.sub(r'\[[^\]]*\]',' ',s)
 rare+=len(re.findall(r'@\d+;',s));s=re.sub(r'@\d+;',' ',s)
 s=s.replace('{','').replace('}','').lower()
 segments+=re.findall('[a-vxyz]+',s)
letters=list('abcdefghijklmnopqrstuvxyz')
compound=['cfh','ckh','cph','cth','ch','sh']
counts={'letters':Counter(''.join(segments)),'groups':Counter(t for s in segments for t in re.findall('|'.join(compound)+r'|[a-vxyz]',s))}
font=TTFont(data_dir/'EVA2.ttf');gs=font.getGlyphSet();cmap=font.getBestCmap()
def glyph(token):
 display={'sh':'Sh','cfh':'cFh','ckh':'cKh','cph':'cPh','cth':'cTh'}.get(token,token)
 pen=SVGPathPen(gs);x=0
 for c in display:
  g=gs[cmap[ord(c)]];g.draw(TransformPen(pen,(1,0,0,1,x,0)));x+=g.width
 # Stable bounds include ascending and descending shapes
 return '<svg aria-hidden="true" viewBox="-250 -150 '+str(x+500)+' 1900"><g transform="translate(0 1200) scale(1 -1)"><path d="'+pen.getCommands()+'"/></g></svg>'
glyphs={s:glyph(s) for s in letters+compound}
data={k:[{'symbol':s,'count':c.get(s,0)} for s in (letters if k=='letters' else letters+compound)] for k,c in counts.items()}
def rows(mode):
 a=sorted(data[mode],key=lambda x:(-x['count'],x['symbol']));total=sum(x['count'] for x in a);maxi=max(x['count'] for x in a)
 return ''.join(f'<tr><th scope="row"><span class="glyph">{glyphs[v["symbol"]]}</span><code>{v["symbol"]}</code></th><td><div class="track"><div class="bar" style="width:{v["count"]/maxi*100}%"></div></div></td><td class="num">{v["count"]:,}</td><td class="num">{v["count"]/total*100:.3f}%</td></tr>' for v in a)
total=sum(counts['groups'].values())
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Voynich • EVA frequency atlas</title>
<style>
:root{color-scheme:light;--ink:#243b38;--muted:#61716c;--accent:#277b72}*{box-sizing:border-box}body{margin:0;background:#f6f3eb;color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:48px 28px}header{border-bottom:1px solid #ced5cc;padding-bottom:22px}.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700}h1{font-family:Georgia,serif;font-size:clamp(32px,5vw,54px);font-weight:400;line-height:1.15;margin:12px 0}p{max-width:850px}.muted{color:var(--muted)}.stats{display:flex;gap:36px;flex-wrap:wrap;margin:26px 0}.stats strong{display:block;font-size:26px}.stats span{font-size:13px;color:var(--muted)}.controls{display:flex;align-items:end;gap:18px;flex-wrap:wrap;margin:24px 0}.controls[hidden]{display:none}label{font-size:13px;font-weight:600}select,button{display:block;margin-top:5px;padding:10px;border:1px solid #a6b7ac;border-radius:6px;background:white;color:var(--ink);font:inherit}button{cursor:pointer}button:hover{background:#e6f0e8}button:focus-visible,select:focus-visible{outline:3px solid #d98f43}table{width:100%;border-collapse:collapse;background:#fffdf8;table-layout:fixed}th,td{padding:5px 14px;border-bottom:1px solid #e5e8df}thead th{text-align:left;font-size:12px;color:var(--muted);padding:14px}thead th:first-child{width:138px}thead th:nth-child(3){width:110px}thead th:last-child{width:95px}tbody th{display:flex;align-items:center;gap:12px;height:62px;text-align:left;font-weight:400}.glyph{display:inline-flex;width:62px;height:52px;justify-content:center}.glyph svg{width:100%;height:100%;fill:var(--ink)}code{font:14px ui-monospace,monospace}.num{text-align:right;font-variant-numeric:tabular-nums;font-size:14px}.track{height:22px;background:#edf2eb;border-radius:3px;overflow:hidden}.bar{height:100%;background:var(--accent);border-radius:3px;min-width:0}details{margin-top:25px;border-top:1px solid #ccd5cb;padding-top:20px}summary{cursor:pointer;font-weight:650}a{color:#1b7168}footer{font-size:12px;color:var(--muted);margin-top:26px}#status{font-size:13px} @media(max-width:600px){main{padding:25px 12px}th,td{padding:4px 6px}thead th:first-child{width:100px}thead th:nth-child(3){width:75px}thead th:last-child{width:73px}.glyph{width:45px}tbody th{gap:6px}.num{font-size:12px}}@media print{.controls{display:none}body{background:white}main{padding:0}tr{break-inside:avoid}}
</style><main><header><div class="eyebrow">Voynich manuscript / reference atlas</div><h1>EVA symbol frequencies</h1><p class="muted">Actual Voynich glyph shapes alongside their EVA codes. An offline reference built from the Zandbergen–Landini transliteration, version 3b (13 May 2025).</p></header>
<div class="stats"><div><strong id="total">TOTAL</strong><span id="unit">counted grouped tokens</span></div><div><strong>LINES</strong><span>transcribed text lines</span></div><div><strong>100% offline</strong><span>embedded data + vector glyphs</span></div></div>
<div class="controls" id="controls" hidden><label>Counting unit<select id="mode"><option value="groups">Grouped forms (ch, sh, ckh…)</option><option value="letters">Individual EVA letters</option></select></label><label>Order<select id="sort"><option value="frequency">Most frequent first</option><option value="alphabet">EVA alphabetical</option></select></label><label>Bar scale<select id="scale"><option value="linear">Linear</option><option value="log">Logarithmic (1 + count)</option></select></label><button id="download">Download counts (CSV)</button></div>
<p id="status" role="status">Embedded reference data · grouped forms · linear bars. Percentages use all counted tokens in the selected mode.</p><noscript><p>JavaScript is disabled. The complete default chart and counts remain available below.</p></noscript>
<table aria-label="EVA symbol frequency chart"><thead><tr><th>Glyph / EVA</th><th>Frequency <span id="scaleLabel">(linear)</span></th><th class="num">Count</th><th class="num">Share</th></tr></thead><tbody id="chart">ROWS</tbody></table>
<details open><summary>How to read these counts</summary><p>This is a categorical frequency bar chart. EVA encodes written shapes, not known sounds. The choice of what constitutes a single manuscript character is unresolved.</p><p><b>Grouped forms</b> uses longest-match segmentation for cfh, ckh, cph, cth, ch and sh; every remaining EVA letter is counted individually. For example, <code>cth</code> is one token, while <code>iin</code> remains three. <b>Individual letters</b> counts c, t and h separately. A zero row means absent under that counting rule; c and h are often parts of groups.</p><p>All LINES text loci are included (paragraph text, labels and other transcribed items). Headers, comments and inline angle-bracket annotations are removed. ALT ambiguous bracketed alternatives are omitted in full rather than choosing a reading. RARE extended @number; codes are excluded. Curly braces marking ligatures are removed while their contents are retained. Other punctuation and unreadable markers break sequences; no group can cross those boundaries. Case is normalized. The 25 EVA font letter codes a–v and x–z are listed, including zeros. This is a basic-EVA reference, not a catalogue of every rare or extended sign. Percentages are rounded.</p><p>Fallback: the default chart is already written into this HTML. If scripting is disabled or initialization fails, it remains visible. All counts and glyph outlines are embedded; no data fetches, font downloads, chart libraries, or network connection are needed.</p></details>
<details><summary>Sources, credits and reconstruction note</summary><p>Transliteration: René Zandbergen and Gabriel Landini, <a href="https://voynich.nu/data/ZL3b-n.txt">ZL3b-n.txt</a> (CC0), obtained from <a href="https://github.com/Aspect-Research/voynich-autoexploration/blob/master/data/transcriptions/eva_zl3b.txt">this mirrored copy</a>. SHA-256: <code style="overflow-wrap:anywhere">HASH</code>. See <a href="https://voynich.nu/transcr.html">transliteration methodology</a>.</p><p>Glyph outlines: Gabriel Landini’s EVA font, <a href="https://voynich.nu/Fonts/EVA2.ttf">2025 EVA2.ttf</a>. Connected displays use Sh, cFh, cKh, cPh and cTh. Font copyright belongs to Gabriel Landini; use this reference privately and noncommercially. See <a href="https://voynich.nu/roadmap.html">font credits and use terms</a>.</p><p>The original /mnt/data/voynich_eva_frequency.html was unavailable in this session. This file is a standalone reconstruction; the original error’s precise cause could not be established.</p></details><footer>Prepared 25 October 2026 · No external runtime dependencies.</footer></main>
<script id="reference" type="application/json">DATA</script><script id="glyphData" type="application/json">GLYPHS</script>
<script>
(function(){'use strict';
 const chart=document.getElementById('chart'),initial=chart.innerHTML;
 try{
 const data=JSON.parse(document.getElementById('reference').textContent),glyphs=JSON.parse(document.getElementById('glyphData').textContent);
 for(const key of ['letters','groups']){if(!Array.isArray(data[key])||!data[key].length||data[key].some(x=>typeof x.symbol!=='string'||!Number.isSafeInteger(x.count)||x.count<0||!glyphs[x.symbol])||!data[key].some(x=>x.count>0))throw Error('Invalid embedded reference data');}
 const mode=document.getElementById('mode'),sort=document.getElementById('sort'),scale=document.getElementById('scale');
 function render(){
 const a=data[mode.value].slice().sort((a,b)=>sort.value==='alphabet'?a.symbol.localeCompare(b.symbol):b.count-a.count||a.symbol.localeCompare(b.symbol));
 const total=a.reduce((s,x)=>s+x.count,0),max=Math.max(...a.map(x=>x.count)),log=scale.value==='log',frag=document.createDocumentFragment();
 for(const x of a){const tr=document.createElement('tr'),th=document.createElement('th');th.scope='row';const g=document.createElement('span');g.className='glyph';g.innerHTML=glyphs[x.symbol];const code=document.createElement('code');code.textContent=x.symbol;th.append(g,code);tr.append(th);const td=document.createElement('td'),track=document.createElement('div'),bar=document.createElement('div');track.className='track';bar.className='bar';bar.style.width=(100*(log?Math.log1p(x.count)/Math.log1p(max):x.count/max))+'%';track.append(bar);td.append(track);tr.append(td);for(const val of [x.count.toLocaleString('en-US'),(100*x.count/total).toFixed(3)+'%']){const cell=document.createElement('td');cell.className='num';cell.textContent=val;tr.append(cell)}frag.append(tr)}
 chart.replaceChildren(frag);document.getElementById('total').textContent=total.toLocaleString('en-US');document.getElementById('unit').textContent=mode.value==='groups'?'counted grouped tokens':'counted EVA letters';document.getElementById('scaleLabel').textContent=log?'(logarithmic)':'(linear)';document.getElementById('status').textContent='Embedded reference data · '+a.length+' categories · '+(log?'logarithmic':'linear')+' bars. Percentages use all counted tokens in this mode.';
 }
 for(const el of [mode,sort,scale])el.addEventListener('change',render);
 document.getElementById('download').addEventListener('click',()=>{const a=data[mode.value],total=a.reduce((s,x)=>s+x.count,0),csv='eva,count,percent,mode\\n'+a.map(x=>[x.symbol,x.count,(100*x.count/total).toFixed(6),mode.value].join(',')).join('\\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download='voynich_eva_'+mode.value+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 render();document.getElementById('controls').hidden=false;
 }catch(e){chart.innerHTML=initial;document.getElementById('controls').hidden=true;document.getElementById('status').textContent='Interactive controls unavailable. Showing the embedded default chart: grouped forms, linear bars.';}
})();</script></html>'''
for key,val in {'TOTAL':f'{total:,}','LINES':str(lines),'ROWS':rows('groups'),'ALT':str(alternatives),'RARE':str(rare),'HASH':hashlib.sha256((data_dir/'transcription.txt').read_bytes()).hexdigest(),'DATA':json.dumps(data),'GLYPHS':json.dumps(glyphs)}.items():page=page.replace(key,val)
Path(output_dir/'voynich_eva_frequency.html').write_text(page)
(output_dir/'counts.json').write_text(json.dumps(data))
print({'lines':lines,'alternatives':alternatives,'rare':rare,'totals':{k:sum(v.values()) for k,v in counts.items()},'size':len(page)})
