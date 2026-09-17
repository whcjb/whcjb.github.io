#!/usr/bin/env python3
"""一条脚注定义里串着下一条：后面几条只剩红字码，没拆成独立的 def。

形态（AGES 书末脚注区连排，发布时整段当成一条定义）：
    [^f726]: “…vaines et inutiles;” —— “…毫无果效。” <span style="color:#800000">f727</span> “Et aussi…;” —— “…”

f727、f728 的定义被压在 f726 的定义里，页面上看不见它们，正文里对应的引用
就成了孤儿（多半已被 fix_orphan_footnote_refs 退成红字死标记）。

修法：在每个内嵌码处断开，各自起一行 `[^fN]: …`。**一个字符都不删**——只是
把 `<span …>f727</span>` 这个标记换成行首的 `[^f727]:`。拆出来正文为空的不拆
（定义正文不在本行，拿不准边界，宁可不动），报出来。

用法：
    python3 scripts/fix_footnote_def_runon.py [--apply] [目录…]     # 默认全库 calvin/
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_SPAN = re.compile(r'<span style="color:#800000">\s*[Ff][Tt]?(\d+[A-Za-z]?)\.?\s*</span>')
DEF_HEAD = re.compile(r'^\[\^f(\d+[A-Za-z]?)\]:')


def split_line(line: str):
    """返回 (新行列表, 拆出条数, 因正文为空而放弃的号)。"""
    if not DEF_HEAD.match(line.lstrip()) or not CODE_SPAN.search(line):
        return [line], 0, []
    parts, last, out = [], 0, []
    for m in CODE_SPAN.finditer(line):
        parts.append((last, m.start(), None))
        last = m.end()
        out.append((m.group(1), last))
    segments = []
    bounds = [m.span() for m in CODE_SPAN.finditer(line)]
    codes = [m.group(1) for m in CODE_SPAN.finditer(line)]
    starts = [0] + [b[1] for b in bounds]
    ends = [b[0] for b in bounds] + [len(line)]
    for i, (s, e) in enumerate(zip(starts, ends)):
        segments.append((None if i == 0 else codes[i - 1], line[s:e]))
    if any(not seg.strip() for code, seg in segments if code):
        return [line], 0, [c for c, seg in segments if c and not seg.strip()]
    lines = [segments[0][1].rstrip()]
    for code, seg in segments[1:]:
        lines.append('')
        lines.append(f'[^f{code}]: {seg.strip()}')
    return lines, len(segments) - 1, []


def main() -> int:
    apply = '--apply' in sys.argv
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith('--')] or [ROOT / 'calvin']
    total = skipped = 0
    for d in dirs:
        files = sorted(d.glob('*/*.md') if d.name == 'calvin' else d.glob('*.md'))
        for p in files:
            src = p.read_text(encoding='utf-8').split('\n')
            out, n, gave_up = [], 0, []
            for line in src:
                new, cnt, empty = split_line(line)
                out.extend(new)
                n += cnt
                gave_up += empty
            if gave_up:
                skipped += len(gave_up)
                print(f'  {p}: 正文为空不拆 {gave_up}')
            if not n:
                continue
            total += n
            print(f'  {p}: 拆出 {n} 条定义')
            if apply:
                p.write_text('\n'.join(out), encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] 拆出 {total} 条，放弃 {skipped} 条')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
