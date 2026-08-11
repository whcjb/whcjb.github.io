#!/usr/bin/env python3
"""用附录自身的分节标记给脚注条目定章，并反查已落位条目是否放错。

附录正文里每隔一段就有 `<p class="title-block-h2">PSALM N</p>`（卷一 72 个、
卷二 101 个）以及 scripture-anchor，标明其后的条目属于哪一篇。这是源头给的
权威归属，比按前后编号推断可靠得多，也能用来校验先前靠上下文定位的结果。

附录页在处理过程中已被改写，完整原文从 git 历史取：
  卷一 47140659f:calvin/psalms-1-en/footnotes.md
  卷二 be1e3b962:calvin/psalms-2-en/150.md （FOOTNOTES 段之后）

用法:
    python3 scripts/psalms_footnotes_sections.py 1 --check   # 只报告，不改文件
    python3 scripts/psalms_footnotes_sections.py 1
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = {'1': ('47140659f', 'calvin/psalms-1-en/footnotes.md'),
       '2': ('be1e3b962', 'calvin/psalms-2-en/150.md')}
CODE_SPAN = re.compile(r'<span style="color:#800000">(ft[a-z]\d+[a-z]?)</span>')
SECTION = re.compile(
    r'<p class="title-block-h2"[^>]*>(?:(?!</p>).)*?PSALM\s+(\d+)(?:(?!</p>).)*?</p>'
    r'|<h2 class="scripture-anchor" id="psalm-(\d+)"')


def appendix_text(vol):
    rev, path = SRC[vol]
    t = subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT,
                       capture_output=True, text=True, check=True).stdout
    if vol == '2':
        t = t[t.find('<p class="title-block-h1"', t.find('FOOTNOTES') - 300):]
    return t


def code_sections(vol):
    """→ {code: psalm}，按附录里最近一个分节标记归属"""
    t = appendix_text(vol)
    events = []
    for m in SECTION.finditer(t):
        events.append((m.start(), 'sec', int(m.group(1) or m.group(2))))
    for m in CODE_SPAN.finditer(t):
        events.append((m.start(), 'code', m.group(1)))
    events.sort()
    cur, out = None, {}
    for _, kind, val in events:
        if kind == 'sec':
            cur = val
        elif cur is not None:
            out[val] = cur
    return out


def placed_map(vol):
    """→ {code: 章节名}，取自各章末尾的定义行"""
    where = {}
    for p in (ROOT / f'calvin/psalms-{vol}-en').glob('*.md'):
        if p.stem == 'footnotes':
            continue
        text = p.read_text(encoding='utf-8')
        for c in re.findall(r'^\[\^([a-z]{1,3}\d+[a-z]?)\]:', text, re.M):
            where['ft' + c[1:]] = p.stem
        for c in re.findall(r'^- \*\*([a-z]\d+[a-z]?)\*\*', text, re.M):   # 未定位区块
            where['ft' + c] = p.stem
    return where


if __name__ == '__main__':
    vol = sys.argv[1] if len(sys.argv) > 1 else '1'
    sec = code_sections(vol)
    where = placed_map(vol)
    defs = json.loads((ROOT / f'calvin_raw/psalms-{vol}/footnote_defs.json')
                      .read_text(encoding='utf-8'))

    mismatch = [(c, where[c], sec[c]) for c in where
                if c in sec and where[c].isdigit() and int(where[c]) != sec[c]]
    unplaced = [c for c in defs if c not in where]
    print(f'卷{vol}: 附录分节覆盖 {len(sec)}/{len(defs)} 条')
    print(f'  已落位 {len(where)} 条，其中与附录分节不符 {len(mismatch)} 条')
    for c, got, want in mismatch[:10]:
        print(f'    {c}: 现放在 ch{got}，附录说属 ch{want}')
    print(f'  仍未落位 {len(unplaced)} 条，其中附录分节可定的 '
          f'{sum(1 for c in unplaced if c in sec)} 条')
    (ROOT / f'calvin_raw/psalms-{vol}/footnote_sections.json').write_text(
        json.dumps(sec, ensure_ascii=False, indent=1), encoding='utf-8')
