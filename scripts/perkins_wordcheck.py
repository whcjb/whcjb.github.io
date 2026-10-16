#!/usr/bin/env python3
"""录入错候选 → 1604 影像行图（第 ③ 层核对）。

    python3 scripts/perkins_wordcheck.py WORD1 WORD2 ...   → witness_1604/sheets/wc_*.jpg

每个候选词按它在产物里的**印本页**（上一个 pk-pb 锚点）+ 前后文定位：
页 → leaf 用 pick_leaf（整页词重合），页内用前后 8 词做短语匹配（perkins_phrase.find），
只在该叶及相邻叶里找，不全书搜，避免撞到别处同句。
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_common as pc  # noqa: E402
import perkins_gapcrop as gc  # noqa: E402
import perkins_phrase as ph  # noqa: E402

RX_PB = re.compile(r'<span class="pk-pb" id="p([^"]+)" data-p="[^"]+" data-facs="(\d+)"></span>')


def occurrences(words):
    want = {w.lower() for w in words}
    out = []
    for f in sorted(pc.SRC.glob('*.md')):
        md = pc.load(f.stem)
        for m in re.finditer(r'[A-Za-z̄]+', md):
            if m.group(0).lower() not in want:
                continue
            # 跳过 HTML 标签内
            if md.rfind('<', 0, m.start()) > md.rfind('>', 0, m.start()):
                continue
            pbs = list(RX_PB.finditer(md, 0, m.start()))
            facs = int(pbs[-1].group(2)) if pbs else None
            t = re.sub(r'<[^>]+>', ' ', md).replace('*', ' ')
            pre = re.sub(r'<[^>]+>', ' ', md[:m.start()]).replace('*', ' ').split()[-8:]
            post = re.sub(r'<[^>]+>', ' ', md[m.end():m.end() + 400]).replace('*', ' ').split()[:8]
            out.append({'slug': f.stem, 'w': m.group(0), 'facs': facs, 'left': pre, 'right': post})
    return out


def main():
    occ = occurrences(sys.argv[1:])
    rows, width = [], 1500
    miss = []
    for k, o in enumerate(occ):
        head = np.full((30, width), 255, np.uint8)
        cv2.putText(head, f"W{k} {o['slug']} {' '.join(o['left'][-5:])} [[{o['w']}]] {' '.join(o['right'][:5])}"[:128],
                    (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 0, 2)
        rows.append(head)
        if o['facs'] is None:
            miss.append(k); rows.append(np.full((10, width), 160, np.uint8)); continue
        F = o['facs']
        src = {L: gc.load_ocr(L) for L in range(2 * F - 4, 2 * F + 1) if L >= 0}
        L = [gc.fold(w) for w in o['left'] if gc.fold(w)]
        R = [gc.fold(w) for w in o['right'] if gc.fold(w)]
        b = ph.find(src, L + [gc.fold(o['w'])], R)
        if not b or b[0] < 0.5:
            miss.append(k); rows.append(np.full((10, width), 160, np.uint8)); continue
        win = b[3]
        im = gc.page_img(b[1])
        ys = sorted(w['y'] for w in win); ym = ys[len(ys) // 2]
        c = im[max(0, ym - 100):ym + 160, :]
        c = cv2.resize(c, (width, int(c.shape[0] * width / c.shape[1])), interpolation=cv2.INTER_AREA)
        rows += [c, np.full((10, width), 160, np.uint8)]
    for f in gc.SHEETS.glob('wc_*.jpg'):
        f.unlink()
    page, h, n = [], 0, 0
    for r in rows:
        page.append(r); h += r.shape[0]
        if h > 2200 and r.shape[0] == 10:
            cv2.imwrite(str(gc.SHEETS / f'wc_{n:02d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 82])
            page, h, n = [], 0, n + 1
    if page:
        cv2.imwrite(str(gc.SHEETS / f'wc_{n:02d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 82]); n += 1
    json.dump(occ, open('/tmp/claude-502/wc.json', 'w'), ensure_ascii=False)
    print(f'{len(occ)} 处 → {n} 张；定位失败 {miss}', file=sys.stderr)


if __name__ == '__main__':
    main()
