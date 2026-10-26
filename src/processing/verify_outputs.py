"""Check historical infographic aggregates after rebuilding with the original inputs."""
from pathlib import Path
import argparse,json,csv,math
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[2]/'generated')
a=p.parse_args();out=a.output_dir
counts=json.loads((out/'counts.json').read_text())
assert sum(x['count'] for x in counts['groups'])==173512
assert sum(x['count'] for x in counts['letters'])==193266
positions=json.loads((out/'positions.json').read_text())
assert positions['groups']['total']==169172
assert positions['letters']['total']==188466
for mode in positions.values():assert sum(map(sum,mode['hist'].values()))==mode['total']
stats=json.loads((out/'length_stats.json').read_text())
assert stats['Forme of Cury']['tokens']==43765
assert stats['Corpus orationum']['tokens']==104081
assert stats['VMS · grouped EVA']['tokens']==37126
sums={}
for row in csv.DictReader((out/'word_length_comparison.csv').open()):
    sums[row['corpus']]=sums.get(row['corpus'],0)+float(row['percent_of_words'])
assert all(math.isclose(s,100,abs_tol=1e-6) for s in sums.values())
print('PASS: all historical totals, position histograms, and normalized distributions')
