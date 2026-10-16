#!/usr/bin/env python3
"""hutcheson_raw/john/en_chapters/*.md（+ manual_fixes.tsv）→ hutcheson/john/*.md

    python3 scripts/publish_hutcheson_en.py            # 试跑，只报不写
    python3 scripts/publish_hutcheson_en.py --apply

分页（同 publish_perkins_en）：按**被讲解的经文段**切页——原书每段讲解前先排出
经文（.hc-text），这是原书自己的段落单位。只有经文、讲解不足 300 字符的段并入
下一段。章首提要随本章第一页。

作者在各章提要里也给了分段（`first… to v. 15. Next… to v. 37.`），但粒度极不均
（6:22–71 一段 17 万字符，2:12 一段一节），按它切还得再自己细分，那就不是原书
结构了，所以不用。

页名：`<章>-<首节>`（`3-16`）；卷首 `title` / `calamy` / `dedication` / `reader`，
正文前 `argument`，书末 `errata`。每章另出一页目录 `<章>.md`（「历代解经」与对照
抽屉按章号找页面）。

**date 一律沿用 en_meta.json 里的原值**，新页才写当前真实时间。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hutcheson_common as hc  # noqa: E402
from extract_hutcheson import NV  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = hc.RAW
OUT = ROOT / 'hutcheson' / 'john'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'

BOOK_ID = 'john'
BOOK_NAME = 'Hutcheson on John'
AUTHOR = 'George Hutcheson'

FRONT = [
    ('title', 'Title Page', 'London, 1657'),
    ('calamy', 'To the Christian Reader', 'Edmund Calamy'),
    ('dedication', 'The Epistle Dedicatory', 'To the Countesses of Wemyss and Buccleuch'),
    ('reader', 'To the Reader', AUTHOR),
    ('argument', 'The Argument', AUTHOR),
]
TAIL = [('errata', 'Errata', AUTHOR)]

RE_BOX = re.compile(r'<div class="hc-text" markdown="1">\n\n(.*?)\n\n</div>', re.S)
RE_VID = re.compile(r'<p class="hc-v" id="v(\d+)"')
RE_VANY = re.compile(r'<p class="hc-v[^"]*"(?: id="v\d+")? markdown="1">(?:<span class="hc-pb"[^>]*></span>)*\*\*(\d+)\*\*')


def box_first(box):
    """经文框的 (首节, 是否以续列起头)。

    续列有两种：带号的后半节（8:6、21:7——原书两半都印号）首节就是那个号；
    不带号的（13:4 后半 `— and laid aside…`）首节是框里头一个号的前一节。"""
    first = box.split('\n')[0]
    nums = [int(x) for x in RE_VANY.findall(box)]
    if 'hc-v-cont' not in first:
        return nums[0], False
    if re.search(r'\*\*\d+\*\*', first):
        return nums[0], True
    return nums[0] - 1, True


def split_chapter(ch, md):
    """一章 → [(首节, 末节, 正文)]。"""
    boxes = list(RE_BOX.finditer(md))
    segs = []
    for i, m in enumerate(boxes):
        end = boxes[i + 1].start() if i + 1 < len(boxes) else len(md)
        start = 0 if i == 0 else m.start()
        segs.append([box_first(m.group(1)), md[start:end]])
    merged, carry = [], None
    for k, (vf, body) in enumerate(segs):
        if carry:
            vf, body = carry[0], carry[1] + '\n\n' + body
            carry = None
        prose = RE_BOX.sub('', body)
        prose = re.sub(r'<[^>]+>', '', prose).strip()
        if len(prose) < 300 and k + 1 < len(segs):
            carry = (vf, body)
            continue
        merged.append([vf, body])
    out = []
    for i, ((v, _), body) in enumerate(merged):
        if i + 1 < len(merged):
            nv, ncont = merged[i + 1][0]
            last = nv if ncont else nv - 1     # 下一页以续列起头：那一节两页各占半
        else:
            last = NV[ch]
        out.append((v, max(v, last), body.strip()))
    slugs = [f'{ch}-{a}' for a, _, _ in out]
    if len(set(slugs)) != len(slugs):
        raise ValueError(f'ch{ch} 页名重复：{slugs}')
    return out


def vref(ch, a, b):
    return f'John {ch}:{a}' if a == b else f'John {ch}:{a}–{b}'


def build_pages():
    fixes = hc.load_fixes()
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=hc.load(slug, fixes), group='front'))
    for ch in range(1, 22):
        md = hc.load(str(ch), fixes)
        for a, b, body in split_chapter(ch, md):
            pages.append(dict(slug=f'{ch}-{a}', title=vref(ch, a, b), subtitle=AUTHOR,
                              body=body, group=f'ch{ch}', ch=ch, v1=a, v2=b))
    for slug, title, sub in TAIL:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=hc.load(slug, fixes), group='tail'))
    return pages


def add_anchors(body, ch):
    """经文框里每节的锚点挪到框**后面**的 commentary-anchor（07-verse-index §1：
    跳转要落在注释开头，不落在经文上）。一框连列几节就出几个锚点，都落在同一处讲解开头。"""
    if not ch:
        return body

    def sub(m):
        box = m.group(1)
        vs = RE_VID.findall(box)
        box = re.sub(r'(<p class="hc-v") id="v\d+"', r'\1', box)
        anchors = ''.join(f'\n\n<div class="commentary-anchor" id="john-{ch}-{v}"></div>' for v in vs)
        return f'<div class="hc-text" markdown="1">\n\n{box}\n\n</div>{anchors}'
    return RE_BOX.sub(sub, body)


def render_body(body, ch=None):
    body = add_anchors(body, ch)
    body = hc.TOK.sub(lambda m: f'<span class="hc-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    return body


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def fm_nav(pg, key):
    o = pg[key]
    if not o:
        return []
    return [f'{key}_url: "/hutcheson/{BOOK_ID}/{o["slug"]}/"', f'{key}_label: "{o["title"]}"']


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
        fm = ['---', 'layout: hutcheson-chapter', f'book_id: {BOOK_ID}',
              f'book_name: "{BOOK_NAME}"', f'title: "{pg["title"]}"',
              f'subtitle: "{pg["subtitle"]}"', f'date: {meta[slug]}']
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        fm += fm_nav(pg, 'prev') + fm_nav(pg, 'next')
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/hutcheson/{BOOK_ID}/zh/{slug}/"')
        fm.append('---')
        text = '\n'.join(fm) + '\n\n' + render_body(pg['body'], pg.get('ch')) + '\n'
        if a.apply:
            (OUT / f'{slug}.md').write_text(text, encoding='utf-8')

    if a.apply:
        # 章目录页
        for ch in range(1, 22):
            secs = [p for p in pages if p.get('ch') == ch]
            slug = str(ch)
            meta.setdefault(slug, stamp)
            fm = ['---', 'layout: hutcheson-chapter', f'book_id: {BOOK_ID}',
                  f'book_name: "{BOOK_NAME}"', f'title: "John {ch}"',
                  f'subtitle: "{AUTHOR}"', f'date: {meta[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/hutcheson/{BOOK_ID}/{ch - 1}/"', f'prev_label: "John {ch - 1}"']
            if ch < 21:
                fm += [f'next_url: "/hutcheson/{BOOK_ID}/{ch + 1}/"', f'next_label: "John {ch + 1}"']
            if (OUT / 'zh' / f'{slug}.md').exists():
                fm.append(f'zh_url: "/hutcheson/{BOOK_ID}/zh/{slug}/"')
            fm.append('---')
            lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>'
                            for p in secs)
            (OUT / f'{slug}.md').write_text('\n'.join(fm) + f'\n\n<ul class="hc-chtoc">\n{lst}\n</ul>\n',
                                            encoding='utf-8')
        # 章顶 verse-nav 数据：每章全部节号 → 所在页（跨页导航）
        nav = {}
        for pg in pages:
            if 'ch' in pg:
                for v in RE_VID.findall(pg['body']):
                    nav.setdefault(str(pg['ch']), []).append({'v': int(v), 'slug': pg['slug']})
        (ROOT / '_data' / 'hutcheson_john.json').write_text(
            json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        PAGES.write_text(json.dumps([{k: v for k, v in p.items() if k not in ('body', 'prev', 'next')}
                                     for p in pages], ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        (OUT / 'en').mkdir(exist_ok=True)
        (OUT / 'en' / 'index.html').write_text(build_index(pages), encoding='utf-8')
        if not (OUT / 'zh').exists():
            (OUT / 'index.html').write_text(build_index(pages), encoding='utf-8')

    left = sum(len(hc.TOK.findall(p['body'])) for p in pages)
    nch = sum(1 for p in pages if 'ch' in p)
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页（正文 {nch}）→ {OUT}；剩余缺字记号 {left}', file=sys.stderr)
    sizes = sorted(len(p['body']) for p in pages if 'ch' in p)
    print(f'  正文页长度 中位 {sizes[len(sizes) // 2] // 1000}k  最短 {sizes[0]}  最长 {sizes[-1] // 1000}k', file=sys.stderr)
    big = sorted(pages, key=lambda p: -len(p['body']))[:5]
    print('  最长：' + '  '.join(f"{p['slug']}({len(p['body']) // 1000}k)" for p in big), file=sys.stderr)


def build_index(pages):
    out = ['---', 'layout: hutcheson-book', f'book_id: {BOOK_ID}',
           f'book_name: "{BOOK_NAME}"', f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1615–1674) · Minister of the Gospel at Edinburgh"',
           'edition: "An Exposition of the Gospel of Jesus Christ according to John · London: Ralph Smith, 1657"',
           f'zh_url: "/hutcheson/{BOOK_ID}/"', '---', '']
    out.append('<h2 class="hc-group">Prefatory Matter</h2>')
    out.append('<ul class="hc-toc">')
    for p in pages:
        if p['group'] == 'front':
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>')
    out.append('</ul>')
    out.append('<h2 class="hc-group">The Exposition</h2>')
    out.append('<ul class="hc-chgrid">')
    for ch in range(1, 22):
        out.append(f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{ch}/">Chapter {ch}</a></li>')
    out.append('</ul>')
    out.append('<h2 class="hc-group">Back Matter</h2>')
    out.append('<ul class="hc-toc">')
    for p in pages:
        if p['group'] == 'tail':
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>')
    out.append('</ul>')
    out.append('<p class="hc-note">Source: EEBO-TCP A45241 (keyed from the 1657 London edition, Wing H3826 / ESTC R11373; '
               'CC0). Original spelling and italics retained; the long s is printed as s. Page numbers of the 1657 edition '
               'are kept as in-page anchors. Letters illegible in the source are restored only where this book’s own '
               'vocabulary admits a single reading; the rest are left marked in red. See '
               '<code>hutcheson_raw/john/PROVENANCE.md</code>.</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
