#!/usr/bin/env python3
"""把待判条目在底本 PDF 上的那一行裁出来拼成长图，供人眼逐条核字。

为什么要裁图
------------
判读（影像）与 raw OCR、PDF 自带文本层是三份来源，前两者不一致时，第三份
往往**跟着一起错**——「藐视」在 raw 和 PDF 文本层里都成了「貌视」（艹头在低
分辨率下丢了）。这种只能回到像素上看。

定位靠模糊对齐：PDF 文本层本身是烂 OCR（`巧诉我们巧上帝`），拿正文串直接
search_for 多半找不到。所以按 words 顺序拼出该页的 CJK 流，把探针对齐上去，
取命中区间对应 words 的包围盒，再上下各放宽一行。

用法：
    python3 scripts/crop_ocr_candidates.py --tsv logs/applied4_john.tsv --out /tmp/crops
"""
import argparse
import difflib
import re
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

CJK = re.compile(r'[一-鿿]')
PDF = '/Users/yanpeifa/Documents/论文/calvin/加尔文--约翰福音注释.pdf'


def page_words_ocr(page, dpi=300, lang='chi_sim'):
    """扫描版（PDF 无文本层）用 tesseract 现场取坐标 → (CJK 流, [每字矩形])

    罗马书那本底本是纯扫描，`get_text()` 返回空，PDF 文本层这条路走不通。
    tesseract 的 TSV 输出带 word 级 bbox，按同样的办法摊到每个字上即可。
    """
    import csv
    import subprocess
    import tempfile
    pm = page.get_pixmap(dpi=dpi)
    sx = 72.0 / dpi                      # 像素 → PDF 坐标
    with tempfile.TemporaryDirectory() as td:
        img = f'{td}/p.png'
        pm.save(img)
        out = subprocess.run(['tesseract', img, 'stdout', '-l', lang,
                              '--psm', '6', 'tsv'],
                             capture_output=True, text=True).stdout
    stream, rects = [], []
    for row in csv.DictReader(out.splitlines(), delimiter='\t',
                              quoting=csv.QUOTE_NONE):
        try:
            x0, y0 = float(row['left']), float(row['top'])
            w, h = float(row['width']), float(row['height'])
        except (TypeError, ValueError, KeyError):
            continue
        chars = CJK.findall(row.get('text') or '')
        if not chars:
            continue
        step = w / len(chars)
        for k, c in enumerate(chars):
            stream.append(c)
            rects.append(fitz.Rect((x0 + k * step) * sx, y0 * sx,
                                   (x0 + (k + 1) * step) * sx, (y0 + h) * sx))
    return ''.join(stream), rects


def page_words(page):
    """→ (CJK 流, [每个字对应的 word 矩形])"""
    stream, rects = [], []
    for w in page.get_text('words'):
        x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
        chars = CJK.findall(txt)
        if not chars:
            continue
        step = (x1 - x0) / len(chars)
        for k, c in enumerate(chars):
            stream.append(c)
            rects.append(fitz.Rect(x0 + k * step, y0, x0 + (k + 1) * step, y1))
    return ''.join(stream), rects


def locate(stream, probe):
    """probe 在 stream 里的最佳落点 → (lo, hi) 或 None（模糊，容 OCR 错字）"""
    if not probe or not stream:
        return None
    sm = difflib.SequenceMatcher(None, stream, probe, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 3]
    if not blocks:
        return None
    tot = sum(b.size for b in blocks)
    if tot < len(probe) * 0.45:
        return None
    return min(b.a for b in blocks), max(b.a + b.size for b in blocks)


def crop(doc, pg, probe, dpi=300, lines=2, ocr=False):
    page = doc[pg - 1]
    stream, rects = page_words_ocr(page) if ocr else page_words(page)
    hit = locate(stream, probe)
    if not hit:
        return None
    lo, hi = hit
    box = rects[lo]
    for r in rects[lo:hi]:
        box |= r
    lh = box.height or 12
    clip = fitz.Rect(page.rect.x0, box.y0 - lh * lines,
                     page.rect.x1, box.y1 + lh * lines)
    pm = page.get_pixmap(clip=clip, dpi=dpi)
    img = Image.frombytes('RGB', (pm.width, pm.height), pm.samples)
    # 在目标字下方画一道标记线，省得人眼在整行里找
    d = ImageDraw.Draw(img)
    sx = dpi / 72.0
    d.rectangle([(box.x0 - clip.x0) * sx, (box.y1 - clip.y0) * sx + 2,
                 (box.x1 - clip.x0) * sx, (box.y1 - clip.y0) * sx + 6],
                fill=(220, 0, 0))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tsv', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pdf', default=PDF)
    ap.add_argument('--per-sheet', type=int, default=6)
    a = ap.parse_args()

    doc = fitz.open(a.pdf)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = [l.rstrip('\n').split('\t') for l in
            Path(a.tsv).read_text(encoding='utf-8').splitlines() if l.strip()]

    sheet, idx = [], 0
    for i, r in enumerate(rows, 1):
        pg, old, new, tag = int(r[0]), r[2], r[3], r[4] if len(r) > 4 else ''
        m = re.search(r'…(.*?)\[(.+?)→(.+?)\](.*?)…', tag)
        probe = (''.join(CJK.findall(m.group(1) + m.group(2) + m.group(4)))
                 if m else ''.join(CJK.findall(old)))
        img = crop(doc, pg, probe[:24])
        if img is None:
            print(f'{i:3d}. p{pg} 定位失败 「{old}」→「{new}」')
            continue
        w = 1400
        img = img.resize((w, max(1, int(img.height * w / img.width))))
        sheet.append((f'{i:02d}. p{pg}  {old} → {new}', img))
        if len(sheet) >= a.per_sheet:
            idx += 1
            save(sheet, out / f'sheet{idx:02d}.png')
            sheet = []
    if sheet:
        idx += 1
        save(sheet, out / f'sheet{idx:02d}.png')
    print(f'→ {idx} 张拼图 in {out}')


def save(sheet, path):
    pad = 34
    W = max(im.width for _, im in sheet)
    H = sum(im.height + pad for _, im in sheet)
    canvas = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    y = 0
    for label, im in sheet:
        d.text((6, y + 8), label, fill=(0, 0, 160))
        y += pad
        canvas.paste(im, (0, y))
        y += im.height
        d.line([(0, y - 2), (W, y - 2)], fill=(180, 180, 180), width=2)
    canvas.save(path)
    print('  ', path)


if __name__ == '__main__':
    main()
