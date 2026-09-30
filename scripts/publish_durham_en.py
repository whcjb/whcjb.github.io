#!/usr/bin/env python3
"""达拉谟《启示录注释》英文版发布：`durham_raw/revelation/durham_revelation.md` → `durham/revelation/*.md`。

分章单位就是启示录的 22 章，提取阶段已把 `# CHAP. N` 落成 H1，直接按它切。
章内保留 `## LECTURE N (a:b–c)` 讲次头与 `### …` 离题论述头。

与贺智/司布真那两条线的不同
---------------------------
· **没有脚注**。这份转写不带脚注，所以不做「脚注按引用归位」那一步。
· **讲次头自带经文范围**（`LECTURE V (11:15–19)`），节锚点直接从范围里展开，
  不必像那两本一样去正文里认 `V. 1.` / `**18.**` 这类节号头。
· 作者序（原书 To the Judicious and Christian Reader）落 preface.md。

发布后必跑（顺序固定，本脚本每次重跑都会冲掉）：
    1. python3 scripts/fix_page_split_paragraphs.py durham/revelation   # Gate 5g，须归零
    2. python3 scripts/add_durham_verse_anchors.py                      # 按讲次范围铺锚点
    3. python3 scripts/build_hodge_verse_index.py --book revelation     # 经文索引

用法:
    python3 scripts/publish_durham_en.py --name "Durham on Revelation"
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_CHAP_RE = re.compile(r'^# CHAP\.\s*(\d{1,2})\s*$', re.M)


def split_chapters(md: str):
    marks = [(m.start(), int(m.group(1))) for m in _CHAP_RE.finditer(md)]
    if not marks:
        raise SystemExit('没找到 `# CHAP. N` 章头，分章判据要重看')
    preface = md[:marks[0][0]].strip('\n')
    chapters = {}
    for k, (pos, ch) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(md)
        chapters[ch] = md[pos:end].strip('\n')
    return preface, chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='revelation')
    ap.add_argument('--name', default='Durham on Revelation')
    ap.add_argument('--src')
    ap.add_argument('--out-dir')
    ap.add_argument('--date')
    a = ap.parse_args()

    src = Path(a.src) if a.src else ROOT / 'durham_raw' / a.book / f'durham_{a.book}.md'
    out_dir = Path(a.out_dir) if a.out_dir else ROOT / 'durham' / a.book
    stamp = a.date or datetime.now().strftime('%Y-%m-%d %H:%M')

    preface, chapters = split_chapters(src.read_text(encoding='utf-8'))
    chs = sorted(chapters)
    n_lect = sum(len(re.findall(r'^## LECTURE', chapters[c], re.M)) for c in chs)
    print(f'{a.book}: preface + {len(chs)} 章 / {n_lect} 讲')
    if chs != list(range(1, len(chs) + 1)):
        print(f'  ⚠ 章号不连续: {chs}', file=sys.stderr)

    keys = ['preface'] + [str(c) for c in chs]
    labels = {'preface': "To the Reader", **{str(c): f'Revelation {c}' for c in chs}}
    bodies = {'preface': preface, **{str(c): chapters[c] for c in chs}}

    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, key in enumerate(keys):
        fm = ['---', 'layout: durham-chapter', f'book_id: {a.book}',
              f'book_name: "{a.name}"', f'title: "{labels[key]}"',
              f'zh_url: "/durham/{a.book}/zh/{key}/"', f'date: {stamp}']
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
        'layout: durham-book\n'
        f'book_id: {a.book}\n'
        f'book_name: "{a.name}"\n'
        f'chapters: {len(chs)}\n'
        'has_preface: true\n'
        '---\n', encoding='utf-8')
    print(f'  → {out_dir}/ 共 {len(keys)} 个页面 + index.html')


if __name__ == '__main__':
    sys.exit(main())
