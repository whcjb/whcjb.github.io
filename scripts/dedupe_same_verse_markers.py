#!/usr/bin/env python3
"""同一 verse 连续多段评注时，把第二段起的 verse-ref 前缀去掉，只留 phrase。

PDF 原文里 Calvin 评注 1 节经文若分多个 phrase 写多段，**第一段**带圈号
(⑨ 你既是犹太人。) 引出 verse-num，**后续段**只以 phrase 开头（不重标
节号）。但 OCR + restructure 把每段都加了 `**书名 N:V。** *phrase。*`
前缀，渲染出来 visual 上重复 "约翰福音 4:9。" 看起来怪。

本脚本扫描每章，把连续相同 verse-num 的段落（≥2 段）从第二段起把
`**书名 N:V。** *phrase。*` 简化为 `*phrase。*`。

用法：
    python3 scripts/dedupe_same_verse_markers.py --book-cn 约翰福音 --dir calvin/john
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path


def process(path: Path, book_cn: str) -> int:
    """Return number of lines where verse-ref was stripped."""
    text = path.read_text(encoding='utf-8')
    if not path.stem.isdigit():
        return 0
    ch = int(path.stem)

    # Pattern: `**书名 ch:V。** *phrase* tail`
    marker_re = re.compile(
        rf'^\*\*{re.escape(book_cn)} {ch}:(\d+)。\*\* (.*)$'
    )
    lines = text.split('\n')
    n_stripped = 0
    last_v: int | None = None
    for i, ln in enumerate(lines):
        m = marker_re.match(ln)
        if not m:
            # blank or non-verse-marker line, reset only if line is non-empty
            # (a blank line within a paragraph group keeps state)
            if ln.strip() and not ln.startswith('<') and not ln.startswith('['):
                # commentary text line — keep last_v so same-verse continuation detected
                pass
            continue
        v = int(m.group(1))
        if last_v == v:
            # Strip `**书名 ch:V。** ` prefix; keep the rest verbatim
            new_line = m.group(2)
            lines[i] = new_line
            n_stripped += 1
        last_v = v

    if n_stripped:
        path.write_text('\n'.join(lines), encoding='utf-8')
    return n_stripped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--dir', required=True)
    args = ap.parse_args()
    total = 0
    for p in sorted(Path(args.dir).glob('*.md')):
        n = process(p, args.book_cn)
        if n:
            print(f'  {p.name}: stripped {n} duplicate verse-refs')
            total += n
    print(f'\nTotal stripped: {total}')


if __name__ == '__main__':
    main()
