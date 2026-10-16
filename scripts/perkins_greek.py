#!/usr/bin/env python3
"""第 ④ 层：TCP 不录的希腊文（〈Greek〉）→ 裁图 + tesseract grc 单独识别 + 判读图。

    python3 scripts/perkins_greek.py

old-book-ocr §2.5：零散的非拉丁活字走单独裁图重扫，不让主通道兼顾。
tesseract grc 的读数只当候选；落盘的希腊文以判读图上的影像为准（含重音、气符）。
来源优先 1604 影像（缺字词框 mid_box）；1604 定位不到的，用他版（other_locs.json）。
"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_gapcrop as gc  # noqa: E402
import perkins_otheredition as oe  # noqa: E402

OUT = gc.RAW / 'greek_ocr.json'
TMP = gc.W / 'greek'


def grc(img):
    TMP.mkdir(exist_ok=True)
    p = TMP / 'x.png'
    cv2.imwrite(str(p), img)
    r = subprocess.run(['tesseract', str(p), '-', '-l', 'grc', '--psm', '7'],
                       capture_output=True, text=True)
    return r.stdout.strip()


def main():
    sites = json.loads(gc.LOCS.read_text(encoding='utf-8'))
    other = json.loads(oe.OUT.read_text(encoding='utf-8')) if oe.OUT.exists() else {}
    res = {}
    rows = []
    width = 1500
    for s in sites:
        if s['kind'] != 'foreign':
            continue
        crops = []
        loc = s.get('loc')
        if loc and loc.get('mid_box'):
            im = gc.page_img(loc['leaf'])
            x0, y0, x1, y1 = loc['mid_box']
            c = im[max(0, y0 - 25):y1 + 25, max(0, x0 - 30):x1 + 30]
            if c.size:
                crops.append(('1604', loc['leaf'], c))
        for ed, v in other.get(str(s['id']), {}).items():
            if v.get('native'):
                continue
            im = cv2.imread(str(oe.fetch(ed, v['leaf'])), cv2.IMREAD_GRAYSCALE)
            x0, y0, x1, y1 = v['box']
            c = im[max(0, y0 - 25):y1 + 25, max(0, x0 - 30):x1 + 30]
            if c.size:
                crops.append((ed, v['leaf'], c))
        res[str(s['id'])] = [{'ed': ed, 'leaf': lf, 'grc': grc(cv2.medianBlur(c, 3))} for ed, lf, c in crops]
        if not crops:
            continue
        head = np.full((34, width), 255, np.uint8)
        cv2.putText(head, f"#{s['id']} {'NOTE ' if s['in_note'] else ''}{gc.ascii_safe(s['tcp'])[:115]}",
                    (6, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.68, 0, 2)
        rows.append(head)
        for (ed, lf, c), r in zip(crops, res[str(s['id'])]):
            sc = min(2.0, width / c.shape[1])
            c = cv2.resize(c, (int(c.shape[1] * sc), int(c.shape[0] * sc)), interpolation=cv2.INTER_CUBIC)
            if c.shape[1] < width:
                c = np.hstack([c, np.full((c.shape[0], width - c.shape[1]), 255, np.uint8)])
            lab = np.full((24, width), 255, np.uint8)
            cv2.putText(lab, f"{ed} leaf {lf}  (grc ocr in greek_ocr.json)", (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, 90, 1)
            rows += [lab, c[:min(c.shape[0], 700)]]
        rows.append(np.full((12, width), 160, np.uint8))
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for f in gc.SHEETS.glob('greek_*.jpg'):
        f.unlink()
    # 按高度切页
    page, h, n = [], 0, 0
    for r in rows:
        page.append(r)
        h += r.shape[0]
        if h > 2400 and r.shape[0] == 12:
            cv2.imwrite(str(gc.SHEETS / f'greek_{n:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 85])
            page, h, n = [], 0, n + 1
    if page:
        cv2.imwrite(str(gc.SHEETS / f'greek_{n:03d}.jpg'), np.vstack(page), [cv2.IMWRITE_JPEG_QUALITY, 85])
        n += 1
    print(f'希腊文 {len(res)} 处，有图 {sum(1 for v in res.values() if v)}，{n} 张判读图', file=sys.stderr)


if __name__ == '__main__':
    main()
