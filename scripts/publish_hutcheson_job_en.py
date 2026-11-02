#!/usr/bin/env python3
"""hutcheson_raw/job/en_chapters/*.md（+ manual_fixes.tsv）→ hutcheson/job/*.md　赫奇森《约伯记释义》(1669)

    python3 scripts/publish_hutcheson_job_en.py            # 试跑，只报不写
    python3 scripts/publish_hutcheson_job_en.py --apply

照搬 publish_hutcheson_en.py（约翰福音），换书目；约翰那份不动。

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
from extract_hutcheson_job import NV, NCH, GAP_PAGES  # noqa: E402

hc.use('job')

ROOT = Path(__file__).resolve().parent.parent
RAW = hc.RAW
OUT = ROOT / 'hutcheson' / 'job'
META = RAW / 'en_meta.json'
PAGES = RAW / 'pages_en.json'

BOOK_ID = 'job'
BOOK_NAME = 'Hutcheson on Job'
AUTHOR = 'George Hutcheson'

# 卷首次序照原书：书名页、致读者、勘误表（本书勘误在卷首），再是全书论旨
FRONT = [
    ('title', 'Title Page', 'London, 1669'),
    ('reader', 'To the Reader', AUTHOR),
    ('errata', 'Errata', AUTHOR),
    ('argument', 'The Argument', AUTHOR),
]
TAIL = []

RE_BOX = re.compile(r'<div class="hc-text" markdown="1">\n\n(.*?)\n\n</div>', re.S)
RE_VID = re.compile(r'<p class="hc-v" id="v(\d+)"')
# 节号印错的（21:21、33:2）带 title 说明；框首节取锚点那一节，不取印的号
RE_VANY = re.compile(r'<p class="hc-v[^"]*"(?: id="v(\d+)")?(?: title="[^"]*")? markdown="1">(?:<span class="hc-pb"[^>]*></span>)*\*\*(\d+)\*\*')


def box_first(box):
    """经文框的 (首节, 是否以续列起头)。

    续列有两种：带号的后半节（8:6、21:7——原书两半都印号）首节就是那个号；
    不带号的（13:4 后半 `— and laid aside…`）首节是框里头一个号的前一节。"""
    first = box.split('\n')[0]
    nums = [int(a or b) for a, b in RE_VANY.findall(box)]
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
    return f'Job {ch}:{a}' if a == b else f'Job {ch}:{a}–{b}'


MANUAL = RAW / 'manual_pages'


def load_front(slug, fixes):
    """扉页：有手排的 HTML（manual_pages/<slug>.html）就用，没有就照 TCP 抽取（本书暂无）。"""
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else hc.load(slug, fixes)


def build_pages():
    fixes = hc.load_fixes()
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_front(slug, fixes), group='front'))
    for ch in range(1, NCH + 1):
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
        anchors = ''.join(f'\n\n<div class="commentary-anchor" id="job-{ch}-{v}"></div>' for v in vs)
        return f'<div class="hc-text" markdown="1">\n\n{box}\n\n</div>{anchors}'
    return RE_BOX.sub(sub, body)


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = 'Editorial conjecture: illegible in the 1669 source; supplied from context (编者据上下文推补，非原书原文)'


def render_conj(m):
    # 编者推补（gap_review_conj.tsv / manual_errata.tsv）：方括号 + 另色，标明不是原文。
    # 推补为「删去」的（⟦⟧）不留痕迹。
    t = m.group(1)
    if not t:
        return ''
    return f'<span class="hc-conj" title="{CONJ_TITLE}">[{t}]</span>'


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示（2026-10-19，同雷登）。
RE_OL = re.compile(r'^(\d+)\. ', re.M)


def render_body(body, ch=None):
    body = add_anchors(body, ch)
    body = RE_OL.sub(r'\1\\. ', body)
    body = RE_CONJ.sub(render_conj, body)
    body = hc.TOK.sub(lambda m: f'<span class="hc-gap" title="TCP: illegible in source">{m.group(0)}</span>', body)
    # 14 章缩微胶片缺两页（原书第 194–195 页），TCP 标 〈2 pages missing〉：明标出来，待补
    body = body.replace(GAP_PAGES, '<span class="hc-gap hc-lost" title="TCP: 2 pages missing from the microfilm (原书第 194–195 页缺，待据他本补)">'
                        '〈2 pages missing〉</span>')
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
        fm = ['---', 'layout: hutcheson-job-chapter', f'book_id: {BOOK_ID}',
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
        for ch in range(1, NCH + 1):
            secs = [p for p in pages if p.get('ch') == ch]
            slug = str(ch)
            meta.setdefault(slug, stamp)
            fm = ['---', 'layout: hutcheson-job-chapter', f'book_id: {BOOK_ID}',
                  f'book_name: "{BOOK_NAME}"', f'title: "Job {ch}"',
                  f'subtitle: "{AUTHOR}"', f'date: {meta[slug]}', f'chapter: {ch}',
                  'verse_from: 1', f'verse_to: {NV[ch]}']
            if ch > 1:
                fm += [f'prev_url: "/hutcheson/{BOOK_ID}/{ch - 1}/"', f'prev_label: "Job {ch - 1}"']
            if ch < NCH:
                fm += [f'next_url: "/hutcheson/{BOOK_ID}/{ch + 1}/"', f'next_label: "Job {ch + 1}"']
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
        (ROOT / '_data' / 'hutcheson_job.json').write_text(
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
    out = ['---', 'layout: hutcheson-job-book', f'book_id: {BOOK_ID}',
           f'book_name: "{BOOK_NAME}"', f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1615–1674) · Minister of the Gospel at Edinburgh"',
           'edition: "An Exposition of the Book of Job, being the Sum of CCCXVI Lectures · London: Ralph Smith, 1669"',
           '---', '']
    out.append('<h2 class="hc-group">Prefatory Matter</h2>')
    out.append('<ul class="hc-toc">')
    for p in pages:
        if p['group'] == 'front':
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{p["slug"]}/">{p["title"]}</a></li>')
    out.append('</ul>')
    out.append('<h2 class="hc-group">The Exposition</h2>')
    out.append('<ul class="hc-chgrid">')
    for ch in range(1, NCH + 1):
        out.append(f'  <li><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{ch}/">Chapter {ch}</a></li>')
    out.append('</ul>')
    left = sum(len(hc.TOK.findall(p['body'])) for p in pages)
    out.append('<div class="hc-note">')
    out.append('<p><b>About this text.</b> The text is EEBO-TCP A45240, keyed by hand from microfilm images of the '
               '1669 London edition (Cambridge University Library copy; CC0). Original spelling and italics '
               'are retained; the long s is printed as s. Page numbers of the 1669 edition are kept as in-page anchors.</p>')
    out.append(f'<p><b>Illegible places.</b> {left} places the keyers could not read on the microfilm are marked '
               '<span class="hc-gap">•</span> (one letter each), <span class="hc-gap">〈◊〉</span> (a word) or '
               '<span class="hc-gap">〈…〉</span> (a longer stretch); they have not yet been restored. '
               'Two pages of chapter 14 (pp. 194–195) are missing from the microfilm and are marked in place. '
               'Two verse numbers misprinted in the text boxes (21:21 printed as 22, 33:2 printed as 3) are kept as printed.</p>')
    out.append(f'<p class="hc-note-zh"><b>文本说明。</b>本书据 EEBO-TCP A45240，即 1669 年伦敦版（剑桥大学图书馆藏本缩微胶片）的人工录入本，'
               '保留原书拼写与斜体，长 ſ 作 s，原书页码作页内锚点。'
               f'录入本有 {left} 个胶片上读不出的缺字记号（<span class="hc-gap">•</span> 一个字母、'
               '<span class="hc-gap">〈◊〉</span> 一个词、<span class="hc-gap">〈…〉</span> 一截），尚未判读补出，暂照录。'
               '第 14 章缩微胶片缺两页（原书第 194–195 页），已在原处标明，待据他本补。'
               '经文框里有两处节号印错（21:21 印作 22、33:2 印作 3），照原书显示，跳转按实际节。'
               '来源与处理见 <code>hutcheson_raw/job/PROVENANCE.md</code>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
