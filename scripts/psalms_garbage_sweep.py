#!/usr/bin/env python3
"""**拉丁乱码残渣**——不限于括号内的那一类。

前几轮只扫「成对括号里全是拉丁乱码」，于是这些一个也看不见：
  · 左括号本身丢了      `a modified form of 0^1), the one used`（印面 `(רַע)`）
  · 希伯来词裸露在正文里 `for אלים 7^♦, Dan. xi. 36`（印面 `for אֵל אֵלִים,`）
  · 方括号该是圆括号     `*The [ones] standing,*`（印面 `(ones)`）
  · 一粒墨点被读成括号   `as the [main idea must`（印面没有方括号）
  · 数字之间的逗号读成 ^ `Ps. xxxvii. 37^ 38`（印面 `37, 38`）

判据：**任何**含 `^ [ ] { } | ~` 的拉丁/数字串，不看它在不在括号里。
全书一次扫出 48 处，逐处翻影像定案。

排除：纯符号串（版式残渣另有账），以及 `<span>` 标记内部。

用法：python3 scripts/psalms_garbage_sweep.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
TAG = re.compile(r'<[^<>]+>')
GARB = re.compile(r'(?<![\w>])[A-Za-z0-9^\]\[|}{~]*[\^\]\[|}{~][A-Za-z0-9^\]\[|}{~)(]*')


def main():
    rows = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        t = TAG.sub(' ', p.read_text(encoding='utf-8'))
        for m in GARB.finditer(t):
            s = m.group(0)
            if len(s) < 2 or re.fullmatch(r'[\^~|]+', s):
                continue
            rows.append((p.stem, s,
                         re.sub(r'\s+', ' ', t[max(0, m.start() - 52):m.end() + 28])))
    print(f'拉丁乱码残渣：{len(rows)} 处')
    for sec, s, ctx in rows:
        print(f'  [{sec:>4}] {s!r}\n        …{ctx}…')
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
