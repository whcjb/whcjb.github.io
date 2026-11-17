#!/usr/bin/env python3
"""1859 初版扫描页（IA christhischurchi00bona）取图与裁切。

页图按需下载到 src/ia1859/pages/n<leaf>.jpg（leaf = hOCR 页号 − 1，已核对）；
crop(hocr_page, y0, y1) 按 hOCR 坐标裁一条（hOCR 页宽 1903，图宽 1883，按比例换算）。
"""
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / 'bonar_raw' / 'psalms' / 'src' / 'ia1859' / 'pages'
URL = 'https://archive.org/download/christhischurchi00bona/page/n{}.jpg'


def page_img(hocr_page):
    PAGES.mkdir(parents=True, exist_ok=True)
    leaf = hocr_page - 1
    f = PAGES / f'n{leaf}.jpg'
    if not f.exists() or f.stat().st_size < 10000:
        subprocess.run(['curl', '-sSL', '--retry', '4', '-o', str(f), URL.format(leaf)], check=True)
    return Image.open(f)


def crop(hocr_page, y0, y1, x0=0, x1=1903, pad=8):
    im = page_img(hocr_page)
    k = im.width / 1903
    return im.crop((max(0, int(x0 * k) - pad), max(0, int(y0 * k) - pad),
                    min(im.width, int(x1 * k) + pad), min(im.height, int(y1 * k) + pad)))
