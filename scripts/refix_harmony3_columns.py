#!/usr/bin/env python3
"""Re-distribute harmony3 raw scripture blocks by verse-prefix.

Problem
-------
calvin_extract.py 提取 harmony3 章首多列经文时，PDF 同一物理行偶尔横跨 2-3 列，
若行宽 < cross_thresh (200px) 不触发 span-level 拆分，整行被按起始 x0 归入一列。
结果：col=0 段里夹有 col=1/2 的字（特别是 verse 编号也跟着串入）。

Strategy
--------
对每个 `## ... ; ... ; ...` section（含 ≥2 个 book 的多列 scripture）：
  1. 解析 header 拿到每个 book column 的 (book, chapter, verse_set)
  2. 把后续所有 <!--SCRIPTURE col=N--> 段合并成一个大字符串（保留 verse markers）
  3. 按 `**N.**` 切成 chunk；每个 chunk = (verse_num, text_until_next_verse_or_end)
  4. 每个 verse 归入"verse N 落在哪个 book 的 verse 范围"对应的列
  5. 同列按 verse 数字升序拼接，重写为 N 个 <!--SCRIPTURE col=N--> 段
  6. 保留章节脚注引用 [^N] 和粗体；保留非 verse-起头的前缀文字（罕见，
     归入 col=0 段首）

Limitation
----------
"行内列泄漏"无 verse 编号的短文字（如孤立的"and the children crying"）若不带
verse 起头会被并入它前面的 verse 文本。可能仍归错列，但少量；明显的整 verse
归错列问题（90%+ 的肉眼可见错误）被修复。

不动 raw 之外的 section（commentary 段、单列 section、index 等）。

⚠️ 配套步骤（必跑）：
  本脚本 + publish.py 完成后，必须重跑 extract_harmony3_footnotes.py
  才能恢复每章末尾 `[^N]: text` 脚注定义——这些定义不在 raw 里，是
  publish 之后单独提取追加的。完整流程：

    python3 scripts/refix_harmony3_columns.py --in-place
    python3 calvin_raw/harmony3/publish.py
    python3 scripts/extract_harmony3_footnotes.py
"""
from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
RAW_FILE = ROOT / 'calvin_raw/harmony3/harmony3_raw.txt'

GOSPEL_TOKENS = {'MATTHEW', 'MARK', 'LUKE', 'JOHN'}
HEADER_RE = re.compile(
    r'^## ((?:MATTHEW|MARK|LUKE|JOHN)\b[A-Z\s\d:,;\-–]+)$',
    re.M,
)
COL_MARKER_RE = re.compile(r'^<!--SCRIPTURE col=(\d+) of=(\d+)-->\s*\n?(.*)$', re.DOTALL)
VERSE_PREFIX_RE = re.compile(r'\*\*(\d+)\.\*\*')


class ColSpec(NamedTuple):
    book: str        # 'MATTHEW'
    chapter: int
    verses: set[int]


def parse_header_cols(header_line: str) -> list[ColSpec]:
    s = re.sub(r'^##\s*', '', header_line).strip()
    # 防御：PDF 提取偶尔丢失 BOOK 之间的 `;`（如 "MARK 12:40 LUKE 11:52;
    # 20:47"），在两个连续 BOOK 关键词之间补入分隔符。
    s = re.sub(r'(\d)(\s+)(MATTHEW|MARK|LUKE|JOHN)\b', r'\1; \3', s, flags=re.I)
    parts = re.split(r'\s*;\s*', s)
    cols: list[ColSpec] = []
    last_book: str | None = None
    last_chapter: int | None = None
    for part in parts:
        part = part.strip()
        m = re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\s+(\d+):(.+)$', part, re.I)
        if m:
            last_book = m.group(1).upper()
            last_chapter = int(m.group(2))
            verses = _expand_verses(m.group(3))
            cols.append(ColSpec(last_book, last_chapter, verses))
        else:
            # 续接 same-gospel ref，如 "MARK 9:49-50; 4:21" 中的 "4:21"
            # 或 "LUKE 11:52; 20:47" 中的 "20:47"（跨章续接同卷）
            m2 = re.match(r'^(\d+):(.+)$', part)
            if m2 and last_book is not None:
                verses = _expand_verses(m2.group(2))
                # 同书跨章/同章续接：把 verse 全部并入同一列 verse_set
                # （列只按"卷书"区分，不按章；redistribute 只用 verse 编号）
                cols[-1] = ColSpec(cols[-1].book, cols[-1].chapter,
                                   cols[-1].verses | verses)
            elif m2 and last_book is None:
                continue
    return cols


def _expand_verses(spec: str) -> set[int]:
    out: set[int] = set()
    for chunk in re.split(r'\s*,\s*', spec):
        chunk = chunk.strip()
        m = re.match(r'(\d+)\s*[-–]\s*(\d+)$', chunk)
        if m:
            out.update(range(int(m.group(1)), int(m.group(2)) + 1))
        elif chunk.isdigit():
            out.add(int(chunk))
    return out


def find_col(verse: int, cols: list[ColSpec]) -> int:
    """Return column index (0-based) whose verse_set contains `verse`. -1 if none."""
    for i, c in enumerate(cols):
        if verse in c.verses:
            return i
    return -1


def split_into_blocks(raw: str) -> list[str]:
    """Split raw text into ¶-separated blocks (preserves trailing newlines)."""
    return raw.split('\n\n')


def is_col_block(blk: str) -> tuple[int, int, str] | None:
    """If blk is `<!--SCRIPTURE col=N of=M-->...`, return (col, n_cols, body)."""
    m = COL_MARKER_RE.match(blk.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), m.group(3).strip()


def is_section_header(blk: str) -> bool:
    s = blk.strip()
    if not s.startswith('## '):
        return False
    return any(tok in s.upper() for tok in GOSPEL_TOKENS)


def find_section_groups(blocks: list[str]) -> list[tuple[int, list[int]]]:
    """Walk blocks; for each section header that's followed by ≥2 col blocks,
    return (header_idx, [col_block_idxs])."""
    groups: list[tuple[int, list[int]]] = []
    i = 0
    while i < len(blocks):
        if is_section_header(blocks[i]):
            j = i + 1
            col_idxs: list[int] = []
            while j < len(blocks):
                if is_col_block(blocks[j]) is not None:
                    col_idxs.append(j)
                    j += 1
                elif blocks[j].strip() == '':
                    j += 1
                else:
                    break
            if col_idxs:
                groups.append((i, col_idxs))
            i = j
        else:
            i += 1
    return groups


def merge_col_blocks(blocks: list[str], col_idxs: list[int]) -> tuple[list[list[str]], int]:
    """Group col-blocks by their declared col=N. Returns (per_col_texts, n_cols).

    Preserves insertion order of texts within each column (PDF reading order).
    """
    n_cols = 0
    per_col: dict[int, list[str]] = {}
    for idx in col_idxs:
        info = is_col_block(blocks[idx])
        if info is None:
            continue
        col, nc, body = info
        n_cols = max(n_cols, nc)
        per_col.setdefault(col, []).append(body)
    result = [per_col.get(c, []) for c in range(n_cols)]
    return result, n_cols


def slice_by_verse(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Split `text` into (lead_text_without_verse, [(verse_num, chunk_text), ...]).

    chunk_text starts with `**N.**` and ends just before next `**M.**` or text end.
    lead_text = anything before first `**N.**`.
    """
    matches = list(VERSE_PREFIX_RE.finditer(text))
    if not matches:
        return text.strip(), []
    lead = text[:matches[0].start()].strip()
    chunks: list[tuple[int, str]] = []
    for k, m in enumerate(matches):
        verse = int(m.group(1))
        start = m.start()
        end = matches[k + 1].start() if k + 1 < len(matches) else len(text)
        chunks.append((verse, text[start:end].strip()))
    return lead, chunks


def redistribute_section(header_line: str,
                          per_col_texts: list[list[str]],
                          raw_n_cols: int) -> list[str]:
    """Given the header + raw per-col text fragments, redistribute by verse.

    Returns the new ordered list of col=N segment bodies (excluding markers,
    which the caller re-attaches). Length = max(header_n_cols, raw_n_cols)。
    若 header 列数 > raw 列数（PDF 提取因 header 缺 `;` 误并列），
    以 header 为准并按 verse 重切——把原 raw 单 col 里夹杂的多卷经文
    分发到正确的列。
    """
    cols = parse_header_cols(header_line)
    n_cols = max(len(cols), raw_n_cols)
    if len(cols) < 2:
        # 只有 1 个 book — 仍按 raw 原样保留
        return [' '.join(parts).strip() for parts in per_col_texts]

    # 把所有 col 段（按 col index 顺序）拼成一个超大文本（保留 verse markers）
    # 然后按 verse 切片重分配。注意：实际 PDF 阅读顺序是 col0_seg1, col1_seg1,
    # col2_seg1, col0_seg2, ... 而 per_col_texts 把 col=N 段已分组归一。所以
    # 拼接顺序应是按 col=0 顺序，再 col=1, 再 col=2——这恰好是 verse 升序
    # （col=0 通常 Matt 在前 verse 在低号）。
    # 简化：拼接每列内部分段，再切 verses，按 verse 重归列。
    merged_chunks_per_input_col: list[list[tuple[int, str]]] = []
    leads: list[str] = []
    for parts in per_col_texts:
        merged = ' '.join(parts).strip()
        lead, chunks = slice_by_verse(merged)
        leads.append(lead)
        merged_chunks_per_input_col.append(chunks)

    # 全部 verse chunks 汇总（保留出处仅供调试/孤立漏入处理）
    all_verses: list[tuple[int, str, int]] = []  # (verse, chunk_text, src_col)
    for src_col, chunks in enumerate(merged_chunks_per_input_col):
        for verse, txt in chunks:
            all_verses.append((verse, txt, src_col))

    # 把每个 verse 归入正确列
    # **核心策略**：优先保留源列（src_col）的归属。仅当 verse 不在
    # 源列的 verse_set 内时，才寻找正确列。这样处理 Matt 21 和 Mark 11
    # 等"verse 编号区间重叠"场景——这些 verse 在多个 col 范围内有效，
    # 不能盲目按"找到第一个匹配的 col"重归。原始提取的 col=N 标记在
    # verse 级粒度上一般正确（错误多发生在子-verse 行内列泄漏，这部分
    # 不在本脚本修复范围）。
    per_col_redistributed: list[list[tuple[int, str]]] = [[] for _ in range(n_cols)]
    unassigned: list[tuple[int, str, int]] = []
    for verse, txt, src_col in all_verses:
        if src_col < n_cols and verse in cols[src_col].verses:
            # verse 在源列 verse 范围内 → 保留在源列（即使其他列范围也包含）
            per_col_redistributed[src_col].append((verse, txt))
            continue
        # verse 不在源列 verse 范围 → 视为提取阶段错位，寻找应在的列
        target = find_col(verse, cols)
        if target < 0:
            unassigned.append((verse, txt, src_col))
            continue
        per_col_redistributed[target].append((verse, txt))

    # 按 verse 升序拼接每列
    out_segments: list[str] = []
    for col_idx in range(n_cols):
        items = per_col_redistributed[col_idx]  # 不排序：保持 source 顺序
        # 去重：仅当**完全相同的 chunk text** 重复时才去（如多页续接切成
        # 同样的两段）。不可按 verse 号去重——同一列可能含同卷不同章的
        # 重叠 verse 号（如 Luke 17:26-37 + 21:34-36，都有 v.34/35/36），
        # 用 len(t) > 之类的判定会丢失其中一组的内容。
        # 同时丢弃"严重逆序"的尾巴：若 verse N 出现在前面已出现的更高
        # verse 之后（≥ 5 差距），且本身是短碎片（< 150 字符），视为 PDF
        # 列尾版式溢出（Calvin PDF 偶尔把某 verse 残留塞到 cell 末），丢弃。
        seen_texts: set[str] = set()
        max_v_seen = -1
        ordered: list[str] = []
        for v, t in items:
            key = re.sub(r'\s+', ' ', t).strip()[:80]
            if key in seen_texts:
                continue
            # 逆序短碎片丢弃：v < max_v_seen 且文本短（< 150 字符）
            # 视为 PDF 列尾版式溢出。同卷跨章续接（如 Luke 21:34 接 17:37）
            # 通常 > 150 字符，不会误删。
            if max_v_seen >= 0 and v < max_v_seen and len(t) < 150:
                continue
            seen_texts.add(key)
            max_v_seen = max(max_v_seen, v)
            ordered.append(t)
        # 把 lead（出现在 col=col_idx 输入段最前的非 verse 文字）放在最前
        lead = leads[col_idx] if col_idx < len(leads) else ''
        body = (lead + ' ' if lead else '') + ' '.join(ordered)
        # 清理：剥掉混入末尾/中间的孤立 "Book X:Y" / "Book X:Y-Z" 子标题
        # （PDF 蓝色小标题如 "Luke 20:47" / "Luke 21:34-36" 混入正文流，
        # header 已显示卷书范围、不需重复；遗漏 verse 范围将留下 "-N" 残尾）
        body = re.sub(
            r'\s*(?:Matthew|Mark|Luke|John)\s+\d+:\d+(?:[-–]\d+)?\s*',
            ' ', body, flags=re.I,
        )
        out_segments.append(re.sub(r'\s+', ' ', body).strip())

    # unassigned verses: 罕见的 verse 编号不在任何 cols verses 内（跨章续接、
    # PDF 错读 verse 号）。简单方案：附在 src_col 末尾（保留信息不丢）。
    for verse, txt, src_col in unassigned:
        if src_col < n_cols:
            sep = ' ' if out_segments[src_col] else ''
            out_segments[src_col] += sep + txt

    return out_segments


def rebuild_raw(raw: str) -> tuple[str, int, int]:
    """Return (new_raw, sections_rewritten, sections_skipped)."""
    blocks = split_into_blocks(raw)
    groups = find_section_groups(blocks)
    rewritten = 0
    skipped = 0

    # Build set of indices to replace, and new content map
    replace: dict[int, str | None] = {}  # idx -> new content (None = drop)

    for hdr_idx, col_idxs in groups:
        header_line = blocks[hdr_idx].strip()
        # Only rewrite if header has ≥2 books
        cols = parse_header_cols(header_line)
        if len(cols) < 2:
            skipped += 1
            continue

        per_col_texts, raw_n_cols = merge_col_blocks(blocks, col_idxs)
        if raw_n_cols < 2:
            skipped += 1
            continue

        new_segments = redistribute_section(header_line, per_col_texts, raw_n_cols)
        # 实际输出列数 = header 列数 与 raw 列数 的较大者（header 缺 `;`
        # 被 PDF 误判时优先以 header 为准 → 升列）
        actual_n_cols = len(new_segments)

        # First col_idx becomes the new merged block (multiple col=N markers joined by \n\n)
        new_block_text = '\n\n'.join(
            f'<!--SCRIPTURE col={i} of={actual_n_cols}-->\n{seg}'
            for i, seg in enumerate(new_segments)
            if seg.strip()
        )
        replace[col_idxs[0]] = new_block_text
        for ci in col_idxs[1:]:
            replace[ci] = None  # drop subsequent col blocks (folded into first)

        rewritten += 1

    # Reassemble
    new_blocks: list[str] = []
    for i, blk in enumerate(blocks):
        if i in replace:
            new = replace[i]
            if new is not None:
                new_blocks.append(new)
        else:
            new_blocks.append(blk)
    return '\n\n'.join(new_blocks), rewritten, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--in-place', action='store_true',
                    help='Write back to harmony3_raw.txt (default: print to stdout)')
    args = ap.parse_args()

    raw = RAW_FILE.read_text(encoding='utf-8')
    new_raw, n_rewritten, n_skipped = rebuild_raw(raw)

    print(f'Rewrote {n_rewritten} multi-col sections, skipped {n_skipped}',
          flush=True)

    if args.dry_run:
        return

    if args.in_place:
        backup = RAW_FILE.with_suffix(
            f'.refix.bak.{datetime.now():%Y%m%d_%H%M%S}.txt')
        shutil.copy2(RAW_FILE, backup)
        print(f'Backed up to {backup.name}', flush=True)
        RAW_FILE.write_text(new_raw, encoding='utf-8')
        print(f'Wrote {RAW_FILE.name}', flush=True)
    else:
        print('--- (use --in-place to write back) ---')
        print(new_raw[:2000])


if __name__ == '__main__':
    main()
