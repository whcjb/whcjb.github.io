#!/usr/bin/env python3
"""把印面比对报出来的条目**按错误类型归并**，决定哪些做成规则、哪些进人工表。

以赛亚的规矩（PROOFREAD_STATUS.md §怎么接着做）：
    同一类出现三次以上 → 做成带闸的规则
    只出现一两次       → 逐条进人工表
    改之前存快照，改完**逐处 diff 复核**

归类不靠读内容，靠**编辑形态**：把 `我们的 ||| 印面的` 两边做字符级对齐，
取出差异片段，按「谁变成了谁」聚类。同一类字形误读（`a.D.`→`A.D.`、
`!`→`¹`）自然会堆到一起。

    python3 scripts/johnstone_pageproof_triage.py
    python3 scripts/johnstone_pageproof_triage.py --min 3      # 只看够做规则的
"""
import argparse
import difflib
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'logs', 'johnstone_pageproof.tsv')
PAIR = re.compile(r'MISMATCH:\s*(.+?)\s*\|\|\|\s*(.+?)\s*$')


def edits(ours, printed):
    """两边对齐，取出「谁变成了谁」。只留真正不同的片段。"""
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, ours, printed, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        a, b = ours[i1:i2].strip(), printed[j1:j2].strip()
        if a or b:
            out.append((a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min', type=int, default=1)
    ap.add_argument('--show', type=int, default=3)
    a = ap.parse_args()

    if not os.path.exists(LOG):
        sys.exit('还没有比对结果')
    pages, anchor_fail, cost = set(), [], 0.0
    cls = defaultdict(list)
    for line in open(LOG, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if not p or not p[0].isdigit():
            continue
        pages.add(p[0])
        try:
            cost += float(p[1])
        except ValueError:
            pass
        if len(p) > 2 and p[2] == 'ANCHOR-FAIL':
            anchor_fail.append(p[0])
            continue
        for chunk in (p[3] if len(p) > 3 else '').split(' ⟂ '):
            m = PAIR.search(chunk)
            if not m:
                continue
            for was, now in edits(m.group(1), m.group(2)):
                cls[(was, now)].append((p[0], m.group(1)[:70]))

    print(f'已比对 {len(pages)} 页，累计 ${cost:.2f}，'
          f'锚不上 {len(anchor_fail)} 页，差异 {sum(len(v) for v in cls.values())} 处\n')
    if anchor_fail:
        print('锚不上的页（多半是整段丢失或错位，要单独看）:',
              ' '.join(anchor_fail[:30]), '\n')

    ranked = sorted(cls.items(), key=lambda kv: -len(kv[1]))
    rule, manual = [], []
    for (was, now), rows in ranked:
        (rule if len(rows) >= 3 else manual).append(((was, now), rows))

    print(f'── 够做规则的（≥3 次）{len(rule)} 类 ──')
    for (was, now), rows in rule:
        if len(rows) < a.min:
            continue
        print(f'  {len(rows):3d}  {was!r:26s} → {now!r}')
        for pg, ctx in rows[:a.show]:
            print(f'        leaf {pg}: {ctx}')
    print(f'\n── 只出现一两次、进人工表的 {len(manual)} 条 ──')
    for (was, now), rows in manual[:60]:
        pg, ctx = rows[0]
        print(f'  leaf {pg:>4s}  {was!r} → {now!r}   « {ctx} »')


if __name__ == '__main__':
    main()
