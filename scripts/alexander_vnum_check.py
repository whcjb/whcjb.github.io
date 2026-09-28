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

诗篇与以赛亚共用。以赛亚原先没有这道闸，代价是四处节号读坏一直挂在页面上
（`V. 1 1.`、`V. 3..`、`V. 1 9.` 拆号或误读，两节同号），章顶 verse-nav 点过去落空。

用法：
    python3 scripts/alexander_vnum_check.py            # 诗篇
    python3 scripts/alexander_vnum_check.py isaiah     # 以赛亚
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = {
    # from_one：这本书每章的第一个显示节号是不是必定为 1。
    # 以赛亚是（`V. 1.` 起头），诗篇不是——希伯来题注在希伯来编号里算第 1 节、
    # 英译不算，于是多数篇的第一个英文号本来就是 2，硬查会报出 64 篇假阳性。
    'psalms': dict(src=ROOT / 'alexander/psalms',
                   as_is=ROOT / 'alexander_raw/psalms/ref_printed_as_is.tsv',
                   from_one=False),
    'isaiah': dict(src=ROOT / 'alexander/isaiah',
                   as_is=ROOT / 'alexander_raw/isaiah/ref_printed_as_is.tsv',
                   from_one=True),
}
VNUM_FMT = r'id="{0}-[a-z0-9-]+-\d+"></span><span class="ax-vnum">([^<]*)<'


def known_gaps(as_is):
    """已核定「印面如此」的缺号：篇 → {节号}"""
    d = {}
    if not as_is.exists():
        return d
    for line in as_is.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        f = line.split('\t')
        m = re.search(r'第\s*(\d+)\s*节无标题', f[1] if len(f) > 1 else '')
        if m:
            d.setdefault(f[0], set()).add(int(m.group(1)))
    return d


def main(book='psalms'):
    cfg = BOOKS[book]
    known = known_gaps(cfg['as_is'])
    vnum = re.compile(VNUM_FMT.format(book))
    bad = 0
    for p in sorted(cfg['src'].glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        t = p.read_text(encoding='utf-8')
        flat = []
        for m in vnum.finditer(t):
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
        # 从 1 起算，不是从 min 起算：**第 1 节丢了的话 min 就变成 2**，
        # 「min..max 之间连号」这条判据对它完全是瞎的（以赛亚 47 章就是
        # `V, 1.`——句点被读成逗号，整节没有锚点，闸子一声不吭）
        lo = 1 if (cfg['from_one'] and p.stem.isdigit()) else min(flat)
        miss = sorted(set(range(lo, max(flat) + 1)) - set(flat)
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
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in BOOKS
                  else 'psalms'))
