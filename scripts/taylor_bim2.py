#!/usr/bin/env python3
"""第二份 1612 年藏本（bim2，IA40310712-34）：bim 上读不出的缺字拿它看。

    python3 scripts/taylor_bim2.py build                 # IA hOCR → witness/words_bim2.json
    python3 scripts/taylor_bim2.py sheets --gids-file witness/later.json --name t   # 判读图（bim 与 bim2 上下对照）

bim2 是另一卷胶片，叶号与 TCP 图号不对应：按缺字上下文在 bim2 全书词流里做字符级定位
（edlib，只认 bim 定位的叶号换算出的前后 ±40 叶），裁出所在行，与 bim 的裁图上下并排。
OCR 只作定位，读法一律看图。
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import taylor_witness as tw  # noqa: E402

W = tw.W
ITEM = tw.ITEMS['bim2']
RE_PAGE = re.compile(r'<div class="ocr_page" id="page_(\d+)" title="[^"]*?bbox 0 0 (\d+) (\d+)')
RE_W = re.compile(r'<span class="ocrx_word" id="[^"]+" title="bbox (\d+) (\d+) (\d+) (\d+)[^"]*">([^<]*)</span>')


def build():
    s = (W / 'bim2_hocr.html').read_text(encoding='utf-8', errors='replace')
    pages = list(RE_PAGE.finditer(s))
    words = []
    for k, m in enumerate(pages):
        end = pages[k + 1].start() if k + 1 < len(pages) else len(s)
        leaf = int(m.group(1))          # page_000000 起，即叶号
        pw, ph = int(m.group(2)), int(m.group(3))
        for w in RE_W.finditer(s, m.end(), end):
            t = html.unescape(w.group(5)).strip()
            if not t:
                continue
            x0, y0, x1, y1 = map(int, w.group(1, 2, 3, 4))
            words.append({'t': t, 'k': tw.fold(t), 'leaf': leaf, 'pw': pw, 'ph': ph,
                          'x': x0, 'y': y0, 'w': x1 - x0, 'h': y1 - y0})
    (W / 'words_bim2.json').write_text(json.dumps(words), encoding='utf-8')
    print(f'bim2: {len(words)} 词，{len(pages)} 叶', file=sys.stderr)


def locate(ws, keys_by_leaf, s, near_leaf, span=40):
    import edlib
    idx = [k for lf in range(near_leaf - span, near_leaf + span + 1) for k in keys_by_leaf.get(lf, [])]
    if not idx:
        return None
    P, cmap = [], []
    for k in idx:
        P.append(ws[k]['k'])
        cmap += [k] * len(ws[k]['k'])
    P = ''.join(P)
    best = None
    tries = [(s['left'], s['right'], 6)]
    if s['stream'] == 'note' and s.get('mleft'):
        tries.append((s['mleft'], s['mright'], 8))
    for L, R, mn in tries:
        lw = [w for w in L if not tw.TOK.search(w)]
        rw = [w for w in R if not tw.TOK.search(w)]
        Ls = ''.join(tw.fold(w) for w in lw)[-30:]
        Rs = ''.join(tw.fold(w) for w in rw)[:30]
        for q, side in ((Ls, 'L'), (Rs, 'R')):
            if len(q) < mn:
                continue
            a = edlib.align(q, P, mode='HW', task='locations', k=int(len(q) * .4))
            if a['editDistance'] < 0:
                continue
            st, en = a['locations'][0]
            pos = en if side == 'L' else st
            sc = a['editDistance'] / len(q)
            if not best or sc < best[1]:
                best = (cmap[min(pos, len(cmap) - 1)], sc)
        if best and best[1] < .3:
            break
    return best


def crop(item_scan, leaf, y, h, pw, ph, out, width=1150, lines=3, full_width=True):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    f = W / 'img2' / f'bim2_{leaf:04d}.jpg'
    if not f.exists():
        f.parent.mkdir(exist_ok=True)
        tmp = f.with_suffix('.part.jpg')
        tw._download(f'https://archive.org/download/{item_scan}/page/n{leaf}_w2245.jpg', tmp)
        tmp.rename(f)
    im = Image.open(f).convert('L')
    sc = im.width / pw
    lh = int(max(h, 40) * 1.5)
    Y0, Y1 = max(0, y - lh * lines), min(ph, y + h + lh * lines)
    c = im.crop((0, int(Y0 * sc), im.width, int(Y1 * sc)))
    c = c.resize((width, max(1, int(c.height * width / c.width))))
    c.save(out, quality=86)
    return out


def sheets(gids, name, per=4):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sites = json.loads((tw.RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    locs = {r['gid']: r for r in json.loads((tw.RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    ws = json.loads((W / 'words_bim2.json').read_text())
    by_leaf = {}
    for k, w in enumerate(ws):
        by_leaf.setdefault(w['leaf'], []).append(k)
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
    out_dir = W / 'sheets2'
    out_dir.mkdir(exist_ok=True)
    for f in out_dir.glob(f'{name}_*.jpg'):
        f.unlink()
    (W / 'crops2').mkdir(exist_ok=True)
    rows, n, k = [], 0, 0
    width = 1150

    def flush():
        nonlocal rows, k
        if rows:
            Image.fromarray(np.vstack(rows)).save(out_dir / f'{name}_{k:03d}.jpg', quality=85)
            rows, k = [], k + 1
    for g in gids:
        s = sites[g]
        loc = locs[g].get('bim')
        f_leaf = loc['leaf'] if loc else 2 * int(s['facs']) - 2
        near = f_leaf + 3                     # bim2 比 bim 多 6 叶左右，宽窗口兜底
        r = locate(ws, by_leaf, s, near)
        head = Image.new('L', (width, 58), 255)
        dr = ImageDraw.Draw(head)
        dr.text((6, 2), f"#{g} {s['slug']} {'[旁注]' if s['stream'] == 'note' else ''} p.{s.get('page')}  bim2"
                + (f" 叶{ws[r[0]]['leaf']} 距{r[1]:.2f}" if r else ' 未定位'), font=font, fill=70)
        ctx = ' '.join(s['left'][-5:]) + ' [[' + s['tcp'] + ']] ' + ' '.join(s['right'][:5])
        dr.text((6, 30), ctx[:95], font=font, fill=0)
        rows.append(np.array(head))
        if r:
            w = ws[r[0]]
            cf = crop(ITEM, w['leaf'], w['y'], w['h'], w['pw'], w['ph'], W / 'crops2' / f'{g:04d}.jpg',
                      lines=4 if s['stream'] == 'note' else 2)
            im = Image.open(cf).convert('L')
            rows.append(np.array(im))
        rows.append(np.full((6, width), 40, np.uint8))
        n += 1
        if n % per == 0:
            flush()
    flush()
    print(f'{n} 条 → {k} 张 {out_dir}/{name}_*.jpg', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'sheets'])
    ap.add_argument('--gids-file')
    ap.add_argument('--gids')
    ap.add_argument('--name', default='t')
    ap.add_argument('--per', type=int, default=4)
    a = ap.parse_args()
    if a.cmd == 'build':
        build()
    else:
        gids = json.loads(Path(a.gids_file).read_text()) if a.gids_file else \
            tw.parse_gids(a.gids, 10 ** 6)
        sheets(gids, a.name, a.per)


if __name__ == '__main__':
    main()
