#!/usr/bin/env python3
"""jenkyn_raw/jude/en_chapters/*.md（+ 判读表，见 jenkyn_common.py）→ jenkyn/jude/*.md

    python3 scripts/publish_jenkyn_en.py            # 试跑
    python3 scripts/publish_jenkyn_en.py --apply

骨架照搬 publish_adams_en.py。原书逐节讲解，一节一页，页名 `1-<首节>`（犹大书只一章；
14–15、17–19、22–23、24–25 合讲各一页）；第 8 节两部分各讲一段，第二部分那段页名 `1-8-ii`。
一节超过 LIMIT 字符时在段落之间切页（优先在原书小标题前），续页 `<页名>-<k>`。
卷首 title1 / to-the-reader / errata1 / advertisement；第二部分 title2 / dedication 排在 8-ii 前；书末 errata2。
章目录页 `1.md`（对照抽屉的 __CH__ 指向它）。

date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jenkyn_common as jc  # noqa: E402
from extract_jenkyn import NV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = jc.RAW
OUT = ROOT / 'jenkyn' / 'jude'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'
MANUAL = RAW / 'manual_pages'

BOOK_ID = 'jude'
BOOK_NAME = 'Jenkyn on Jude'
AUTHOR = 'William Jenkyn'

FRONT1 = [('title1', 'Title Page (Part I)', 'London, 1652'),
          ('to-the-reader', 'To the Reader', 'To the Inhabitants in the Parish of Christ-Church, London'),
          ('errata1', 'Errata (Part I)', ''),
          ('advertisement', "The Publisher to the Reader", '')]
FRONT2 = [('title2', 'Title Page (Part II)', 'London, 1654'),
          ('dedication', 'Epistle Dedicatory (Part II)', 'To the Church of God in the Precinct of Black-Friars, London')]
TAIL = [('errata2', 'Errata (Part II)', '')]


def load_page(slug):
    """扉页等排版性页面：有照原书影像手排的 HTML（manual_pages/<slug>.html）就用它。"""
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else jc.load(slug)


def vref(a, b):
    return f'Jude {a}' if a == b else f'Jude {a}–{b}'


def build_pages():
    meta = json.loads((RAW / 'order.json').read_text())
    order, ranges = meta['order'], meta['ranges']
    pages = []
    for slug, title, sub in FRONT1:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(slug), group='front1'))
    for src in order:
        if src not in ranges:
            continue
        a, b, part = ranges[src]
        if src == '8-ii':
            for s2, t2, sub2 in FRONT2:
                pages.append(dict(slug=s2, title=t2, subtitle=sub2, body=load_page(s2), group='front2'))
        base = f'1-{src}'
        label = vref(a, b) + (' (Part II)' if src == '8-ii' else '')
        parts = split_long(jc.load(src))
        for k, body in enumerate(parts, 1):
            pg = dict(slug=base if k == 1 else f'{base}-{k}',
                      title=label + (f' (part {k} of {len(parts)})' if len(parts) > 1 else ''),
                      subtitle=AUTHOR, body=body, group=f'part{part}', ch=1, v1=a, v2=b, part=part,
                      src=src)
            if k > 1:
                pg['cont'] = True
            pages.append(pg)
    for slug, title, sub in TAIL:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=jc.load(slug), group='tail'))
    return pages


LIMIT = 120_000


def split_long(body):
    """一节的讲解太长：切成几页，每页约 LIMIT 字符。切点优先取原书小标题（###）前；不在 <div> 块里切。"""
    if len(body) <= LIMIT:
        return [body]
    chunks = body.split('\n\n')
    blocks, cur, depth = [], [], 0
    for c in chunks:
        cur.append(c)
        depth += c.count('<div') - c.count('</div>')
        if depth == 0:
            blocks.append('\n\n'.join(cur))
            cur = []
    if cur:
        blocks.append('\n\n'.join(cur))
    n_parts = -(-len(body) // LIMIT)
    target = len(body) / n_parts
    parts, buf, size = [], [], 0
    for blk in blocks:
        heading = blk.startswith('### ')
        if buf and (size >= target or (heading and size >= target * 0.7)) and len(parts) < n_parts - 1:
            parts.append('\n\n'.join(buf))
            buf, size = [], 0
        buf.append(blk)
        size += len(blk) + 2
    parts.append('\n\n'.join(buf))
    return parts


def add_anchors(body, pg):
    """经文框后面每节一个 commentary-anchor（07-verse-index §1）。第 8 节第二部分那页不再挂（锚点只挂第一次讲解）。"""
    if 'ch' not in pg or pg.get('cont') or pg['src'] == '8-ii':
        return body
    anchors = ''.join(f'\n\n<div class="commentary-anchor" id="jude-1-{v}"></div>'
                      for v in range(pg['v1'], pg['v2'] + 1))
    # 经文框可能连排两节（VER. 1 / VER. 2 两个框），锚点挂在最后一个连续框之后
    m = None
    for x in re.finditer(r'<div class="jk-text" markdown="1">.*?\n\n</div>', body, re.S):
        if m is None or body[m.end():x.start()].strip() == '':
            m = x
        else:
            break
    if not m:
        return anchors.strip() + '\n\n' + body
    return body[:m.end()] + anchors + body[m.end():]


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = 'Editorial conjecture: illegible in the source; supplied from the stated evidence (编者推补；非原书原文)'
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, pg):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(body, pg)
    body = RE_CONJ.sub(lambda m: f'<span class="jk-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = jc.TOK.sub(lambda m: f'<span class="jk-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/jenkyn/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o["title"]}"']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    pages = build_pages()
    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        slug = pg['slug']
        meta.setdefault(slug, stamp)
        fm = ['---', 'layout: jenkyn-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {meta[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/jenkyn/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        if a.apply:
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(pg['body'], pg) + '\n',
                                            encoding='utf-8')
    if a.apply:
        secs = [p for p in pages if 'ch' in p]
        meta.setdefault('1', stamp)
        fm = ['---', 'layout: jenkyn-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              'title: "Jude"', f'subtitle: "{AUTHOR}"', f'date: {meta["1"]}', 'chapter: 1',
              'verse_from: 1', f'verse_to: {NV}', '---']
        def li(p):
            return f'<li><a href="{{{{ site.baseurl }}}}/jenkyn/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>'
        body = ('<h2 class="jk-group">The First Part (1652)</h2>\n<ul class="jk-chtoc">\n'
                + '\n'.join(li(p) for p in secs if p['part'] == 1) + '\n</ul>\n\n'
                + '<h2 class="jk-group">The Second Part (1654)</h2>\n<ul class="jk-chtoc">\n'
                + '\n'.join(li(p) for p in secs if p['part'] == 2) + '\n</ul>\n')
        (OUT / '1.md').write_text('\n'.join(fm) + '\n\n' + body, encoding='utf-8')
        nav = {'1': []}
        for pg in secs:
            if pg.get('cont') or pg['src'] == '8-ii':
                continue
            for v in range(pg['v1'], pg['v2'] + 1):
                nav['1'].append({'v': v, 'slug': pg['slug']})
        (ROOT / '_data' / 'jenkyn_jude.json').write_text(json.dumps(nav, ensure_ascii=False, indent=1) + '\n',
                                                        encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        PAGES.write_text(json.dumps([{k: v for k, v in p.items() if k not in ('body', 'prev', 'next')} for p in pages],
                                    ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')
    left = sum(len(jc.TOK.findall(p['body'])) for p in pages)
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    nch = sum(1 for p in pages if 'ch' in p)
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页（正文 {nch}）→ {OUT}；推补 {conj}；剩余缺字记号 {left}',
          file=sys.stderr)
    big = sorted(pages, key=lambda p: -len(p['body']))[:5]
    print('  最长：' + '  '.join(f"{p['slug']}({len(p['body']) // 1000}k)" for p in big), file=sys.stderr)


def conj_table():
    """首页的推补逐条说明（memory feedback_conjecture_itemized）：从判读表生成。"""
    f = RAW / 'gap_review.tsv'
    ok = {ln.split('\t')[0] for ln in (RAW / 'gap_approved.tsv').read_text(encoding='utf-8').splitlines()
          if ln[:1].isdigit()} if (RAW / 'gap_approved.tsv').exists() else set()
    if not f.exists() or not ok:
        return []
    sites = {str(s['gid']): s for s in jc.sites()}
    rows = []
    for ln in f.read_text(encoding='utf-8').splitlines():
        p = ln.split('\t')
        if not p[0].isdigit() or p[0] not in ok or not p[1].startswith('P:'):
            continue
        s = sites[p[0]]
        loc = f"Part {s['part']}, {s['where'].split(':')[-1] and 'v. ' + s['where'].split(':')[-1]}"
        ctx = ' '.join(s['left'][-4:]) + ' <b>' + s['tcp'] + '</b> ' + ' '.join(s['right'][:4])
        rows.append(f'<tr><td><code>#{p[0]}</code></td><td>{loc}</td><td>{ctx}</td><td>[{p[1][2:]}]</td>'
                    f'<td>{p[2] if len(p) > 2 else ""}</td></tr>')
    if not rows:
        return []
    return ['<h3 class="jk-conjhead">编者推补逐条说明</h3>',
            '<table class="jk-conjtab"><tr><th>编号</th><th>位置</th><th>录入本原样</th><th>现作</th><th>依据</th></tr>',
            *rows, '</table>']


def build_index(pages):
    out = ['---', 'layout: jenkyn-book', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
           f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1613–1685)"',
           'edition: "An Exposition of the Epistle of Jude, together with many large and usefull Deductions · '
           'London: Tho. Maxey for Samuel Gellibrand, Part I 1652, Part II 1654"',
           '---', '']
    if (OUT / 'zh').exists():
        out.insert(-2, f'zh_url: "/jenkyn/{BOOK_ID}/"')

    def group(name, lst):
        if not lst:
            return
        out.append(f'<h2 class="jk-group">{name}</h2>')
        out.append('<ul class="jk-toc">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/jenkyn/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>'
                   for p in lst)
        out.append('</ul>')
    group('The First Part (1652): Prefatory Matter', [p for p in pages if p['group'] == 'front1'])
    group('The First Part: Verses 1–8', [p for p in pages if p.get('part') == 1 and not p.get('cont')])
    group('The Second Part (1654): Prefatory Matter', [p for p in pages if p['group'] == 'front2'])
    group('The Second Part: Verses 8–25', [p for p in pages if p.get('part') == 2 and not p.get('cont')])
    group('Errata', [p for p in pages if p['group'] == 'tail'])
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    left = sum(len(jc.TOK.findall(p['body'])) for p in pages)
    nsite = len(jc.sites())
    out.append('<div class="jk-note">')
    out.append('<p><b>About this text.</b> EEBO-TCP A87554 (Part I, London 1652; Thomason copy) and A87557 '
               '(Part II, London 1654), keyed by hand from the microfilm; CC0. Original spelling and italics are '
               'retained; the long s is printed as s. Page numbers of the original are kept as in-page anchors '
               '(each part is paged from 1). Manuscript notes on the Thomason copy (dates) are omitted.</p>')
    out.append(f'<p><b>Illegible places.</b> The keyers marked {nsite:,} places they could not read, most of them '
               f'Greek and Hebrew words, which TCP does not transcribe. English words were supplied from the same '
               f'place in the 1865 Edinburgh reprint (Nichol), keeping the original spelling, and checked against '
               f'page images; Greek, Hebrew and the marginal notes (dropped from the 1865 reprint) were read from '
               f'the 1652 microfilm for Part I and the 1656 second edition for Part II. '
               + (f'Editorial conjectures are shown <span class="jk-conj">[in brackets]</span> ({conj:,}); ' if conj else '')
               + f'places still undecided remain marked in red ({left:,}).</p>')
    out.append(f'<p class="jk-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A87554（第一部分，伦敦 1652，Thomason 藏本）'
               f'与 A87557（第二部分，伦敦 1654），保留原书拼写与斜体，长 ſ 作 s；原书页码保留为页内锚点（两部分各自从 1 起）；'
               f'Thomason 藏本扉页上的手写日期不录。录入本标出 {nsite:,} 处读不出的字，大半是录入本照例不录的希腊文、希伯来文：'
               f'英文词按 1865 年爱丁堡重印本（Nichol）同一位置读出、看图核对，拼法照原书；希腊文、希伯来文与页边旁注'
               f'（1865 本把旁注删了）对照原书胶片判读——第一部分用 1652 同版胶片，第二部分用 1656 年第二版胶片（1654 初版网上无扫描）。'
               + (f'推补以 <span class="jk-conj">[方括号]</span> 另色标出（{conj:,} 处）；' if conj else '')
               + f'仍未定的标红留在明面（{left:,} 处）。'
               f'逐条依据见 <code>jenkyn_raw/jude/PROVENANCE.md</code>。</p>')
    out.extend(conj_table())
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
