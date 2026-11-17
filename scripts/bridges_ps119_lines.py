#!/usr/bin/env python3
"""布里奇斯《诗篇 119 篇讲解》：Biblical eLearning 录入本（Word 导出 HTML，逐行录入）→ 行表。

    python3 scripts/bridges_ps119_lines.py   → bridges_raw/psalm119/work/lines.json

录入本每个印刷行一个 <p class=MsoPlainText>；段首行用 mso-spacerun 空格缩进；分页处有
<br … page-break-before:always>，其后第一行是页眉（「VERSE 9.   19」「vi  PREFACE.」），丢掉。
每行记：文字（斜体转 <em>）、缩进空格数、是否紧跟分页。拼段与去连字符在 publish 脚本里做。
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'bridges_raw' / 'psalm119' / 'src' / 'bel.htm'
OUT = ROOT / 'bridges_raw' / 'psalm119' / 'work' / 'lines.json'


def main():
    s = SRC.read_bytes().decode('cp1252')
    s = s[s.lower().find('<body'):]
    s = re.sub(r'<br[^>]*page-break-before:always[^>]*>', '\x01PB\x01', s)
    out, pb = [], False
    for m in re.finditer(r'\x01PB\x01|<p\b[^>]*>(.*?)</p>', s, re.S):
        if m.group(0) == '\x01PB\x01':
            pb = True
            continue
        x = m.group(1)
        x = re.sub(r'<o:p>.*?</o:p>', '', x, flags=re.S)
        lead = 0
        sp = re.match(r"\s*(?:<span[^>]*>\s*)*<span\s+style='mso-spacerun:yes'>([^<]*)</span>", x)
        if sp:
            lead = len(sp.group(1).replace('&nbsp;', ' '))
        x = re.sub(r'<i\b[^>]*>', '<em>', x)
        x = x.replace('</i>', '</em>')
        x = re.sub(r'<(?!/?em>)[^>]+>', '', x)
        x = html.unescape(x).replace('\xa0', ' ')
        x = re.sub(r'\s+', ' ', x).strip()
        x = re.sub(r'<em>\s*</em>', '', x)
        if x == '\x01PB\x01':
            pb = True
            continue
        if not x:
            continue
        # 有几处分页符落在 <p> 里面（同一段里接着就是下页页眉）：「1, 2.⟨分页⟩ 170 EXPOSITION OF PSALM CXIX.」
        m2 = re.search(r'\x01PB\x01', x)
        if m2:
            if x[:m2.start()].strip():
                out.append({'t': x[:m2.start()].strip(), 'ind': lead, 'pb': pb})
            out.append({'t': x[m2.end():].strip() or '(running head)', 'ind': 0, 'pb': True})
            pb = False
            continue
        out.append({'t': x, 'ind': lead, 'pb': pb})
        pb = False
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    print(len(out), 'lines;', sum(l['pb'] for l in out), 'page breaks')


if __name__ == '__main__':
    main()
