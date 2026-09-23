#!/usr/bin/env python3
"""**显示出来的**节号必须连号——整节丢失的唯一判据。

既有的「节号自查」查的是锚点 id（`psalms-19-2`），那是发布时按顺序发的，
永远单调，查不出问题。真正会错的是**印在页面上的那个号**：
  · 节号本身被读坏（`8` 其实是 3、`G` 其实是 6、`178` 其实是 173、`o20`）
    → 号码不连续，或者干脆认不出、整节没有锚点
  · 节号标题粘进上一段 → `transform` 的 `^` 锚匹配不到，**整节消失**

后一种在页面上一点异常都看不出来：段落照样显示，只是少了一个编号和锚点，
章顶 verse-nav 点那一节会落空。全书 11 处就是这么查出来的。

判据：把每篇所有 `.ax-vnum` 里的号（含 `15, 16` `31-33` 这类合并与范围）
摊平，必须覆盖 min..max 且不重号。

印面自己就缺标题的（诗 26 把第 4、5 节合在一段讲）记在
`alexander_raw/psalms/ref_printed_as_is.tsv`，不再计入。

用法：python3 scripts/psalms_vnum_check.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
AS_IS = ROOT / 'alexander_raw/psalms/ref_printed_as_is.tsv'
VNUM = re.compile(r'id="psalms-[a-z0-9]+-\d+"></span><span class="ax-vnum">([^<]*)<')


def known_gaps():
    """已核定「印面如此」的缺号：篇 → {节号}"""
    d = {}
    if not AS_IS.exists():
        return d
    for line in AS_IS.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        f = line.split('\t')
        m = re.search(r'第\s*(\d+)\s*节无标题', f[1] if len(f) > 1 else '')
        if m:
            d.setdefault(f[0], set()).add(int(m.group(1)))
    return d


def main():
    known = known_gaps()
    bad = 0
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        t = p.read_text(encoding='utf-8')
        flat = []
        for m in VNUM.finditer(t):
            head = m.group(1).split('(')[0]          # 括号里是英文编号，另一套
            nums = [int(x) for x in re.findall(r'\d+', head)]
            if not nums:
                continue
            rng = set(nums)
            for a, b in re.findall(r'(\d+)\s*[-–—]\s*(\d+)', head):
                rng |= set(range(int(a), int(b) + 1))
            flat += sorted(rng)
        if not flat:
            continue
        miss = sorted(set(range(min(flat), max(flat) + 1)) - set(flat)
                      - known.get(p.stem, set()))
        dup = sorted({v for v in flat if flat.count(v) > 1})
        if miss or dup:
            bad += 1
            print(f'  [{p.stem}] 缺 {miss[:10]}  重 {dup[:6]}  范围 {min(flat)}-{max(flat)}')
    n_known = sum(len(v) for v in known.values())
    print(f'显示节号自查：' + ('全部连号 ✓' if not bad else f'{bad} 篇有缺口/重号')
          + (f'（另有 {n_known} 处已核定「印面本来就没有」）' if n_known else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
