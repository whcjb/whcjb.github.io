#!/usr/bin/env python3
"""判不了（?）的缺字按 800 ppi 原图重看：原分辨率裁图，不缩放。

    python3 scripts/rollock_fullcrop.py --gids a,b,...  [--h 7] [--w 1700]

每条：叶号按 rollock_pagesheets 的选叶法（印本页码 → 上下文编辑距离），纵坐标取定位（半尺寸坐标 ×2），
横向以缺字为中心取 w 像素、纵向上下各 h 行，原分辨率出图（字高约 70px）。整页原图用完即删（磁盘紧）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402
import rollock_witness as rw  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--gids', required=True)
ap.add_argument('--h', type=int, default=4)
ap.add_argument('--w', type=int, default=1800)
ap.add_argument('--leaf', default='')
a = ap.parse_args()
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
gids = [int(x) for x in a.gids.split(',')]
force = {int(x.split(':')[0]): int(x.split(':')[1]) for x in a.leaf.split(',') if x}
locs = {r['gid']: r for r in json.loads((rc.RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
pn = json.loads((rw.W / 'page_numbers.json').read_text())['pages']
pmap = {}
for x in pn:
    if x['pageNumber']:
        pmap.setdefault(x['pageNumber'], []).append(x['leafNum'])
sites = {s['gid']: s for s in json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
_PAGE = {}


def _hits(lf, s):
    import edlib
    if lf not in _PAGE:
        f = rw.W / 'ocr' / f'{lf:04d}.json'
        _PAGE[lf] = ''.join(rw.fold(w[0]) for w in json.loads(f.read_text())['words']) if f.exists() else ''
    P = _PAGE[lf]
    if not P:
        return -999
    sc = 0
    for side in (s['left'], s['right']):
        q = ''.join(rw.fold(w) for w in side if not rw.TOK.search(w))
        q = q[-40:] if side is s['left'] else q[:40]
        if len(q) >= 6:
            sc -= edlib.align(q, P, mode='HW')['editDistance'] / len(q)
    return sc


def leaf_of(r):
    """与 rollock_pagesheets 同法：印本页码对上的叶 ±1 里挑；否则 TCP 图号窗口里挑上下文最像的。"""
    s = sites[r['gid']]
    if r.get('bim') and not r['bim'].get('est') and _hits(r['bim']['leaf'], s) > -0.6:
        return r['bim']['leaf']
    cand = [lf for lf in pmap.get(s.get('page') or '', []) if 2 * s['facs'] - 6 <= lf <= 2 * s['facs']]
    if len(cand) == 1:
        c = [cand[0] - 1, cand[0], cand[0] + 1]
        return max(c, key=lambda lf: _hits(lf, s) + (0.35 if lf == c[1] else 0))
    cand = ([r['bim']['leaf']] if r.get('bim') else []) + list(range(2 * s['facs'] - 6, 2 * s['facs'] + 1))
    return max(dict.fromkeys(cand), key=lambda lf: _hits(lf, s))

out = rw.W / 'sheets'
out.mkdir(exist_ok=True)
for f in out.glob('f_*.jpg'):
    f.unlink()
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 26)
FULL = rw.W / 'full'
FULL.mkdir(exist_ok=True)
by = {}
for g in gids:
    r = locs[g]
    lf = force.get(g) or leaf_of(r)
    by.setdefault(lf, []).append(g)
k = 0
for lf, gs in by.items():
    f = FULL / f'bim_{lf:04d}.jpg'
    rw._download(rw.page_url(lf), f)
    im = Image.open(f).convert('L')
    half = json.loads((rw.W / 'ocr' / f'{lf:04d}.json').read_text())
    sc = im.width / half['w']
    for g in gs:
        r = locs[g]
        b = r['bim']
        same = b['leaf'] == lf and not b.get('est')
        gh = max(30, b.get('gh', 40)) * sc
        cy = (b['gy'] * sc + gh / 2) if same else None
        cx = (b['gx'] * sc) if same else im.width / 2
        if cy is None:      # 估位/改叶：整栏高分三段
            segs = [(int(im.height * t), int(im.height * (t + .36))) for t in (0.02, 0.32, 0.62)]
            xs = [(0, im.width)]
        else:
            lh = gh * 1.5
            segs = [(int(cy - lh * a.h), int(cy + lh * a.h))]
            xs = [(int(max(0, min(im.width - a.w, cx - a.w / 2))), int(max(0, min(im.width - a.w, cx - a.w / 2)) + a.w))]
        for (y0, y1) in segs:
            for (x0, x1) in xs:
                c = im.crop((x0, max(0, y0), x1, min(im.height, y1)))
                if c.width > 2300:
                    c = c.resize((2300, int(c.height * 2300 / c.width)))
                head = Image.new('L', (c.width, 70), 255)
                dr = ImageDraw.Draw(head)
                s = r
                dr.text((8, 4), f"#{g} 叶{lf} {r['book'][0]}T {r['slug']}  {'' if same else '【整栏】'}", font=font, fill=90)
                dr.text((8, 36), (' '.join(s['left'][-6:]) + ' [[' + s['tcp'] + ']] ' + ' '.join(s['right'][:6]))[:120],
                        font=font, fill=0)
                sheet = Image.new('L', (c.width, c.height + 70), 255)
                sheet.paste(head, (0, 0))
                sheet.paste(c, (0, 70))
                sheet.save(out / f'f_{k:03d}.jpg', quality=88)
                k += 1
    f.unlink()
print(f'{len(gids)} 条 → {k} 张', file=sys.stderr)
