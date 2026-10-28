#!/usr/bin/env python3
"""barlow_raw/2timothy/src/A04220.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_barlow.py            # 试跑，只报统计
    python3 scripts/extract_barlow.py --apply

约翰·巴洛《提摩太后书第一章讲解》London: I. D[awson] for Iohn Bellamie 1625（STC 1434；录入本扉页年份误录作 1624，原图为 1625）。
底本是 TCP 人工录入的 TEI，**不是 OCR**。缺字原样留记号，交给 barlow_common.py 按判读表回填。

录入本 body 是一个 <div type="tract">：总标题 + 全章导论（Analysis）若干段 + 18 个 <div type="verse">。
一节一页，页名 `1-<节>`；导论单独一页 `introduction`。每节讲解按原书分「The Logicall resolution」
「The Theologicall exposition」「Doctrines」，这些标题在原书是页边旁注，照录为旁注。

录入所据的胶片漏拍了 16 处、每处 2 页（TCP 标 <gap reason="missing" extent="2 pages">）；
1625 本 IA 胶片扫描（bim）上这些页在，抽取时先留 `〈MISSING:N〉`，由 barlow_missing.py 按影像补录。
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
RAW = ROOT / 'barlow_raw' / '2timothy'
SRC = RAW / 'src' / 'A04220.xml'
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'bl'
NV = {1: 18}
FRONT = {'title_page': 'title', 'dedication': 'dedication', 'to_the_reader': 'to-the-reader',
         'table_of_contents': 'contents'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    text = root.find(TEI + 'text')
    r = tt.R(P, '1625')
    files, order, sections = {}, [], []

    def put(slug, paras):
        md = tt.to_md(P, paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    for div in text.find(TEI + 'front'):
        paras = []
        tt.blocks(r, div, paras)
        put(FRONT[div.get('type')], paras)

    tract = text.find(TEI + 'body')[0]
    intro, carry = [], []
    for x in tract:
        if tt.tag(x) == 'div' and x.get('type') == 'verse':
            v = int(x.get('n'))
            paras = carry
            carry = []
            for c in x:
                if tt.tag(c) == 'head':
                    paras.append(('text', r.text(c)))
                else:
                    tt.block(r, c, paras)
            # 节末的页码锚点挪到下一节开头（下一页从那里起）
            while paras and paras[-1][0] == 'pb':
                carry.insert(0, paras.pop())
            put(f'1-{v}', paras)
            sections.append([1, v])
        elif not sections:
            if tt.tag(x) == 'head':
                intro.append(('head', '## ' + r.text(x)))
            else:
                tt.block(r, x, intro)
        else:                              # 章末 FINIS.
            tt.block(r, x, carry)
    if carry:
        put(f'1-{sections[-1][1]}', carry)
    files_intro = intro
    order.insert(len(FRONT), 'introduction')
    files['introduction'] = tt.to_md(P, files_intro)

    for div in text.find(TEI + 'back'):  # 书末只有一行「Laus Deo. Amen.」：挂在第 18 节末
        paras = []
        tt.blocks(r, div, paras)
        put(f'1-{sections[-1][1]}', paras)

    secs = [dict(slug=f'1-{v}', ch=1, v1=v, v2=v) for _, v in sections]
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
