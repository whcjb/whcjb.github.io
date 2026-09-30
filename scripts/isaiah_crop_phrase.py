#!/usr/bin/env python3
"""按一句话裁一条**原生分辨率**的窄带，用来判那一处印的是逗号还是句号。

`crop_alexander_isaiah.py` 渲染的是整页：一页两千多字，标点只有几个像素，
送进去等于没送。这里拿 PDF 文本层的坐标定位到那一行，只裁那一行上下各
一点点，再按整数倍放大（最近邻，不插值——扫描件原生就 166 dpi，
更高的 dpi 只是把同样的像素铺开，[[feedback_native_resolution_first]]）。

用法：
    python3 scripts/isaiah_crop_phrase.py "blood-thirsty enemy"
    python3 scripts/isaiah_crop_phrase.py "present moment" --vol v1 --zoom 4
"""
import argparse
import os
from pathlib import Path

import fitz

PDF = {
    'v1': Path.home() / 'Documents/论文/alexander/propheciesisaiah01alexuoft.pdf',
    'v2': Path.home() / 'Documents/论文/alexander/propheciesisaiah02alexuoft.pdf',
}
OFFSET = {'v1': 78, 'v2': 46}
NATIVE_DPI = 166        # 实测：879×1466 像素铺在 379.9×633.6 pt 上


def crop(needle, vol=None, zoom=4, pad=14, out_dir=None):
    out_dir = Path(out_dir or os.environ.get('SCRATCHPAD', '/tmp'))
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for v in ([vol] if vol else ('v1', 'v2')):
        doc = fitz.open(PDF[v])
        for i in range(len(doc)):
            page = doc[i]
            rects = page.search_for(needle)
            if not rects:
                continue
            r = rects[0]
            for extra in rects[1:]:
                r |= extra
            band = fitz.Rect(max(0, r.x0 - pad), max(0, r.y0 - pad),
                             min(page.rect.x1, r.x1 + pad * 4),
                             min(page.rect.y1, r.y1 + pad))
            printed = i + 1 - OFFSET[v]
            tag = f'{v}_p{printed}_{abs(hash(needle)) % 10000}'
            path = out_dir / f'isaiah_band_{tag}.png'
            page.get_pixmap(dpi=NATIVE_DPI * zoom, clip=band).save(path)
            made.append((v, printed, path))
        doc.close()
    return made


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('needle')
    ap.add_argument('--vol', choices=('v1', 'v2'))
    ap.add_argument('--zoom', type=int, default=4)
    ap.add_argument('--pad', type=int, default=14)
    ap.add_argument('--out')
    a = ap.parse_args()
    hits = crop(a.needle, a.vol, a.zoom, a.pad, a.out)
    if not hits:
        raise SystemExit('文本层里没搜到，把串截短些再试')
    for v, printed, path in hits:
        print(v, f'书页 {printed}', '→', path)
