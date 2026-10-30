#!/usr/bin/env python3
"""adams_raw/2peter/en_chapters/*.md（+ 判读表，见 adams_common.py）→ adams/2peter/*.md

    python3 scripts/publish_adams_en.py            # 试跑
    python3 scripts/publish_adams_en.py --apply

骨架照搬 publish_leighton_en.py。分页：原书逐节讲解，一节一页（1:20–21 合讲一页），页名 `<章>-<首节>`；
卷首 title1 / dedication、卷二 title2，书末 index / errata。每章另出一页目录 `<章>.md`。

date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adams_common as ac  # noqa: E402
from extract_adams import NV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ac.RAW
OUT = ROOT / 'adams' / '2peter'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'

BOOK_ID = '2peter'
BOOK_NAME = 'Adams on 2 Peter'
AUTHOR = 'Thomas Adams'

FRONT = [('title1', 'Title Page (Vol. I)', 'London, 1633'),
         ('dedication', 'Epistle Dedicatory', 'To Sir Henry Marten')]
VOL2 = [('title2', 'Title Page (Vol. II)', 'London, 1633')]
TAIL = [('index', 'An Alphabeticall Direction', 'Index of the principal points'),
        ('errata', 'Errata', '')]

PUB_SLUG = {'index': 'alphabetical-index'}
RE_BOX = re.compile(r'<div class="ad-text" markdown="1">')


MANUAL = RAW / 'manual_pages'


def load_page(slug):
    """扉页等排版性页面：用照原书影像手排的 HTML（manual_pages/<slug>.html），文字取自 TCP，
    版式（分行、字号、小型大写、斜体、横线、印刷商徽记）照 1633 原书。"""
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else ac.load(slug)


def chtoc(secs, base, vlabel):
    """章目录：一节一格，分成几部分的在格内并排列 1 2 3 小链接。publish_adams_zh.py 有同名一份。"""
    rows, groups = [], {}
    for p in secs:
        groups.setdefault((p['v1'], p['v2']), []).append(p)
    for (a, b), ps in groups.items():
        href = lambda p: f'{{{{ site.baseurl }}}}{base}{p["slug"]}/'
        parts = ''
        if len(ps) > 1 or RE_PART_T.search(ps[0]['title']):
            parts = '<span class="ad-pt">' + ''.join(
                f'<a href="{href(p)}">{(RE_PART_T.search(p["title"]) or [0, 1])[1]}</a>' for p in ps) + '</span>'
        rows.append(f'<li><a href="{href(ps[0])}">{vlabel(a, b)}</a>{parts}</li>')
    return '\n'.join(rows)


RE_PART_T = re.compile(r'\(part (\d+) of (\d+)\)')


def vref(ch, a, b):
    return f'2 Peter {ch}:{a}' if a == b else f'2 Peter {ch}:{a}–{b}'


def build_pages():
    order = json.loads((RAW / 'order.json').read_text())
    verse_slugs = [s for s in order if re.fullmatch(r'\d-\d+', s)]
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(slug), group='front'))
    for i, slug in enumerate(verse_slugs):
        ch, a = map(int, slug.split('-'))
        nxt = verse_slugs[i + 1] if i + 1 < len(verse_slugs) else None
        b = (int(nxt.split('-')[1]) - 1) if nxt and int(nxt.split('-')[0]) == ch else NV[ch]
        if slug == '2-11':          # 卷二从 2:11 起：卷二扉页排在它前面
            for s2, t2, sub2 in VOL2:
                pages.append(dict(slug=s2, title=t2, subtitle=sub2, body=load_page(s2), group='vol2'))
        parts = split_long(ac.load(slug))
        for k, body in enumerate(parts, 1):
            pg = dict(slug=slug if k == 1 else f'{slug}-{k}',
                      title=vref(ch, a, b) + (f' (part {k} of {len(parts)})' if len(parts) > 1 else ''),
                      subtitle=AUTHOR, body=body, group=f'ch{ch}', ch=ch, v1=a, v2=b)
            if k > 1:
                pg['cont'] = True
            pages.append(pg)
    for slug, title, sub in TAIL:
        # 书末索引的抽取篇名是 index：发布成 index.md 会占掉书首页 /adams/2peter/（与 index.html 同路径，
        # 历代解经点进来落到索引页）。发布页名另取 alphabetical-index，抽取产物与判读对齐仍用 index
        pages.append(dict(slug=PUB_SLUG.get(slug, slug), title=title, subtitle=sub, body=ac.load(slug), group='tail'))
    return pages


LIMIT = 120_000


def split_long(body):
    """一节的讲解太长（3:18 原书一百多页）：切成几页，每页约 LIMIT 字符。
    切点优先取原书小标题（###）前；没有就取段落之间（不在 <div> 块里切）。"""
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
    for i, blk in enumerate(blocks):
        heading = blk.startswith('### ')
        if buf and (size >= target or (heading and size >= target * 0.7)) and len(parts) < n_parts - 1:
            parts.append('\n\n'.join(buf))
            buf, size = [], 0
        buf.append(blk)
        size += len(blk) + 2
    parts.append('\n\n'.join(buf))
    return parts


def add_anchors(body, pg):
    """经文框后面每节一个 commentary-anchor（07-verse-index §1）。"""
    if 'ch' not in pg or pg.get('cont'):
        return body
    anchors = ''.join(f'\n\n<div class="commentary-anchor" id="2peter-{pg["ch"]}-{v}"></div>'
                      for v in range(pg['v1'], pg['v2'] + 1))
    m = re.search(r'<div class="ad-text" markdown="1">.*?\n\n</div>', body, re.S)
    if not m:
        return anchors.strip() + '\n\n' + body
    return body[:m.end()] + anchors + body[m.end():]


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = ('Editorial conjecture: illegible in the 1633 source (lost in the gutter of the EEBO microfilm); '
              'supplied from the stated evidence (编者推补；非原书原文)')
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, pg):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(body, pg)
    body = RE_CONJ.sub(lambda m: f'<span class="ad-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = ac.TOK.sub(lambda m: f'<span class="ad-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/adams/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o["title"]}"']


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
        fm = ['---', 'layout: adams-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {meta[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/adams/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        if a.apply:
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(pg['body'], pg) + '\n',
                                            encoding='utf-8')
    if a.apply:
        for ch in (1, 2, 3):
            secs = [p for p in pages if p.get('ch') == ch]   # 分页的续页也列出，标题带 part k
            slug = str(ch)
            meta.setdefault(slug, stamp)
            fm = ['---', 'layout: adams-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
                  f'title: "2 Peter {ch}"', f'subtitle: "{AUTHOR}"', f'date: {meta[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/adams/{BOOK_ID}/{ch - 1}/"', f'prev_label: "2 Peter {ch - 1}"']
            if ch < 3:
                fm += [f'next_url: "/adams/{BOOK_ID}/{ch + 1}/"', f'next_label: "2 Peter {ch + 1}"']
            fm.append('---')
            lst = chtoc(secs, f'/adams/{BOOK_ID}/', lambda a, b: f'v. {a}' + (f'–{b}' if b != a else ''))
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="ad-chtoc">\n{lst}\n</ul>\n', encoding='utf-8')
        nav = {}
        for pg in pages:
            if 'ch' in pg:
                if pg.get('cont'):
                    continue
                for v in range(pg['v1'], pg['v2'] + 1):
                    nav.setdefault(str(pg['ch']), []).append({'v': v, 'slug': pg['slug']})
        (ROOT / '_data' / 'adams_2peter.json').write_text(json.dumps(nav, ensure_ascii=False, indent=1) + '\n',
                                                         encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        PAGES.write_text(json.dumps([{k: v for k, v in p.items() if k not in ('body', 'prev', 'next')} for p in pages],
                                    ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')
    left = sum(len(ac.TOK.findall(p['body'])) for p in pages)
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    nch = sum(1 for p in pages if 'ch' in p)
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页（正文 {nch}）→ {OUT}；推补 {conj}；剩余缺字记号 {left}',
          file=sys.stderr)
    big = sorted(pages, key=lambda p: -len(p['body']))[:5]
    print('  最长：' + '  '.join(f"{p['slug']}({len(p['body']) // 1000}k)" for p in big), file=sys.stderr)


def build_index(pages):
    out = ['---', 'layout: adams-book', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
           f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1583–1652)"',
           'edition: "A Commentary or, Exposition vpon the Diuine Second Epistle Generall, written by the Blessed '
           'Apostle St. Peter · London: Richard Badger and Felix Kyngston for Iacob Bloome, 1633"',
           '---', '']
    if (OUT / 'zh').exists():
        out.insert(-2, f'zh_url: "/adams/{BOOK_ID}/"')

    def group(name, pred):
        lst = [p for p in pages if pred(p)]
        if not lst:
            return
        out.append(f'<h2 class="ad-group">{name}</h2>')
        out.append('<ul class="ad-toc">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/adams/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>' for p in lst)
        out.append('</ul>')
    group('Prefatory Matter', lambda p: p['group'] == 'front')
    out.append('<h2 class="ad-group">Chapters</h2>')
    out.append('<ul class="ad-chgrid">' + ''.join(
        f'<li><a href="{{{{ site.baseurl }}}}/adams/{BOOK_ID}/{c}/">Chapter {c}</a></li>' for c in (1, 2, 3)) + '</ul>')
    group('Volume II', lambda p: p['group'] == 'vol2')
    group('Index and Errata', lambda p: p['group'] == 'tail')
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    left = sum(len(ac.TOK.findall(p['body'])) for p in pages)
    out.append('<div class="ad-note">')
    out.append('<p><b>About this text.</b> EEBO-TCP A00665 (London, 1633; STC 108), keyed by hand from the '
               'British Library copy on microfilm; CC0. Original spelling and italics are retained; the long s is '
               'printed as s. Page numbers of the original are kept as in-page anchors (Vol. II continues from 801).</p>')
    out.append(f'<p><b>Illegible places.</b> The keyers marked about 11,000 places they could not read. Most were '
               f'supplied from the same place in the 1862 Edinburgh reprint (ed. James Sherman), checked against page '
               f'images, keeping the 1633 spelling; Latin, Greek and passages Sherman rewrote were read from the '
               f'1633 microfilm itself. Where the letters are lost in the gutter of the film, the reading is an '
               f'editorial conjecture shown <span class="ad-conj">[in brackets]</span> ({conj:,}); places still '
               f'undecided remain marked in red ({left:,}).</p>')
    out.append(f'<p class="ad-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A00665（伦敦 1633，STC 108，大英图书馆藏本缩微胶片），'
               f'保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点（卷二从 801 起）。录入本约 11,000 处读不出的字：'
               f'多数按 1862 年爱丁堡重印本（Sherman 修订）同一位置读出、看图核对，拼法照 1633 原书；拉丁、希腊文和 Sherman 改写过的地方'
               f'对照 1633 原书胶片判读。落在胶片装订缝黑边里、原图读不出的，按上下文与引文出处推补，以 '
               f'<span class="ad-conj">[方括号]</span> 另色标出（{conj:,} 处）；仍未定的标红留在明面（{left:,} 处）。'
               f'逐条依据见 <code>adams_raw/2peter/PROVENANCE.md</code>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
