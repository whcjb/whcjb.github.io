#!/usr/bin/env python3
"""按 notes_map.tsv 把每条脚注的初版页面区域裁出，拼成对照图 work/fn_sheets2/gNN.png。"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bonar_scan import crop  # noqa: E402

B = Path(__file__).resolve().parent.parent / 'bonar_raw' / 'psalms'
OUT = B / 'work' / 'fn_sheets2'


def main():
    only = set(map(int, sys.argv[1:]))
    pages = {pg['p']: pg['lines'] for pg in json.load(open(B / 'work' / 'hocr_lines.json'))}
    typed = {int(l.split('\t')[0]) for l in open(B / 'notes_typed.tsv') if not l.startswith('#')}
    items = []
    for l in open(B / 'notes_map.tsv'):
        if l.startswith('#'):
            continue
        n, spec = l.rstrip('\n').split('\t')
        n = int(n)
        if spec.startswith('DUP') or (only and n not in only) or (not only and n in typed):
            continue
        ims = []
        for part in spec.split(';'):
            p, ys = part.split(':')
            p = int(p)
            y0, y1 = map(int, ys.split('-'))
            L = [x for x in pages[p] if y0 <= x['y0'] <= y1 and len(x['t'].strip()) > 2]
            im = crop(p, y0 - 12, max(x['y1'] for x in L) + 40)
            ims.append((f'#{n} p{p}', im.resize((1000, int(im.height * 1000 / im.width)))))
        items.append((n, ims))
    OUT.mkdir(exist_ok=True)
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22)
    sheets, cur, h = [], [], 0
    for n, ims in items:
        hh = sum(im.height + 30 for _, im in ims)
        if cur and h + hh > 1900:
            sheets.append(cur)
            cur, h = [], 0
        cur.append((n, ims))
        h += hh
    if cur:
        sheets.append(cur)
    for k, sh in enumerate(sheets, 1):
        parts = [x for _, ims in sh for x in ims]
        S = Image.new('RGB', (1000, sum(im.height + 30 for _, im in parts)), 'white')
        d = ImageDraw.Draw(S)
        y = 0
        for lab, im in parts:
            d.text((4, y + 2), lab, fill='red', font=font)
            S.paste(im, (0, y + 30))
            y += 30 + im.height
        S.save(OUT / f'g{k:02d}.png')
        print(f'g{k:02d}', [n for n, _ in sh])


if __name__ == '__main__':
    main()
