"""Run the infographic generators in order, then optionally assemble the site."""
import argparse,subprocess,sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--data-dir',type=Path,default=ROOT/'data/local')
p.add_argument('--output-dir',type=Path,default=ROOT/'generated')
p.add_argument('--skip-png',action='store_true',help='Generate HTML/SVG/data only; do not assemble docs/')
a=p.parse_args()
a.output_dir.mkdir(parents=True,exist_ok=True)
for script in ['eva_frequencies.py','word_positions.py','word_lengths.py']:
    subprocess.run([sys.executable,str(HERE/script),'--data-dir',str(a.data_dir),'--output-dir',str(a.output_dir)],check=True)
# Record actual input fingerprints, including any differences from the historical manifest.
inputs={name:hashlib.sha256((a.data_dir/name).read_bytes()).hexdigest() for name in ['transcription.txt','EVA2.ttf','forme_of_cury.txt','orationum_ocr.txt']}
(a.output_dir/'input_hashes.json').write_text(json.dumps(inputs,indent=2)+'\n')
if not a.skip_png:
    subprocess.run(['node',str(HERE/'render_pngs.cjs'),'--output-dir',str(a.output_dir)],check=True)
    subprocess.run([sys.executable,str(HERE/'assemble_site.py'),'--artifacts',str(a.output_dir)],check=True)
