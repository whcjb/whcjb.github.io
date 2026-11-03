#!/usr/bin/env python3
"""dickson_raw/matthew/src/A35949.xml（EEBO-TCP）→ en_chapters/*.md

    python3 scripts/extract_dickson.py            # 试跑，只报统计
    python3 scripts/extract_dickson.py --apply

大卫·迪克森《马太福音简释》London: for Ralph Smith 1651（第三版，Wing D1400）。
底本是 TCP 人工录入的 TEI，**不是 OCR**。缺字原样留记号，交给 dickson_common.py 按判读表回填。

录入本结构：<div type="chapter"> = 章，章下先是 <argument>（本章提要）与 <epigraph><q>（首节经文），
其后 <q>（一段经文，「Verse 18.」起头，几节连引时每节一个 <p n>）与 <p>（讲解）交替。
发布按 q 一页，页名 `<章>-<首节>`；节段 = 本段首节到下一段首节 − 1。
本章提要放进本章第一页。卷首两段总题解（「新约」之名、「马太福音」之名）合一页 `titles`。
第二十六章录入本 n="6"、章题印作 CHAP. VI.：章号按 div 顺序取，不信 n。
第五章 23 节后录入本缺两页（`〈MISSING:1〉`），发布时按 supplied/1.md 补录或标明缺页。
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
RAW = ROOT / 'dickson_raw' / 'matthew'
SRC = RAW / 'src' / 'A35949.xml'
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'dk'
# 马太福音各章节数（钦定本）
NV = dict(enumerate([25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34,
                     46, 46, 39, 51, 46, 75, 66, 20], 1))
RE_V = re.compile(r'^\W*(?:Vers(?:e|es)?|Ver|Ve)\.?\s*(\d+)', re.I)
FRONT = ['title', 'dedication', 'to-the-reader', 'titles']
# 经文头节号印错／录错（经文对钦定本可证）：正文照录不改，只按真节号取页名与节段。
# (章, 第几个经文段, 头上的号) → 真节号；未看影像，不定是印错还是录错（PROVENANCE 列明）。
VNUM_FIX = {(10, 11, 29): 19, (12, 6, 18): 8, (12, 7, 8): 9, (12, 20, 17): 27}


def verse_box(r, q):
    """一段经文：几节连引时录入本每节一个 <p>，各成一行。首行前的 <hi>Verse 46.</hi> 并入首行。"""
    ps = [c for c in q if tt.tag(c) == 'p']
    if not ps:
        return r.text(q)
    if (q.text or '').strip():
        raise ValueError('q 带散字又带 p')
    lines, pre = [], ''
    for c in q:
        k = tt.tag(c)
        if k == 'p':
            lines.append((pre + ' ' if pre else '') + r.text(c))
            pre = ''
        elif k == 'pb':
            lines.append(r.pb(c))
        elif k == 'hi' and not lines:
            pre = f'*{r.text(c)}*'
        else:
            raise ValueError(f'q 下未处理 <{k}>')
    out = []
    for x in lines:                       # 页码锚点挂进下一行
        if out and out[-1].endswith('</span>') and out[-1].startswith(f'<span class="{P}-pb"'):
            out[-1] += x
        else:
            out.append(x)
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    root = ET.parse(SRC).getroot()
    text = root.find(TEI + 'text')
    r = tt.R(P, '1651')
    files, order, sections = {}, [], []

    def put(slug, paras):
        md = tt.to_md(P, paras)
        if slug in files:
            files[slug] += '\n\n' + md
        else:
            files[slug] = md
            order.append(slug)

    front = {}
    for div in text.find(TEI + 'front'):
        paras = []
        tt.blocks(r, div, paras)
        front.setdefault({'title_page': 'title'}[div.get('type')], []).extend(paras)

    body = text.find(TEI + 'body')
    chapters = []
    for div in body:
        ty = div.get('type')
        if ty == 'dedication':
            paras = []
            for c in div:
                if tt.tag(c) == 'floatingText':
                    for b in c.find(TEI + 'body'):
                        tt.block(r, b, paras)
                else:
                    tt.block(r, c, paras)
            front['dedication'] = paras
        elif ty == 'to_the_reader':
            paras = []
            tt.blocks(r, div, paras)
            front['to-the-reader'] = paras
        elif ty == 'biblical_commentary':
            paras = []
            trailer = None
            for c in div:
                if tt.tag(c) == 'div':          # <div type="part">：书题解 + 二十八章
                    for x in c:
                        if tt.tag(x) == 'div':
                            chapters.append(x)
                        else:
                            tt.block(r, x, paras)
                elif tt.tag(c) == 'trailer':
                    trailer = c
                else:
                    tt.block(r, c, paras)
            front['titles'] = paras
        else:
            raise ValueError(f'正文未处理的 div {ty}')
    for slug in FRONT:
        put(slug, front[slug])

    if len(chapters) != 28:
        raise ValueError(f'章数 {len(chapters)}')
    bad = 0
    for ch, part in enumerate(chapters, 1):
        lead, cur, last = [], None, 0

        def open_section(q):
            nonlocal cur, last, lead, bad
            htxt = tt.text_of(q)
            m = RE_V.match(htxt)
            if not m:
                raise ValueError(f'{ch}: 经文头认不出 {htxt[:60]}')
            v = int(m.group(1))
            k = sum(1 for c, _ in sections if c == ch) + 1
            v = VNUM_FIX.get((ch, k, v), v)
            if v <= last or v > NV[ch]:
                print(f'⚠️ {ch}:{v} 节号不递增或越界（上一段 {last}）', file=sys.stderr)
                bad += 1
            last = v
            if cur:
                put(cur[0], cur[1])
            cur = (f'{ch}-{v}', lead + [('text', verse_box(r, q))])
            lead = []
            sections.append([ch, v])

        for x in part:
            k = tt.tag(x)
            if k == 'head':
                lead.append(('head', '## ' + r.text(x)))
            elif k == 'argument':
                for p in x:
                    if tt.tag(p) != 'p':
                        raise ValueError(f'argument 下 <{tt.tag(p)}>')
                    lead.append(('cls', f'{P}-argument', r.text(p)))
            elif k == 'epigraph':
                qs = [c for c in x if tt.tag(c) == 'q']
                if len(qs) != 1:
                    raise ValueError(f'{ch}: epigraph 下 q 数 {len(qs)}')
                open_section(qs[0])
            elif k == 'q':
                open_section(x)
            elif cur is None:
                tt.block(r, x, lead)
            else:
                tt.block(r, x, cur[1])
        if ch == 28 and trailer is not None:
            cur[1].append(('cls', f'{P}-closer', r.text(trailer)))
        put(cur[0], cur[1])

    secs = []
    for i, (ch, v) in enumerate(sections):
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        end = nxt[1] - 1 if nxt and nxt[0] == ch else NV[ch]
        secs.append(dict(slug=f'{ch}-{v}', ch=ch, v1=v, v2=end))

    bad += tt.check(files)
    print(f'篇 {len(files)}（经文段 {len(secs)}）  页码 {len(r.pages)}  缺字 {r.gaps}', file=sys.stderr)
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
