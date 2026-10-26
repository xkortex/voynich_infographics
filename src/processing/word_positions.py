"""Generate word positions artifacts. See README.md."""
import re,json,math,html
from pathlib import Path
from collections import Counter,defaultdict
from config import paths
data_dir, output_dir = paths(__doc__)
raw=(data_dir/'transcription.txt').read_text()
base=Path(output_dir/'voynich_eva_frequency.html').read_text()
glyphs=json.loads(re.search(r'<script id="glyphData" type="application/json">(.*?)</script>',base,re.S)[1])
letters=list('abcdefghijklmnopqrstuvxyz');groups=['cfh','ckh','cph','cth','ch','sh'];bins=15
words=[]
for line in raw.splitlines():
 m=re.match(r'^<f[^>]*\.[^>]*>\s*(.*)',line)
 if not m:continue
 s=re.sub(r'<[^>]*>','',m[1]).lower()
 # Keep uncertain material in its word until word splitting, then omit that entire word.
 for word in re.split(r'[.,\s\-=]+',s):
  word=word.replace('{','').replace('}','')
  if word and re.fullmatch('[a-vxyz]+',word):words.append(word)
colors=['#fff9bf','#ffe28a','#ffc267','#ff963e','#ff602e','#e52722','#b9002e']
allstats={}
for mode in ['groups','letters']:
 counts=Counter();hist=defaultdict(lambda:[0]*bins)
 for word in words:
  toks=re.findall('|'.join(groups)+r'|[a-vxyz]',word) if mode=='groups' else list(word)
  for i,t in enumerate(toks):
   p=i/(len(toks)-1) if len(toks)>1 else .5
   hist[t][min(bins-1,int(p*bins))]+=1;counts[t]+=1
 total=sum(counts.values());syms=sorted(letters+groups if mode=='groups' else letters)
 allstats[mode]={'total':total,'counts':dict(counts),'hist':dict(hist)}
 def draw(shared=False):
  rows=math.ceil(len(syms)/2);W=1120;H=230+rows*105+230
  out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc"><title id="title">Where EVA symbols occur within words</title><desc id="desc">Position distributions for {mode}. Left is word beginning; right is word end. Each panel '+('shares the same vertical count scale.' if shared else 'is scaled to its own peak; compare shape, not panel height.')+'</desc><rect width="1120" height="100%" fill="#fffdf7"/>', '<style>text{font-family:system-ui,sans-serif;fill:#263a37}.small{font-size:13px;fill:#62716c}.label{font-size:16px;font-family:monospace}.head{font-family:Georgia,serif;font-size:42px}.axis{stroke:#9da79e;stroke-width:1}</style>', '<text x="45" y="62" class="head">Where EVA symbols occur within words</text>',f'<text x="45" y="98" font-size="18">Beginning → middle → end · {mode=="groups" and "Grouped EVA forms" or "Individual EVA letters"}</text>',f'<text x="45" y="128" class="small">{len(words):,} word occurrences · {total:,} counted tokens · Zandbergen–Landini 3b</text>',f'<text x="45" y="153" class="small">'+('Shared vertical scale: absolute occurrences per position bin.' if shared else 'Each panel scaled to its own peak. Color shows overall frequency; height shows relative position.')+'</text>']
  globalmax=max(max(h) for h in hist.values())
  for idx,sym in enumerate(syms):
   col=idx//rows;row=idx%rows;x=45+col*550;y=215+row*105;px=x+100;pw=410;ph=61
   h=hist[sym];peak=globalmax if shared else max(h) or 1;share=counts[sym]/total*100
   color=colors[next((i for i,t in enumerate([.1,.5,1,2,5,9]) if share<t),6)]
   embedded=re.sub(r'<svg aria-hidden="true"',f'<svg x="{x}" y="{y-54}" width="66" height="66"',glyphs[sym])
   out.extend([embedded,f'<text x="{x+32}" y="{y+25}" class="label" text-anchor="middle">{sym}</text>',f'<line x1="{px}" x2="{px+pw}" y1="{y+ph}" y2="{y+ph}" class="axis"/>'])
   # Equal-width histogram bins rendered as a continuous area through bin centers.
   points=[(px,y+ph)]+[(px+(i+.5)/bins*pw,y+ph-v/peak*ph) for i,v in enumerate(h)]+[(px+pw,y+ph)]
   out.append('<path d="M'+' L'.join(f'{a:.2f},{b:.2f}' for a,b in points)+f' Z" fill="{color}" stroke="#665d4e" stroke-width="1.1"/>')
   out.append(f'<text x="{px}" y="{y-9}" class="small">{counts[sym]:,} occurrences</text><text x="{px+pw}" y="{y-9}" text-anchor="end" class="small">{share:.3f}%</text>')
   if not counts[sym]:out.append(f'<text x="{px+pw/2}" y="{y+36}" text-anchor="middle" class="small">No occurrences in this mode</text>')
  fy=215+rows*105
  out.append(f'<text x="45" y="{fy}" font-size="15">Color = overall token frequency</text>')
  for i,c in enumerate(colors):out.append(f'<rect x="{45+i*110}" y="{fy+14}" width="110" height="15" fill="{c}"/><text x="{45+i*110}" y="{fy+48}" class="small">{["&lt;0.1%","0.1–0.5%","0.5–1%","1–2%","2–5%","5–9%","≥9%"][i]}</text>')
  notes=['Position = token index / (word length − 1), binned into 15 equal intervals. First and last tokens map to the endpoints.', 'Single-token words map to the middle. Every repeated word occurrence contributes; word types are not deduplicated.', 'Uncertain words (alternatives, rare codes, unreadable markers) are omitted in full. Inline annotations are removed.', 'Groups: cfh, ckh, cph, cth, ch, sh use longest match; other letters remain separate. This is a convention, not a decipherment.', 'Data: Zandbergen & Landini, ZL3b-n.txt (CC0). Glyph outlines: Gabriel Landini, EVA2.ttf (2025); private noncommercial use.']
  for i,n in enumerate(notes):out.append(f'<text x="45" y="{fy+79+i*21}" class="small">{html.escape(n)}</text>')
  return ''.join(out)+'</svg>'
 allstats[mode]['svg']=draw();allstats[mode]['shared']=draw(True)
Path(output_dir/'voynich_eva_word_positions.svg').write_text(allstats['groups']['svg'])
svgset={k:{'own':v['svg'],'shared':v['shared']} for k,v in allstats.items()}
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EVA word-position distributions</title><style>body{margin:0;background:#eaece5;color:#263a37;font:15px system-ui}nav{padding:16px;display:flex;gap:20px;align-items:center;flex-wrap:wrap;max-width:1080px;margin:auto}label{display:flex;gap:8px;align-items:center}select,button{font:inherit;padding:8px;border:1px solid #a2b3a8;border-radius:5px;background:#fffdf7;color:inherit}main{max-width:1120px;margin:auto}main>svg{display:block;width:100%;height:auto}footer{max-width:1080px;margin:20px auto;padding:12px;line-height:1.6}a{color:#216f63}@media print{nav,footer{display:none}}</style><nav id="controls" hidden><label>Units <select id="mode"><option value="groups">Grouped EVA forms</option><option value="letters">Individual EVA letters</option></select></label><label>Panel heights <select id="scale"><option value="own">Each symbol’s own peak</option><option value="shared">Shared count scale</option></select></label><button id="save">Download current chart (SVG)</button></nav><main id="chart">DEFAULT</main><footer>The default uses a separate vertical scale for every symbol, like the supplied reference: compare position shapes, and use the percentages and colors to compare frequency. Switch to “Shared count scale” to compare absolute counts. All data and vector glyphs are embedded; the default chart works without JavaScript.<br>Source: <a href="https://voynich.nu/data/ZL3b-n.txt">ZL3b transcription</a> (<a href="https://github.com/Aspect-Research/voynich-autoexploration/blob/master/data/transcriptions/eva_zl3b.txt">retrieved mirror</a>) · <a href="https://voynich.nu/roadmap.html">EVA font credits and terms</a>. Cleaning differs from the earlier frequency chart by excluding entire uncertain words, so totals differ.</footer><script type="application/json" id="views">DATA</script><script>(()=>{try{const views=JSON.parse(document.getElementById('views').textContent),mode=document.getElementById('mode'),scale=document.getElementById('scale');function render(){document.getElementById('chart').innerHTML=views[mode.value][scale.value]}mode.onchange=scale.onchange=render;document.getElementById('save').onclick=()=>{let url=URL.createObjectURL(new Blob([views[mode.value][scale.value]],{type:'image/svg+xml'}));let a=document.createElement('a');a.href=url;a.download='eva_word_positions_'+mode.value+'_'+scale.value+'.svg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};document.getElementById('controls').hidden=false}catch(e){}})()</script></html>'''
Path(output_dir/'voynich_eva_word_positions.html').write_text(page.replace('DEFAULT',svgset['groups']['own']).replace('DATA',json.dumps(svgset)))
(output_dir/'positions.json').write_text(json.dumps({k:{a:b for a,b in v.items() if a not in ['svg','shared']} for k,v in allstats.items()}))
print('words',len(words),'totals',[(k,v['total']) for k,v in allstats.items()])
