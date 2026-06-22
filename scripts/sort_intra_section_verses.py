#!/usr/bin/env python3
"""按 verse 号对同一 section 内部的 `**书名 ch:V。**` 注释段做稳定排序。

OCR publish 经常出现：section `4:8-14` 内部 verse 注释出现 `4:14 → 4:9 → 4:9 → 4:13 → 4:14`
这种倒乱顺序。本脚本只在 section 内部排序，不移动跨 section 段落（那个由
relocate_misplaced_verse_commentary.py 处理）。

排序规则：
- 同一 verse 号的段落保序（稳定排序），允许同节多段注释
- 非 `**书名 ch:V。**` 开头的段落保持位置（不动 HTML、scripture-box、footnote 等）

用法：
    python3 scripts/sort_intra_section_verses.py --book-cn 约翰福音 --dir calvin/john
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path


def parse_paragraphs(body_lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split body_lines into paragraphs by blank lines.
    Return [(type, lines), ...] where type ∈ {'verse', 'other'}.
    A 'verse' paragraph starts with `**书名 ch:V。**`.
    """
    paras: list[tuple[str, list[str]]] = []
    cur: list[str] = []

    def flush():
        if cur:
            # Skip leading/trailing blanks
            first_nonblank = next((i for i, l in enumerate(cur) if l.strip()), None)
            if first_nonblank is None:
                paras.append(('blank', cur[:]))
            else:
                paras.append(('para', cur[:]))
            cur.clear()

    for ln in body_lines:
        if not ln.strip():
            flush()
            cur.append(ln)
            flush()
        else:
            cur.append(ln)
    flush()
    return paras


def get_verse_num(para_lines: list[str], book_cn: str, chapter: int) -> int | None:
    if not para_lines:
        return None
    first = para_lines[0]
    m = re.match(rf'^\*\*{re.escape(book_cn)} {chapter}:(\d+)。\*\*', first)
    if m:
        return int(m.group(1))
    return None


def sort_section(body_lines: list[str], book_cn: str, chapter: int) -> tuple[list[str], int]:
    """Return (new_body_lines, n_out).

    安全粒度：把"verse marker 段 + 它后面所有非 marker 续段（含空行/小标题/续注释）
    直到下一个 marker 段或 section 末"打包成一个 commentary block。然后按
    block leading verse 号稳定排序。这样续段会跟着 marker 一起移动，不会
    被遗弃在原 section。

    block 前的 prefix（没有任何 marker 前的内容，如 scripture-box / 段总论）
    保持原位不参与排序。
    """
    paras = parse_paragraphs(body_lines)

    # 找第一个 verse-marker 段的位置
    first_marker_idx = None
    for i, (typ, plines) in enumerate(paras):
        if typ == 'para' and get_verse_num(plines, book_cn, chapter) is not None:
            first_marker_idx = i
            break
    if first_marker_idx is None:
        return body_lines, 0

    prefix_paras = paras[:first_marker_idx]
    rest = paras[first_marker_idx:]

    # 把 rest 按 marker 切成 blocks: 每个 block = [marker_para, follow_paras...]
    blocks: list[tuple[int, list[tuple[str, list[str]]]]] = []
    cur_block: list[tuple[str, list[str]]] = []
    cur_v: int | None = None
    for p in rest:
        typ, plines = p
        v = get_verse_num(plines, book_cn, chapter) if typ == 'para' else None
        if v is not None:
            if cur_block:
                blocks.append((cur_v, cur_block))
            cur_block = [p]
            cur_v = v
        else:
            cur_block.append(p)
    if cur_block:
        blocks.append((cur_v, cur_block))

    if len(blocks) < 2:
        return body_lines, 0

    # 计算 out-of-order block 数量
    n_out = sum(1 for k in range(1, len(blocks)) if blocks[k][0] < blocks[k - 1][0])
    if n_out == 0:
        return body_lines, 0

    # 稳定排序 (Python sort 稳定)
    sorted_blocks = sorted(blocks, key=lambda b: b[0])

    new_paras = list(prefix_paras)
    for _, bparas in sorted_blocks:
        new_paras.extend(bparas)

    new_body: list[str] = []
    for typ, plines in new_paras:
        new_body.extend(plines)
    return new_body, n_out


def process_chapter(path: Path, book_cn: str) -> int:
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    # Parse sections
    hdr_re = re.compile(rf'^## {re.escape(book_cn)} (\d+):(\d+)(?:-(\d+))?')
    section_starts = [i for i, ln in enumerate(lines) if hdr_re.match(ln)]
    if not section_starts:
        return 0
    section_ranges = []
    for k, start in enumerate(section_starts):
        end = section_starts[k + 1] if k + 1 < len(section_starts) else len(lines)
        section_ranges.append((start, end))

    new_lines = lines[:section_starts[0]]  # pre-section prefix
    total_swapped = 0
    for start, end in section_ranges:
        header = lines[start]
        m = hdr_re.match(header)
        chapter = int(m.group(1))
        body = lines[start + 1:end]
        sorted_body, n_out = sort_section(body, book_cn, chapter)
        total_swapped += n_out
        new_lines.append(header)
        new_lines.extend(sorted_body)
    new_text = '\n'.join(new_lines)
    new_text = re.sub(r'\n{3,}', '\n\n', new_text)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
    return total_swapped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--dir', required=True)
    args = ap.parse_args()
    dir_path = Path(args.dir).resolve()
    total = 0
    for path in sorted(dir_path.glob('*.md')):
        if not path.stem.isdigit():
            continue
        n = process_chapter(path, args.book_cn)
        if n:
            print(f'  {path.name}: sorted {n} out-of-order verse paragraphs')
            total += n
    print(f'\nTotal sorted: {total}')


if __name__ == '__main__':
    main()
