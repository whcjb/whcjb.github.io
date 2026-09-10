#!/usr/bin/env python3
"""按**书页**统计已发布正文里还剩多少可疑 token，给影像逐页排查排个先后。

1153 页全看一遍成本太高，而问题分布极不均匀：希伯来引文密的页面一页能有
二三十个残串，纯英文议论的页面一个都没有。所以先按可疑密度排序，从最脏的
页面看起。

「可疑」= 判词典不认、且不是罗马数字。输出 TSV：书页、卷、章、可疑数、样例。
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
OUT = ROOT / 'logs/alexander_isaiah_page_suspects.tsv'

TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")
FRONT = re.compile(r'^---.*?^---\n', re.S | re.M)
SEGMENT = re.compile(r'(<!--.*?-->|</?[A-Za-z][^<>]*>)', re.S)
PAGE = re.compile(r'<!-- PAGE (\d+) -->')
SECTION_VOL = {'preface': 'v1', 'introduction': 'v1',
               'later-preface': 'v2', 'later-introduction': 'v2'}


def main():
    lex = build()
    per = defaultdict(lambda: {'n': 0, 'ex': [], 'ch': set()})
    for path in sorted(SRC.glob('*.md')):
        stem = path.stem
        vol = SECTION_VOL.get(stem)
        if vol is None:
            if not stem.isdigit():
                continue
            vol = 'v1' if int(stem) <= 39 else 'v2'
        raw = FRONT.sub('', path.read_text(encoding='utf-8'))
        page = None
        for seg in SEGMENT.split(raw):
            if seg.startswith('<!--'):
                m = PAGE.search(seg)
                if m:
                    page = int(m.group(1))
                continue
            if seg.startswith('<') or page is None:
                continue
            for w in TOKEN.findall(seg):
                if is_word(w, lex):
                    continue
                d = per[(vol, page)]
                d['n'] += 1
                d['ch'].add(stem)
                if len(d['ex']) < 8:
                    d['ex'].append(w)
    rows = sorted(per.items(), key=lambda kv: -kv[1]['n'])
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tpage\tchapters\tsuspects\texamples\n')
        for (vol, page), d in rows:
            f.write(f"{vol}\t{page}\t{','.join(sorted(d['ch']))}\t{d['n']}\t"
                    f"{' '.join(d['ex'])}\n")
    tot = sum(d['n'] for _, d in rows)
    print(f'{len(rows)} 页有可疑 token，合计 {tot}；最脏的 15 页：')
    for (vol, page), d in rows[:15]:
        print(f"   {vol} 书页 {page:>3} (ch{','.join(sorted(d['ch']))}) "
              f"{d['n']:>3} 处  {' '.join(d['ex'][:6])}")
    print('→', OUT)


if __name__ == '__main__':
    main()
