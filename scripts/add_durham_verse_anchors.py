#!/usr/bin/env python3
"""给达拉谟《启示录注释》铺 per-verse 锚点。

与贺智/司布真那条线的判据不同
-----------------------------
那两本要去正文里认节号头（`V. 1.` / `**18.**` / `第 1 节`），形态杂、要三条正则。
这本不用：**讲次标题自带经文范围**，提取阶段已落成

    ## LECTURE V (11:15–19)

范围里的每一节各出一个锚点，都落在这条讲次标题之前——点任何一节都到这一讲，
与 skill 07 §4「一个胶囊一节注释」一致。

范围形态实测只有三种：`11:15–19`（区间）、`1:10`（单节）、`6:1`（单节）。
连字符可能是 en dash（–）也可能是 hyphen（-），两种都认。

幂等：先剥旧锚点再重铺，可反复跑。

用法:
    python3 scripts/add_durham_verse_anchors.py
    python3 scripts/add_durham_verse_anchors.py --check
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = 'revelation'

ANCHOR_RE = re.compile(r'^<div class="commentary-anchor" id="[^"]+"></div>\n', re.M)
LECT_RE = re.compile(r'^## LECTURE(?:\s+[IVXL]+)?\s*\((\d{1,2}):(\d{1,3})(?:[–\-](\d{1,3}))?\)\s*$')


def process(path: Path, write: bool):
    text = ANCHOR_RE.sub('', path.read_text(encoding='utf-8'))
    out, seen, n = [], {}, 0
    for line in text.split('\n'):
        m = LECT_RE.match(line)
        if m:
            ch = int(m.group(1))
            lo = int(m.group(2))
            hi = int(m.group(3)) if m.group(3) else lo
            if hi < lo or hi - lo > 60:          # 反序或离谱跨度 → 只当两个孤立节
                rng = [lo, hi]
            else:
                rng = range(lo, hi + 1)
            for v in rng:
                seen[(ch, v)] = seen.get((ch, v), 0) + 1
                sfx = '' if seen[(ch, v)] == 1 else f'-{seen[(ch, v)]}'
                out.append(f'<div class="commentary-anchor" id="{BOOK}-{ch}-{v}{sfx}"></div>')
                n += 1
        out.append(line)
    new = '\n'.join(out)
    if write and new != text:
        path.write_text(new, encoding='utf-8')
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    d = ROOT / 'durham' / BOOK
    total = 0
    for sub, label in (('', 'en'), ('zh', 'zh')):
        dd = d / sub if sub else d
        if not dd.is_dir():
            continue
        files = sorted(dd.glob('[0-9]*.md'), key=lambda p: int(p.stem))
        if not files:
            continue
        n = sum(process(f, not a.check) for f in files)
        total += n
        print(f'{BOOK}/{label:2s}  {len(files):2d} 章  {n:4d} 锚点')
    print(f'合计 {total} 锚点' + ('（--check，未写入）' if a.check else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
