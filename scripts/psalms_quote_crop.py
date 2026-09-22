#!/usr/bin/env python3
"""把「段内引号配对不上」的每一处，从 1864 影像上就近裁出来。

定位不靠引号本身（它正是争议所在），靠它**前面最近的几个正体实词**：
斜体在 PDF 文本层里字距与正体不同，`search_for` 常搜不到，所以专挑正体词。
裁前后各三四行——配对不上有「多一个」和「少一半」两种成因，少的那一半
在「那一处」上没有字可看，得看到上下文才知道另一半在哪。

原生 400 dpi，不上采样。

用法：python3 scripts/psalms_quote_crop.py <输出目录>
"""
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
META = ROOT / 'logs/alexander_psalms_quote_para.json'
PAGE_RE = re.compile(r'<!-- PAGE (\d+) -->')
TAG = re.compile(r'<[^<>]+>')
OFFSET = 3
ROMAN_RUN = re.compile(r"(?<![*\w])[A-Za-z][A-Za-z'-]{2,}(?![*\w])")


def anchors(plain, pos):
    """引号前面的正体词，从近到远拼成几个候选短语。"""
    left = plain[max(0, pos - 160):pos]
    ws = ROMAN_RUN.findall(left)
    out = []
    for n in (5, 4, 3):
        if len(ws) >= n:
            out.append(' '.join(ws[-n:]))
    right = ROMAN_RUN.findall(plain[pos:pos + 160])
    if len(right) >= 4:
        out.append(' '.join(right[:4]))
    return out


def main(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(PDF)
    items = json.loads(META.read_text(encoding='utf-8'))
    want = {(it['sec'], it['page']) for it in items}
    n = miss = 0
    for p in sorted(SRC.glob('*.md')):
        t = p.read_text(encoding='utf-8')
        marks = [(m.start(), int(m.group(1))) for m in PAGE_RE.finditer(t)]
        for para in t.split('\n\n'):
            plain = TAG.sub('', para)
            if plain.count('"') % 2 == 0:
                continue
            off = t.find(para)
            pg = next((v for o, v in reversed(marks) if o <= off), None)
            if (p.stem, pg) not in want:
                continue
            for m in re.finditer(r'"', plain):
                cands = anchors(plain, m.start())
                hit = None
                for d in (0, 1, -1):
                    idx = pg + OFFSET + d
                    if not (0 <= idx < doc.page_count):
                        continue
                    pageobj = doc[idx]
                    for ph in cands:
                        r = pageobj.search_for(ph)
                        if r:
                            hit = (pageobj, r[0])
                            break
                    if hit:
                        break
                if not hit:
                    miss += 1
                    continue
                pageobj, r = hit
                clip = fitz.Rect(0, max(0, r.y0 - 44), pageobj.rect.x1,
                                 min(pageobj.rect.y1, r.y1 + 52))
                tag = re.sub(r'\W+', '', plain[max(0, m.start() - 12):m.start()])[-10:]
                pageobj.get_pixmap(dpi=400, clip=clip).save(
                    out / f'{p.stem}_{pg}_{tag}.png')
                n += 1
    print(f'裁了 {n} 处，定位失败 {miss} 处 → {out}')


if __name__ == '__main__':
    main(sys.argv[1])
