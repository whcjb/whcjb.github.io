#!/usr/bin/env python3
"""把重扫出来的希伯来／希腊文落回已发布正文。

按位置替换，不按串全局替换：同一串拉丁乱码可能来自不同的希伯来词
（ABBYY 的误读是有损的），所以每条都要用行内上下文锚定位，且要求**全书唯一**。

两处归一，不做就对不上：
  · publish 会把正文里的野生 `<` 转成 `&lt;`（HTML 合法性），
    而重扫的锚来自 XML，那里还是 `<`；
  · TSV 写出时用 `\\` 做转义符，读回来要还原。

用法：
    python3 scripts/psalms_hebrew_apply.py            # 只报告
    python3 scripts/psalms_hebrew_apply.py --apply    # 落盘
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'alexander_raw/psalms/hebrew_ocr_accepted.tsv'
OUT = ROOT / 'alexander_raw/psalms/hebrew_ocr_rules.tsv'
SRC = ROOT / 'alexander/psalms'

ENT = [('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&')]


def unent(t):
    for a, b in ENT:
        t = t.replace(a, b)
    return t


def reent(t):
    """反向：只把裸 `<` `>` 转回实体，`&` 不动（正文里 `&c.` 很多）。"""
    return t.replace('<', '&lt;').replace('>', '&gt;')


def main(apply=False):
    rows = list(csv.DictReader(open(TSV, encoding='utf-8'), delimiter='\t',
                               quoting=csv.QUOTE_NONE))
    files = {f: f.read_text(encoding='utf-8') for f in sorted(SRC.glob('*.md'))}
    plain = {f: unent(t) for f, t in files.items()}
    joined = '\n'.join(plain.values())

    rules, miss, dup = [], [], []
    for r in rows:
        g = r['garbage'].replace('\\\\', '\\')
        reading = r['reading'].replace('\\\\', '\\')
        n = joined.count(g)
        if n == 0:
            miss.append(r)
            continue
        if n > 1:
            # 不唯一就带上行内的前文锚，锚也来自同一行，一起在正文里找
            before = r['before'].replace('\\\\', '\\').split()
            found = False
            for k in range(1, min(4, len(before)) + 1):
                anchor = ' '.join(before[-k:]) + ' ' + g
                if joined.count(anchor) == 1:
                    rules.append((anchor, ' '.join(before[-k:]) + ' ' + reading, r))
                    found = True
                    break
            if not found:
                dup.append(r)
            continue
        rules.append((g, reading, r))

    print(f'可落盘 {len(rules)} 条；锚不唯一 {len(dup)} 条；正文里找不到 {len(miss)} 条')
    if miss:
        print('  找不到的（多半是抽取阶段改写过这一段）:')
        for r in miss[:8]:
            print(f"    {r['garbage'][:30]!r} → {r['reading'][:18]!r}")

    OUT.write_text('old\tnew\tscript\tconf\n' + ''.join(
        f'{o}\t{n}\t{r["script"]}\t{r["conf"]}\n' for o, n, r in rules),
        encoding='utf-8')
    print(f'规则 → {OUT}')

    if not apply:
        return
    hit = 0
    for f, t in files.items():
        p = unent(t)
        changed = False
        for o, n, _ in rules:
            if o in p:
                p = p.replace(o, n)
                changed = True
                hit += 1
        if changed:
            f.write_text(reent(p), encoding='utf-8')
    print(f'落盘 {hit} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
