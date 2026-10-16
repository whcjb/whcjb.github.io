#!/usr/bin/env python3
"""对缺字所在的 leaf 重跑 tesseract，取词级坐标（old-book-ocr §2.5 实测配置）。

    python3 scripts/perkins_ocr.py [--jobs 8]

IA 自带的那层 OCR 不能用来定位：缩微胶片版心两侧的竖线把版面切碎，词序
整页打乱（leaf 0035：`For there one ſo goſpeli. Paul ; word men,…`）。
这里只要它做一件事——**给 TCP 缺字两侧的词找到页面坐标**，好裁图。
字是什么，由裁图判读决定，不由这一遍 OCR 决定。

配置：原生分辨率（不上采样）、medianBlur(3)、--psm 4、eng。
输出：witness_1604/ocr/<leaf>.tsv（tesseract TSV，第 5 层 = 词）。
"""
import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / 'perkins_raw' / 'galatians' / 'witness_1604'
JP2 = W / 'jp2'
OCR = W / 'ocr'


def run(jp2):
    leaf = jp2.stem.rsplit('_', 1)[1]
    out = OCR / f'{leaf}.tsv'
    if out.exists() and out.stat().st_size > 0:
        return leaf, 'skip'
    im = cv2.imread(str(jp2), cv2.IMREAD_GRAYSCALE)
    im = cv2.medianBlur(im, 3)
    png = OCR / f'{leaf}.png'
    cv2.imwrite(str(png), im)
    r = subprocess.run(['tesseract', str(png), str(OCR / leaf), '-l', 'eng',
                        '--psm', '4', 'tsv'], capture_output=True, text=True)
    png.unlink()
    if r.returncode:
        return leaf, 'ERR ' + r.stderr[-300:]
    return leaf, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=8)
    a = ap.parse_args()
    OCR.mkdir(exist_ok=True)
    files = sorted(JP2.glob('*.jp2'))
    bad = 0
    with ProcessPoolExecutor(a.jobs) as ex:
        for leaf, st in ex.map(run, files):
            if st.startswith('ERR'):
                bad += 1
                print(leaf, st, file=sys.stderr)
    print(f'{len(files)} 叶，失败 {bad}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
