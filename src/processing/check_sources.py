"""Compare local input bytes to the input fingerprints for the original charts."""
from pathlib import Path
import argparse,hashlib,json,sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[2]/'data/local')
a=p.parse_args();failed=False
for item in json.loads(Path(__file__).with_name('sources.json').read_text())['inputs']:
    path=a.data_dir/item['local_filename']
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    ok=actual==item['sha256'];failed|=not ok
    print(('MATCH' if ok else 'MISSING' if actual is None else 'DIFFERENT')+' '+item['local_filename'])
    if actual and not ok:print('  actual SHA-256: '+actual)
sys.exit(int(failed))
