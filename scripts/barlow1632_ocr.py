#!/usr/bin/env python3
"""巴洛 1632 年对开本第二章：逐叶 OCR → witness/ocr/NNNN.json（按行，带坐标）。

    python3 scripts/barlow1632_ocr.py 272-664          # 已做的跳过
    python3 scripts/barlow1632_ocr.py 272-664 --redo

底本只有 IA 这一份胶片扫描（`bim_…_barlow-john_1633`，扉页 1632），没有录入本，正文只能由 OCR 产出。
引擎与预处理在第一章上量过（第一章有 1625 年 TCP 录入本可对照，见 PROVENANCE）：
  - 胶片发灰、透印重、四角暗：先**展平背景**（灰度图除以 41px 闭运算得到的背景）再中值滤波 3，
    对上率 0.537 → 0.610；自适应二值化、CLAHE 都更差。
  - 模型 `eng+enm`（enm 认长 ſ 与早期拼法），`--psm 4`。
  - 不上采样：取原生 800 ppi 的一半（≈400 ppi，barlow1632_fetch.py）。
版面：单栏正文 + 右侧页边旁注（出处、Vse/Doct./Reas. 标记）。按墨迹的横向投影找正文栏右界与旁注栏之间的白缝，
两栏分开识别，避免旁注被并进正文行。页眉（VERS. N. … 页码）是正文栏第一行，组装时剔。
"""
import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / 'barlow_raw' / '2timothy-1632' / 'witness'
IMG = W / 'img'
OUT = W / 'ocr'
LANG = 'eng+enm'

RE_LINE = re.compile(r"<span class='ocr_line' id='[^']+' title=\"bbox (\d+) (\d+) (\d+) (\d+)[^\"]*\">(.*?)</span>\s*(?=<span class='ocr_line'|</p>)", re.S)
RE_WORD = re.compile(r"<span class='ocrx_word' id='[^']+' title='bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)'[^>]*>(.*?)</span>", re.S)


def flat(im, k=41):
    bg = cv2.morphologyEx(im, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return cv2.divide(im, bg, scale=255)


def page_box(im):
    """胶片黑边内的纸面：Otsu 后最大连通块。"""
    _, m = cv2.threshold(cv2.GaussianBlur(im, (31, 31), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return cv2.boundingRect(max(cnts, key=cv2.contourArea))


def columns(f, box):
    """→ (正文 x0, x1, 旁注 x0, x1)。在纸面中段（避开页眉、页脚）做墨迹横向投影，
    正文栏 = 最宽的一段连续高墨迹区；其右侧（或左侧）隔着白缝的较窄墨迹区 = 旁注栏。"""
    x, y, w, h = box
    band = (f[y + h // 8: y + h * 7 // 8, x:x + w] < 140).astype(np.float32)
    prof = cv2.blur(band.mean(0).reshape(1, -1), (61, 1)).ravel()
    on = prof > 0.06
    runs, k = [], 0
    while k < len(on):
        if on[k]:
            j = k
            while j < len(on) and on[j]:
                j += 1
            runs.append((k, j))
            k = j
        else:
            k += 1
    runs = [r for r in runs if r[1] - r[0] > 40]
    if not runs:
        return x, x + w, None, None
    body = max(runs, key=lambda r: r[1] - r[0])
    # 旁注在纸面外侧：正面（奇数页）在右、反面在左。取正文栏两侧留白较宽的一侧
    lw, rw = body[0], w - body[1]
    if max(lw, rw) < w * 0.08:
        mx0 = mx1 = None
    elif rw >= lw:
        mx0, mx1 = x + body[1] + 10, x + w
    else:
        mx0, mx1 = x, x + body[0] - 10
    return x + body[0] - 25, x + body[1] + 25, mx0, mx1


def tess(img, psm):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'p.png'
        cv2.imwrite(str(p), img)
        r = subprocess.run(['tesseract', str(p), str(Path(td) / 'o'), '-l', LANG, '--psm', str(psm), 'hocr'],
                           capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr.decode('utf-8', 'replace')[:200])
        return (Path(td) / 'o.hocr').read_text(encoding='utf-8')


def lines_of(h, dx, dy):
    out = []
    for m in RE_LINE.finditer(h):
        ws = []
        for w in RE_WORD.finditer(m.group(5)):
            t = html.unescape(re.sub(r'<[^>]+>', '', w.group(6))).strip()
            if not t:
                continue
            x0, y0, x1, y1, c = map(int, w.group(1, 2, 3, 4, 5))
            ws.append([t, x0 + dx, y0 + dy, x1 - x0, y1 - y0, c])
        if ws:
            x0, y0, x1, y1 = map(int, m.group(1, 2, 3, 4))
            out.append({'bbox': [x0 + dx, y0 + dy, x1 + dx, y1 + dy], 'words': ws,
                        'text': ' '.join(w[0] for w in ws)})
    return out


def one(leaf, redo=False):
    out = OUT / f'{leaf:04d}.json'
    if out.exists() and not redo:
        return 0
    im = cv2.imread(str(IMG / f'{leaf:04d}.jpg'), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return -1
    f = cv2.medianBlur(flat(im), 3)
    box = page_box(im)
    bx0, bx1, mx0, mx1 = columns(f, box)
    y0, y1 = box[1], box[1] + box[3]
    body = lines_of(tess(f[y0:y1, bx0:bx1], 4), bx0, y0)
    margin = []
    if mx0 is not None:
        margin = lines_of(tess(f[y0:y1, max(0, mx0):mx1], 4), max(0, mx0), y0)
    out.write_text(json.dumps({'leaf': leaf, 'w': im.shape[1], 'h': im.shape[0], 'page': box,
                               'body_x': [bx0, bx1], 'margin_x': [mx0, mx1],
                               'body': body, 'margin': margin}, ensure_ascii=False), encoding='utf-8')
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('range')
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--jobs', type=int, default=6)
    a = ap.parse_args()
    lo, hi = map(int, a.range.split('-'))
    OUT.mkdir(parents=True, exist_ok=True)
    leaves = [lf for lf in range(lo, hi + 1) if (IMG / f'{lf:04d}.jpg').exists()]
    with ProcessPoolExecutor(a.jobs) as ex:
        for k, r in enumerate(ex.map(one, leaves, [a.redo] * len(leaves))):
            if k % 10 == 0:
                print(f'{k}/{len(leaves)}', file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
