#!/usr/bin/env python3
"""希尔德沙姆《诗篇 51 篇讲义 152 讲》TCP 录入本 → hildersham_raw/psalm51/units.json

    python3 scripts/extract_hildersham.py

底本 EEBO-TCP A03343（CC0）：*CLII Lectures vpon Psalme LI. Preached at Ashby-Delazouch in Leicester-shire*,
London 1635（STC 13459）。无缺页；读不出的字照 tcp_tei 记号录入、页面标红。

结构：body 下 8 个 part（标题 / 1–2 / 3 / 4 / 5 / 6 / 6 / 7 节），各含若干 lecture（共 152 讲，讲于 1625-09-28 至 1631）。
讲次按标题印的罗马数字（TCP 的 n 有录错：第 60 讲作 55、第 57 讲作 57 但排在第 60 讲后）。原书第 287–303 页的次序
是 LVIII、LIX、LX、LVII（第 57 讲印在第 60 讲之后，卷首提要也记它在 p. 301–303），页面按讲次排，第 57 讲回到 56、58 之间
（日期 5 月 15 日也正落在其间）。标题印了两个「LXXI」：第一个（10 月 2 日）按日期与卷首提要实为第 70 讲；两个「CXVI」：第二个（4 月 28 日）实为第 117 讲。
所讲经节按所属 part 的标题定——lecture 标题里的节次有印错的（第 118 讲在第 7 节部分却印「51.6」），不用。
卷首 table_of_contents 是作者自编的逐讲提要（「Lect. N.」下一串条目，带原书页码），挂到各讲页首。
卷首：title_page、dedication、errata 各一页；table_of_citations（经文索引）与卷末 index 暂不出。
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_tei as tt                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hildersham_raw' / 'psalm51'
TEI = tt.TEI
P = 'hd'
ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def roman(s):
    v = [ROMAN[c] for c in s]
    return sum(-a if i + 1 < len(v) and v[i + 1] > a else a for i, a in enumerate(v))


def verses_of(head):
    """part 标题「LECTVRES ON PSAL. LI. 1, 2.」→ 'title' / '1-2' / '3' …"""
    m = re.search(r'LI\.\s*([\d,\s]+)\.?$', head)
    if not m:
        return 'title'
    ns = [int(x) for x in re.findall(r'\d+', m.group(1))]
    return f'{ns[0]}-{ns[-1]}' if len(ns) > 1 else str(ns[0])


def render(r, e, skip_head=True):
    out = []
    for c in e:
        if skip_head and c.tag == TEI + 'head':
            continue
        if c.tag == TEI + 'epigraph':           # 讲首所讲经文 → 经文框
            inner = []
            tt.blocks(r, c, inner)
            txt = '\n\n'.join(x[-1] if isinstance(x[-1], str) else '' for x in inner if x[0] != 'pb')
            out.append(('text', txt.strip()))
            continue
        tt.block(r, c, out, 3)
    return tt.to_md(P, out)


def main():
    root = ET.parse(RAW / 'src' / 'A03343.xml').getroot()
    for el in root.iter():                  # 原书字面星号不当斜体
        for a in ('text', 'tail'):
            v = getattr(el, a)
            if v and '*' in v:
                setattr(el, a, v.replace('*', '&#42;'))
    r = tt.R(P, '1635')
    text = root.find(f'.//{TEI}text')
    front, contents = [], {}
    for d in text.find(TEI + 'front'):
        if d.tag != TEI + 'div':
            continue
        ty = d.get('type')
        if ty == 'title_page':
            front.append(dict(slug='title', title='Title Page', md=render(r, d, False)))
        elif ty == 'dedication':
            front.append(dict(slug='dedication', title='The Epistle Dedicatory', md=render(r, d, False)))
        elif ty == 'errata':
            front.append(dict(slug='errata', title='Errata', md=render(r, d, False)))
        elif ty == 'table_of_contents':
            for lec in d.iter(TEI + 'div'):
                if lec.get('type') != 'lecture':
                    continue
                items = [tt.norm(r, r.inline(it)) for it in lec.iter(TEI + 'item')]
                contents[int(lec.get('n'))] = items
        elif ty == 'table_of_citations':
            continue
        else:
            raise ValueError(f'未处理的卷首 div {ty}')
    lectures, parts = [], []
    for part in text.find(TEI + 'body'):
        if part.tag != TEI + 'div':
            continue
        ph = tt.text_of(part.find(TEI + 'head')).replace('ſ', 's')
        v = verses_of(ph)
        parts.append(dict(head=ph, verses=v))
        for lec in part:
            if lec.tag == TEI + 'trailer':          # 全书末 FINIS：挂到最后一讲
                lectures[-1]['md'] += f'\n\n<p class="{P}-trailer">{tt.text_of(lec)}</p>'
                continue
            if lec.tag != TEI + 'div':
                continue
            assert lec.get('type') == 'lecture', lec.get('type')
            h = tt.norm(r, r.inline(lec.find(TEI + 'head')))
            n = roman(re.match(r'\*?Lecture\*? ([IVXLC]+)\.', h).group(1))
            if any(x['num'] == n for x in lectures):     # 重号：LXXI ×2（前一个实为 70）、CXVI ×2（后一个实为 117）
                n = 70 if n == 71 else lectures[-1]['num'] + 1
                if n == 70:                               # 前一个 LXXI 改 70，本讲才是 71
                    next(x for x in lectures if x['num'] == 71)['num'] = 70
                    n = 71
            md = render(r, lec)
            lectures.append(dict(num=n, head=h, verses=v, md=md,
                                 words=len(re.sub(r'<[^>]+>', ' ', md).split())))
    lectures.sort(key=lambda x: x['num'])
    for x in lectures:                          # 提要在定号之后再配（重号的讲在上面改过号）
        x['contents'] = contents.get(x['num'], [])
    nums = [x['num'] for x in lectures]
    assert nums == list(range(1, 153)), [n for i, n in enumerate(nums) if n != i + 1][:5]
    assert set(contents) == set(nums), set(nums) ^ set(contents)
    if tt.check({f'l{x["num"]}': x['md'] for x in lectures} | {f['slug']: f['md'] for f in front}):
        print('⚠️ 星号/ſ 检查未过')
    u = dict(tcp='A03343', front=front, parts=parts, lectures=lectures, gaps=r.gaps)
    (RAW / 'units.json').write_text(json.dumps(u, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    by = {}
    for x in lectures:
        by.setdefault(x['verses'], []).append(x['num'])
    print(f'hildersham: 卷首 {len(front)}，讲 {len(lectures)}，{sum(x["words"] for x in lectures)} 词；缺字 {r.gaps}')
    for v, ns in by.items():
        print(f'  {v}: 第 {ns[0]}–{ns[-1]} 讲（{len(ns)}）')


if __name__ == '__main__':
    main()
