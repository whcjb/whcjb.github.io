#!/usr/bin/env python3
"""短语检索定位：缺字两侧上下文（各 10 词）当一整串，在三个版本的 OCR 里找最像的那一段。

    python3 scripts/perkins_phrase.py --ids 1,2,3      → witness_1604/sheets/ph_*.jpg

锚点投票（perkins_gapcrop.locate / perkins_otheredition.vote）在上下文全是常见词时
会撞车，落到别段（ed_000 六条错五条）。这里换判据（同一个坑第二次必须换机制）：
  1. 粗筛：上下文里 ≥6 字母的词，在哪几叶出现得最多 → 取前 4 叶（三版各自）；
  2. 精配：叶内按词滑窗，把窗口词串与上下文词串折叠成字母串比 SequenceMatcher，
     取最高分；< 0.55 的不出图（宁可报找不到，不出错图）。
三版各出一条，人工看图定夺。
"""
import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_gapcrop as gc  # noqa: E402
import perkins_otheredition as oe  # noqa: E402

N = 10


def leaves_1604():
    out = {}
    for p in sorted(gc.OCR.glob('*.tsv')):
        out[int(p.stem)] = gc.load_ocr(int(p.stem))
    return out


def find(ws_by_leaf, L, R):
    ctx = L + R
    long_ = {k for k in ctx if len(k) >= 6}
    scored = []
    for leaf, ws in ws_by_leaf.items():
        ks = {w['k'] for w in ws}
        n = sum(1 for k in long_ if k in ks or any(len(x) >= 6 and SequenceMatcher(None, k, x).ratio() > .8 for x in ks if x[:2] == k[:2]))
        if n:
            scored.append((n, leaf))
    scored.sort(reverse=True)
    target = ''.join(ctx)
    best = None
    for _, leaf in scored[:4]:
        ws = ws_by_leaf[leaf]
        W = len(L) + len(R) + 2
        for i in range(0, max(1, len(ws) - W // 2)):
            win = ws[i:i + W]
            s = ''.join(w['k'] for w in win)
            r = SequenceMatcher(None, target, s, autojunk=False).ratio()
            if best is None or r > best[0]:
                best = (r, leaf, i, win)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', required=True)
    a = ap.parse_args()
    ids = [int(x) for x in a.ids.split(',') if x]
    sites = {s['id']: s for s in json.loads(gc.LOCS.read_text(encoding='utf-8'))}
    srcs = {'1604': leaves_1604()}
    for ed in oe.EDS:
        srcs[ed] = {i: ws for i, ws in enumerate(oe.leaves(ed))}
    rows, res = [], {}
    width = 1500
    for i in ids:
        s = sites[i]
        L = [gc.fold(w) for w in s['left'][-N:] if gc.fold(w)]
        R = [gc.fold(w) for w in s['right'][:N] if gc.fold(w)]
        head = np.full((34, width), 255, np.uint8)
        cv2.putText(head, f"#{i} {s['kind']} {gc.ascii_safe(s['tcp'])[:120]}", (6, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, 0, 2)
        rows.append(head)
        res[i] = {}
        for ed, src in srcs.items():
            b = find(src, L, R)
            if not b or b[0] < 0.55:
                continue
            r, leaf, j, win = b
            res[i][ed] = {'leaf': leaf, 'ratio': round(r, 2)}
            if ed == '1604':
                im = gc.page_img(leaf)
            else:
                im = cv2.imread(str(oe.fetch(ed, leaf)), cv2.IMREAD_GRAYSCALE)
            x0 = min(w['x'] for w in win); y0 = min(w['y'] for w in win)
            x1 = max(w['x'] + w['w'] for w in win); y1 = max(w['y'] + w['h'] for w in win)
            if y1 - y0 > 400:   # 跨了好几行：以中段为准
                ym = sorted(w['y'] for w in win)[len(win) // 2]
                y0, y1 = ym - 150, ym + 200
            c = im[max(0, y0 - 40):y1 + 40, max(0, x0 - 60):x1 + 60]
            if c.size == 0:
                continue
            sc = min(1.0, width / c.shape[1])
            c = cv2.resize(c, (int(c.shape[1] * sc), int(c.shape[0] * sc)), interpolation=cv2.INTER_AREA)
            if c.shape[1] < width:
                c = np.hstack([c, np.full((c.shape[0], width - c.shape[1]), 255, np.uint8)])
            lab = np.full((24, width), 255, np.uint8)
            cv2.putText(lab, f"{ed} leaf {leaf} match {r:.2f}", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 90, 1)
            rows += [lab, c[:420]]
        rows.append(np.full((12, width), 160, np.uint8))
    for f in gc.SHEETS.glob('ph_*.jpg'):
        f.unlink()
    page, h, n = [], 0, 0
    for r in rows:
        page.append(r); h += r.shape[0]
        if h > 2300 and r.shape[0] == 12:
            cv2.imwrite(str(gc.SHEETS / f'ph_{n:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 82])
            page, h, n = [], 0, n + 1
    if page:
        cv2.imwrite(str(gc.SHEETS / f'ph_{n:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 82]); n += 1
    (gc.RAW / 'phrase_locs.json').write_text(json.dumps(res, indent=0) + '\n', encoding='utf-8')
    print(f'{len(ids)} 条 → {n} 张；三版都没找到的：{[i for i in ids if not res[i]]}', file=sys.stderr)


if __name__ == '__main__':
    main()
