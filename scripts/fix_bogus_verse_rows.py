#!/usr/bin/env python3
"""合并双语经文表里的「伪行」：节号落在本段 verse-range 之外。

来源：正文里的数字被误当成节号切开。实例——

    calvin/joel/1.md  ref 1:1-20
      <tr><td scripture-en></td>
          <td scripture-la><strong>42.</strong> habetur: est illic idem
              verbum: clamabunt igitur bestiae ad te,) quia aruerunt…</td></tr>

上一行 v20 的拉丁以 `…sicuti etiam Psalmo` 收尾 —— 那个 `42` 是
**「Psalmo 42」（诗篇 42 篇）**的一部分，被切成了「第 42 节」。
同类还有 ezekiel/16 的 v407、daniel/5 的 v244（都是脚注号或引用号）。

判据（严格，避免误伤）：
  1. 该行只有一侧有内容（另一侧空）；
  2. 节号 **不在** 本 box 的 `verse-range` 区间内；
  3. 前面存在同侧非空的行。
三条同时满足才合并——把内容接到上一行同侧末尾，删掉伪行。

零丢失：字符多重集守恒（内容只是换了位置），脚本内置断言。

用法:
    python3 scripts/fix_bogus_verse_rows.py --check
    python3 scripts/fix_bogus_verse_rows.py
"""
import argparse
import glob
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r'<[^>]+>')


def _rng(inner):
    m = re.search(r'<span class="verse-range">([^<]+)</span>', inner)
    if not m:
        return None
    t = m.group(1)
    m2 = re.search(r'(?:\d+:)?(\d+)\s*[-–]\s*(\d+)', t)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    m3 = re.search(r'(?:\d+:)?(\d+)', t)
    return (int(m3.group(1)), int(m3.group(1))) if m3 else None


def _num(cell):
    m = re.search(r'<strong>\s*(\d{1,3})\s*\.?\s*</strong>', cell)
    return int(m.group(1)) if m else None


def fix_text(text):
    merged = 0

    def fix_box(bm):
        nonlocal merged
        whole = bm.group(0)
        inner = bm.group(1)
        rr = _rng(inner)
        if not rr:
            return whole
        lo, hi = rr
        trs = re.findall(r'<tr>.*?</tr>', inner, re.S)
        if len(trs) < 2:
            return whole
        rows = []
        for tr in trs:
            cs = dict(re.findall(r'<td class="scripture-(en|la)">(.*?)</td>', tr, re.S))
            rows.append(cs)
        out, drop = [], set()
        for idx, cs in enumerate(rows):
            filled = [k for k in ('en', 'la') if TAG.sub('', cs.get(k, '')).strip()]
            if len(filled) != 1:
                continue
            side = filled[0]
            n = _num(cs[side])
            if n is None or lo <= n <= hi:
                continue
            # 往前找同侧非空行
            prev = None
            for k in range(idx - 1, -1, -1):
                if k in drop:
                    continue
                if TAG.sub('', rows[k].get(side, '')).strip():
                    prev = k
                    break
            if prev is None:
                continue
            body = re.sub(r'^\s*<strong>\s*\d{1,3}\s*\.?\s*</strong>\s*', '',
                          cs[side]).strip()
            rows[prev][side] = rows[prev][side].rstrip() + ' ' + str(n) + '. ' + body
            drop.add(idx)
            merged += 1
        if not drop:
            return whole
        new_trs = ''.join(
            f'<tr><td class="scripture-en">{r.get("en", "")}</td>'
            f'<td class="scripture-la">{r.get("la", "")}</td></tr>\n'
            for i, r in enumerate(rows) if i not in drop)
        head = inner[:inner.index('<tr>')]
        tail = inner[inner.rindex('</tr>') + 5:]
        return whole.replace(inner, head + new_trs.rstrip('\n') + tail)

    new = re.sub(r'<div class="scripture-box[^"]*"[^>]*>(.*?)</div>', fix_box,
                 text, flags=re.S)
    return new, merged


def _ch(s):
    return Counter(re.sub(r'\s+', '', TAG.sub(' ', s)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    tot = 0
    for f in sorted(glob.glob(str(ROOT / 'calvin' / '*' / '*.md'))):
        s = open(f, encoding='utf-8').read()
        if 'scripture-bilingual' not in s:
            continue
        new, n = fix_text(s)
        if not n:
            continue
        if _ch(s) != _ch(new):
            d = _ch(s) - _ch(new)
            print(f'  !! {os.path.relpath(f, ROOT)} 字符不一致（少 {sum(d.values())}），跳过')
            continue
        tot += n
        print(f'  {os.path.relpath(f, ROOT)}: 合并 {n} 个伪行')
        if not a.check:
            open(f, 'w', encoding='utf-8').write(new)
    print(f'\n  {"可合并" if a.check else "已合并"} {tot} 个伪行')
    return 0


if __name__ == '__main__':
    sys.exit(main())
