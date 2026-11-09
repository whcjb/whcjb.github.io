#!/usr/bin/env python3
"""jones_raw/<book>/en_chapters/*.md（+ 判读表，见 jones_common.py）→ jones/<book>/*.md

    python3 scripts/publish_jones_en.py            # 试跑（两卷）
    python3 scripts/publish_jones_en.py --apply
    python3 scripts/publish_jones_en.py --apply --book 3john

骨架照搬 publish_attersoll_en.py。一节一页，页名 `1-<节>`（约翰三书末段合讲 13–14 节，页名 `1-13`）；
每卷另出章目录 `1.md`。卷首：书名页 / 献辞（献杰尔明爵士）/ 致读者（全书共用，两卷各一份）；卷末：勘误（只取约翰书信一节）。

date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import collections
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jones_common as jc  # noqa: E402
from extract_jones import NV  # noqa: E402

ROOT = jc.ROOT
AUTHOR = 'William Jones'
REF = {'2john': '2 John', '3john': '3 John'}
NAME = {'2john': 'Jones on 2 John', '3john': 'Jones on 3 John'}
EDITION = ('A Commentary upon the Epistles of Saint Paul to Philemon, and to the Hebrewes; together with '
           'a Compendious Explication of the Second and Third Epistles of Saint Iohn · London: R. B. for Robert Allot, 1635')
FRONT = [('title', 'Title Page', 'London, 1635'),
         ('dedication', 'Epistle Dedicatory', 'To Sir Thomas Jermyn'),
         ('to-the-reader', 'To the Christian Reader', '')]
BACK = [('errata', 'Errata', 'In Epist. Iohan.')]


def out_dir(book):
    return ROOT / 'jones' / book


def rng(book, ch, a, b):
    return f'{REF[book]} {ch}:{a}' + ('' if a == b else f'–{b}')


MANUAL = jc.BASE / 'manual_pages'


def load_page(book, slug):
    """扉页照 1635 原书影像逐行手排（old-book-ocr §5.6），两卷共用 manual_pages/<slug>.html；其余走抽取。"""
    f = MANUAL / f'{slug}.html'
    if f.exists():
        return f.read_text(encoding='utf-8').strip()
    return jc.load(book, slug)


def build_pages(book):
    od = jc.order(book)
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_page(book, slug), group='front'))
    for x in od['sections']:
        r = rng(book, x['ch'], x['v1'], x['v2'])
        short = f'{x["ch"]}:{x["v1"]}' + ('' if x['v1'] == x['v2'] else f'–{x["v2"]}')
        pages.append(dict(slug=x['slug'], title=r, short=short, rng=r, subtitle=AUTHOR, body=jc.load(book, x['slug']),
                          group='section', ch=x['ch'], v1=x['v1'], v2=x['v2']))
    for slug, title, sub in BACK:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=jc.load(book, slug), group='back'))
    return pages


def add_anchors(book, body, pg):
    """本段每节一个 commentary-anchor（07-verse-index §1），挂在页首（本书节下不排经文）。"""
    if 'ch' not in pg:
        return body
    anc = ''.join(f'<div class="commentary-anchor" id="{book}-{pg["ch"]}-{v}"></div>\n\n'
                  for v in range(pg['v1'], pg['v2'] + 1))
    return anc + body


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = ('Editorial conjecture: not certain in the original (1635, checked against the 1636 issue); '
              'see the table on this book\'s front page (编者推补；非原书确定文字，依据见本卷首页)')
RE_OL = re.compile(r'^(\d+)\. ', re.M)
GAP_TITLE = {'〈Greek〉': 'TCP: Greek not keyed by the transcribers (录入本未录的希腊文)'}


def render_body(book, body, pg):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(book, body, pg)
    if pg['slug'] == 'title' and not body.startswith('<div class="jw-tpg">'):
        body = '<div class="jw-tp" markdown="1">\n\n' + body + '\n\n</div>'
    body = RE_CONJ.sub(lambda m: f'<span class="jw-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = jc.TOK.sub(lambda m: f'<span class="jw-gap" title="{GAP_TITLE.get(m.group(0), "TCP: illegible in source")}">'
                      f'{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(book, pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/jones/{book}/{o["slug"]}/"', f'{key}_label: "{o.get("short", o["title"])}"']


def publish(book, apply, meta, stamp):
    pages = build_pages(book)
    for i, pg in enumerate(pages):
        pg['prev'] = pages[i - 1] if i else None
        pg['next'] = pages[i + 1] if i + 1 < len(pages) else None
    out = out_dir(book)
    if apply:
        out.mkdir(parents=True, exist_ok=True)
    m = meta.setdefault(book, {})
    for pg in pages:
        slug = pg['slug']
        m.setdefault(slug, stamp)
        fm = ['---', 'layout: jones-chapter', f'book_id: {book}', f'book_name: "{NAME[book]}"', f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {m[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(book, pg, 'prev') + fm_nav(book, pg, 'next')
        if (out / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/jones/{book}/zh/{slug}/"')
        fm.append('---')
        if apply:
            (out / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(book, pg['body'], pg) + '\n',
                                            encoding='utf-8')
    if apply:
        secs = [p for p in pages if p.get('ch') == 1]
        m.setdefault('1', stamp)
        fm = ['---', 'layout: jones-chapter', f'book_id: {book}', f'book_name: "{NAME[book]}"',
              f'title: "{REF[book]}"', f'subtitle: "{AUTHOR}"', f'date: {m["1"]}', 'chapter: 1',
              'verse_from: 1', f'verse_to: {NV[book]}']
        if (out / 'zh' / '1.md').exists():
            fm.append(f'zh_url: "/jones/{book}/zh/1/"')
        fm.append('---')
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/jones/{book}/{p["slug"]}/">{p["short"]}'
                        f'<small>{p["rng"]}</small></a></li>' for p in secs)
        (out / '1.md').write_text('\n'.join(fm) + f'\n\n<ul class="jw-chtoc">\n{lst}\n</ul>\n', encoding='utf-8')
        idx = build_index(book, pages)
        (out / 'en').mkdir(exist_ok=True)
        (out / 'en' / 'index.html').write_text(idx, encoding='utf-8')
        if not (out / 'zh').exists():
            (out / 'index.html').write_text(idx, encoding='utf-8')
    left = sum(len(jc.TOK.findall(p['body'])) for p in pages)
    conj = sum(len(RE_CONJ.findall(p['body'])) for p in pages)
    print(f'{book}: {"写入" if apply else "试跑"} {len(pages)} 页；推补 {conj}；剩余缺字记号 {left}', file=sys.stderr)
    return pages


def _ctx(s):
    return html.escape(' '.join(s['left'][-5:]) + ' ⟨' + s['tcp'] + '⟩ ' + ' '.join(s['right'][:5]))


def notes_tables(book):
    """首页逐条说明（从判读表生成）：① 编者推补（用户同意的推断）② 仍读不出的。"""
    f = jc.raw(book) / 'gap_sites.json'
    if not f.exists():
        return []
    sites = {s['gid']: s for s in json.loads(f.read_text(encoding='utf-8'))}
    review = {int(r[0]): r for r in jc.tsv(book, 'gap_review.tsv')}
    appr = [r + [''] * (5 - len(r)) for r in jc.tsv(book, 'gap_approved.tsv')]
    done = {int(r[0]) for r in appr}

    def where(s):
        return (f'<a href="{{{{ site.baseurl }}}}/jones/{book}/{s["slug"]}/'
                + (f'#p{s["page"]}' if s.get('page') else '') + f'">{s["slug"]}'
                + (f' · p.{s["page"]}' if s.get('page') else '') + '</a>')
    out = []
    if appr:
        kinds = collections.Counter(r[2] for r in appr)
        out.append(f'<h3 class="jw-conjhead">编者推补逐条说明（{len(appr)} 处）</h3>')
        out.append('<p class="jw-note-zh">以下各处录入本空着，原书在 1635 年胶片影像上又读不定；编者再拿 1636 年印本'
                   '（Internet Archive 另一份扫描）逐处看图对照，仍须编者下判断，经本站同意后发布。正文中以 '
                   '<span class="jw-conj">[另一种字体加方括号]</span> 标出，<b>不是原书确定的文字</b>。分三类：</p>')
        out.append('<ul class="jw-note-zh">'
                   + (f'<li><b>残缺补</b>（{kinds["残缺补"]} 处）：两本同一处字母都残缺或墨淡，按看得见的笔画与上下文补出。</li>' if kinds['残缺补'] else '')
                   + (f'<li><b>误植改</b>（{kinds["误植改"]} 处）：两本字形一致、看得清楚，是原书印错了；按文意改正，原书印作什么见「原书所见」一栏。</li>' if kinds['误植改'] else '')
                   + (f'<li><b>照录</b>（{kinds["照录"]} 处）：两本字形一致，照印本录，但词形可疑，存疑待考。</li>' if kinds['照录'] else '')
                   + '</ul>')
        out.append('<table class="jw-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>原书所见（1635、1636 两本）</th>'
                   '<th>现作</th><th>类别与依据</th></tr>')
        for r in appr:
            s = sites[int(r[0])]
            out.append(f'<tr><td>{where(s)}</td><td>{_ctx(s)}</td><td>{html.escape(r[3])}</td>'
                       f'<td>[{html.escape(r[1].replace("*", ""))}]</td>'
                       f'<td><b>{html.escape(r[2])}</b>：{html.escape(r[4])}</td></tr>')
        out.append('</table>')
    pend = [g for g, r in sorted(review.items()) if r[1].startswith('P:') and g not in done]
    if pend:
        out.append(f'<h3 class="jw-conjhead">推断待同意（{len(pend)} 处）</h3>')
        out.append('<p class="jw-note-zh">这些位置在 1635 年原版胶片影像上只认得出一部分字形，下列「拟补」是按可见字形与上下文的推断，'
                   '<b>尚未经本站同意，正文仍标红，不补</b>。</p>')
        out.append('<table class="jw-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>拟补</th><th>依据</th></tr>')
        for g in pend:
            s, r = sites[g], review[g]
            out.append(f'<tr><td>{where(s)}</td><td>{_ctx(s)}</td><td>{html.escape(r[1][2:].replace("*", ""))}</td>'
                       f'<td>{html.escape(r[3] if len(r) > 3 else "")}</td></tr>')
        out.append('</table>')
    left = [g for g, r in sorted(review.items()) if r[1] == '?' and g not in done]
    if left:
        out.append(f'<h3 class="jw-conjhead">读不出的（{len(left)} 处）</h3>')
        out.append('<p class="jw-note-zh">这些位置在 1635 年胶片与 1636 年印本两份影像上都读不出，正文中标红留在明面，不推补。</p>')
        out.append('<table class="jw-conjtab"><tr><th>位置</th><th>录入本原样（前后文）</th><th>原因</th></tr>')
        for g in left:
            s, r = sites[g], review[g]
            out.append(f'<tr><td>{where(s)}</td><td>{_ctx(s)}</td><td>{html.escape(r[3] if len(r) > 3 else "")}</td></tr>')
        out.append('</table>')
    return out


def gap_stats(book):
    f = jc.raw(book) / 'gap_sites.json'
    if not f.exists():
        return 0, 0, 0
    sites = json.loads(f.read_text(encoding='utf-8'))
    dec = jc.decisions(book)
    return (len(sites), sum(1 for v in dec.values() if v[1] == 'w'), sum(1 for v in dec.values() if v[1] == 'c'))


def gap_counts(pages):
    """正文各页（不含书名页、致读者、勘误这些两卷共用的）缺字记号：(希腊文, 其他)。"""
    toks = [t for p in pages if p['group'] == 'section' for t in jc.TOK.findall(p['body'])]
    g = sum(1 for t in toks if t == '〈Greek〉')
    return g, len(toks) - g


def build_index(book, pages):
    out = ['---', 'layout: jones-book', f'book_id: {book}', f'book_name: "{NAME[book]}"',
           f'title: "{NAME[book]}"', f'author: "{AUTHOR} (1561–1636)"', f'edition: "{EDITION}"', '---', '']
    if (out_dir(book) / 'zh').exists():
        out.insert(-2, f'zh_url: "/jones/{book}/"')
    other = '3john' if book == '2john' else '2john'

    def toc(group):
        return [f'  <li><a href="{{{{ site.baseurl }}}}/jones/{book}/{p["slug"]}/">{p["title"]}'
                + (f'<small>{p["subtitle"]}</small>' if p.get('subtitle') else '')
                + '</a></li>' for p in pages if p['group'] == group]
    out.append('<h2 class="jw-group">Prefatory Matter</h2>')
    out += ['<ul class="jw-toc">'] + toc('front') + ['</ul>']
    out.append('<h2 class="jw-group">Commentary</h2>')
    out.append('<ul class="jw-toc">')
    out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/jones/{book}/{p["slug"]}/">{p["short"]}'
               f'<small>{p["rng"]}</small></a></li>' for p in pages if p['group'] == 'section')
    out.append('</ul>')
    out.append('<h2 class="jw-group">Tables</h2>')
    out += ['<ul class="jw-toc">'] + toc('back') + ['</ul>']
    g, o = gap_counts(pages)
    n, w, c = gap_stats(book)
    rv = jc.tsv(book, 'gap_review.tsv')
    done = {int(r[0]) for r in jc.tsv(book, 'gap_approved.tsv')}
    n_p = sum(1 for r in rv if r[1].startswith('P:') and int(r[0]) not in done)
    n_q = sum(1 for r in rv if r[1] == '?')
    out.append('<div class="jw-note">')
    out.append(f'<p><b>About this text.</b> The second and third Epistles of St John are expounded at the end of William '
               f'Jones\'s <i>Commentary upon the Epistles of Saint Paul to Philemon, and to the Hebrewes</i> (London, 1635; '
               f'STC 14739.5); see also <a href="{{{{ site.baseurl }}}}/jones/{other}/">{NAME[other]}</a>. Text from EEBO-TCP '
               'A04619, keyed by hand from the EEBO microfilm (Phase 1, public domain). Original spelling and italics are '
               'retained; the long s is printed as s. Page numbers of the original are kept as in-page anchors.</p>')
    if w or c:
        out.append(f'<p><b>Gaps.</b> The keyers left {n:,} places blank: Greek, which they did not transcribe, and letters '
                   f'they could not read from the film. {w:,} have been read from the grayscale scan of the same microfilm '
                   '(Internet Archive), place by place against the page image, with the 1636 issue as a second witness for doubtful places'
                   + (f'; {c:,} are editorial conjectures shown <span class="jw-conj">[in brackets]</span>, each explained in the table below' if c else '')
                   + (f'. {n_p + n_q:,} place{"s" if n_p + n_q > 1 else ""} remain{"" if n_p + n_q > 1 else "s"} marked <span class="jw-gap">in red</span> ('
                      + ', '.join(x for x in (f'{n_p} proposed readings awaiting approval' if n_p else '', f'{n_q} unreadable' if n_q else '') if x)
                      + '); all are listed below.' if n_p + n_q else '.') + '</p>')
    else:
        out.append(f'<p><b>Gaps.</b> The keyers did not transcribe Greek: {g} Greek words or phrases in these pages are '
                   f'marked <span class="jw-gap">〈Greek〉</span>, and {o} other places they could not read are marked '
                   '<span class="jw-gap">in red</span>. They have not yet been checked against the page images.</p>')
    out.append('<p class="jw-note-zh"><b>文本说明。</b>约翰二书、三书的讲解附在琼斯《腓利门书、希伯来书注释》卷末'
               '（伦敦 1635 年，STC 14739.5），本站只收这两篇，两卷分开上线'
               f'（另一卷见 <a href="{{{{ site.baseurl }}}}/jones/{other}/">{NAME[other]}</a>）。底本是 EEBO-TCP 人工录入本 A04619'
               '（据 EEBO 缩微胶片录入，第一期，已进入公有领域）。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。'
               + (f'录入本空着的 {n:,} 处（录入者不录的希腊文与读不出的字），{w:,} 处已对照同一卷缩微胶片的灰度扫描'
                  '（Internet Archive）逐处看图读出，读不定的再拿 1636 年印本对照'
                  + (f'；{c:,} 处为编者推补，以 <span class="jw-conj">[另一种字体加方括号]</span> 标出，原书所见与补改依据逐条列在下表' if c else '')
                  + (f'；其余 {n_p + n_q:,} 处（' + '、'.join(x for x in (f'推断待同意 {n_p}' if n_p else '', f'读不出 {n_q}' if n_q else '') if x) + '）标红留在明面，逐条列在下表' if n_p + n_q else '')
                  + f'。判读记录见 <code>jones_raw/{book}/gap_review.tsv</code>。</p>'
                  if (w or c) else
                  f'录入者没有录希腊文，本卷正文 {g} 处以 <span class="jw-gap">〈Greek〉</span> 标出；另有 {o} 处读不出的字标红。'
                  '这些都还没有对照原书影像补出，判读做完后再更新本页。</p>'))
    out.extend(notes_tables(book))
    out.append('</div>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--book', choices=jc.BOOKS)
    a = ap.parse_args()
    meta_f = jc.BASE / 'en_meta.json'
    meta = json.loads(meta_f.read_text(encoding='utf-8')) if meta_f.exists() else {}
    stamp = now()
    for book in ([a.book] if a.book else jc.BOOKS):
        publish(book, a.apply, meta, stamp)
    if a.apply:
        meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
