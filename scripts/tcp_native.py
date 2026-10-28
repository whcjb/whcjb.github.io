#!/usr/bin/env python3
"""判读用原生分辨率裁片（霍尔、巴洛共用）。

    python3 scripts/tcp_native.py hall crops --gids 0-99      # 取原图、裁片，原图不留
    python3 scripts/tcp_native.py hall sheets --gids 0-99 --name n [--per 8]

本地 OCR 与 *_witness.py 的判读图用的是 IA 缩到 1/4 的整页（霍尔 1282 px 宽，胶片原生 5127 px）。正文够看，
页边拉丁小字、希腊文、标点在缩图上认不清：这里按定位框从 IA 的 *_jp2.zip 里按 HTTP Range 只取那一叶的原图
（ia_rangezip.py；page/nN.jpg 走现场转码一页 40 秒，太慢），只裁那一小块存 witness/ncrops/<gid>.jpg，整页不落盘。

裁片范围（原图像素 = 定位框坐标 × 原图宽 / pw）：
- 正文：定位框左右各 420、上下各一行半；
- 旁注：定位框左右各 520、上下各两行；
- 估位（est，按上下文插值出来的大致位置）或旁注挂靠正文定位（anchor）：横向取整页、上下各八行，
  再缩到 1400 宽——估位本来就不准，宁可大。
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
ITEMS = {'hall': 'bim_early-english-books-1641-1700_a-practical-and-polemica_hall-thomas_1658',
         'barlow': 'bim_early-english-books-1475-1640_an-exposition-of-the-sec_barlow-john_1625'}
Image.MAX_IMAGE_PIXELS = None


def paths(book):
    raw = ROOT / f'{book}_raw' / '2timothy'
    return raw, raw / 'witness'


def parse_gids(s):
    out = []
    for part in s.split(','):
        if '-' in part:
            a, b = map(int, part.split('-'))
            out += list(range(a, b + 1))
        elif part:
            out.append(int(part))
    return out


def body_x(W_, leaf, pw):
    """本叶正文栏左右边界（pw 坐标）：本地 OCR 词 x 的 5% / 95% 分位（只算三个字母以上的词）。"""
    f = W_ / 'ocr' / f'{leaf:04d}.json'
    if not f.exists():
        return pw * .2, pw * .8
    d = json.loads(f.read_text())
    xs = sorted(w[1] for w in d['words'] if len(w[0]) > 3)
    xe = sorted(w[1] + w[3] for w in d['words'] if len(w[0]) > 3)
    if len(xs) < 20:
        return pw * .2, pw * .8
    return xs[int(len(xs) * .05)], xe[int(len(xe) * .95)]


def box(rec, W, H, Wdir=None):
    """→ [(x0, y0, x1, y1), …]（原图像素）。
    正文：定位框左右各 420、上下各一行半。
    旁注：本地 OCR 的旁注词定位常偏到正文里，所以一律裁左右两条整页边（正文栏以外），上下各七行；
    挂正文定位或估位的上下各十行。正文估位：整宽、上下各九行。"""
    loc = rec['bim']
    sc = W / loc['pw']
    gh = max(loc.get('gh', 30), 20)
    est = loc.get('est') or rec.get('anchor')
    if rec['stream'] == 'note':
        n = 10 if est else 7
        y0, y1 = max(0, (loc['gy'] - gh * 1.45 * n) * sc), min(H, (loc['gy'] + gh * (1 + 1.45 * n)) * sc)
        bx0, bx1 = body_x(Wdir, loc['leaf'], loc['pw'])
        return [(0, y0, min(W, (bx0 + 10) * sc), y1), (max(0, (bx1 - 10) * sc), y0, W, y1)]
    if est:
        return [(0, max(0, (loc['gy'] - gh * 9) * sc), W, min(H, (loc['gy'] + gh * 10) * sc))]
    dx, dy = 420, gh * 1.6 * sc
    x0 = loc['gx'] * sc - dx
    x1 = max(loc.get('gx1', loc['gx'] + gh), loc['gx'] + 5) * sc + dx
    y0 = loc['gy'] * sc - dy
    y1 = (loc['gy'] + gh) * sc + dy
    return [(max(0, x0), max(0, y0), min(W, x1), min(H, y1))]


def crops(book, gids, workers=8):
    raw, W = paths(book)
    out = W / 'ncrops'
    out.mkdir(exist_ok=True)
    locs = {r['gid']: r for r in json.loads((raw / 'witness_locs.json').read_text(encoding='utf-8'))}
    by_leaf = {}
    for g in gids:
        r = locs[g]
        if 'bim' not in r or (out / f'{g:04d}.jpg').exists():
            continue
        by_leaf.setdefault(r['bim']['leaf'], []).append(g)

    import threading
    from ia_rangezip import RangeZip
    local = threading.local()

    def one(leaf):
        try:
            if not hasattr(local, 'z'):     # zipfile 不是线程安全的：每个线程各开一个
                local.z = RangeZip(ITEMS[book], f'{ITEMS[book]}_jp2.zip')
            im = local.z.image(leaf).convert('L')
        except Exception as e:      # noqa: BLE001
            return leaf, str(e)[:60]
        if True:
            for g in by_leaf[leaf]:
                bs = [b for b in box(locs[g], im.width, im.height, W) if b[2] - b[0] > 10 and b[3] - b[1] > 10]
                parts = [im.crop(tuple(int(v) for v in b)) for b in bs]
                c = Image.new('L', (sum(p.width for p in parts) + 30 * (len(parts) - 1), max(p.height for p in parts)), 255)
                x = 0
                for p_ in parts:
                    c.paste(p_, (x, 0))
                    x += p_.width + 30
                if c.width > 1800:
                    c = c.resize((1800, int(c.height * 1800 / c.width)))
                c.save(out / f'{g:04d}.jpg', quality=88)
        return leaf, None
    bad = []
    with ThreadPoolExecutor(workers) as ex:
        for k, (leaf, e) in enumerate(ex.map(one, sorted(by_leaf))):
            if e:
                bad.append((leaf, e))
            if k % 10 == 0:
                print(f'{k}/{len(by_leaf)} 叶', file=sys.stderr, flush=True)
    print(f'裁片完成，{len(by_leaf)} 叶，失败 {bad}', file=sys.stderr)


def sheets(book, gids, name, per=8, width=1150):
    raw, W = paths(book)
    locs = {r['gid']: r for r in json.loads((raw / 'witness_locs.json').read_text(encoding='utf-8'))}
    sh = W / 'sheets'
    sh.mkdir(exist_ok=True)
    for f in sh.glob(f'{name}_*.jpg'):
        f.unlink()
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    rows, n, k = [], 0, 0

    def flush():
        nonlocal rows, k
        if rows:
            hh = sum(r.height for r in rows)
            o = Image.new('L', (width, hh), 255)
            y = 0
            for r in rows:
                o.paste(r, (0, y))
                y += r.height
            o.save(sh / f'{name}_{k:03d}.jpg', quality=85)
            rows, k = [], k + 1
    for g in gids:
        rec = locs[g]
        head = Image.new('L', (width, 58), 255)
        dr = ImageDraw.Draw(head)
        tag = '【估位】' if rec.get('bim', {}).get('est') else '【旁注·挂正文】' if rec.get('anchor') else ''
        dr.text((6, 2), f"#{g} {rec['slug']} {'[旁注]' if rec['stream'] == 'note' else ''} {tag}"[:90], font=font, fill=70)
        ctx = ' '.join(rec['left'][-5:]) + ' [[' + rec['tcp'] + ']] ' + ' '.join(rec['right'][:5])
        dr.text((6, 30), ctx[:95], font=font, fill=0)
        f = W / 'ncrops' / f'{g:04d}.jpg'
        if f.exists():
            im = Image.open(f).convert('L')
            if im.width > width:
                im = im.resize((width, int(im.height * width / im.width)))
            pad = Image.new('L', (width, im.height), 255)
            pad.paste(im, (0, 0))
            im = pad
        else:
            im = Image.new('L', (width, 40), 235)
            ImageDraw.Draw(im).text((6, 8), '（无裁片：未定位）', font=font, fill=120)
        rows += [head, im, Image.new('L', (width, 6), 40)]
        n += 1
        if n % per == 0:
            flush()
    flush()
    print(f'{n} 条 → {k} 张 {sh}/{name}_*.jpg', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', choices=list(ITEMS))
    ap.add_argument('cmd', choices=['crops', 'sheets'])
    ap.add_argument('--gids', required=True)
    ap.add_argument('--name', default='n')
    ap.add_argument('--per', type=int, default=8)
    a = ap.parse_args()
    g = parse_gids(a.gids)
    if a.cmd == 'crops':
        crops(a.book, g)
    else:
        sheets(a.book, g, a.name, a.per)


if __name__ == '__main__':
    main()
