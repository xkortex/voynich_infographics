"""Generate word lengths artifacts. See README.md."""
from pathlib import Path
import re,unicodedata,json,statistics,csv,hashlib,html
from collections import Counter
from config import paths
data_dir, output_dir = paths(__doc__)
out=output_dir
paths={'Forme of Cury':data_dir/'forme_of_cury.txt','Corpus orationum':data_dir/'orationum_ocr.txt'}
data={};meta={}
for name,path in paths.items():
 text=Path(path).read_text();original=text
 if name=='Forme of Cury':
  text=re.split(r'\*\*\* START OF .*?\*\*\*',text,maxsplit=1)[-1]
  text=re.split(r'\*\*\* END OF ',text,maxsplit=1)[0]
 text=re.sub(r'^\s*===== PDF PAGE \d+ =====\s*$','',text,flags=re.M)
 text=re.sub(r'^\s*Digitized by Google\s*$','',text,flags=re.M|re.I)
 # Join only a hyphen directly between letters across a line break.
 text=re.sub(r'([^\W\d_])-\s*\n\s*([^\W\d_])',r'\1\2',text)
 text=unicodedata.normalize('NFC',text)
 words=re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)*",text)
 lengths=[sum(c.isalpha() for c in w) for w in words]
 data[name]=Counter(lengths);meta[name]={'tokens':len(lengths),'mean':statistics.mean(lengths),'median':statistics.median(lengths),'mode':Counter(lengths).most_common(1)[0][0],'sha256_normalized_text':hashlib.sha256(original.encode()).hexdigest(),'sha256_bytes':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
raw=(data_dir/'transcription.txt').read_text();words=[]
for line in raw.splitlines():
 m=re.match(r'^<f[^>]*\.[^>]*>\s*(.*)',line)
 if not m:continue
 s=re.sub(r'<[^>]*>','',m[1]).lower()
 for w in re.split(r'[.,\s\-=]+',s):
  w=w.replace('{','').replace('}','')
  if w and re.fullmatch('[a-vxyz]+',w):words.append(w)
for name,group in [('VMS · grouped EVA',True),('VMS · EVA letters',False)]:
 lengths=[len(re.findall(r'cfh|ckh|cph|cth|ch|sh|[a-vxyz]',w)) if group else len(w) for w in words]
 data[name]=Counter(lengths);meta[name]={'tokens':len(lengths),'mean':statistics.mean(lengths),'median':statistics.median(lengths),'mode':Counter(lengths).most_common(1)[0][0]}
with open(out/'word_length_comparison.csv','w') as f:
 writer=csv.writer(f);writer.writerow(['corpus','word_length','count','percent_of_words'])
 for name,c in data.items():
  for k in range(1,max(c)+1):writer.writerow([name,k,c[k],f'{100*c[k]/sum(c.values()):.8f}'])
colors=['#187e83','#d36b28','#8159a5'];names=['VMS · grouped EVA','Forme of Cury','Corpus orationum']
maxbin=25
peak=max(100*v/sum(c.values()) for c in data.values() for v in c.values());ceiling=mathceil= int(peak//5+1)*5
views={}
for mode in ['grouped','letters']:
 names[0]='VMS · grouped EVA' if mode=='grouped' else 'VMS · EVA letters'
 for style in ['line','bars']:
  W=1200;H=850;x=90;y=220;pw=1060;ph=390
  svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img"><title>Word-length distributions: VMS, Forme of Cury and Corpus orationum</title><rect width="1200" height="850" fill="#fffdf7"/><style>text{{font-family:system-ui,sans-serif;fill:#263c3a}}.muted{{fill:#65736e;font-size:13px}}.tick{{font-size:12px}}</style><text x="50" y="57" font-family="Georgia,serif" font-size="36">How long are the words?</text><text x="50" y="88" class="muted">VMS vs. Forme of Cury vs. Corpus orationum · word occurrences, normalized within each corpus</text>']
  for i,name in enumerate(names):
   m=meta[name];lx=50+i*385
   svg += [f'<rect x="{lx}" y="118" width="13" height="13" fill="{colors[i]}"/><text x="{lx+23}" y="130" font-size="17">{html.escape(name)}</text>',f'<text x="{lx}" y="156" class="muted">{m["tokens"]:,} words · mean {m["mean"]:.2f} · median {m["median"]:g} · mode {m["mode"]}</text>']
  for tick in range(0,ceiling+1,5):
   yy=y+ph-tick/ceiling*ph;svg.append(f'<line x1="{x}" x2="{x+pw}" y1="{yy}" y2="{yy}" stroke="#dce2d9"/><text x="{x-13}" y="{yy+4}" text-anchor="end" class="tick">{tick}%</text>')
  svg.append(f'<text x="{x}" y="{y-20}" class="muted">Share of word occurrences</text>')
  step=pw/maxbin
  for k in range(1,maxbin+1):
   xx=x+(k-.5)*step;svg.append(f'<text x="{xx}" y="{y+ph+23}" text-anchor="middle" class="tick">{k if k<maxbin else "25+"}</text>')
  for i,name in enumerate(names):
   c=data[name];n=sum(c.values());values=[100*(c[k] if k<maxbin else sum(v for j,v in c.items() if j>=maxbin))/n for k in range(1,maxbin+1)]
   points=[]
   for k,v in enumerate(values):
    xx=x+(k+.5)*step;yy=y+ph-v/ceiling*ph;points.append(f'{xx:.2f},{yy:.2f}')
    tooltip=html.escape(f'{name} | length {k+1 if k+1<25 else "25+"}: {v:.3f}%')
    if style=='line':svg.append(f'<circle cx="{xx}" cy="{yy}" r="3.5" fill="{colors[i]}"><title>{tooltip}</title></circle>')
    else:
     bw=step*.25;svg.append(f'<rect x="{xx-step*.375+i*bw}" y="{yy}" width="{bw-1}" height="{y+ph-yy}" fill="{colors[i]}"><title>{tooltip}</title></rect>')
   if style=='line':svg.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[i]}" stroke-width="2.7"/>')
  svg.extend([f'<text x="{x+pw/2}" y="{y+ph+54}" text-anchor="middle" font-size="15">Word length (letters / EVA units)</text>', '<text x="50" y="706" class="muted">Full-edition comparison: Forme includes introduction, notes, glossary and appendices; Orationum includes editorial apparatus.</text>', '<text x="50" y="730" class="muted">OCR noise is retained; page markers and “Digitized by Google” are removed. Gutenberg wrapper removed; line-end hyphens joined.</text>', '<text x="50" y="754" class="muted">Latin/English: Unicode letters counted; internal apostrophes do not add length. Other punctuation splits words; Roman numerals remain.</text>', '<text x="50" y="778" class="muted">VMS: ZL3b text loci; uncertain words omitted. Grouped EVA treats ch, sh, cfh, ckh, cph, cth as one unit; iin remains three.</text>', '<text x="50" y="802" class="muted">Repeated word occurrences are counted. Each corpus sums to 100%. Last bin combines lengths ≥25; CSV retains every exact length.</text>', '</svg>'])
  views[mode+'_'+style]=''.join(svg)
Path(out/'word_length_comparison.svg').write_text(views['grouped_line'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Word lengths · VMS / Forme / Orationum</title><style>body{margin:0;background:#e9ede7;color:#263c3a;font:15px system-ui}nav,footer{max-width:1150px;margin:auto;padding:16px;line-height:1.6}nav{display:flex;gap:20px;flex-wrap:wrap}select,button{padding:8px;font:inherit;background:white;border:1px solid #9eafa4;border-radius:5px}main{max-width:1200px;margin:auto}main>svg{width:100%;height:auto;display:block}nav[hidden]{display:none}</style><nav id="controls" hidden><label>VMS counting <select id="mode"><option value="grouped">Grouped EVA</option><option value="letters">EVA letters</option></select></label><label>Chart <select id="style"><option value="line">Line chart</option><option value="bars">Grouped histogram</option></select></label><button id="save">Download current SVG</button></nav><main id="chart">DEFAULT</main><footer><b>Interpretation:</b> This compares the supplied editions, including their commentary, rather than isolated recipe and prayer texts. OCR errors, abbreviations and mixed languages can affect Orationum’s distribution. EVA segmentation also changes lengths; use the switch to inspect both conventions. No phonetic equivalence between EVA units and Latin/English letters is assumed. The default chart remains visible without JavaScript.</footer><script id="views" type="application/json">DATA</script><script>(()=>{try{const views=JSON.parse(document.getElementById('views').textContent),mode=document.getElementById('mode'),style=document.getElementById('style');const key=()=>mode.value+'_'+style.value;const render=()=>document.getElementById('chart').innerHTML=views[key()];mode.onchange=style.onchange=render;document.getElementById('save').onclick=()=>{const u=URL.createObjectURL(new Blob([views[key()]],{type:'image/svg+xml'})),a=document.createElement('a');a.href=u;a.download='word_lengths_'+key()+'.svg';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};document.getElementById('controls').hidden=false}catch(e){}})()</script></html>'''
Path(out/'word_length_comparison.html').write_text(page.replace('DEFAULT',views['grouped_line']).replace('DATA',json.dumps(views)))
(output_dir/'length_stats.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
