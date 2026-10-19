#!/usr/bin/env python3
"""perkins_raw/galatians/en_chapters/*.md（+ manual_fixes.tsv）→ perkins/galatians/*.md

    python3 scripts/publish_perkins_en.py            # 试跑，只报不写
    python3 scripts/publish_perkins_en.py --apply

分页：原书是逐节讲解，每章十几万到五十万字符，一章一页太长。按**被讲解的
经文段**（`.pk-text` 带锚点的块）切页——这是原书自己的段落单位。连着列出、
中间没有讲解的几节经文（4:1–7 先列七节再一并讲）合成一页。

页名：`<章>-<首节>`（`3-13`）；卷首 `dedication` / `reader`，补编扉页
`supplement`，书末 `conclusion`。

**date 一律沿用 en_meta.json 里的原值**，新页才写当前真实时间
（CLAUDE.md：已有文件的时间不要修改）。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perkins_common as pc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'perkins_raw' / 'galatians'
OUT = ROOT / 'perkins' / 'galatians'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'

BOOK_ID = 'galatians'
BOOK_NAME = 'Perkins on Galatians'
NV = {1: 24, 2: 21, 3: 29, 4: 31, 5: 26, 6: 18}
# 和合本/KJV 分节：1:24 在 Geneva/1604 印本里与 1:23 同列，以印本标注为准显示，
# 节段范围只用于标题与索引。

FRONT = [
    ('dedication', 'The Epistle Dedicatorie', 'Ralph Cudworth to Robert, Lord Rich'),
    ('reader', 'To the Courteous Reader', 'Ralph Cudworth'),
]
SUPP = [('supplement', 'The Supplement upon the Sixth Chapter',
         'Title page and dedication to Sir Bassingbourne Gawdy')]
TAIL = [('conclusion', 'The Conclusion', 'Ralph Cudworth')]

RE_VBLOCK = re.compile(r'<div class="pk-text" id="v(\d+)" markdown="1">')


def author(ch):
    return 'William Perkins' if ch <= 5 else 'Ralph Cudworth'


def split_chapter(ch, md):
    """一章 → [(首节, 末节, 正文)]。"""
    cuts = [(m.start(), int(m.group(1))) for m in RE_VBLOCK.finditer(md)]
    if not cuts:
        return [(1, NV[ch], md)]
    segs = []
    for i, (pos, v) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(md)
        start = 0 if i == 0 else pos
        segs.append([v, md[start:end]])
    # 只有经文、没有讲解的段并入下一段
    merged = []
    carry = None
    for v, body in segs:
        if carry:
            v0, b0 = carry
            v, body = v0, b0 + '\n\n' + body
            carry = None
        prose = re.sub(r'<div class="pk-text".*?</div>', '', body, flags=re.S)
        prose = re.sub(r'<[^>]+>', '', prose).strip()
        if len(prose) < 300 and body is not segs[-1][1]:
            carry = (v, body)
            continue
        merged.append([v, body])
    if carry:
        merged.append(list(carry))
    out = []
    for i, (v, body) in enumerate(merged):
        last = merged[i + 1][0] - 1 if i + 1 < len(merged) else NV[ch]
        out.append((v, max(v, last), body.strip()))
    return out


def vref(ch, a, b):
    return f'Galatians {ch}:{a}' if a == b else f'Galatians {ch}:{a}–{b}'


def build_pages():
    fixes = pc.load_fixes()
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=pc.load(slug, fixes),
                          group='front'))
    for ch in range(1, 7):
        if ch == 6:
            for slug, title, sub in SUPP:
                pages.append(dict(slug=slug, title=title, subtitle=sub,
                                  body=pc.load(slug, fixes), group='supp'))
        md = pc.load(str(ch), fixes)
        for a, b, body in split_chapter(ch, md):
            pages.append(dict(slug=f'{ch}-{a}', title=vref(ch, a, b), subtitle=author(ch),
                              body=body, group=f'ch{ch}', ch=ch, v1=a, v2=b))
    for slug, title, sub in TAIL:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=pc.load(slug, fixes),
                          group='tail'))
    return pages


RE_VBOX = re.compile(r'<div class="pk-text" id="v(\d+)" markdown="1">(.*?)\n</div>', re.S)


def add_anchors(body, ch):
    """经文框的锚点 id 挪到框**后面**的 commentary-anchor（07-verse-index §1：
    跳转要落在注释开头，不落在经文上）。必须是 <div>，kramdown 不包它。"""
    if not ch:
        return body
    return RE_VBOX.sub(lambda m: f'<div class="pk-text" markdown="1">{m.group(2)}\n</div>\n\n'
                                 f'<div class="commentary-anchor" id="galatians-{ch}-{m.group(1)}"></div>', body)


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示（2026-10-19，同雷登）。
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, ch=None):
    body = add_anchors(body, ch)
    body = RE_OL.sub(r'\1\\. ', body)
    # 剩下判不出的缺字记号包成 .pk-gap，页面上看得见
    body = pc.TOK.sub(lambda m: f'<span class="pk-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                          text=True).stdout.strip()


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

    OUT.mkdir(parents=True, exist_ok=True)
    for pg in pages:
        slug = pg['slug']
        meta.setdefault(slug, stamp)
        fm = ['---', 'layout: perkins-chapter', f'book_id: {BOOK_ID}',
              f'book_name: "{BOOK_NAME}"', f'title: "{pg["title"]}"',
              f'subtitle: "{pg["subtitle"]}"', f'date: {meta[slug]}']
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        for k in ('prev', 'next'):
            if pg[k]:
                fm += [f'{k}_url: "/perkins/{BOOK_ID}/{pg[k]["slug"]}/"',
                       f'{k}_label: "{pg[k]["title"]}"']
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/perkins/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        text = '\n'.join(fm) + '\n\n' + render_body(pg['body'], pg.get('ch')) + '\n'
        if a.apply:
            (OUT / f'{slug}.md').write_text(text, encoding='utf-8')

    if a.apply:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        PAGES.write_text(json.dumps([{k: v for k, v in p.items() if k not in ('body', 'prev', 'next')}
                                     for p in pages], ensure_ascii=False, indent=1) + '\n',
                         encoding='utf-8')
        # 章目录页 /perkins/galatians/<章>/：「历代解经」与对照抽屉按章号找页面
        # （build_commentaries_index 认 <N>.md），本书按经文段分页，所以每章另出一页目录。
        for ch in range(1, 7):
            secs = [p for p in pages if p.get('ch') == ch]
            slug = str(ch)
            meta.setdefault(slug, stamp)
            fm = ['---', 'layout: perkins-chapter', f'book_id: {BOOK_ID}',
                  f'book_name: "{BOOK_NAME}"', f'title: "Galatians {ch}"',
                  f'subtitle: "{author(ch)}"', f'date: {meta[slug]}', f'chapter: {ch}',
                  f'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/perkins/{BOOK_ID}/{ch - 1}/"', f'prev_label: "Galatians {ch - 1}"']
            if ch < 6:
                fm += [f'next_url: "/perkins/{BOOK_ID}/{ch + 1}/"', f'next_label: "Galatians {ch + 1}"']
            if (OUT / 'zh' / f'{slug}.md').exists():
                fm.append(f'zh_url: "/perkins/{BOOK_ID}/zh/{slug}/"')
            fm.append('---')
            lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/perkins/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>'
                            for p in secs)
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="pk-chtoc">\n{lst}\n</ul>\n',
                                            encoding='utf-8')
        # 章顶 verse-nav 数据：每章全部节号 → 所在页（跨页导航）
        nav = {}
        for pg in pages:
            if 'ch' in pg:
                for v in RE_VBLOCK.findall(pg['body']):
                    nav.setdefault(str(pg['ch']), []).append({'v': int(v), 'slug': pg['slug']})
        (ROOT / '_data' / 'perkins_galatians.json').write_text(
            json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
        # 中文目录未出之前，书的首页先指向英文目录
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')

    left = sum(len(pc.TOK.findall(p['body'])) for p in pages)
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页 → {OUT}；剩余缺字记号 {left}',
          file=sys.stderr)
    big = sorted(pages, key=lambda p: -len(p['body']))[:5]
    print('  最长：' + '  '.join(f"{p['slug']}({len(p['body']) // 1000}k)" for p in big),
          file=sys.stderr)


GROUP_NAMES = {
    'front': 'Prefatory Matter', 'supp': None, 'tail': None,
    **{f'ch{i}': f'Chapter {i}' for i in range(1, 7)},
}


def build_index(pages):
    out = ['---', 'layout: perkins-book', f'book_id: {BOOK_ID}',
           f'book_name: "{BOOK_NAME}"', 'title: "Perkins on Galatians"',
           'author: "William Perkins (chs. 1–5) · Ralph Cudworth (ch. 6)"',
           'edition: "A Commentarie or Exposition vpon the Fiue First Chapters of the Epistle to the Galatians · Cambridge: John Legat, 1604"',
           f'zh_url: "/perkins/{BOOK_ID}/"', '---', '']
    groups = []
    for p in pages:
        g = p['group'] if p['group'] not in ('supp',) else 'ch6'
        if g == 'tail':
            g = 'ch6'
        if not groups or groups[-1][0] != g:
            groups.append((g, []))
        groups[-1][1].append(p)
    for g, lst in groups:
        name = GROUP_NAMES[g]
        if g == 'ch6':
            name = 'Chapter 6 · The Supplement by Ralph Cudworth'
        out.append(f'<h2 class="pk-group">{name}</h2>')
        out.append('<ul class="pk-toc">')
        for p in lst:
            label = p['title'] if 'ch' in p else f"{p['title']}"
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/perkins/{BOOK_ID}/{p["slug"]}/">{label}</a></li>')
        out.append('</ul>')
    out.append('<p class="pk-note">Source: EEBO-TCP A09383 (keyed from the 1604 Cambridge edition, STC 19680; CC0). '
               'Original spelling and italics retained; page numbers of the 1604 edition are kept as in-page anchors. '
               'Readings illegible in the source are filled from the page images of the same edition '
               '(Internet Archive), see <code>perkins_raw/galatians/PROVENANCE.md</code>.</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
