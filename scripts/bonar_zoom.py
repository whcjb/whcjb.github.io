#!/usr/bin/env python3
"""把若干希伯来片段在 1859 初版里的那一行按原分辨率放大，左右两半上下拼，出一张图。

    python3 scripts/bonar_zoom.py OUT.png id1 id2 …     （id 为 hebrew_runs.json 的片段号；行位置取 work/hebrew_1859_sites.json）
    python3 scripts/bonar_zoom.py OUT.png p<hocr页>:<y0>:<y1> …   （直接给页与 y 范围）
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bonar_scan as S  # noqa: E402

RAW = S.ROOT / 'bonar_raw' / 'psalms'


def main():
    out, keys = sys.argv[1], sys.argv[2:]
    sites = json.loads((RAW / 'work' / 'hebrew_1859_sites.json').read_text(encoding='utf-8'))
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 34)
    rows = []
    for k in keys:
        if k.startswith('p'):
            pg, y0, y1 = map(int, k[1:].split(':'))
        else:
            v = sites[k]
            pg, y0, y1 = v['page'], v['y0'] - 10, v['y1'] + 12
        im = S.crop(pg, y0, y1, x0=60, x1=1860)
        h = im.width // 2
        rows.append((k, im.crop((0, 0, h + 40, im.height))))
        rows.append(('', im.crop((h - 40, 0, im.width, im.height))))
    W = max(r.width for _, r in rows) + 110
    sh = Image.new('RGB', (W, sum(r.height + 8 for _, r in rows)), 'white')
    dr = ImageDraw.Draw(sh)
    y = 0
    for k, r in rows:
        dr.text((4, y + 10), k, fill='red', font=font)
        sh.paste(r, (105, y))
        y += r.height + 8
    sh.save(out)


if __name__ == '__main__':
    main()
