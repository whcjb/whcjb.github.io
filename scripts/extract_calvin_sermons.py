#!/usr/bin/env python3
"""加尔文讲章（戈尔丁英译）TCP 录入本 → calvin_sermons_raw/<书>/units.json

    python3 scripts/extract_calvin_sermons.py job
    python3 scripts/extract_calvin_sermons.py deuteronomy

底本（均 EEBO-TCP Phase I，CC0 1.0）：
  job          A69056  Sermons of Master Iohn Caluin, vpon the booke of Iob（London 1574，STC 4445）
  deuteronomy  A17698  The Sermons of M. Iohn Caluin vpon the fifth booke of Moses called Deuteronomie（London 1583，STC 4442）

行内/块级渲染复用 tcp_tei（ſ→s、斜体、页码锚点、缺字记号 •／〈◊〉／〈…〉／〈MISSING:N〉），拼法照录原书。
一篇讲章一页；卷首（书名页、献辞、致读者、祷文）各一页；卷末索引暂不出。

申命记：录入所据胶片缺页 28 处（<gap reason="missing" extent="2 pages">）。其中 9 处缺页跨在两篇交界上，
后一篇的标题随之丢失，TCP 便把两篇录成一个 div——**不按猜测拆开**，照 TCP 原样一页，书首页目录把丢了开头的
那篇列出来、指向所并入的页。另有两处 div 编号与原书篇次不合：n 缺省的那篇标题作「threescore」（第 60 篇）；
第二个 n="70" 的标题印作 Lxx，按日期与「第十章第五篇」实为第 73 篇（原书印错，照录标题）。
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_tei as tt                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEI = tt.TEI
BOOKS = {
    'job': dict(tcp='A69056', P='cs', edition='1574', total=159),
    'deuteronomy': dict(tcp='A17698', P='cs', edition='1583', total=200),
}
ORD = {'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fourth': 4, 'fift': 5, 'fifth': 5, 'sixt': 6, 'sixth': 6,
       'seuenth': 7, 'eight': 8, 'eighth': 8, 'ninth': 9, 'tenth': 10, 'eleuenth': 11, 'twelfth': 12,
       'thirteenth': 13, 'thirtenth': 13, 'fourteenth': 14, 'fourtenth': 14, 'foureteenth': 14, 'fifteenth': 15,
       'fiftenth': 15, 'sixteenth': 16, 'sixeteenth': 16, 'seuenteenth': 17, 'eighteenth': 18, 'nineteenth': 19,
       'twentith': 20, 'thirtith': 30}
UNITS = {'one': 1, 'two': 2, 'three': 3, 'foure': 4, 'fiue': 5, 'sixe': 6, 'seuen': 7, 'eight': 8, 'nine': 9}
ROMAN = {'i': 1, 'j': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}
# 标题章号印错：约伯记第 124 篇印「.xxxiiij.」，前后均为 33 章、本篇是「第 33 章第三篇」（经文框为 33:14–17）
CH_FIX = {('job', 124): 33}
# 申命记 TCP div 编号 → 原书篇次的更正（见文件头说明）
DEUT_FIX = {'60:None': 60, '73:70': 73}


def roman(s):
    s = s.lower().strip('. ')
    v = [ROMAN[c] for c in s if c in ROMAN]
    return sum(-a if i + 1 < len(v) and v[i + 1] > a else a for i, a in enumerate(v)) if v and len(v) == len(s) else None


def chapter_of(head):
    h = head.lower().replace('▪', ' ')
    m = re.search(r'(?:vp+on|of) the\s+(.{1,30}?)\s*chap', h)
    if not m:
        return None
    w = m.group(1).strip()
    r = roman(w.strip('.'))
    if r:
        return r
    m2 = re.match(r'(\w+) (?:and|&) (twentith|thirtith)$', w)
    if m2 and m2.group(1) in UNITS:
        return UNITS[m2.group(1)] + ORD[m2.group(2)]
    return ORD.get(w)


def chapter2_of(head):
    """跨章的篇：「…the fourth vpon the fourth Chapter, and the firste vpon the fift Chapter」→ 后一章。"""
    m = re.search(r'and the firs?te? vp+on (the .{1,30}?chap)', head.lower().replace('▪', ' '))
    return chapter_of('of ' + m.group(1)) if m else None


def verses_of(epi):
    """epigraph 里的节号（行首数字）→ (首节, 末节)。"""
    ns = [int(x) for x in re.findall(r'(?:^|[\s.:;,)])(\d{1,3})(?=\.?\s+[A-Z&])', ' ' + epi)]
    ns = [n for n in ns if n < 60]
    return (ns[0], ns[-1]) if ns else (None, None)


def render(r, e, P):
    """一个 div → 段落元组。epigraph（所讲经文）出成经文框。"""
    out = []
    for c in e:
        t = tt.tag(c)
        if t == 'epigraph':
            inner = []
            tt.blocks(r, c, inner)
            txt = ' '.join(x[1] if x[0] != 'cls' else x[2] for x in inner if x[0] in ('p', 'cls'))
            pbs = [x for x in inner if x[0] == 'pb']
            out.extend(pbs)
            out.append(('text', txt))
        elif t == 'head':
            txt = r.text(c)
            if txt:
                out.append(('cls', f'{P}-head', txt))
        elif t == 'argument':                       # 篇首提要
            inner = []
            tt.blocks(r, c, inner)
            for x in inner:
                out.append(('cls', f'{P}-argument', x[1] if x[0] != 'cls' else x[2]) if x[0] in ('p', 'cls') else x)
        elif t == 'div':                            # 篇内小节（申命记附带的执事讲章等）：同样认 epigraph
            out.extend(render(r, c, P))
        else:
            tt.block(r, c, out, 3)
    return out


def missing_note(md, P):
    return re.sub(r'\s*〈MISSING:\d+〉\s*',
                  f'\n\n<p class="{P}-lost">[Two pages are wanting here in the copy from which the keyed text was made '
                  f'(原书此处缺两页：录入所据的胶片本缺页)]</p>\n\n', md)


def main():
    book = sys.argv[1]
    cfg = BOOKS[book]
    RAW = ROOT / 'calvin_sermons_raw' / book
    root = ET.parse(RAW / 'src' / f'{cfg["tcp"]}.xml').getroot()
    for el in root.iter():                 # 原书印的星号（旁注标记，如约伯记第 131 篇 19 节前）是字面，不是斜体
        if el.text and '*' in el.text:
            el.text = el.text.replace('*', '&#42;')
        if el.tail and '*' in el.tail:
            el.tail = el.tail.replace('*', '&#42;')
    P = cfg['P']
    r = tt.R(P, cfg['edition'])
    body = root.find(f'.//{TEI}text')
    front, sermons = [], []

    def add_front(slug, title, e):
        md = tt.to_md(P, render(r, e, P))
        front.append(dict(slug=slug, title=title, md=missing_note(md, P)))

    seen70 = 0
    for top in body.iter(TEI + 'div'):
        pass
    for part in (body.find(TEI + 'front'), body.find(TEI + 'body'), body.find(TEI + 'back')):
        if part is None:
            continue
        for d in part:
            if d.tag != TEI + 'div':
                continue
            ty = d.get('type')
            if ty == 'title_page':
                add_front('title', 'Title Page', d)
            elif ty == 'dedication':
                add_front('dedication', 'The Epistle Dedicatory', d)
            elif ty == 'to_the_reader':
                k = sum(1 for f in front if f['slug'].startswith('to-the-reader')) + 1
                add_front(f'to-the-reader-{k}' if book == 'deuteronomy' else 'to-the-reader', 'To the Reader', d)
            elif ty == 'sermons':
                kids = [x for x in d if x.tag == TEI + 'div']
                flat = []
                for x in kids:          # 约伯记：sermons > chapter > sermon（+ 卷末两篇祷文）
                    if x.get('type') == 'chapter' and any(y.get('type') == 'sermon' for y in x if y.tag == TEI + 'div'):
                        flat += [y for y in x if y.tag == TEI + 'div']
                    else:
                        flat.append(x)
                for x in flat:
                    xt = x.get('type')
                    if xt == 'prayer':
                        h = x.find(TEI + 'head')
                        ht = tt.text_of(h) if h is not None else ''
                        slug = 'prayer-before' if 'before' in ht else 'prayer-after'
                        add_front(slug, 'The Prayer before the Sermon' if slug == 'prayer-before'
                                  else 'The Prayer after the Sermon', x)
                        continue
                    if xt not in ('sermon', 'chapter'):
                        raise ValueError(f'sermons 下未处理 div type={xt}')
                    h = x.find(TEI + 'head')
                    head = tt.text_of(h).replace('ſ', 's') if h is not None else ''
                    n = x.get('n')
                    if book == 'deuteronomy':
                        if n is None:
                            num = DEUT_FIX['60:None']
                        elif n == '70':
                            seen70 += 1
                            num = 70 if seen70 == 1 else DEUT_FIX['73:70']
                        else:
                            num = int(n)
                    else:
                        # 约伯记 159 篇齐全、按原书顺序排；TCP 的 n 有录错（第 11 篇作 13、第 110 篇作 10），
                        # 原书标题也有印错的（第 78 篇印 lxxvij、第 112 篇印 Cij），篇次一律按顺序数
                        num = sum(1 for z in sermons) + 1
                    epi = x.find(TEI + 'epigraph')
                    epitxt = tt.text_of(epi) if epi is not None else ''
                    md = missing_note(tt.to_md(P, render(r, x, P)), P)
                    sermons.append(dict(num=num, head=head, chapter=CH_FIX.get((book, num)) or chapter_of(head),
                                        chapter2=chapter2_of(head), verses=verses_of(epitxt),
                                        lost=md.count(f'{P}-lost'), words=len(re.sub(r'<[^>]+>', ' ', md).split()),
                                        md=md))
            elif ty in ('Scripture_index', 'subject_index', 'table_of_contents', 'table_of_biblical_references',
                        'colophon'):
                continue                                            # 索引、目录、版权页暂不出
            else:
                raise ValueError(f'未处理的顶层 div type={ty}')
    # 章号缺的（标题里没写章）沿用前一篇；没有经文框的（提要作「本篇仍讲上一篇的经文」）节号也沿用前一篇
    last, lastv = None, (None, None)
    for s in sermons:
        if s['chapter'] is None:
            s['chapter'] = last
        if s['verses'][0] is None:
            s['verses'] = lastv
            s['same_text'] = True
        last, lastv = s['chapter'], s['verses']
    nums = [s['num'] for s in sermons]
    assert len(nums) == len(set(nums)), [x for x in nums if nums.count(x) > 1]
    absent = sorted(set(range(1, cfg['total'] + 1)) - set(nums))
    # 丢了开头、并入前一篇的：挂到编号比它小的最近一篇（该页必有缺页标记）
    merged = {}
    for a in absent:
        host = max((s for s in sermons if s['num'] < a), key=lambda s: s['num'])
        assert host['lost'], (a, host['num'])
        merged[a] = host['num']
        host.setdefault('absorbs', []).append(a)
    if tt.check({f"{book}/{s['num']}": s['md'] for s in sermons} | {f"{book}/{f['slug']}": f['md'] for f in front}):
        print('⚠️ 星号/ſ 检查未过')
    units = dict(book=book, tcp=cfg['tcp'], front=front, sermons=sermons, merged=merged, gaps=r.gaps)
    (RAW / 'units.json').write_text(json.dumps(units, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{book}: 卷首 {len(front)} 篇（{", ".join(f["slug"] for f in front)}）；讲章 {len(sermons)} 页，'
          f'对应 {len(sermons) + len(merged)} / {cfg["total"]} 篇；并入他页的 {merged}')
    print('  缺字统计', r.gaps, '| 缺页标记', sum(s['lost'] for s in sermons))
    nochap = [s['num'] for s in sermons if s['chapter'] is None]
    nov = [s['num'] for s in sermons if s['verses'][0] is None]
    print('  无章号', nochap, '| 无节号', nov)


if __name__ == '__main__':
    main()
