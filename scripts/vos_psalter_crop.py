#!/usr/bin/env python3
"""按锚词在 PTR 原刊页图上裁出所在行（原生分辨率 JP2），拼成一张对照图供判读。

用法: vos_psalter_crop.py OUT.png "锚词1" "锚词2" ...
  锚词按扫描本 OCR（djvu.xml）的词匹配（不区分大小写，子串）；同一锚词多处命中全部裁出。
  锚词可写成 "p17:锚词" 限定原刊页码。
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'vos_raw' / 'psalter' / 'src'
ARTICLE_PAGES = range(1, 44)


def load_pages():
    x = (SRC / 'ptr_djvu.xml').read_text(encoding='utf-8')
    pages = {}
    for o in re.findall(r'<OBJECT[^>]*>.*?</OBJECT>', x, flags=re.S):
        leaf = int(re.search(r'_(\d{4})\.djvu', o).group(1))
        p = leaf - 2
        if p not in ARTICLE_PAGES:
            continue
        lines = []
        for ln in re.findall(r'<LINE>(.*?)</LINE>', o, flags=re.S):
            ws = [(tuple(map(int, c.split(',')[:4])), t)
                  for c, t in re.findall(r'<WORD coords="([^"]+)"[^>]*>([^<]*)</WORD>', ln)]
            if ws:
                lines.append(ws)
        pages[p] = (leaf, lines)
    return pages


def main():
    out = Path(sys.argv[1])
    anchors = sys.argv[2:]
    pages = load_pages()
    crops = []
    for a in anchors:
        pg = None
        m = re.match(r'p(\d+):(.*)', a)
        if m:
            pg, a = int(m.group(1)), m.group(2)
        hit = False
        for p, (leaf, lines) in sorted(pages.items()):
            if pg and p != pg:
                continue
            for li, ws in enumerate(lines):
                if any(a.lower() in t.lower() for _, t in ws):
                    xs = [c for ln in lines[max(0, li - 1):li + 2] for c, _ in ln]
                    l, b, r, t = min(c[0] for c in xs), max(c[1] for c in xs), \
                        max(c[2] for c in xs), min(c[3] for c in xs)
                    img = Image.open(SRC / 'jp2' / f'{leaf:04d}.jp2').convert('L')
                    box = (max(0, l - 20), max(0, t - 15), min(img.width, r + 20), min(img.height, b + 15))
                    crops.append((f'p{p} [{a}]', img.crop(box)))
                    hit = True
        if not hit:
            print('未命中:', a, file=sys.stderr)
    if not crops:
        return
    W = max(c.width for _, c in crops)
    H = sum(c.height + 36 for _, c in crops)
    sheet = Image.new('L', (W, H), 255)
    d = ImageDraw.Draw(sheet)
    y = 0
    for label, c in crops:
        d.text((4, y + 8), label, fill=0)
        y += 30
        sheet.paste(c, (0, y))
        y += c.height + 6
    sheet.save(out)
    print(out, len(crops), 'crops', sheet.size)


if __name__ == '__main__':
    main()
