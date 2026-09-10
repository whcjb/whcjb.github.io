#!/usr/bin/env python3
"""希腊文那一路：把两卷正文页再用 `grc` 模型读一遍，取出希腊词。

为什么单开一遍
--------------
正文里的希腊词原书是希腊活字，我们那遍 OCR 用的是 `eng+lat`，读出来是
一串拉丁乱码（`Qpovi're` / `wpooxaprspeire` / `"E» mae copia`）。IA 那一层
同样是英文模型，两个证人一起花，前面三方相校那一路救不了它。

但**不能把 grc 加进主 OCR**：实测会把小型大写的页眉 `Ver. 3.` 读成
`Ρεν, 8.`（见 ocr_davenant.py 抬头）。所以单跑一遍、只取希腊字母那部分，
英文照旧用主 OCR 的结果。

输出 davenant_raw/colossians/vol{1,2}_grc.jsonl，每行一页 {page, text}。

用法:
    python3 scripts/ocr_davenant_grc.py --vol 2 --pages 233-233   # 试跑
    python3 scripts/ocr_davenant_grc.py                           # 两卷正文页
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import fitz
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PDFS = {1: 'expositionofepis01dave.pdf', 2: 'expositionofepis02dave.pdf'}
# 覆盖到卷二末尾：附卷《论基督之死》、法国之争与六种索引都在 318 页之后，
# 只跑到 317 的话那一半书拿不到第三证人（附卷同样有词内数字与撇号的错）。
RANGES = {1: (86, 631), 2: (14, 620)}


def ocr_page(args):
    pdf, idx = args
    doc = fitz.open(pdf)
    pix = doc[idx].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
    doc.close()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    img = cv2.medianBlur(img, 3)
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p.png')
        cv2.imwrite(png, img)
        out = os.path.join(td, 'o')
        r = subprocess.run(['tesseract', png, out, '-l', 'grc+eng', '--psm', '6'],
                           capture_output=True)
        if r.returncode != 0:
            return idx, ''
        return idx, open(out + '.txt', encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages')
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    for vol in ([a.vol] if a.vol else (1, 2)):
        lo, hi = RANGES[vol]
        if a.pages:
            lo, hi = (int(x) for x in a.pages.split('-'))
        pdf = str(RAW / PDFS[vol])
        idxs = list(range(lo, hi + 1))
        tag = '_sample' if a.pages else ''
        out = RAW / f'vol{vol}_grc{tag}.jsonl'
        print(f'▶ vol{vol}  {len(idxs)} 页 → {out.name}', flush=True)
        res = {}
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for k, (idx, txt) in enumerate(
                    ex.map(ocr_page, [(pdf, i) for i in idxs]), 1):
                res[idx] = txt
                if k % 25 == 0:
                    print(f'  {k}/{len(idxs)}', flush=True)
        with out.open('w', encoding='utf-8') as fh:
            for i in idxs:
                fh.write(json.dumps({'page': i, 'text': res[i]},
                                    ensure_ascii=False) + '\n')
        print(f'[ok] → {out.name}  {out.stat().st_size:,} 字节', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
