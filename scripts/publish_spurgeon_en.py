#!/usr/bin/env python3
"""司布真著作英文版发布：`spurgeon_raw/<book>/spurgeon_<book>.md` → `spurgeon/<book>/*.md`。

与贺智那条线（publish_hodge_en.py）最大的不同在**分章单位**：

贺智是「一章一个 CHAPTER <罗马数字> 标题」，分章即分文件。
司布真这本是讲道体，全书 102 个分节，标题形如 `CHAPTER 1:18-25` / `CHAPTER 2`，
一个马太福音章往往对应好几节（马太 26 章就有 9 节）。所以分文件的单位是
**马太福音的章**，从分节头里解析章号后把同章的节归到一个页面。

分节头在 structured_to_md 阶段已落成隐藏锚点：

    <h2 class="scripture-anchor" id="chapter-1-18-25" data-ref="CHAPTER 1:18-25" …>

判据就读 data-ref，不看样式——这本的分节头是 size16 蓝，与贺智的 size20 绿
不是一回事，按样式判会两头落空。

本书**没有脚注**（文末无 NOTES 区，9pt span 是小型大写的后半截），
所以不做贺智那套「脚注按引用归位」。

发布后必跑（顺序固定，本脚本每次重跑都会冲掉，重发要照跑）：

    1. python3 scripts/fix_page_split_paragraphs.py spurgeon/<book>   # Gate 5g，须归零
    2. python3 scripts/add_spurgeon_verse_anchors.py --book <book>    # 节锚点
    3. python3 scripts/build_spurgeon_verse_index.py --book <book>

用法:
    python3 scripts/publish_spurgeon_en.py matthew --name "Spurgeon on Matthew"
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 分节锚点：structured_to_md 为每个 `CHAPTER …` 分节头生成的隐藏 h2
_SEC_RE = re.compile(r'<h2 class="scripture-anchor"[^>]*data-ref="CHAPTER\s+([^"]+)"')


def chapter_of(ref: str):
    """'1:18-25' → 1；'2' → 2。取不到章号返回 None（调用方会报出来，不静默丢）。"""
    m = re.match(r'\s*(\d{1,3})', ref)
    return int(m.group(1)) if m else None


def split_by_chapter(md: str):
    """→ (preface_body, {章号: body})，章内保持原顺序拼接。"""
    lines = md.split('\n')
    marks = []
    for i, l in enumerate(lines):
        m = _SEC_RE.search(l)
        if m:
            ch = chapter_of(m.group(1))
            if ch is None:
                print(f'  ⚠ 第 {i} 行分节头解析不出章号: {m.group(1)!r}', file=sys.stderr)
                continue
            marks.append((i, ch, m.group(1)))
    if not marks:
        raise SystemExit('没找到任何分节锚点，判据要重看')

    preface = '\n'.join(lines[:marks[0][0]]).rstrip('\n')
    chapters = {}
    order = []
    for k, (i, ch, ref) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        seg = '\n'.join(lines[i:end]).rstrip('\n')
        if ch not in chapters:
            chapters[ch] = []
            order.append(ch)
        chapters[ch].append(seg)
    return preface, {c: '\n\n'.join(chapters[c]) for c in order}, marks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', help='spurgeon_raw/<book>/ 子目录名，如 matthew')
    ap.add_argument('--name', help='book_name')
    ap.add_argument('--book-cn', default='', help='中文书名，写进 index.html 注释')
    ap.add_argument('--src')
    ap.add_argument('--out-dir')
    ap.add_argument('--date')
    args = ap.parse_args()

    book = args.book
    src = Path(args.src) if args.src else ROOT / 'spurgeon_raw' / book / f'spurgeon_{book}.md'
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / 'spurgeon' / book
    book_name = args.name or f'Spurgeon on {book.capitalize()}'
    stamp = args.date or datetime.now().strftime('%Y-%m-%d %H:%M')

    preface, chapters, marks = split_by_chapter(src.read_text(encoding='utf-8'))
    chs = sorted(chapters)
    print(f'{book}: preface + {len(chs)} 章（{len(marks)} 个分节）')
    if chs != list(range(1, len(chs) + 1)):
        print(f'  ⚠ 章号不连续: {chs}', file=sys.stderr)
    per = {c: sum(1 for _, cc, _ in marks if cc == c) for c in chs}
    print('  每章分节数: ' + ' '.join(f'{c}:{per[c]}' for c in chs))

    keys = ['preface'] + [str(c) for c in chs]
    labels = {'preface': 'Introductory Note',
              **{str(c): f'Matthew {c}' for c in chs}}
    bodies = {'preface': preface, **{str(c): chapters[c] for c in chs}}

    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, key in enumerate(keys):
        fm = ['---', 'layout: spurgeon-chapter', f'book_id: {book}',
              f'book_name: "{book_name}"', f'title: "{labels[key]}"',
              f'zh_url: "/spurgeon/{book}/zh/{key}/"', f'date: {stamp}']
        if idx > 0:
            p = keys[idx - 1]
            fm += [f'prev_section: {p}', f'prev_label: "{labels[p]}"']
        if idx + 1 < len(keys):
            n = keys[idx + 1]
            fm += [f'next_section: {n}', f'next_label: "{labels[n]}"']
        fm.append('---')
        (out_dir / f'{key}.md').write_text(
            '\n'.join(fm) + '\n\n' + bodies[key].strip('\n') + '\n', encoding='utf-8')

    (out_dir / 'index.html').write_text(
        '---\n'
        'layout: spurgeon-book\n'
        f'book_id: {book}\n'
        f'book_name: "{book_name}"\n'
        f'chapters: {len(chs)}\n'
        'has_preface: true\n'
        '---\n', encoding='utf-8')
    print(f'  → {out_dir}/ 共 {len(keys)} 个页面 + index.html')


if __name__ == '__main__':
    sys.exit(main())
