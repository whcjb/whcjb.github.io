#!/usr/bin/env python3
"""**斜体丢了**的那一类——比「斜体多余」大得多，而且方向相反。

ABBYY 的斜体检测两头都不稳：`psalms_italic_stray.py` 查的是「本该正体却成了
斜体」，这个脚本查反过来的「本该斜体却成了正体」。后者在页面上看不出异常，
读者只会觉得这段话平平无奇——可丢掉的正是「这句是**引文**」的记号。

判据靠**框架**，不靠词形：亚历山大引某个译本时，句式几乎总是
`The common version (…)`、`too vaguely rendered in the English versions (…)`，
括号里是被引的译文，印面一律斜体。框架词表见 FRAME。

影像核过诗 104 `(do creep forth)`、诗 76 `(excellent)`、诗 24 `(take in vain)`，
无一例外是斜体。

**只认框架内的**：括号里成串英文词全书 550 多处，绝大多数是他补出来的词
（`(ye that are)` `(One)` `(about thee)`），那些印面就是正体，一刀切会毁掉
「这几个字不在原文里」的记号。

用法：python3 scripts/psalms_italic_lost.py
"""
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
FRAME = re.compile(
    r'\b(?:common|English|Prayer Book|Septuagint|Vulgate|ancient|old|latest|'
    r'masoretic|marginal|received|authori[sz]ed|Chaldee|Syriac|Arabic|'
    r'Jerome[’\']?s?|Luther[’\']?s?)\s+'
    r'(?:version|translation|rendering|text)s?\s*$', re.I)


def main():
    rows = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        raw = p.read_text(encoding='utf-8')
        body = raw.split('---', 2)[2] if raw.startswith('---') else raw
        out = subprocess.run(['kramdown', '--input', 'GFM'], input=body,
                             capture_output=True, text=True).stdout
        # 用哨兵标出 <em> 边界，这样括号是否落在斜体里一目了然
        plain = html.unescape(
            re.sub(r'<em>', '\x01',
                   re.sub(r'</em>', '\x02',
                          re.sub(r'<(?!/?em)[^<>]+>', '', out))))
        for m in re.finditer(r'\(([a-z][^()\x01\x02]{6,80})\)', plain):
            if not FRAME.search(plain[max(0, m.start() - 46):m.start()].rstrip()):
                continue
            rows.append((p.stem, m.group(1),
                         re.sub(r'\s+', ' ', plain[max(0, m.start() - 54):m.end() + 22])))
    print(f'译本引文括号里是正体的：{len(rows)} 处')
    for sec, g, ctx in rows:
        print(f'  [{sec:>4}] ({g})\n        …{ctx}…')
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
