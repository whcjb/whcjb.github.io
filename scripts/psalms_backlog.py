#!/usr/bin/env python3
"""诗篇英文底本还剩多少要判——把账算清楚，分母不准排期就是瞎猜。

判读跑完之后账上还有一堆「不是真词」的串，但它们不是同一回事：

  外文活字     希伯来/希腊字母的串。页面上印的就是外文，不该按拉丁字母去判
  已核实原样   底本就这么印的（darknees、Notwitstanding），见
               alexander_raw/psalms/printed_as_is.txt
  已落过判读   这一处在 manual_fixes.tsv / 影像判读账本里出现过，改过了；
               现在这串是**改完之后**的形态
  待判         剩下的才是真要人判的

以前拿「非词总数」当残留，数字虚高十倍：一多半是判词典收不到的专名
（Adhonai、Al-tashheth、burnt-offering），本来就没错。2026-09-16 把这批
专名补进 lexicon_extra.txt 之后，这个脚本报的才是真实残留。

用法：
    python3 scripts/psalms_backlog.py          # 分桶算账
    python3 scripts/psalms_backlog.py --list   # 把「待判」逐条列出来
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
PRINTED = ROOT / 'alexander_raw/psalms/printed_as_is.txt'
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
OUT = ROOT / 'logs/alexander_psalms_backlog.tsv'

FOREIGN = re.compile(r'[֐-׿Ͱ-Ͽἀ-῿]')


def printed_as_is():
    out = set()
    if PRINTED.exists():
        for line in PRINTED.open(encoding='utf-8'):
            for w in line.split('#')[0].split():
                out.add(w)
    return out


def already_fixed():
    """manual_fixes 改完之后的形态：这些串是判读的**结果**，不是残留。"""
    out = set()
    if FIXES.exists():
        with FIXES.open(encoding='utf-8') as fh:
            next(fh)
            for line in fh:
                f = line.rstrip('\n').split('\t')
                if len(f) >= 3:
                    out.update(f[2].split())
    return out


def main(show=False):
    vocab = L.build()
    asis, fixed = printed_as_is(), already_fixed()
    stat = Counter()
    pending = []
    for sec in ['preface'] + [str(i) for i in range(1, 151)]:
        p = SRC / f'{sec}.md'
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        # front matter 不是正文：book_id / prev_label 这类键名一个都不是词，
        # 混进来能把账做大一倍（763 处）。正文从第一个 <!-- PAGE n --> 起算。
        start = raw.find('<!-- PAGE ')
        if start < 0:
            continue
        masked = A._mask_markup(raw)
        for m in A.SPAN.finditer(masked, start):
            bad, core = A._suspect(m.group(0), vocab)
            if not bad:
                continue
            if FOREIGN.search(core):
                stat['外文活字'] += 1
            elif core in asis:
                stat['已核实原样'] += 1
            elif core in fixed or m.group(0) in fixed:
                stat['已落过判读'] += 1
            else:
                stat['待判'] += 1
                pending.append((sec, core,
                                re.sub(r'\s+', ' ', raw[max(0, m.start() - 45):m.end() + 45])))
    total = sum(stat.values())
    print(f'非词 {total} 处：' + '，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t串\t上下文\n')
        for sec, core, ctx in pending:
            fh.write(f'{sec}\t{core}\t{ctx}\n')
    print(f'待判清单 → {OUT}')
    if show:
        for sec, core, ctx in pending:
            print(f'  [{sec}] {core}\t…{ctx}…')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    main(ap.parse_args().list)
