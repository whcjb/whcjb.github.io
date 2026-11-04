#!/usr/bin/env python3
"""亚历山大《马太福音释义》脚注核对批：几页的脚注区按原生分辨率拼一张图 + 打印投票稿与疑似挂点。

    python3 scripts/alexander_matthew_fnbatch.py 26 27 28 29
    → alexander_raw/matthew/work/fnsheets/batch_<首页>.png

裁法：从本页最上面一个小字段（ABBYY 坐标按页高比例换算到 jp2）往上 30 像素起，到页底。
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_alexander_matthew as X  # noqa: E402

PAGE_H = 3431


def main():
    pages = [int(x) for x in sys.argv[1:]]
    d = dict(X.load_abbyy(X.VOLS[0]))
    crops = []
    for pg in pages:
        im = Image.open(X.WORK / 'pages' / f'{pg:04d}.png')
        W, H = im.size
        txt = lambda p: ' '.join(w for w, _ in p['words'])
        tops = [p['top'] for p in d[pg] if p['small'] and p['top'] and X.FOOTNOTE.match(txt(p))] or \
               [p['top'] for p in d[pg] if p['small'] and p['top'] and not X.RUNHEAD.match(txt(p))
                and len(re.findall(r'[A-Za-z]', txt(p))) >= 3]
        t = int(min(tops) / PAGE_H * H) - 70 if tops else int(H * 0.6)
        crops.append((pg, im.crop((0, max(t, 0), W, int(H * 0.985)))))
    W = max(c.width for _, c in crops)
    out = Image.new('L', (W, sum(c.height + 34 for _, c in crops)), 255)
    y, dr = 0, ImageDraw.Draw(out)
    for pg, c in crops:
        dr.rectangle((0, y, W, y + 33), fill=0)
        dr.text((10, y + 10), f'p{pg}', fill=255)
        y += 34
        out.paste(c, (0, y))
        y += c.height
    f = X.WORK / 'fnsheets' / f'batch_{pages[0]}.png'
    out.save(f)
    print(f, out.size)
    votes = [l.split('\t') for l in (X.WORK / 'footnotes_vote.tsv').read_text(encoding='utf-8').splitlines()[1:]]
    plan = (X.WORK / 'fnplan.txt').read_text(encoding='utf-8').split('=== ')
    for pg in pages:
        print(f'--- p{pg}')
        for v in votes:
            if int(v[0]) == pg:
                print(f'  [{v[1]}] {v[2]} {v[3]}')
        blk = next((b for b in plan if b.startswith(f'p{pg}\n')), '')
        for line in blk.splitlines():
            if line.startswith('  号'):
                print(line)


if __name__ == '__main__':
    main()
