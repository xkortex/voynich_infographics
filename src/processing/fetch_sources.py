"""Fetch public text inputs to a local ignored directory. No corpus is published."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[2]/'data/local')
p.add_argument('--vms-mirror',action='store_true',help='Explicitly use the documented GitHub mirror instead of voynich.nu')
a=p.parse_args();a.data_dir.mkdir(parents=True,exist_ok=True)
manifest=json.loads(Path(__file__).with_name('sources.json').read_text())['inputs']
for key,url in [('zl3b','https://voynich.nu/data/ZL3b-n.txt'),('forme','https://www.gutenberg.org/cache/epub/8102/pg8102.txt')]:
    item=next(x for x in manifest if x['id']==key)
    if key=='zl3b' and a.vms_mirror:url=item['retrieved_mirror']
    dest=a.data_dir/item['local_filename']
    if dest.exists():print('Kept existing '+str(dest));continue
    request=urllib.request.Request(url,headers={'User-Agent':'voynich-infographics source acquisition'})
    body=urllib.request.urlopen(request,timeout=60).read()
    # Preserve newer upstream bytes and report differences; never pretend a hash matched.
    dest.write_bytes(body);digest=hashlib.sha256(body).hexdigest()
    print(str(dest)+' SHA-256 '+digest+(' (historical match)' if digest==item['sha256'] else ' (DIFFERS from historical bytes; inspect before rebuilding)'))
print('Obtain EVA2.ttf manually under its source terms. Supply your own authorized Orationum OCR; see SOURCE_DATA.md.')
