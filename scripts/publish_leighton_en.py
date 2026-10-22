#!/usr/bin/env python3
"""leighton_raw/1peter/en_chapters/*.md（+ manual_fixes.tsv）→ leighton/1peter/*.md

    python3 scripts/publish_leighton_en.py            # 试跑
    python3 scripts/publish_leighton_en.py --apply

骨架照搬 publish_hutcheson_en.py。分页：按被讲解的经文段（原书 77 个单元）一单元一页；
章首（本书只有章标题）随本章第一页。页名 `<章>-<首节>`；卷首 title1/reader1、title2/reader2，
两卷书末勘误 errata1/errata2。每章另出一页目录 `<章>.md`（历代解经与对照抽屉按章号找页面）。

date 一律沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leighton_common as lc  # noqa: E402
from extract_leighton import NV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = lc.RAW
OUT = ROOT / 'leighton' / '1peter'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'

BOOK_ID = '1peter'
BOOK_NAME = 'Leighton on 1 Peter'
AUTHOR = 'Robert Leighton'

VOL1_FRONT = [('title1', 'Title Page (Vol. I)', 'York, 1693'),
              ('reader1', 'To the Pious Reader', 'The Publisher')]
VOL1_TAIL = [('errata1', 'Errata (Vol. I)', '')]
VOL2_FRONT = [('title2', 'Title Page (Vol. II)', 'London, 1694'),
              ('reader2', 'To the Christian Reader', 'The Publisher')]
VOL2_TAIL = [('errata2', 'Errata (Vol. II)', '')]

RE_BOX = re.compile(r'<div class="lt-text" data-verses="([^"]*)" markdown="1">\n\n(.*?)\n\n</div>', re.S)


def split_chapter(ch, md):
    """一章 → [(首节, 末节, 正文)]。经文框之前的章标题随第一段。"""
    boxes = list(RE_BOX.finditer(md))
    segs = []
    for i, m in enumerate(boxes):
        end = boxes[i + 1].start() if i + 1 < len(boxes) else len(md)
        start = 0 if i == 0 else m.start()
        vs = [int(x) for x in m.group(1).split()] or [None]
        segs.append((vs, md[start:end]))
    out = []
    for i, (vs, body) in enumerate(segs):
        v1 = vs[0] if vs[0] else (out[-1][1] if out else 1)
        nxt = next((s[0][0] for s in segs[i + 1:] if s[0][0]), None)
        v2 = (nxt - 1) if nxt else NV[ch]
        v2 = max(v1, v2, max(v for v in vs if v) if vs[0] else v1)
        out.append((v1, v2, body.strip()))
    slugs = [f'{ch}-{a}' for a, _, _ in out]
    if len(set(slugs)) != len(slugs):
        raise ValueError(f'ch{ch} 页名重复：{slugs}')
    return out


def vref(ch, a, b):
    return f'1 Peter {ch}:{a}' if a == b else f'1 Peter {ch}:{a}–{b}'


MANUAL = Path(__file__).resolve().parent.parent / 'leighton_raw' / '1peter' / 'manual_pages'


def load(slug, fixes):
    """扉页：照原书影像手排的 HTML（manual_pages/<slug>.html；卷一 comment00leig n4、卷二 pract00leig n5–6），
    文字取自 TCP，分行、字号、斜体、字距、双线框与分隔线照原书。"""
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else lc.load(slug, fixes)


def build_pages():
    fixes = lc.load_fixes()
    pages = []

    def add_simple(lst, group):
        for slug, title, sub in lst:
            pages.append(dict(slug=slug, title=title, subtitle=sub, body=load(slug, fixes), group=group))
    add_simple(VOL1_FRONT, 'v1front')
    for ch in (1, 2):
        for a, b, body in split_chapter(ch, load(str(ch), fixes)):
            pages.append(dict(slug=f'{ch}-{a}', title=vref(ch, a, b), subtitle=AUTHOR, body=body,
                              group=f'ch{ch}', ch=ch, v1=a, v2=b))
    add_simple(VOL1_TAIL, 'v1tail')
    add_simple(VOL2_FRONT, 'v2front')
    for ch in (3, 4, 5):
        for a, b, body in split_chapter(ch, load(str(ch), fixes)):
            pages.append(dict(slug=f'{ch}-{a}', title=vref(ch, a, b), subtitle=AUTHOR, body=body,
                              group=f'ch{ch}', ch=ch, v1=a, v2=b))
    add_simple(VOL2_TAIL, 'v2tail')
    return pages


def add_anchors(body, ch):
    """经文框后面每节一个 commentary-anchor（07-verse-index §1）。"""
    if not ch:
        return body

    def sub(m):
        vs = m.group(1).split()
        anchors = ''.join(f'\n\n<div class="commentary-anchor" id="1peter-{ch}-{v}"></div>' for v in vs)
        return f'<div class="lt-text" markdown="1">\n\n{m.group(2)}\n\n</div>{anchors}'
    return RE_BOX.sub(sub, body)


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = 'Editorial conjecture, approved: illegible in the 1693/94 source; supplied from the stated evidence (编者推补，经同意；非原书原文)'


# 原书分条讲「2. It must be pure…」——段首「数字 + 点 + 空格」会被 kramdown 当成
# 有序列表，从 1 重新编号（页面上第 2 条显示成 1.）。转义那个点，原样显示。
# old-book-ocr §4.4 渲染层校验「行首 1. 」那一项（2026-10-19 补查出 205 段）。
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, ch=None):
    body = RE_OL.sub(r'\1\\. ', body)
    body = add_anchors(body, ch)
    body = RE_CONJ.sub(lambda m: f'<span class="lt-conj" title="{CONJ_TITLE}">[{m.group(1)}]</span>'
                       if m.group(1) else '', body)
    body = lc.TOK.sub(lambda m: f'<span class="lt-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/leighton/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o["title"]}"']


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
        fm = ['---', 'layout: leighton-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
              f'title: "{pg["title"]}"']
        if pg['subtitle']:
            fm.append(f'subtitle: "{pg["subtitle"]}"')
        fm.append(f'date: {meta[slug]}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/leighton/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        if a.apply:
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + render_body(pg['body'], pg.get('ch')) + '\n',
                                            encoding='utf-8')
    if a.apply:
        for ch in range(1, 6):
            secs = [p for p in pages if p.get('ch') == ch]
            slug = str(ch)
            meta.setdefault(slug, stamp)
            fm = ['---', 'layout: leighton-chapter', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
                  f'title: "1 Peter {ch}"', f'subtitle: "{AUTHOR}"', f'date: {meta[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/leighton/{BOOK_ID}/{ch - 1}/"', f'prev_label: "1 Peter {ch - 1}"']
            if ch < 5:
                fm += [f'next_url: "/leighton/{BOOK_ID}/{ch + 1}/"', f'next_label: "1 Peter {ch + 1}"']
            if (OUT / 'zh' / f'{slug}.md').exists():
                fm.append(f'zh_url: "/leighton/{BOOK_ID}/zh/{slug}/"')
            fm.append('---')
            lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/leighton/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>'
                            for p in secs)
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="lt-chtoc">\n{lst}\n</ul>\n', encoding='utf-8')
        nav = {}
        for pg in pages:
            if 'ch' in pg:
                for m in RE_BOX.finditer(pg['body']):
                    for v in m.group(1).split():
                        nav.setdefault(str(pg['ch']), []).append({'v': int(v), 'slug': pg['slug']})
        (ROOT / '_data' / 'leighton_1peter.json').write_text(json.dumps(nav, ensure_ascii=False, indent=1) + '\n',
                                                            encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        PAGES.write_text(json.dumps([{k: v for k, v in p.items() if k not in ('body', 'prev', 'next')} for p in pages],
                                    ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')
    left = sum(len(lc.TOK.findall(p['body'])) for p in pages)
    nch = sum(1 for p in pages if 'ch' in p)
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页（正文 {nch}）→ {OUT}；剩余缺字记号 {left}', file=sys.stderr)
    big = sorted(pages, key=lambda p: -len(p['body']))[:5]
    print('  最长：' + '  '.join(f"{p['slug']}({len(p['body']) // 1000}k)" for p in big), file=sys.stderr)


def build_index(pages):
    out = ['---', 'layout: leighton-book', f'book_id: {BOOK_ID}', f'book_name: "{BOOK_NAME}"',
           f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1611–1684) · sometime Archbishop of Glasgow"',
           'edition: "A Practical Commentary upon the First Epistle General of St. Peter · Vol. I York 1693; Vol. II London 1694"',
           '---', '']
    # 中译未出时根目录就是这份英文目录，「中文版 →」会链回自己——有 zh/ 才挂
    if (OUT / 'zh').exists():
        out.insert(-2, f'zh_url: "/leighton/{BOOK_ID}/"')

    def group(name, pred):
        lst = [p for p in pages if pred(p)]
        if not lst:
            return
        out.append(f'<h2 class="lt-group">{name}</h2>')
        out.append('<ul class="lt-toc">')
        out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/leighton/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>' for p in lst)
        out.append('</ul>')
    group('Volume I · Prefatory Matter', lambda p: p['group'] == 'v1front')
    out.append('<h2 class="lt-group">Volume I · Chapters 1–2</h2>')
    out.append('<ul class="lt-chgrid">' + ''.join(
        f'<li><a href="{{{{ site.baseurl }}}}/leighton/{BOOK_ID}/{c}/">Chapter {c}</a></li>' for c in (1, 2)) + '</ul>')
    group('Volume I · Errata', lambda p: p['group'] == 'v1tail')
    group('Volume II · Prefatory Matter', lambda p: p['group'] == 'v2front')
    out.append('<h2 class="lt-group">Volume II · Chapters 3–5</h2>')
    out.append('<ul class="lt-chgrid">' + ''.join(
        f'<li><a href="{{{{ site.baseurl }}}}/leighton/{BOOK_ID}/{c}/">Chapter {c}</a></li>' for c in (3, 4, 5)) + '</ul>')
    group('Volume II · Errata', lambda p: p['group'] == 'v2tail')
    out.append('<div class="lt-note">')
    out.append('<p><b>About this text.</b> EEBO-TCP A47642 (Vol. I, York: J. White, 1693, Wing L1028A) and A47643 '
               '(Vol. II, London: B.G. for Sam. Keble, 1694), keyed by hand from microfilm; CC0. Original spelling and '
               'italics are retained; the long s is printed as s. Page numbers of the original are kept as in-page '
               'anchors (each volume numbered separately).</p>')
    out.append('<p><b>Illegible places.</b> Of the 1,095 places the keyers could not read, 1,054 have been read '
               'directly from page images of the <i>same edition</i> (Internet Archive: Princeton Theological Seminary '
               'copies), using the 1864 Philadelphia reprint only to locate the passage; the original spelling is kept, '
               'including the printer’s own misprints. The rest are listed for approval; any conjecture adopted is '
               'shown <span class="lt-conj">[in brackets]</span>, and places still undecided remain marked in red.</p>')
    out.append('<p class="lt-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本：卷一 A47642（约克 1693）、卷二 A47643（伦敦 1694），'
               '保留原书拼写与斜体，长 ſ 作 s；两卷印本页码各自从 1 起，保留为页内锚点。录入本有 1,095 处读不出的字，'
               '其中 1,054 处已对照<b>同一版</b>原书（普林斯顿神学院藏本扫描）逐处看图判读，1864 年费城重印本只用来定位；'
               '原书拼写照录，连原书自己的排印错也照录。其余几十处列清单待定：经同意采用的推补以 '
               '<span class="lt-conj">[方括号]</span> 另色标出，仍未定的标红留在明面。'
               '逐条依据见 <code>leighton_raw/1peter/PROVENANCE.md</code>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
