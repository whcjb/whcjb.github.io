#!/usr/bin/env python3
"""福特《路加福音讲义》第 ④ 层：希腊活字定位（skill old-book-ocr §1 第 ④ 层 / §2.5）。

主通道（ABBYY、tesseract eng）读不出希腊活字，只吐拉丁乱码（`Ka»^«`、`ats Uofn^tro`）。
这里对全书再跑一遍 tesseract `eng+grc` 出逐词 TSV（含坐标与置信度），挑出含希腊字母的词，
作为第 ④ 层的候选来源。**只当证人**：希腊词要和我们正文里同位置的乱码对上、置信度过线才落。

    python3 scripts/foote_greek_scan.py [--jobs 6]
产物：foote_raw/luke/tess_grc/v{vol}/{leaf:04d}.tsv
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import fitz
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PDF = {1: 'vol1_ed2_lecturesongospe03footgoog.pdf', 2: 'vol2_ed2_lecturesongospe02footgoog.pdf',
       3: 'vol3_ed2_lecturesongospe00footgoog.pdf'}
OUT = ROOT / 'foote_raw' / 'luke' / 'tess_grc'


def one(args):
    vol, leaf = args
    out = OUT / f'v{vol}' / f'{leaf:04d}.tsv'
    if out.exists() and out.stat().st_size > 0:
        return 0
    doc = fitz.open(ROOT / 'foote_raw' / 'luke' / 'pdf' / PDF[vol])
    imgs = doc[leaf].get_images(full=True)
    if not imgs:
        out.write_text('')
        return 0
    img = cv2.imdecode(np.frombuffer(doc.extract_image(imgs[0][0])['image'], np.uint8), cv2.IMREAD_GRAYSCALE)
    tmp = out.with_suffix('.png')
    cv2.imwrite(str(tmp), cv2.medianBlur(img, 3))
    r = subprocess.run(['tesseract', str(tmp), 'stdout', '-l', 'eng+grc', '--psm', '4', 'tsv'],
                       capture_output=True, text=True, env=dict(os.environ, OMP_THREAD_LIMIT='1'))
    tmp.unlink()
    out.write_text(r.stdout, encoding='utf-8')
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    jobs = []
    for v in (1, 2, 3):
        (OUT / f'v{v}').mkdir(parents=True, exist_ok=True)
        jobs += [(v, i) for i in range(fitz.open(ROOT / 'foote_raw' / 'luke' / 'pdf' / PDF[v]).page_count)]
    with ProcessPoolExecutor(a.jobs) as ex:
        done = sum(ex.map(one, jobs, chunksize=8))
    print(f'eng+grc 重扫 {done} 页（共 {len(jobs)}）', file=sys.stderr)


if __name__ == '__main__':
    main()
