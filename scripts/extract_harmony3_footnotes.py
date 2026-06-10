#!/usr/bin/env python3
"""Extract footnote definitions from calvin_matai_make3.pdf and append as
kramdown `[^N]: text` lines to calvin/harmony-3-en/{ch}.md files.

vol3 .md files use kramdown `[^N]` inline refs but lack the corresponding
`[^N]: ...` definitions — they were dropped at PDF extraction time
(footnote_size_max filter in extract_ccel_harmony).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import fitz

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
PDF = '/Users/yanpeifa/Documents/论文/calvin_matai_make3.pdf'
EN_DIR = ROOT / 'calvin/harmony-3-en'

FN_FONT_SIZE_MAX = 9.5
FN_Y_MIN_HARD = 200  # 任何脚注定义至少在页中部以下；防止把页眉小字误判


def _block_starts_with_small_digit(block) -> bool:
    """True 若 block 的第一非空 span 是小字（≤ FN_FONT_SIZE_MAX）且全为数字。"""
    for ln in block.get('lines', []):
        for sp in ln.get('spans', []):
            t = sp.get('text', '').strip()
            if not t:
                continue
            return (sp.get('size', 0) <= FN_FONT_SIZE_MAX
                    and t.isdigit())
    return False


def parse_page_footnotes(page: fitz.Page) -> list[tuple[int, str]]:
    """Per-page parser: find page-bottom footnote blocks, split by
    superscript-number markers (smaller font than body)。

    判定块为脚注：y ≥ FN_Y_MIN_HARD，且块首 span 是 ≤9.5pt 纯数字
    （脚注定义起首一定是 marker 数字）。后续小字 block 通过历史延续判断。
    """
    blocks = sorted(page.get_text('dict')['blocks'],
                     key=lambda b: b['bbox'][1])
    out: list[tuple[int, str]] = []
    # 先定位本页脚注区起点：第一个"小字 + 数字起首"的 block，认为是 fn 区始
    fn_zone_y = None
    for b in blocks:
        if b['type'] != 0 or b['bbox'][1] < FN_Y_MIN_HARD:
            continue
        if _block_starts_with_small_digit(b):
            fn_zone_y = b['bbox'][1]
            break
    if fn_zone_y is None:
        return []
    for b in blocks:
        if b['type'] != 0 or b['bbox'][1] < fn_zone_y:
            continue
        spans_data: list[tuple[float, str]] = []
        for line in b.get('lines', []):
            for span in line.get('spans', []):
                if not span.get('text', '').strip():
                    continue
                spans_data.append((span.get('size', 0), span['text']))
        if not spans_data:
            continue
        # 过滤掉 large-size 的杂项 span（页码、印刷标记等），保留脚注本体。
        # 旧版直接把 max(sizes) > FN_FONT_SIZE_MAX 的块整体丢弃——会
        # 在同 block 里夹着 size 11 的 "63" 页码时丢失 fn 92 等。
        spans_data = [(sz, t) for sz, t in spans_data if sz <= FN_FONT_SIZE_MAX]
        if not spans_data:
            continue
        sizes = [s for s, _ in spans_data]
        min_size = min(sizes)
        if min_size == max(sizes):
            out.extend(_split_by_text_pattern(' '.join(t for _, t in spans_data)))
            continue
        current_n: int | None = None
        current_text: list[str] = []
        for size, text in spans_data:
            if size == min_size and text.strip().isdigit():
                if current_n is not None:
                    out.append((current_n, ' '.join(current_text).strip()))
                current_n = int(text.strip())
                current_text = []
            else:
                current_text.append(text)
        if current_n is not None:
            out.append((current_n, ' '.join(current_text).strip()))
    cleaned: list[tuple[int, str]] = []
    for n, content in out:
        content = content.replace('\x00', '').strip()
        content = re.sub(r'\s+\d{1,4}\s*$', '', content).strip()
        if content:
            cleaned.append((n, content))
    return cleaned


def _split_by_text_pattern(text: str) -> list[tuple[int, str]]:
    parts: list[tuple[int, int]] = []
    for m in re.finditer(r'(?:^|\s)(\d{1,4})\s+(?=[“"\'\w])', text):
        parts.append((m.start(1), int(m.group(1))))
    out: list[tuple[int, str]] = []
    for i, (pos, n) in enumerate(parts):
        m = re.match(r'\d+\s+', text[pos:])
        cs = pos + (m.end() if m else 0)
        ce = parts[i + 1][0] if i + 1 < len(parts) else len(text)
        out.append((n, text[cs:ce].strip()))
    return out


def extract_all(pdf_path: str) -> list[tuple[int, str]]:
    doc = fitz.open(pdf_path)
    all_defs: dict[int, str] = {}
    for p in range(len(doc)):
        for n, content in parse_page_footnotes(doc[p]):
            if n in all_defs:
                all_defs[n] += ' ' + content
            else:
                all_defs[n] = content
    doc.close()
    return sorted(all_defs.items())


def build_chapter_ranges(en_chapter_files: dict[int, str]) -> dict[int, tuple[int, int]]:
    ranges: dict[int, tuple[int, int]] = {}
    for ch, text in en_chapter_files.items():
        nums = [int(m.group(1))
                for m in re.finditer(r'\[\^(\d+)\]', text)]
        # filter refs (not definitions)
        nums = sorted(set(nums))
        if nums:
            ranges[ch] = (min(nums), max(nums))
    return ranges


def chapter_for_fn(n: int, ranges: dict[int, tuple[int, int]]) -> int | None:
    candidates = [(ch, lo, hi) for ch, (lo, hi) in ranges.items() if lo <= n <= hi]
    if candidates:
        candidates.sort(key=lambda x: x[2] - x[1])  # tightest first
        return candidates[0][0]
    best_ch, best_dist = None, float('inf')
    for ch, (lo, hi) in ranges.items():
        dist = lo - n if n < lo else n - hi
        if dist < best_dist:
            best_dist = dist
            best_ch = ch
    return best_ch


def append_to_chapter(ch: int, defs: list[tuple[int, str]]) -> int:
    """Append `[^N]: text` kramdown defs at chapter end."""
    path = EN_DIR / f'{ch}.md'
    text = path.read_text(encoding='utf-8')
    # Strip any prior set of footnote defs we may have appended
    text = re.sub(
        r'\n+(?:\[\^\d+\]: [^\n]*\n)+\s*$',
        '\n',
        text,
    )
    if not defs:
        path.write_text(text, encoding='utf-8')
        return 0
    items = '\n'.join(
        f'[^{n}]: {content}'
        for n, content in sorted(defs)
    )
    text = text.rstrip() + '\n\n' + items + '\n'
    path.write_text(text, encoding='utf-8')
    return len(defs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    print(f'Extracting footnotes from {PDF}...')
    all_defs = extract_all(PDF)
    print(f'Found {len(all_defs)} footnote definitions')

    en_chapter_files: dict[int, str] = {}
    for path in sorted(EN_DIR.glob('*.md')):
        if path.stem.isdigit():
            en_chapter_files[int(path.stem)] = path.read_text(encoding='utf-8')

    ranges = build_chapter_ranges(en_chapter_files)
    print('Chapter ref ranges:')
    for ch, (lo, hi) in sorted(ranges.items()):
        print(f'  ch{ch}: {lo}–{hi}')

    by_chapter: dict[int, list[tuple[int, str]]] = {}
    for n, content in all_defs:
        ch = chapter_for_fn(n, ranges)
        if ch is not None:
            by_chapter.setdefault(ch, []).append((n, content))

    print('\nFootnotes assigned by chapter:')
    for ch in sorted(by_chapter):
        defs = by_chapter[ch]
        print(f'  ch{ch}: {len(defs)} fns (range {defs[0][0]}–{defs[-1][0]})')

    if args.dry_run:
        return

    for ch, defs in by_chapter.items():
        n = append_to_chapter(ch, defs)
        print(f'  appended {n} fns to ch{ch}.md')


if __name__ == '__main__':
    main()
