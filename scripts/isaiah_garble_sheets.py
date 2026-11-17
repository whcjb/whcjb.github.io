#!/usr/bin/env python3
"""把 isaiah_garble_verify 判为 HEB / GRC / unclear 的条目拼成看图用的长条图。

每条一行：左边编号 + 正文里的可疑串，右边是原书那一行（候选词连同前后词）的裁图。
一张图放 N 条，看图时对着编号记读法，免得一条一张图地翻（[[feedback_no_bulk_image_reading]]）。

用法：python3 scripts/isaiah_garble_sheets.py $S/verify [每张条数=24]
输出：$S/verify/sheets/sheet_000.png …，与 $S/verify/sheets/index.tsv（编号 → 章、页、串、上下文）
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out = Path(sys.argv[1])
per = int(sys.argv[2]) if len(sys.argv) > 2 else 24
rows = [l.rstrip('\n').split('\t') for l in open(out / 'verified.tsv', encoding='utf-8')][1:]
rows = [r for r in rows if r[0] in ('HEB', 'GRC', 'unclear')]
(out / 'sheets').mkdir(exist_ok=True)
try:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 22)
except OSError:
    font = ImageFont.load_default()
W, LABEL, ROWH = 1500, 420, 70
with open(out / 'sheets' / 'index.tsv', 'w', encoding='utf-8') as idx:
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        sheet = Image.new('RGB', (W, ROWH * len(chunk)), 'white')
        d = ImageDraw.Draw(sheet)
        for k, r in enumerate(chunk):
            no = s + k
            verdict, ch, page, tok = r[0], r[1], r[2], r[3]
            y = k * ROWH
            d.text((6, y + 8), f'{no} {verdict[0]} {ch}:{page}', fill='black', font=font)
            d.text((6, y + 36), tok[:28], fill='red', font=font)
            try:
                im = Image.open(r[9])
                sc = min((W - LABEL) / im.width, (ROWH - 4) / im.height)
                im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
                sheet.paste(im, (LABEL, y + 2))
            except (OSError, IndexError):
                pass
            d.line([(0, y + ROWH - 1), (W, y + ROWH - 1)], fill='#ccc')
            idx.write('\t'.join([str(no)] + r[:5] + [r[10] if len(r) > 10 else '']) + '\n')
        sheet.save(out / 'sheets' / f'sheet_{s // per:03d}.png')
print(f'{len(rows)} 条 → {(len(rows) + per - 1) // per} 张')
