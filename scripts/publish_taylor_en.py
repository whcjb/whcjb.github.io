#!/usr/bin/env python3
"""taylor_raw/titus/en_chapters/*.md（+ 判读表，见 taylor_common.py）→ taylor/titus/*.md

    python3 scripts/publish_taylor_en.py            # 试跑
    python3 scripts/publish_taylor_en.py --apply

骨架照搬 publish_rollock_en.py。原书不分讲，按经文一段一段讲；一段一页，页名 `<章>-<首节>`。
每章另出一页目录 `<章>.md`（历代解经扫描器与对照抽屉按章号页找书）。
卷首：书名页 / 献辞 / 致读者 / 本书缘起与分段；卷末：三个索引表 / 勘误。

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
import taylor_common as tc  # noqa: E402
from extract_taylor import NV  # noqa: E402

ROOT = tc.ROOT
RAW = tc.RAW
META = RAW / 'en_meta.json'
BOOK = 'titus'
OUT = ROOT / 'taylor' / BOOK
AUTHOR = 'Thomas Taylor'
NAME = 'Taylor on Titus'
REF = 'Titus'
EDITION = 'A Commentarie vpon the Epistle of S. Paul written to Titus · Cambridge: Cantrell Legge for L. Greene, 1612'
FRONT = [('title', 'Title Page', 'Cambridge, 1612'),
         ('dedication', 'Epistle Dedicatory', 'To Robert Lord Rich, Baron of Leez'),
         ('to-the-reader', 'To the Christian Reader', ''),
         ('argument', 'The Occasion and Parts of the Epistle', '')]
BACK = [('doctrines', 'A Short View of the Doctrines', 'The first table'),
        ('observations', 'Other Profitable Notes', 'The second table'),
        ('questions', 'A Brief Table of the Questions', 'The third table'),
        ('errata', 'Errata', '')]


def rng(ch, a, b):
    return f'{REF} {ch}:{a}' + ('' if a == b else f'–{b}')


MANUAL = RAW / 'manual_pages'


def load_page(slug):
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else tc.load(slug)


def build_pages():
    od = tc.order()
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(slug), group='front'))
    for x in od['sections']:
        r = rng(x['ch'], x['v1'], x['v2'])
        short = f'{x["ch"]}:{x["v1"]}' + ('' if x['v1'] == x['v2'] else f'–{x["v2"]}')
        pages.append(dict(slug=x['slug'], title=r, short=short, rng=r, subtitle=AUTHOR, body=tc.load(x['slug']),
                          group='section', ch=x['ch'], v1=x['v1'], v2=x['v2']))
    for slug, title, sub in BACK:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(slug), group='back'))
    return pages


def add_anchors(body, pg):
    """本段每节一个 commentary-anchor（07-verse-index §1），挂在段前经文框后；没有经文框的挂在页首。"""
    if 'ch' not in pg:
        return body
    anc = ''.join(f'\n\n<div class="commentary-anchor" id="{BOOK}-{pg["ch"]}-{v}"></div>'
                  for v in range(pg['v1'], pg['v2'] + 1))
    m = re.search(r'<div class="ty-text" markdown="1">.*?\n\n</div>', body, re.S)
    if m and m.start() < 3000:
        return body[:m.end()] + anc + body[m.end():]
    return anc.lstrip('\n') + '\n\n' + body


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = ('Editorial conjecture: illegible in the 1612 source; supplied from the stated evidence '
              '(编者推补；非原书原文)')
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, pg):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(body, pg)
    if pg['slug'] == 'title' and not body.startswith('<div class="ty-tpg">'):
        body = '<div class="ty-tp" markdown="1">\n\n' + body + '\n\n</div>'
    body = RE_CONJ.sub(lambda m: f'<span class="ty-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = tc.TOK.sub(lambda m: f'<span class="ty-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/taylor/{BOOK}/{o["slug"]}/"', f'{key}_label: "{o.get("short", o["title"])}"']


def publish(apply, meta, stamp):
    pages = build_pages()
    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
    if apply:
        OUT.mkdir(parents=True, exist_ok=True)
    m = meta.setdefault(BOOK, {})
    for pg in pages:
        slug = pg['slug']
        m.setdefault(slug, stamp)
        fm = ['---', 'layout: taylor-chapter', f'book_id: {BOOK}', f'book_name: "{NAME}"', f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {m[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/taylor/{BOOK}/zh/{slug}/"')
        fm.append('---')
        if apply:
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(pg['body'], pg) + '\n',
                                            encoding='utf-8')
    nch = len(NV)
    if apply:
        for ch in range(1, nch + 1):
            secs = [p for p in pages if p.get('ch') == ch]
            slug = str(ch)
            m.setdefault(slug, stamp)
            fm = ['---', 'layout: taylor-chapter', f'book_id: {BOOK}', f'book_name: "{NAME}"',
                  f'title: "{REF} {ch}"', f'subtitle: "{AUTHOR}"', f'date: {m[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/taylor/{BOOK}/{ch - 1}/"', f'prev_label: "{REF} {ch - 1}"']
            if ch < nch:
                fm += [f'next_url: "/taylor/{BOOK}/{ch + 1}/"', f'next_label: "{REF} {ch + 1}"']
            fm.append('---')
            lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/taylor/{BOOK}/{p["slug"]}/">{p["short"]}'
                            f'<small>{p["rng"]}</small></a></li>' for p in secs)
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="ty-chtoc">\n{lst}\n</ul>\n',
                                            encoding='utf-8')
        idx = build_index(pages)
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(idx, encoding='utf-8')
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(idx, encoding='utf-8')
    left = sum(len(tc.TOK.findall(p['body'])) for p in pages)
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    print(f'{BOOK}: {"写入" if apply else "试跑"} {len(pages)} 页；推补 {conj}；剩余缺字记号 {left}', file=sys.stderr)
    return pages


def stats():
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    dec = tc.decisions()
    w = sum(1 for g, v in dec.items() if v[1] == 'w')
    c = sum(1 for g, v in dec.items() if v[1] == 'c')
    return len(sites), w, c


def _anchor(slug, page):
    return f'/taylor/{BOOK}/{slug}/' + (f'#p{page}' if page else '')


def _ctx(s):
    return html.escape(' '.join(s['left'][-5:]) + ' ⟨' + s['tcp'] + '⟩ ' + ' '.join(s['right'][:5]))


def notes_tables():
    """首页逐条说明（从判读表生成，表改首页跟着变）：① 编者推补（用户同意的推断）② 仍读不出的。"""
    sites = {s['gid']: s for s in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    review = {int(r[0]): r for r in tc._tsv('gap_review.tsv')}
    appr = [(int(r[0]), r[1]) for r in tc._tsv('gap_approved.tsv')]
    out = []
    if appr:
        out.append(f'<h3 class="ty-conjhead">编者推补逐条说明（{len(appr)} 处）</h3>')
        out.append('<p class="ty-note-zh">以下各处录入本标为读不出，两份 1612 年藏本的影像上也只能认出大致字形；'
                   '按字形并参照经文、上下文与后出版次推补，正文中以 <span class="ty-conj">[方括号]</span> 另色标出，'
                   '不是原书确定的文字。</p>')
        out.append('<table class="ty-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>现作</th><th>依据</th></tr>')
        for g, v in appr:
            s = sites[g]
            note = review.get(g, ['', '', '', ''])[3] if len(review.get(g, [])) > 3 else ''
            out.append(f'<tr><td><a href="{{{{ site.baseurl }}}}{_anchor(s["slug"], s.get("page"))}">'
                       f'{s["slug"]} · p.{s.get("page")}</a></td><td>{_ctx(s)}</td>'
                       f'<td>[{html.escape(v.replace("*", ""))}]</td><td>{html.escape(note)}</td></tr>')
        out.append('</table>')
    left = [g for g, r in review.items() if r[1] == '?']
    if left:
        out.append(f'<h3 class="ty-conjhead">仍读不出的（{len(left)} 处）</h3>')
        out.append('<p class="ty-note-zh">这些位置在两份 1612 年藏本的影像上都读不出，正文中标红留在明面，不推补。</p>')
        out.append('<table class="ty-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>原因</th></tr>')
        for g in sorted(left):
            s = sites[g]
            note = review[g][3] if len(review[g]) > 3 else ''
            out.append(f'<tr><td><a href="{{{{ site.baseurl }}}}{_anchor(s["slug"], s.get("page"))}">'
                       f'{s["slug"]} · p.{s.get("page")}</a></td><td>{_ctx(s)}</td><td>{html.escape(note)}</td></tr>')
        out.append('</table>')
    return out


def build_index(pages):
    out = ['---', 'layout: taylor-book', f'book_id: {BOOK}', f'book_name: "{NAME}"',
           f'title: "{NAME}"', f'author: "{AUTHOR} (1576–1633)"', f'edition: "{EDITION}"', '---', '']
    if (OUT / 'zh').exists():
        out.insert(-2, f'zh_url: "/taylor/{BOOK}/"')

    def toc(group):
        return [f'  <li><a href="{{{{ site.baseurl }}}}/taylor/{BOOK}/{p["slug"]}/">{p["title"]}'
                + (f'<small>{p["subtitle"]}</small>' if p.get('subtitle') and group != 'section' else '')
                + '</a></li>' for p in pages if p['group'] == group]
    out.append('<h2 class="ty-group">Prefatory Matter</h2>')
    out += ['<ul class="ty-toc">'] + toc('front') + ['</ul>']
    out.append('<h2 class="ty-group">Chapters</h2>')
    out.append('<ul class="ty-chgrid">' + ''.join(
        f'<li><a href="{{{{ site.baseurl }}}}/taylor/{BOOK}/{c}/">Chapter {c}</a></li>'
        for c in range(1, len(NV) + 1)) + '</ul>')
    out.append('<h2 class="ty-group">Commentary</h2>')
    out.append('<ul class="ty-toc">')
    out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/taylor/{BOOK}/{p["slug"]}/">{p["short"]}'
               f'<small>{p["rng"]}</small></a></li>' for p in pages if p['group'] == 'section')
    out.append('</ul>')
    out.append('<h2 class="ty-group">Tables</h2>')
    out += ['<ul class="ty-toc">'] + toc('back') + ['</ul>']
    n, w, c = stats()
    left = sum(len(tc.TOK.findall(p['body'])) for p in pages)
    out.append('<div class="ty-note">')
    out.append('<p><b>About this text.</b> EEBO-TCP A13535 (Cambridge: Cantrell Legge for L. Greene, 1612; STC 23825), '
               'keyed by hand from the EEBO microfilm; CC0. The commentary was preached in Cambridge; this is the first '
               'edition. Original spelling and italics are retained; the long s is printed as s. Page numbers of the '
               'original are kept as in-page anchors.</p>')
    out.append(f'<p><b>Illegible places.</b> The keyers marked {n:,} places they could not read from the black-and-white '
               f'film images. {w:,} were read from the grayscale scans of two copies of the 1612 edition (Internet Archive), '
               'place by place against the page image'
               + (f'; {c:,} are editorial conjectures shown <span class="ty-conj">[in brackets]</span>' if c else '')
               + f'. Places still unread remain marked <span class="ty-gap">in red</span> ({left:,}).</p>')
    out.append('<p class="ty-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A13535（剑桥 1612 年初版，STC 23825，'
               'EEBO 缩微胶片）。原书是泰勒在剑桥讲道的讲稿。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。'
               f'录入本有 {n:,} 处读不出的字，{w:,} 处对照两份 1612 年藏本的胶片灰度扫描（Internet Archive）逐处看图读出'
               + (f'；{c:,} 处为编者推补，以 <span class="ty-conj">[方括号]</span> 另色标出' if c else '')
               + f'；仍读不出的标红留在明面（{left:,} 处）。逐条依据见下表与 <code>taylor_raw/titus/</code>。</p>')
    out.extend(notes_tables())
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    publish(a.apply, meta, stamp)
    if a.apply:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
