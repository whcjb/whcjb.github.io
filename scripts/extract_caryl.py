#!/usr/bin/env python3
"""卡里尔《约伯记释义》TCP 录入本 → caryl_raw/job/en_chapters/*.md + order.json

    python3 scripts/extract_caryl.py            # 试跑：列各段经节、查越界／缺节／重叠
    python3 scripts/extract_caryl.py --apply

Joseph Caryl, *An Exposition with Practical Observations upon … the Book of Job*，伦敦 1643–1666 分 12 部出版。
EEBO-TCP 只录了其中 8 部（CC0，src/ 入库），另 4 部（11–14、18–21、27–29、30–31 章）无录入本，待据影像 OCR 补。

| 部 | 章 | TCP | 年 | 结构 |
|---|---|---|---|---|
| 1 | 1–3 | A35389 | 1643 | part（每段一 div，n="Job 1.1,2"）|
| 2 | 4–7 | A35438 | 1656（再版）| chapter > verses/verse |
| 3 | 8–10 | A35439 | 1647 | chapter > verses > verse（外层带经文框即一段）|
| 5 | 15–17 | A35473 | 1650 | 每段一个 chapter div（同章重复）> verse |
| 7 | 22–26 | A81199 | 1655 | 同 5 |
| 10 | 32–34 | A35535 | 1661 | 同 5 |
| 11 | 35–37 | A35537 | 1664 | chapter > verses/verse |
| 12 | 38–42 | A35538 | 1666（TCP 编目误作 1653）| chapter > verse（n 写区间）|

一致的规则：**直接带 <epigraph> 的最外层 div 即一段**（≈一讲或连续几讲），一段一页 `<章>-<首节>`。
段的经节取段首经文框的出处行（「JOB, Chap. 22. Vers. 1, 2, 3, 4.」），比各家 div 的 n 可靠（n 有录错，如 23:2 作 30）。
段内各节的小经文框 → `.cy-vhead`，并在此处挂该节的 commentary-anchor（比全挂页首准）。
卷首（书名页、致读者、勘误、出版许可）各一页 `p<部>-<类>`；第 1 部正文前的全书总论一页 `p1-intro`。
卷末主题索引与经文索引暂不出。
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
RAW = ROOT / 'caryl_raw' / 'job'
OUT = RAW / 'en_chapters'
TEI = tt.TEI
P = 'cy'
# 约伯记各章节数（钦定本）
NV = dict(enumerate([22, 13, 26, 21, 27, 30, 21, 22, 35, 22, 20, 25, 28, 22, 35, 22, 16, 21, 29, 29, 34,
                     30, 17, 25, 6, 14, 23, 28, 25, 31, 40, 22, 33, 37, 16, 33, 24, 41, 30, 24, 34, 17], 1))
# 部次、TCP 号、所含章、印本年份（扉页所印；第 2 部是 1656 再版，第 12 部 TCP 编目误作 1653，扉页 1666）
PARTS = [
    (1, 'A35389', (1, 3), '1643'),
    (2, 'A35438', (4, 7), '1656'),
    (3, 'A35439', (8, 10), '1647'),
    (4, None, (11, 14), None),
    (5, 'A35473', (15, 17), '1650'),
    (6, None, (18, 21), None),
    (7, 'A81199', (22, 26), '1655'),
    (8, None, (27, 29), None),
    (9, None, (30, 31), None),
    (10, 'A35535', (32, 34), '1661'),
    (11, 'A35537', (35, 37), '1664'),
    (12, 'A35538', (38, 42), '1666'),
]
FRONT_KIND = {'title_page': ('title', 'Title Page', '书名页'),
              'license': ('license', 'Imprimatur', '出版许可'),
              'to_the_reader': ('reader', 'To the Christian Reader', '致读者'),
              'errata': ('errata', 'Errata', '勘误表')}
BACK_SKIP = {'index', 'subject_index', 'table', 'Scripture_index', 'publishers_note'}   # publishers_note：书商广告


def bibl_of(ep):
    b = ep.find(f'.//{TEI}bibl')
    return tt.text_of(b).replace('ſ', 's') if b is not None else ''


def parse_ref(s, ch_ctx):
    """「JOB, Chap. 22. Vers. 1, 2, 3, 4.」「IOB 1.1, 2.」「JOB 8.1, 2, 3.」→ (章, [节…])"""
    s = re.sub(r'&c\.?', '', s)
    m = re.search(r'C(?:h)?ap\.?\s*(\d+)[.,]?\s*(?:Vers?\.?)?\s*(.*)', s, re.I)
    if m:
        ch, rest = int(m.group(1)), m.group(2)
    else:
        m = re.search(r'[IJ]OB\.?,?\s*(\d+)\s*[.,:]\s*(.*)', s, re.I)
        if not m:
            raise ValueError(f'出处行认不出：{s!r}')
        ch, rest = int(m.group(1)), m.group(2)
    vs = [int(x) for x in re.findall(r'\d+', rest)]
    if '-' in rest or '–' in rest:
        a, b = vs[0], vs[-1]
        vs = list(range(a, b + 1))
    if ch_ctx and ch != ch_ctx:
        raise ValueError(f'出处行章号 {ch} 与所在 chapter div {ch_ctx} 不合：{s!r}')
    return ch, sorted(set(vs))


def verse_box(r, q):
    """段首经文：出处行作小标签，其余每个 <p> 一行。"""
    label, lines, loose = '', [], []
    for c in q:
        k = tt.tag(c)
        if k == 'bibl' and not label and not lines:
            label = r.text(c)
            loose_tail = (c.tail or '').strip()
            if loose_tail:
                loose.append(c)
        elif k == 'p':
            lines.append(r.text(c))
        elif k == 'pb':
            x = r.pb(c)
            if x:
                lines.append(x)
        elif k in ('hi', 'note', 'g', 'gap', 'seg', 'lb', 'bibl'):
            loose.append(c)
        elif k == 'l':
            lines.append(r.text(c))
        else:
            raise ValueError(f'经文框 q 下未处理 <{k}>')
    if loose or (q.text or '').strip():
        # 出处行后直接接经文（不分 <p>）：把 bibl 之后的整段当一行
        b = q.find(TEI + 'bibl')
        tmp = ET.Element(TEI + 'q')
        tmp.text = (b.tail if b is not None else q.text) or ''
        started = b is None
        for c in q:
            if c is b:
                started = True
                continue
            if started and tt.tag(c) != 'p':
                tmp.append(c)
        txt = r.text(tmp)
        if txt:
            lines.insert(0, txt)
    out = []
    if label:
        out.append(f'{label}\n{{: .{P}-vlabel}}')       # kramdown IAL：页码锚点挂到本行前也不破 HTML
    out += [x for x in lines if x]
    return '\n\n'.join(out)


def vhead(r, ep):
    """段内各节的小经文框（「V. 2. Can a man be profitable unto God?」）→ 一行。"""
    qs = [c for c in ep if tt.tag(c) == 'q']
    if not qs:
        return r.text(ep)
    return ' '.join(r.text(q) for q in qs)


def anchor(ch, v):
    return f'<div class="commentary-anchor" id="job-{ch}-{v}"></div>'


def render_section(r, d, ch, paras, top=True):
    """一段（或段内一节）的子元素 → 段落元组。"""
    for c in d:
        k = tt.tag(c)
        if k == 'epigraph':
            q = c.find(TEI + 'q')
            if top:
                paras.append(('text', verse_box(r, q if q is not None else c)))
            else:
                paras.append(('cls', f'{P}-vhead', vhead(r, c)))
            top = False
        elif k == 'div':
            ns = [int(x) for x in re.findall(r'\d+', c.get('n') or '')]
            if c.get('type') in ('verse', 'verses') and ns and c.find(TEI + 'epigraph') is not None:
                ep = c.find(TEI + 'epigraph')
                b = bibl_of(ep)
                vs = [int(x) for x in re.findall(r'\d+', b)] or ns
                v = vs[0] if 0 < vs[0] <= NV[ch] else ns[0]
                paras.append(('raw', anchor(ch, v)))
            elif c.get('type') in ('verse', 'verses') and ns:
                paras.append(('raw', anchor(ch, ns[0])))
            render_section(r, c, ch, paras, top=False)
        elif k == 'trailer':
            paras.append(('cls', f'{P}-closer', r.text(c)))
        else:
            tt.block(r, c, paras, 3)


def front_div(r, d):
    paras = []
    tt.blocks(r, d, paras)
    return tt.to_md(P, paras)


def extract_part(part, tcp, chs, year, files, order_front, sections, warn):
    root = ET.parse(RAW / 'src' / f'{tcp}.xml').getroot()
    for el in root.iter():                  # 原书字面星号不当斜体
        for a in ('text', 'tail'):
            v = getattr(el, a)
            if v and '*' in v:
                setattr(el, a, v.replace('*', '&#42;'))
    r = tt.R(P, year)
    text = root.find(f'.//{TEI}text')
    for d in text.find(TEI + 'front'):
        if d.tag != TEI + 'div':
            continue
        kind, title, cn = FRONT_KIND[d.get('type')]
        slug = f'p{part}-{kind}'
        files[slug] = front_div(r, d)
        order_front.append(dict(slug=slug, part=part, title=title, cn=cn))
    back = text.find(TEI + 'back')
    if back is not None:
        for d in back:
            if d.tag == TEI + 'div' and d.get('type') in FRONT_KIND:     # 第 3 部勘误印在卷末
                kind, title, cn = FRONT_KIND[d.get('type')]
                files[f'p{part}-{kind}'] = front_div(r, d)
                order_front.append(dict(slug=f'p{part}-{kind}', part=part, title=title, cn=cn))
            elif d.tag == TEI + 'div' and d.get('type') not in BACK_SKIP:
                raise ValueError(f'{tcp}: 未处理的卷末 div {d.get("type")}')
    tops = [d for d in text.find(TEI + 'body') if d.tag == TEI + 'div']
    assert len(tops) == 1, tcp
    top = tops[0]

    intro, trailer = [], None
    secs = []

    def walk(d, ch):
        for c in d:
            if c.tag != TEI + 'div':
                if d is top:
                    if tt.tag(c) == 'trailer':
                        nonlocal trailer
                        trailer = c
                    else:
                        tt.block(r, c, intro, 2)
                continue
            cch = int(c.get('n')) if c.get('type') == 'chapter' else ch
            ep = c.find(TEI + 'epigraph')
            if ep is not None:
                ref = bibl_of(ep)
                if not ref and c.get('type') == 'part':
                    ref = c.get('n')
                rch, vs = parse_ref(ref, cch)
                if not vs:              # 出处行没印节号（「JOB Chap. 4. Verse」）：取 div 的 n
                    vs = parse_ref(f'JOB {rch}.{c.get("n")}', None)[1]
                    warn.append(f'第 {part} 部 {ref!r} 无节号，按 div n={c.get("n")} → {vs}')
                elif secs and secs[-1]['ch'] == rch and secs[-1]['vs'] == vs:
                    # 出处行照抄了上一段（第 2 部 4:12–13 印作「Vers. 9, 10, 11」，框内经文是 12–13 节）：取 div 的 n
                    vs = parse_ref(f'JOB {rch}.{c.get("n")}', None)[1]
                    warn.append(f'第 {part} 部 {ref!r} 与上一段重号，按 div n={c.get("n")} → {vs}')
                secs.append(dict(div=c, ch=rch, vs=vs, ref=ref))
            else:
                walk(c, cch)
    walk(top, None)

    if intro:
        # 第 1 部正文前的全书总论；别部只有一行总题（不出页，只核对）
        md = tt.to_md(P, intro)
        words = len(re.sub(r'<[^>]+>', ' ', md).split())
        if words > 200:
            slug = f'p{part}-intro'
            files[slug] = md
            order_front.append(dict(slug=slug, part=part, title='The Preface to the Exposition', cn='全书引论'))
        else:
            warn.append(f'第 {part} 部总题（未出页）：{re.sub(r"<[^>]+>", "", md)[:100]}')

    for i, s in enumerate(secs):
        ch, vs = s['ch'], s['vs']
        if not (chs[0] <= ch <= chs[1]) or not vs or vs[0] < 1 or vs[-1] > NV[ch]:
            raise ValueError(f'{tcp}: 段越界 {s["ref"]!r} → {ch}:{vs}')
        paras = []
        render_section(r, s['div'], ch, paras)
        if i + 1 == len(secs) and trailer is not None:
            paras.append(('cls', f'{P}-closer', r.text(trailer)))
        slug = f'{ch}-{vs[0]}'
        if slug in files:
            raise ValueError(f'页名重复 {slug}')
        files[slug] = to_md(paras)
        sections.append(dict(slug=slug, part=part, ch=ch, v1=vs[0], v2=vs[-1], ref=s['ref']))
    return r


def to_md(paras):
    out, buf = [], []
    for p in paras:
        if p[0] == 'raw':
            if buf:
                out.append(tt.to_md(P, buf))
                buf = []
            out.append(p[1])
        else:
            buf.append(p)
    if buf:
        out.append(tt.to_md(P, buf))
    return '\n\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    files, front, sections, warn = {}, [], [], []
    gaps, pages = {}, {}
    for part, tcp, chs, year in PARTS:
        if not tcp:
            continue
        r = extract_part(part, tcp, chs, year, files, front, sections, warn)
        for k, v in r.gaps.items():
            gaps[k] = gaps.get(k, 0) + v
        pages[part] = r.pages
    # 覆盖检查：各章逐节，标出无段覆盖的节与重叠
    bad = 0
    by = {}
    for s in sections:
        by.setdefault(s['ch'], []).append(s)
    for ch, ss in sorted(by.items()):
        # 出处行只引了头几节、讲解其实一路讲到下一段之前（1:13 段讲到 1:22，3:14 段讲到 19 节……，正文里有
        # 「Verse 20.」之类小标题为证）：段尾延到下一段首节之前，本章末段延到章末
        for i, s in enumerate(ss):
            end = ss[i + 1]['v1'] - 1 if i + 1 < len(ss) else NV[ch]
            if end > s['v2']:
                warn.append(f'{s["slug"]}：出处行止于 {s["v2"]} 节，延到 {end} 节')
                s['v2'] = end
        seen = {}
        for s in ss:
            for v in range(s['v1'], s['v2'] + 1):
                seen.setdefault(v, []).append(s['slug'])
        miss = [v for v in range(1, NV[ch] + 1) if v not in seen]
        dup = {v: x for v, x in seen.items() if len(x) > 1}
        if miss:
            warn.append(f'{ch} 章：无段标出的节 {miss}')
        if dup:
            warn.append(f'{ch} 章：两段都标的节 {dup}')
    # 锚点：每节一个，优先段内小经文框处；段内没有的，由发布脚本补在段首
    for s in sections:
        s['anchored'] = sorted(int(v) for v in re.findall(rf'id="job-{s["ch"]}-(\d+)"', files[s['slug']]))
    bad += tt.check(files)
    for w in warn:
        print('·', w, file=sys.stderr)
    print(f'卷首 {len(front)} 页，段 {len(sections)}（{len(by)} 章），缺字 {gaps}', file=sys.stderr)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for f in OUT.glob('*.md'):
            f.unlink()
        for k, md in files.items():
            (OUT / f'{k}.md').write_text(md.strip() + '\n', encoding='utf-8')
        (RAW / 'order.json').write_text(json.dumps(dict(front=front, sections=sections, gaps=gaps,
                                                        parts=[dict(part=p, tcp=t, chs=c, year=y) for p, t, c, y in PARTS]),
                                                   ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (RAW / 'pages.json').write_text(json.dumps(pages) + '\n', encoding='utf-8')
        print(f'写入 {len(files)} 篇 → {OUT}', file=sys.stderr)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
