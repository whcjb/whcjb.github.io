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
    """Return (new_body_lines, n_swaps_avoided).
    Stable sort verse paragraphs by verse number; other paragraphs stay anchored
    to their relative position in the "skeleton" (non-verse) sequence.
    """
    paras = parse_paragraphs(body_lines)
    # Separate into two streams: skeleton (non-verse paragraphs incl. blanks/html)
    # and verse paragraphs (with their verse number). We'll interleave them back:
    # for each skeleton slot we insert any pending verse paragraphs in sorted
    # order... actually simpler:
    # 1. Extract all verse paragraphs (with positions and verse nums)
    # 2. Sort them by verse num (stable)
    # 3. Re-emit: walk paras in original order, when we hit a verse para, take
    #    next from the sorted queue instead.
    verse_positions = []
    for i, (typ, plines) in enumerate(paras):
        if typ == 'para':
            v = get_verse_num(plines, book_cn, chapter)
            if v is not None:
                verse_positions.append((i, v))
    if len(verse_positions) < 2:
        return body_lines, 0
    # Count out-of-order before
    n_out = sum(1 for k in range(1, len(verse_positions))
                if verse_positions[k][1] < verse_positions[k - 1][1])
    if n_out == 0:
        return body_lines, 0
    # Build sorted list of verse paragraphs by verse num (stable)
    sorted_verse_paras = sorted(verse_positions, key=lambda x: x[1])
    verse_para_queue = [paras[idx] for idx, _ in sorted_verse_paras]
    verse_idx_set = {idx for idx, _ in verse_positions}
    # Reassemble: walk original paras; at each verse-para slot, pop next from queue
    new_paras = []
    q_iter = iter(verse_para_queue)
    for i, p in enumerate(paras):
        if i in verse_idx_set:
            new_paras.append(next(q_iter))
        else:
            new_paras.append(p)
    new_body = []
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
