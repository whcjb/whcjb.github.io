#!/usr/bin/env python3
"""hall_raw/2timothy/src/A45335.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_hall.py            # 试跑，只报统计
    python3 scripts/extract_hall.py --apply

托马斯·霍尔《提摩太后书第三、四章注释》London: E. Tyler for John Starkey 1658（Wing H436）。
底本是 TCP 人工录入的 TEI，**不是 OCR**。缺字原样留记号，交给 hall_common.py 按判读表回填。

录入本的 div 已经按原书分好：<div type="part"> = 章，<div type="subpart"> = 一段经文（「VERSE 2.」起头），
其下 section / subsection 是逐语解说的小标题。发布按 subpart 一页，页名 `<章>-<首节>`；
节段 = 本段首节到下一段首节 − 1。第三章第 8 节后插了一篇加尔文《驳放纵派》第七章的译文，
单独一页 `3-8-calvin`；全书末 POST-SCRIPT 单独一页。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_tei as tt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hall_raw' / '2timothy'
SRC = RAW / 'src' / 'A45335.xml'
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'hl'
NV = {3: 17, 4: 22}
RE_V = re.compile(r'^\W*(?:2 TIM\. *\d+\.|VERS(?:E|ES)?\.?)\s*(\d+)', re.I)

FRONT = ['title', 'epistle-to-reader', 'dedication', 'to-the-reader', 'to-the-reader-2', 'books', 'errata']
FRONT_TYPE = {'title_page': 'title', 'dedication': 'dedication', 'list': 'books', 'errata': 'errata'}
BACK = {'table_of_contents': None, 'table': 'texts', 'list_of_books': 'starkey'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    text = root.find(TEI + 'text')
    r = tt.R(P, '1658')
    files, order, sections = {}, [], []

    def put(slug, paras):
        md = tt.to_md(P, paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    def simple(slug, div):
        paras = []
        tt.blocks(r, div, paras)
        put(slug, paras)

    reader = 0
    front = {}
    for div in text.find(TEI + 'front'):
        ty = div.get('type')
        if ty == 'illustration':          # 卷首肖像：只有图注
            paras = []
            tt.blocks(r, div, paras)
            front.setdefault('title', []).extend(paras)
            continue
        if ty == 'to_the_reader':
            slug = ['epistle-to-reader', 'to-the-reader', 'to-the-reader-2'][reader]
            reader += 1
        else:
            slug = FRONT_TYPE[ty]
        paras = []
        tt.blocks(r, div, paras)
        front.setdefault(slug, []).extend(paras)
    for slug in FRONT:
        put(slug, front[slug])

    body = text.find(TEI + 'body')
    parts = [d for d in body if tt.tag(d) == 'div']
    for ch, part in zip((3, 4, None), parts):
        if ch is None:                     # POST-SCRIPT
            simple('postscript', part)
            continue
        lead = []
        for x in part:
            if tt.tag(x) == 'div' and x.get('type') == 'subpart':
                h = x.find(TEI + 'head')
                htxt = tt.text_of(h)
                m = RE_V.match(htxt)
                paras = lead
                lead = []
                if not m:                  # 加尔文《驳放纵派》第七章译文
                    slug = f'{ch}-{sections[-1][1]}-calvin'
                    tt.blocks(r, x, paras)
                    put(slug, paras)
                    continue
                v = int(m.group(1))
                slug = f'{ch}-{v}'
                if slug in files:
                    raise ValueError(f'页名重复 {slug}')
                for c in x:
                    if c is h:
                        paras.append(('text', r.text(h)))
                    else:
                        tt.block(r, c, paras)
                put(slug, paras)
                sections.append([ch, v])
            elif tt.tag(x) == 'head':
                lead.append(('head', '## ' + r.text(x)))
            else:
                tt.block(r, x, lead)
        if lead:                           # 章末「The end of the Third Chapter.」挂在本章末页
            put(f'{ch}-{sections[-1][1]}', lead)

    for div in text.find(TEI + 'back'):
        ty = div.get('type')
        if ty == 'table_of_contents':
            slug = 'questions' if 'QUESTIONS' in tt.text_of(div.find(TEI + 'head')) else 'subject-index'   # 不能叫 index：会盖掉书首页（memory feedback_slug_index_collision）
        else:
            slug = BACK[ty]
        simple(slug, div)

    secs = []
    for i, (ch, v) in enumerate(sections):
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        end = nxt[1] - 1 if nxt and nxt[0] == ch else NV[ch]
        secs.append(dict(slug=f'{ch}-{v}', ch=ch, v1=v, v2=end))

    bad = tt.check(files)
    print('  ' + ' '.join(f'{k}({len(files[k]) // 1000}k)' for k in order), file=sys.stderr)
    print(f'页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(r.pages) + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps({'order': order, 'sections': secs}, indent=1) + '\n',
                                        encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
