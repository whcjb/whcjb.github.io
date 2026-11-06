#!/usr/bin/env python3
"""判读补裁：jones_witness 的紧图偏了（跨行、行首、旁注、定位落到同页别处）时用。

    python3 scripts/jones_fix_crop.py OUT.jpg 2john-014:wrap 2john-033:margin …

模式：wrap = 本行 + 下一行整行（跨行的希腊文）；up = 上一行整行 + 本行；margin = 定位行上下各 3 行、整页宽两半（旁注栏在版心内）；
page = 定位行上下 6 行整页宽（缩到 1400，只用来找位置）。整行模式按原生分辨率分两半拼，不缩放。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jones_common as jc  # noqa: E402
import jones_witness as jw  # noqa: E402

W = 1400


def pad(t):
    if t.shape[1] > W:
        t = cv2.resize(t, (W, int(t.shape[0] * W / t.shape[1])), interpolation=cv2.INTER_AREA)
    return np.hstack([t, np.full((t.shape[0], W - t.shape[1]), 255, np.uint8)])


def halves(img, y0, y1):
    """整行按原生分辨率左右两半叠放（每半 ≤ 2800 宽 → 缩到 1400，约 0.5 倍，希腊小字仍可读）。"""
    h, w = img.shape
    l, r = int(w * .04), int(w * .96)
    m = (l + r) // 2
    return [pad(img[y0:y1, l:m + 60]), pad(img[y0:y1, m - 60:r])]


def main():
    out, rows = sys.argv[1], []
    for arg in sys.argv[2:]:
        key, _, mode = arg.partition(':')
        book, g = key.split('-')
        s = json.loads((jc.raw(book) / 'gap_sites.json').read_text(encoding='utf-8'))[int(g)]
        loc = jw.locate(s) or (jw.locate(s, 'm') if s['stream'] == 'note' else None)
        if not loc:
            print(f'{key} 定位不到', file=sys.stderr)
            continue
        leaf, x, y = loc[:3]
        img = cv2.imread(str(jw.leaf_img(leaf)), cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        bar = np.full((34, W), 255, np.uint8)
        cv2.putText(bar, f'{key} {mode} leaf {leaf}', (6, 26), cv2.FONT_HERSHEY_SIMPLEX, .9, 0, 2)
        rows.append(bar)
        if mode == 'wrap':
            parts = halves(img, y - 70, y + 190)
        elif mode == 'up':
            parts = halves(img, y - 230, y + 60)
        elif mode == 'margin':                 # 旁注栏在版心内（单页左或右），取整页宽两半，上下各约 3 行
            parts = halves(img, max(0, y - 300), y + 300)
        else:
            parts = [pad(img[max(0, y - 600):y + 600, :])]
        for p in parts:
            rows += [p, np.full((4, W), 128, np.uint8)]
        rows.append(np.zeros((8, W), np.uint8))
    cv2.imwrite(out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])


if __name__ == '__main__':
    main()
