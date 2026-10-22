#!/usr/bin/env python3
"""估位条目（OCR 太糊、定位不到行的）按页出判读图：每页正文栏（连右侧页边）一张，
页头列出这一页所有待判缺字组（编号 + TCP 上下文），按上下文在图上找。

    python3 scripts/rollock_pagesheets.py [--n 页数] [--gids a,b,...]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402
import rollock_witness as rw  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--n', type=int, default=6)
ap.add_argument('--gids')
ap.add_argument('--leaf', help='gid:叶,…  强制指定叶（自动挑错页时）')
ap.add_argument('--q', action='store_true', help='含已判 ? 的')
ap.add_argument('--zoom', type=int, default=1, help='每页切成几段、按原分辨率出图（透印页用 3）')
a = ap.parse_args()
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import numpy as np  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
done = {int(f[0]) for f in rc._tsv('gap_review.tsv') if not (a.q and f[1] == '?')}
force = {int(x.split(':')[0]): int(x.split(':')[1]) for x in (a.leaf or '').split(',') if x}
locs = json.loads((rc.RAW / 'witness_locs.json').read_text(encoding='utf-8'))
want = set(map(int, a.gids.split(','))) if a.gids else None
# 叶号优先按印本页码：IA page_numbers.json（叶 → 页面上印的页码）在 TCP 图号的窗口里找同页码的叶；
# 插值估位的叶在透印页上常偏一两叶
pn = json.loads((rw.W / 'page_numbers.json').read_text())['pages']
pmap = {}
for x in pn:
    if x['pageNumber']:
        pmap.setdefault(x['pageNumber'], []).append(x['leafNum'])
sites = {s['gid']: s for s in json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}


_PAGE = {}


def _hits(lf, s):
    """这一叶 OCR 的折叠字串里，左右上下文（各约 40 字）的最好编辑距离之和（越小越像）。"""
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
        if len(q) < 6:
            continue
        sc -= edlib.align(q, P, mode='HW')['editDistance'] / len(q)
    return sc


def leaf_of(r):
    """候选：印本页码对上的叶、插值估位的叶、TCP 图号窗口里的各叶；取上下文词命中最多的。"""
    s = sites[r['gid']]
    cand = [lf for lf in pmap.get(s.get('page') or '', []) if 2 * s['facs'] - 6 <= lf <= 2 * s['facs']]
    if len(cand) == 1:      # 页码对上的叶 ±1 里挑（透印页 OCR 是乱码，全窗口挑会被邻页抢走）
        cand = [cand[0] - 1, cand[0], cand[0] + 1]
        return max(cand, key=lambda lf: _hits(lf, s) + (0.35 if lf == cand[1] else 0))
    cand += [r['bim']['leaf']] + list(range(2 * s['facs'] - 6, 2 * s['facs'] + 1))
    return max(dict.fromkeys(cand), key=lambda lf: _hits(lf, s))


by = collections.OrderedDict()
for r in locs:
    b = r.get('bim')
    if not b or r['gid'] in done or (want is not None and r['gid'] not in want):
        continue
    if want is None and not (b.get('est') or r.get('anchor')):
        continue
    by.setdefault(force.get(r['gid']) or leaf_of(r), []).append(r)
out = rw.W / 'sheets'
out.mkdir(exist_ok=True)
for f in out.glob('p_*.jpg'):
    f.unlink()
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 21)
W = 1150
k = 0
for leaf, items in list(by.items())[:a.n]:
    im = Image.open(rw.full_page(leaf)).convert('L')
    d = json.loads((rw.W / 'ocr' / f'{leaf:04d}.json').read_text())
    sc = im.width / d['w']
    ys = sorted(w[2] for w in d['words'] if len(w[0]) > 2)
    y0, y1 = (ys[int(len(ys) * .01)], ys[int(len(ys) * .995)] + 80) if ys else (0, d['h'])
    xs = sorted(w[1] for w in d['words'] if len(w[0]) > 2)
    xe = sorted(w[1] + w[3] for w in d['words'] if len(w[0]) > 2)
    X0 = max(0, xs[int(len(xs) * .02)] - 300) if xs else 0
    X1 = min(d["w"], xe[int(len(xe) * .98)] + 300) if xe else d["w"]
    mid = (y0 + y1) // 2
    step = (y1 - y0) / a.zoom
    segs = [(int(y0 + i * step) - 60, int(y0 + (i + 1) * step) + 60) for i in range(a.zoom)]
    for hi, (ya, yb) in enumerate(segs):
        c = im.crop((int(X0 * sc), int(max(0, ya) * sc), int(X1 * sc), int(min(d['h'], yb) * sc)))
        if a.zoom == 1:
            c = c.resize((W, int(c.height * W / c.width)))
        lines = [f"叶 {leaf}  {hi + 1}/{a.zoom}  ({items[0]['book'][0]}T {items[0]['slug']}  TCP 页码 p.{sites[items[0]['gid']].get('page')})"]
        for r in items:
            lines.append(f"#{r['gid']}  " + ' '.join(r['left'][-5:]) + ' [[' + r['tcp'] + ']] ' + ' '.join(r['right'][:5]))
        head = Image.new('L', (c.width, 28 * len(lines) + 8), 255)
        dr = ImageDraw.Draw(head)
        for i, t in enumerate(lines):
            dr.text((6, 4 + 28 * i), t[:100], font=font, fill=0 if i else 90)
        Image.fromarray(np.vstack([np.array(head), np.array(c)])).save(out / f'p_{k:03d}.jpg', quality=85)
        k += 1
print(f'{min(a.n, len(by))}/{len(by)} 页 → {k} 张；剩 {sum(len(v) for v in list(by.values())[a.n:])} 条', file=sys.stderr)
