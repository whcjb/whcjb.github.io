#!/usr/bin/env python3
"""1625 原版胶片扫描（bim）按叶重新 OCR，只为定位缺字（不作证据）。

    python3 scripts/rollock_bim_ocr.py            # need_leaves.json 里的叶，已做的跳过

IA 自带的 hOCR 漏词严重（一行常只认出一半），定位只能落到页，落不到行。本地 tesseract（eng，psm 3，
中值滤波）重跑：整页按 IA 服务端半宽图（_w2245，≈400 ppi）下载存 witness/img/bim_NNNN.jpg
供裁图 → hOCR 词 → witness/ocr/NNNN.json。原图不留（磁盘紧，见 memory project_adams_2peter_gapfill）。
"""
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import barlow_witness as rw  # noqa: E402

OCR = rw.W / 'ocr'
UP = 1.5
RE_WORD = re.compile(r"<span class='ocrx_word' id='[^']+' title='bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)'[^>]*>(.*?)</span>",
                     re.S)


def one(leaf):
    out = OCR / f'{leaf:04d}.json'
    if out.exists():
        return 0
    import cv2
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    half = rw.IMG / f'bim_{leaf:04d}.jpg'
    full = rw.IMG / f'bim_{leaf:04d}_full.jpg'
    if not half.exists():
        rw._download(rw.page_url(leaf, 2245), full)      # IA 服务端缩到半宽（≈400 ppi），省 3/4 流量
        im = Image.open(full).convert('L')
        if im.width > 2400:
            im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        im.save(half, quality=90)
        full.unlink()
    # 1625 本胶片发灰、四周黑边、透印重：直接 OCR 一叶只认出几十词。先按 Otsu 找页面区切掉黑边，
    # 放大 1.5 倍后自适应二值化（实测叶 150：53 词 → 502 词）；词框坐标再换回整页半尺寸图。
    img = cv2.imread(str(half), cv2.IMREAD_GRAYSCALE)
    _, m = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cx, cy, cw, ch = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    up = cv2.resize(img[cy:cy + ch, cx:cx + cw], None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
    bw = cv2.adaptiveThreshold(cv2.medianBlur(up, 3), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 18)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'p.png'
        cv2.imwrite(str(p), bw)
        subprocess.run(['tesseract', str(p), str(Path(td) / 'o'), '-l', 'eng', '--psm', '3', 'hocr'],
                       check=True, capture_output=True)
        h = (Path(td) / 'o.hocr').read_text(encoding='utf-8')
    import html
    ws = []
    for m in RE_WORD.finditer(h):
        t = html.unescape(re.sub(r'<[^>]+>', '', m.group(6))).strip()
        if t:
            x0, y0, x1, y1, c = map(int, m.group(1, 2, 3, 4, 5))
            x0, y0, x1, y1 = (round(x0 / UP) + cx, round(y0 / UP) + cy, round(x1 / UP) + cx, round(y1 / UP) + cy)
            ws.append([t, x0, y0, x1 - x0, y1 - y0, c])
    out.write_text(json.dumps({'w': img.shape[1], 'h': img.shape[0], 'words': ws}), encoding='utf-8')
    return 1


def main():
    OCR.mkdir(parents=True, exist_ok=True)
    leaves = json.loads((rw.W / 'need_leaves.json').read_text())
    done = 0
    with ThreadPoolExecutor(10) as ex:
        for i, r in enumerate(ex.map(one, leaves)):
            done += r
            if i % 20 == 0:
                print(f'{i}/{len(leaves)}', file=sys.stderr, flush=True)
    print(f'新做 {done}，共 {len(leaves)}', file=sys.stderr)


if __name__ == '__main__':
    main()
