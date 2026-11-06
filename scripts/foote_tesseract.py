#!/usr/bin/env python3
"""福特《路加福音讲义》第二条非生成式字流：tesseract 重扫第 2 版三卷（skill §2.5 / §3.2c）。

主字流是 IA 自带 ABBYY。这条流只当**证人**：给第 67–137 讲（没有第二份扫描）做按位置判读，
给全书游离符号（`^` `«` `♦`…）逐个取证。它的字不直接进产物，要和 ABBYY 同位一致才落。

配置（skill §2.5 实测）：PDF 内嵌原图（约 500 dpi，不上采样）→ cv2.medianBlur(3) → tesseract eng --psm 4。
主通道只用 eng；希腊活字走第 ④ 层单独裁图重扫。

    python3 scripts/foote_tesseract.py [--vol 1|2|3] [--jobs 6]
产物：foote_raw/luke/tess/v{vol}/{leaf:04d}.txt（leaf 与 ABBYY 页序一致，0 起）
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
OUT = ROOT / 'foote_raw' / 'luke' / 'tess'


def one(args):
    vol, leaf = args
    out = OUT / f'v{vol}' / f'{leaf:04d}.txt'
    if out.exists() and out.stat().st_size > 0:
        return 0
    doc = fitz.open(ROOT / 'foote_raw' / 'luke' / 'pdf' / PDF[vol])
    imgs = doc[leaf].get_images(full=True)
    if not imgs:
        out.write_text('')
        return 0
    raw = doc.extract_image(imgs[0][0])['image']
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
    img = cv2.medianBlur(img, 3)
    tmp = out.with_suffix('.png')
    cv2.imwrite(str(tmp), img)
    env = dict(os.environ, OMP_THREAD_LIMIT='1')
    r = subprocess.run(['tesseract', str(tmp), 'stdout', '-l', 'eng', '--psm', '4'],
                       capture_output=True, text=True, env=env)
    tmp.unlink()
    out.write_text(r.stdout, encoding='utf-8')
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2, 3))
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    jobs = []
    for v in ([a.vol] if a.vol else [1, 2, 3]):
        (OUT / f'v{v}').mkdir(parents=True, exist_ok=True)
        n = fitz.open(ROOT / 'foote_raw' / 'luke' / 'pdf' / PDF[v]).page_count
        jobs += [(v, i) for i in range(n)]
    with ProcessPoolExecutor(a.jobs) as ex:
        done = sum(ex.map(one, jobs, chunksize=8))
    print(f'重扫 {done} 页（共 {len(jobs)}）', file=sys.stderr)


if __name__ == '__main__':
    main()
