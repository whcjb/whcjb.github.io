#!/usr/bin/env python3
"""福特《路加福音讲义》句中被页码标记切成两段的接回（2026-11-12 用户指出第 1 讲 `the antidote of` / `superstition`）。

发布时每个 `<!-- PAGE -->` 起一个段落。原先卷进正文的页脚注常夹在翻页处：`…antidote of` ／ PAGE 11 ／ 注文 + `superstition…`。
注文删出后（foote_notes_leak2、foote_hand_pending）前后两半没接回，句子中间断成两段。全书 24 处，少数是原本就有的同型。

判据：上一块末尾无句末/引号/破折号等收束标点，下一块以小写字母起头 → 同一句被页码标记切开，去掉其间的段落分隔与标记、
以一个空格接回（上一块以连字符结尾的不加空格）。该页标记丢了不影响页码：同页后面还有标记的照旧，没有的接到上一页。

    python3 scripts/foote_seam_join.py --rules    # 链条末段（foote_hand_pending --apply 之后）→ seam_join_fixes.tsv
    python3 scripts/foote_seam_join.py --apply
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402

RULES = A.RAW / 'seam_join_fixes.tsv'
SEAM = re.compile(r'([^\n]{0,60})\n\n((?:<!-- PAGE \S* -->\n)+)([a-z][^\n]{0,40})')


def rules():
    out = []
    for f in sorted(A.SRC.glob('*.md')):
        lec = f.stem
        t = f.read_text(encoding='utf-8')
        body = t.partition('\n---\n')[0]
        for m in SEAM.finditer(body):
            a, b = m.group(1), m.group(3)
            if not a or re.search(r'[.!?:;"\'*)—\]]\s*$', a) or a.lstrip().startswith(('#', '>', '**')):
                continue
            o = m.group(0)
            m2 = re.search(r'([A-Za-z]+)-$', a)
            w2 = re.match(r'[a-z]+', b)
            if m2 and w2 and A._isword((m2.group(1) + w2.group()).lower()):
                n = a[:-1] + b                          # 行末断词：`wor-` ／ `shipping` → worshipping
            else:
                n = a + ('' if a.endswith('-') else ' ') + b
            if t.count(o) != 1:
                raise SystemExit(f'{lec}: 不唯一 {o!r}')
            out.append((lec, o, n))
        # 序数被空格拆开：`the 8 th chapter` → 8th（全书 21 处，后接 chapter/verse/Psalm/book 等）
        for m in re.finditer(r'\b(\d+) th (chapter|chapters|verse|verses|Psalm|book|year|day|and)\b', body):
            o = m.group(0)
            if t.count(o) == 1:
                out.append((lec, o, f'{m.group(1)}th {m.group(2)}'))
            else:
                k = t.find(o)
                o2 = t[max(0, k - 20):k + len(o)]
                if t.count(o2) == 1:
                    out.append((lec, o2, o2.replace(o, f'{m.group(1)}th {m.group(2)}')))
    RULES.write_text('# lecture\t原串\t改作 —— foote_seam_join.py 生成（句中被页码标记切开的接回）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
