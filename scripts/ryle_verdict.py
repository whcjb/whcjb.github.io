#!/usr/bin/env python3
"""往 ryle_raw/matthew/review.tsv 填判读：  python3 scripts/ryle_verdict.py 1=es 4=1857 10=1857 12=1857:"reading" ...
es＝e-Sword 对（不改）；1857＝照原书（取 OCR 栏，或冒号后给出看图读出的文字）。"""
import csv, sys
from pathlib import Path
TSV = Path(__file__).resolve().parent.parent / 'ryle_raw' / 'matthew' / 'review.tsv'
rows = list(csv.DictReader(TSV.open(encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
cols = list(rows[0].keys())
by = {r['id']: r for r in rows}
for a in sys.argv[1:]:
    i, v = a.split('=', 1)
    v, _, reading = v.partition(':')
    by[i]['verdict'] = v
    by[i]['reading'] = reading if reading else (by[i]['ocr1857'] if v == '1857' else '')
with TSV.open('w', encoding='utf-8') as f:
    f.write('\t'.join(cols) + '\n')
    for r in rows:
        f.write('\t'.join(r[c] for c in cols) + '\n')
print(sum(1 for r in rows if r['verdict']), '/', len(rows), '已判')
