#!/usr/bin/env python3
"""修复表自检：规则本身有没有毛病。

这张表是**按字面替换**的，而链条里 `adjudicate --apply` 会跑不止一遍，
每遍内部还跑多轮。于是规则不幂等的代价是静默的、而且会叠加：

  · `…50: 2, an` → `…50: 2, and`      旧串是新串的前缀 → 第二遍写出 `andd`（反复了三次）
  · `or done them` → `(or done them)`  旧串套在新串里 → 每跑一遍加一层括号，
                                        实测叠到 37 层 `(((((((…or done them)))))))`
  · `…ruin` → `…ruin.`                 正文里后面本来就是句点 → `ruin..`

三条判据，都便宜：
  ① **旧串不许出现在新串里**（不幂等）
  ② 旧串在已发布正文里必须恰好命中一次（0 次＝白写，多次＝会改错位置）
  ③ 补在末尾的标点，正文里紧跟着不许已经是同一个

用法：python3 scripts/isaiah_fixes_lint.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
TABLES = [ROOT / 'alexander_raw/isaiah/manual_fixes.tsv']


def rules():
    for tsv in TABLES:
        if not tsv.exists():
            continue
        for lineno, line in enumerate(tsv.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.startswith('#'):
                continue
            f = line.split('\t')
            if len(f) >= 2 and f[0] and f[0] != 'before':   # 'before' 是表头
                yield tsv.name, lineno, f[0], f[1]


def main():
    pub = ''.join(p.read_text(encoding='utf-8') for p in SRC.glob('*.md'))
    bad = {'不幂等': [], '命中 0 次': [], '命中多次': [], '会写出双标点': []}
    for name, ln, old, new in rules():
        if old == new:
            continue
        if old in new and not (new.startswith(old) or new.endswith(old)):
            # 只在末尾补／只在开头补这两种形态，`apply_manual` 用环视挡住了
            # 重复施加；两头都加的（`or done them`→`(or done them)`）挡不住，
            # 跑一遍加一层，实测叠到 37 层括号。
            bad['不幂等'].append((ln, old, new))
            continue
        n = pub.count(old)
        if n == 0:
            # 已经落过盘的规则，正文里自然就找不到旧串了——那是正常的。
            # 只有**新串也找不到**才说明这条规则从来没生效过。
            if pub.count(new) == 0:
                bad['命中 0 次'].append((ln, old, new))
        elif n > 1:
            bad['命中多次'].append((ln, old, new))
        # 纯追加（new = old + 一截）由 `apply_manual` 的环视挡着，不会重复施加；
        # 这里只查两头都改、环视挡不住的那种。
        if (new and new[-1] in '.,;:' and not old.endswith(new[-1])
                and not new.startswith(old)):
            for m in re.finditer(re.escape(old), pub):
                nxt = pub[m.end():m.end() + 1]
                if nxt == new[-1]:
                    bad['会写出双标点'].append((ln, old, new))
                    break
    # 「命中 0 次」是提醒不是错：多半是上游 repair 改了写法、这条规则从此空转。
    warn = bad.pop('命中 0 次')
    total = sum(len(v) for v in bad.values())
    if warn:
        print(f'（提醒）空转的规则 {len(warn)} 条：旧串和新串在正文里都找不到，'
              f'多半被上游 repair 的改动顶掉了')
    for k, v in bad.items():
        if not v:
            continue
        print(f'{k}：{len(v)} 条')
        for ln, old, new in v[:8]:
            print(f'   行{ln} {old[:44]!r} → {new[:44]!r}')
    print('修复表自检：' + ('全部通过 ✓' if not total else f'{total} 条有问题'))
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
