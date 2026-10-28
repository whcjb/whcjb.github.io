#!/usr/bin/env python3
"""判读辅助：把某几组缺字所在处按原分辨率裁出来拼成一张（不缩小），看标点、小字用。

    python3 scripts/tcp_zoom.py hall 6 9 [--w 260] [--h 70]

book = hall / barlow；读 <book>_raw/2timothy/witness_locs.json 的定位框，从 witness/img/bim_NNNN.jpg 裁
定位框左右各 w、上下各 h（原图像素）。输出 witness/sheets/zoom.jpg。
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book')
    ap.add_argument('gids', nargs='+', type=int)
    ap.add_argument('--w', type=int, default=260)
    ap.add_argument('--h', type=int, default=60)
    ap.add_argument('--out', default='zoom')
    a = ap.parse_args()
    W = ROOT / f'{a.book}_raw' / '2timothy' / 'witness'
    locs = {r['gid']: r for r in json.loads((W.parent / 'witness_locs.json').read_text(encoding='utf-8'))}
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 20)
    rows = []
    for g in a.gids:
        loc = locs[g].get('bim')
        if not loc:
            continue
        im = Image.open(W / 'img' / f'bim_{loc["leaf"]:04d}.jpg').convert('L')
        sc = im.width / loc['pw']
        x0, x1 = loc['gx'] - a.w, loc.get('gx1', loc['gx']) + a.w
        y0, y1 = loc['gy'] - a.h, loc['gy'] + loc['gh'] + a.h
        c = im.crop((int(x0 * sc), int(y0 * sc), int(x1 * sc), int(y1 * sc))).convert('RGB')
        hd = Image.new('RGB', (c.width, 26), 'white')
        ImageDraw.Draw(hd).text((4, 2), f'#{g}  [[{locs[g]["tcp"]}]]', font=font, fill=(0, 0, 0))
        rows += [hd, c]
    wd = max(r.width for r in rows)
    out = Image.new('RGB', (wd, sum(r.height for r in rows)), 'white')
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    if out.width > 1400:
        out = out.resize((1400, int(out.height * 1400 / out.width)))
    p = W / 'sheets' / f'{a.out}.jpg'
    out.save(p, quality=90)
    print(p)


if __name__ == '__main__':
    main()
