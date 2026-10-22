#!/usr/bin/env python3
"""rollock_raw/thessalonians/en_chapters/<书>/*.md（+ 判读表，见 rollock_common.py）→ rollock/<书>/*.md

    python3 scripts/publish_rollock_en.py            # 试跑
    python3 scripts/publish_rollock_en.py --apply

骨架照搬 publish_adams_en.py。原书一讲讲几节（讲前排出这几节经文），一讲一页，页名 `<章>-<首节>`；
跨章的讲（帖前第 4 讲 1:9–2:2、第 13 讲 3:13–4:3）在两章的目录页里都列出。每章另出一页目录 `<章>.md`
（历代解经扫描器与对照抽屉按章号页找书）。
帖前：书名页 / 献辞 / 致读者 / 提要 + 27 讲；帖后：书名页 / 提要 + 14 讲。

date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rollock_common as rc  # noqa: E402
from extract_rollock import NV  # noqa: E402

ROOT = rc.ROOT
RAW = rc.RAW
META = RAW / 'en_meta.json'
AUTHOR = 'Robert Rollock'
BOOKS = {
    '1thessalonians': dict(name='Rollock on 1 Thessalonians', ref='1 Thessalonians',
                           front=[('title', 'Title Page', 'Edinburgh, 1606'),
                                  ('dedication', 'Epistle Dedicatory', 'To Maister William Scot of Ely'),
                                  ('to-the-reader', 'To the Christian Reader', ''),
                                  ('argument', 'The Argument of the First Epistle', '')],
                           edition='Lectures vpon the First and Second Epistles of Paul to the Thessalonians · '
                                   'Edinburgh: Robert Charteris, 1606'),
    '2thessalonians': dict(name='Rollock on 2 Thessalonians', ref='2 Thessalonians',
                           front=[('title', 'Title Page', 'Edinburgh, 1606'),
                                  ('argument', 'The Argument of the Second Epistle', '')],
                           edition='Lectures vpon the Second Epistle of the Apostle Paul to the Thessalonians · '
                                   'Edinburgh: Robert Charteris, 1606'),
}
ORD = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth', 5: 'Fifth', 6: 'Sixth', 7: 'Seventh', 8: 'Eighth',
       9: 'Ninth', 10: 'Tenth', 11: 'Eleventh', 12: 'Twelfth', 13: 'Thirteenth', 14: 'Fourteenth',
       15: 'Fifteenth', 16: 'Sixteenth', 17: 'Seventeenth', 18: 'Eighteenth', 19: 'Nineteenth', 20: 'Twentieth'}


def ordinal(n):
    if n in ORD:
        return ORD[n]
    return 'Twenty-' + ORD[n - 20].lower()


def span(ref, a, b):
    (c1, v1), (c2, v2) = a, b
    if c1 == c2:
        return f'{ref} {c1}:{v1}' + ('' if v1 == v2 else f'–{v2}')
    return f'{ref} {c1}:{v1}–{c2}:{v2}'


MANUAL = RAW / 'manual_pages'


def load_page(book, slug):
    """扉页：照 1606 原书影像手排的 HTML（manual_pages/<书>-<slug>.html），文字取自 TCP，
    分行、字号、斜体、花边与印刷商徽记照原书（叶 0 / 叶 360）。"""
    f = MANUAL / f'{book}-{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else rc.load(book, slug)


def build_pages(book):
    cfg = BOOKS[book]
    lecs = [x for x in json.loads((RAW / 'lectures.json').read_text()) if x['book'] == book]
    pages = []
    for slug, title, sub in cfg['front']:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(book, slug), group='front'))
    for x in lecs:
        rng = span(cfg['ref'], x['start'], x['end'])
        pages.append(dict(slug=x['slug'], title=f'Lecture {x["n"]} · {rng}', short=f'Lecture {x["n"]}', rng=rng,
                          subtitle=f'The {ordinal(x["n"])} Lecture · {AUTHOR}', body=rc.load(book, x['slug']),
                          group='lecture', ch=x['start'][0], boxes=x['boxes'],
                          chs=sorted({x['start'][0], x['end'][0]}),
                          v1=x['start'][1], v2=x['end'][1] if x['end'][0] == x['start'][0] else NV[book][x['start'][0]]))
    return pages


def add_anchors(book, body, pg):
    """每个讲前经文框后面，按框里的节号每节一个 commentary-anchor（07-verse-index §1）。"""
    if 'boxes' not in pg:
        return body
    out, pos = [], 0
    boxes = list(re.finditer(r'<div class="rl-text" markdown="1">.*?\n\n</div>', body, re.S))
    if len(boxes) != len(pg['boxes']):
        print(f'⚠️ {book}/{pg["slug"]}: 经文框 {len(boxes)} 个，经文标签 {len(pg["boxes"])} 条', file=sys.stderr)
    for m, (c, a, b) in zip(boxes, pg['boxes']):
        out.append(body[pos:m.end()])
        out.append(''.join(f'\n\n<div class="commentary-anchor" id="{book}-{c}-{v}"></div>' for v in range(a, b + 1)))
        pos = m.end()
    out.append(body[pos:])
    return ''.join(out)


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = ('Editorial conjecture: illegible in the 1606 source; supplied from the stated evidence '
              '(编者推补；非原书原文)')
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(book, body, pg):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(book, body, pg)
    if pg['slug'] == 'title' and not body.startswith('<div class="rl-tpg">'):
        body = '<div class="rl-tp" markdown="1">\n\n' + body + '\n\n</div>'
    body = RE_CONJ.sub(lambda m: f'<span class="rl-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = rc.TOK.sub(lambda m: f'<span class="rl-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(book, pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/rollock/{book}/{o["slug"]}/"', f'{key}_label: "{o.get("short", o["title"])}"']


def publish(book, apply, meta, stamp):
    cfg = BOOKS[book]
    out_dir = ROOT / 'rollock' / book
    pages = build_pages(book)
    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
    if apply:
        out_dir.mkdir(parents=True, exist_ok=True)
    m = meta.setdefault(book, {})
    for pg in pages:
        slug = pg['slug']
        m.setdefault(slug, stamp)
        fm = ['---', 'layout: rollock-chapter', f'book_id: {book}', f'book_name: "{cfg["name"]}"',
              f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {m[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(book, pg, 'prev') + fm_nav(book, pg, 'next')
        if (out_dir / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/rollock/{book}/zh/{slug}/"')
        fm.append('---')
        if apply:
            (out_dir / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(book, pg['body'], pg) + '\n',
                                                encoding='utf-8')
    nch = len(NV[book])
    if apply:
        for ch in range(1, nch + 1):
            secs = [p for p in pages if ch in p.get('chs', [])]
            slug = str(ch)
            m.setdefault(slug, stamp)
            fm = ['---', 'layout: rollock-chapter', f'book_id: {book}', f'book_name: "{cfg["name"]}"',
                  f'title: "{cfg["ref"]} {ch}"', f'subtitle: "{AUTHOR}"', f'date: {m[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[book][ch]}']
            if ch > 1:
                fm += [f'prev_url: "/rollock/{book}/{ch - 1}/"', f'prev_label: "{cfg["ref"]} {ch - 1}"']
            if ch < nch:
                fm += [f'next_url: "/rollock/{book}/{ch + 1}/"', f'next_label: "{cfg["ref"]} {ch + 1}"']
            fm.append('---')
            lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/rollock/{book}/{p["slug"]}/">{p["short"]}'
                            f'<small>{p["rng"]}</small></a></li>' for p in secs)
            (out_dir / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="rl-chtoc">\n{lst}\n</ul>\n',
                                                encoding='utf-8')
        idx = build_index(book, pages)
        (out_dir / 'en').mkdir(exist_ok=True)
        (out_dir / 'en' / 'index.html').write_text(idx, encoding='utf-8')
        if not (out_dir / 'zh').exists():
            (out_dir / 'index.html').write_text(idx, encoding='utf-8')
    left = sum(len(rc.TOK.findall(p['body'])) for p in pages)
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    print(f'{book}: {"写入" if apply else "试跑"} {len(pages)} 页；推补 {conj}；剩余缺字记号 {left}', file=sys.stderr)
    return pages


def stats():
    """全书（两卷）缺字统计：首页说明里用。"""
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    dec = rc.decisions()
    w = sum(1 for g, v in dec.items() if v[1] == 'w')
    c = sum(1 for g, v in dec.items() if v[1] == 'c')
    return len(sites), w, c


def build_index(book, pages):
    cfg = BOOKS[book]
    other = '2thessalonians' if book == '1thessalonians' else '1thessalonians'
    out = ['---', 'layout: rollock-book', f'book_id: {book}', f'book_name: "{cfg["name"]}"',
           f'title: "{cfg["name"]}"', f'author: "{AUTHOR} (c.1555–1599)"',
           f'edition: "{cfg["edition"]}"', '---', '']
    if (ROOT / 'rollock' / book / 'zh').exists():
        out.insert(-2, f'zh_url: "/rollock/{book}/"')

    out.append('<h2 class="rl-group">Prefatory Matter</h2>')
    out.append('<ul class="rl-toc">')
    out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/rollock/{book}/{p["slug"]}/">{p["title"]}</a></li>'
               for p in pages if p['group'] == 'front')
    out.append('</ul>')
    out.append('<h2 class="rl-group">Chapters</h2>')
    out.append('<ul class="rl-chgrid">' + ''.join(
        f'<li><a href="{{{{ site.baseurl }}}}/rollock/{book}/{c}/">Chapter {c}</a></li>'
        for c in range(1, len(NV[book]) + 1)) + '</ul>')
    out.append('<h2 class="rl-group">Lectures</h2>')
    out.append('<ul class="rl-toc">')
    out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/rollock/{book}/{p["slug"]}/">{p["short"]}'
               f'<small>{p["rng"]}</small></a></li>' for p in pages if p['group'] == 'lecture')
    out.append('</ul>')
    n, w, c = stats()
    left = sum(len(rc.TOK.findall(p['body'])) for p in pages)
    ref_other = BOOKS[other]['ref']
    out.append('<div class="rl-note">')
    out.append('<p><b>About this text.</b> EEBO-TCP A11010 (Edinburgh: Robert Charteris, 1606; STC 21281), keyed by '
               'hand from the EEBO microfilm; CC0. The lectures on both epistles were printed in one volume; the '
               f'lectures on {ref_other} are <a href="{{{{ site.baseurl }}}}/rollock/{other}/en/">here</a>. '
               'Original spelling and italics are retained; the long s is printed as s. Page numbers of the '
               'original are kept as in-page anchors.</p>')
    out.append(f'<p><b>Illegible places.</b> The keyers marked {n:,} places (in both epistles) they could not read '
               f'from the black-and-white film images. {w:,} were read from the grayscale scan of the same film '
               f'(Internet Archive), place by place against the page image'
               + (f'; {c:,} are editorial conjectures shown <span class="rl-conj">[in brackets]</span>' if c else '')
               + f'. Places still unread in this epistle remain marked <span class="rl-gap">in red</span> ({left:,}); '
               'they lie where the film itself fails — double exposures, show-through from the reverse, a blot on pp. 65–66 — '
               'and could only be read from another copy.</p>')
    out.append('<p class="rl-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A11010（爱丁堡 1606，STC 21281，EEBO 缩微胶片），'
               '帖前、帖后两部讲章原为一册。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。'
               f'录入本有 {n:,} 处读不出的字（两卷合计），{w:,} 处对照同一卷胶片的灰度扫描（Internet Archive）逐处看图读出'
               + (f'；{c:,} 处为编者推补，以 <span class="rl-conj">[方括号]</span> 另色标出' if c else '')
               + f'；本卷仍读不出的标红留在明面（{left:,} 处）——都落在胶片本身的毛病上：两次曝光叠印、背面透印、p.65–66 页底污渍，'
               '只有另一份藏本的影像才可能读出。逐条依据见 <code>rollock_raw/thessalonians/</code>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    for book in BOOKS:
        publish(book, a.apply, meta, stamp)
    if a.apply:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
