#!/usr/bin/env python3
"""重影/透印页：按 800 ppi 原图把正文栏横切成若干条带，只出含待判缺字的条带（缩到 2300 宽，≈510 ppi）。

    python3 scripts/rollock_bands.py --leaf 354 --gids a,b,... [--bands 6]

缺字落在哪一条带：按缺字在本页 TCP 文字里的位置比例估（页首=0，页末=1），前后各多给一条。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402
import rollock_witness as rw  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--leaf', type=int, required=True)
ap.add_argument('--gids', required=True)
ap.add_argument('--bands', type=int, default=6)
ap.add_argument('--frac', default='', help='gid:页内比例,… 手工指定')
a = ap.parse_args()
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
gids = [int(x) for x in a.gids.split(',')]
sites = {s['gid']: s for s in json.loads((rc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
fr = {int(x.split(':')[0]): float(x.split(':')[1]) for x in a.frac.split(',') if x}


def page_frac(g):
    """缺字在 TCP 本页里的位置比例：本页 = 前一个 rl-pb 到下一个 rl-pb 之间。"""
    if g in fr:
        return fr[g]
    s = sites[g]
    md = rc.read_src(s['book'], s['slug'])
    k = [x['gid'] for x in sites.values() if x['book'] == s['book'] and x['slug'] == s['slug']].index(g)
    pos = rc.gap_groups(md)[k][0]
    pbs = [m.start() for m in re.finditer(r'<span class="rl-pb"', md)]
    a0 = max([p for p in pbs if p <= pos], default=0)
    a1 = min([p for p in pbs if p > pos], default=len(md))
    return (pos - a0) / max(1, a1 - a0)


out = rw.W / 'sheets'
out.mkdir(exist_ok=True)
for f in out.glob('b_*.jpg'):
    f.unlink()
FULL = rw.W / 'full'
FULL.mkdir(exist_ok=True)
f = FULL / f'bim_{a.leaf:04d}.jpg'
rw._download(rw.page_url(a.leaf), f)
im = Image.open(f).convert('L')
half = json.loads((rw.W / 'ocr' / f'{a.leaf:04d}.json').read_text())
sc = im.width / half['w']
ws = [w for w in half['words'] if len(w[0]) > 2]
xs = sorted(w[1] for w in ws); xe = sorted(w[1] + w[3] for w in ws); ys = sorted(w[2] for w in ws)
if len(ws) > 50:
    X0 = max(0, int((xs[int(len(xs) * .02)] - 260) * sc)); X1 = min(im.width, int((xe[int(len(xe) * .98)] + 260) * sc))
    Y0 = max(0, int((ys[0] - 40) * sc)); Y1 = min(im.height, int((ys[-1] + 120) * sc))
else:                                   # OCR 几乎全空（重影页）：取整页中间 90%
    X0, X1, Y0, Y1 = int(im.width * .05), int(im.width * .97), int(im.height * .05), int(im.height * .95)
n = a.bands
step = (Y1 - Y0) / n
want = {}
for g in gids:
    b = min(n - 1, int(page_frac(g) * n))
    for bb in (b - 1, b, b + 1):
        if 0 <= bb < n:
            want.setdefault(bb, []).append(g)
font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 26)
k = 0
for bb in sorted(want):
    y0, y1 = int(Y0 + bb * step - 60), int(Y0 + (bb + 1) * step + 60)
    c = im.crop((X0, max(0, y0), X1, min(im.height, y1)))
    if c.width > 2300:
        c = c.resize((2300, int(c.height * 2300 / c.width)))
    lines = [f'叶 {a.leaf}  条带 {bb + 1}/{n}']
    for g in sorted(set(want[bb])):
        s = sites[g]
        lines.append(f"#{g}  " + ' '.join(s['left'][-6:]) + ' [[' + s['tcp'] + ']] ' + ' '.join(s['right'][:6]))
    head = Image.new('L', (c.width, 32 * len(lines) + 8), 255)
    dr = ImageDraw.Draw(head)
    for i, t in enumerate(lines):
        dr.text((8, 4 + 32 * i), t[:130], font=font, fill=0 if i else 90)
    sheet = Image.new('L', (c.width, head.height + c.height), 255)
    sheet.paste(head, (0, 0)); sheet.paste(c, (0, head.height))
    sheet.save(out / f'b_{k:02d}.jpg', quality=88)
    k += 1
f.unlink()
print(f'{k} 张', file=sys.stderr)
