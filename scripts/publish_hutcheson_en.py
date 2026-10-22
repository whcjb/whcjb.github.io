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


MANUAL = RAW / 'manual_pages'


def load_front(slug, fixes):
    """扉页：照 1657 原书影像手排的 HTML（manual_pages/<slug>.html；Google Books vy1kAAAAcAAJ PP5），
    文字取自 TCP，分行、字号、字距、双线框、分隔线照原书，花饰裁自原图。"""
    f = MANUAL / f'{slug}.html'
    return f.read_text(encoding='utf-8').strip() if f.exists() else hc.load(slug, fixes)


def build_pages():
    fixes = hc.load_fixes()
    pages = []
    for slug, title, sub in FRONT:
        pages.append(dict(slug=slug, title=title, subtitle=sub, body=load_front(slug, fixes), group='front'))
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


RE_CONJ = re.compile(r'⟦([^⟧]*)⟧')
CONJ_TITLE = 'Editorial conjecture: illegible in the 1657 source; supplied from context (编者据上下文推补，非原书原文)'


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


# ── 书首页「最后 29 处缺字」逐条说明 ─────────────────────────────────
CONJ_TSV = RAW / 'gap_review_conj.tsv'
ERRATA_TSV = RAW / 'manual_errata.tsv'
REV1841 = RAW / 'gap_review_1841.tsv'
# 这两处原在推补之列，复查时在 1841 本里找到了吻合的读法，改为 1841 判出（不加括号）
MOVED_TO_1841 = {('13', 31), ('9', 22)}
ZH_BOOK = {'calamy': '卡拉米序', 'errata': '书末勘误表', 'dedication': '献辞', 'reader': '致读者', 'argument': '论旨'}


def _locate(slug, needle_pos, pages):
    """缺字在 en_chapters/<slug>.md 里的位置 → (显示位置, 页面 slug)。"""
    if not slug.isdigit():
        return ZH_BOOK.get(slug, slug), slug
    raw = (hc.SRC / f'{slug}.md').read_text(encoding='utf-8')
    vs = re.findall(r'id="v(\d+)"', raw[:needle_pos])
    ch = int(slug)
    v = int(vs[-1]) if vs else None
    secs = [p for p in pages if p.get('ch') == ch]
    if v is None:
        return f'约翰福音第 {ch} 章章首提要', secs[0]['slug']
    pg = next((p for p in secs if p['v1'] <= v <= p['v2']), secs[-1])
    rng = f"{pg['v1']}" if pg['v1'] == pg['v2'] else f"{pg['v1']}–{pg['v2']}"
    return f'约翰福音 {ch}:{rng} 讲解', pg['slug']


def conj_table(pages):
    """→ HTML 表格行。数据只从三张表取（推补表、errata 表、1841 复核表中移入的两条），
    表里改了，首页说明自动跟着变，不会两处说法不一。"""
    rows = []

    def esc(x):
        return x.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def show(x):
        return esc(x).replace('⟦', '<span class="hc-conj">[').replace('⟧', ']</span>')
    for ln in CONJ_TSV.read_text(encoding='utf-8').splitlines():
        if not ln or ln.startswith('#'):
            continue
        slug, o, tcp, fixed, ev = ln.split('\t')
        raw = (hc.SRC / f'{slug}.md').read_text(encoding='utf-8')
        m = list(hc.TOK.finditer(raw))[int(o)]
        loc, pg = _locate(slug, m.start(), pages)
        grade, why = ev.split('｜', 1)
        # ⟦⟧（空推补）＝删去：删去的是标点就写「（删去标点）」，整个记号删就写「（删去）」
        if fixed == '⟦⟧':
            now = '（删去）'
        elif fixed.endswith('⟦⟧'):
            now = esc(fixed[:-2]) + '（删去标点）'
        else:
            now = show(fixed)
        rows.append((slug, m.start(), loc, pg, esc(tcp), now, grade, esc(why)))
    for ln in ERRATA_TSV.read_text(encoding='utf-8').splitlines():
        if not ln or ln.startswith('#'):
            continue
        slug, old, new, ev = ln.split('\t')
        raw = (hc.SRC / f'{slug}.md').read_text(encoding='utf-8')
        pos = raw.find(old.split('•')[0][-12:]) if '•' in old else raw.find(old)
        loc, pg = _locate(slug, max(pos, 0), pages)
        grade, why = ev.split('｜', 1)
        rows.append((slug, max(pos, 0), loc, pg, esc(old), show(new), grade, esc(why)))
    for ln in REV1841.read_text(encoding='utf-8').splitlines():
        if not ln or ln.startswith('#'):
            continue
        f = ln.split('\t')
        if (f[0], int(f[1])) not in MOVED_TO_1841:
            continue
        raw = (hc.SRC / f'{f[0]}.md').read_text(encoding='utf-8')
        m = list(hc.TOK.finditer(raw))[int(f[1])]
        loc, pg = _locate(f[0], m.start(), pages)
        why = ('复查时在 1841 本里找到对应文字：' + f[4].replace('img 1841 ', '', 1)
               + '，与录入本残字吻合，按 1841 本补出，不加括号。')
        rows.append((f[0], m.start(), loc, pg, esc(f[2]), esc(f[3]), '1841 本吻合', esc(why)))

    def key(r):
        s = r[0]
        return (0, int(s), r[1]) if s.isdigit() else ((-1 if s == 'calamy' else 1), 0, r[1])
    rows.sort(key=key)
    out = ['<table class="hc-conjtab">',
           '<tr><th>#</th><th>位置</th><th>录入本原样</th><th>现在作</th><th>把握</th><th>依据</th></tr>']
    for i, (slug, o, loc, pg, tcp, now, grade, why) in enumerate(rows, 1):
        why = re.sub(r'（PA(\d+)）', r'（第 \1 页）', why)
        why = re.sub(r'PA(\d+) ', r'1841 本第 \1 页作 ', why)
        out.append(f'<tr><td>{i}</td><td><a href="{{{{ site.baseurl }}}}/hutcheson/{BOOK_ID}/{pg}/">{loc}</a></td>'
                   f'<td><code>{tcp}</code></td><td>{now}</td><td class="hc-grade">{grade}</td><td>{why}</td></tr>')
    out.append('</table>')
    return '\n'.join(out), len(rows)


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
    out.append('<div class="hc-note">')
    out.append('<p><b>About this text.</b> The text is EEBO-TCP A45241, keyed by hand from microfilm images of the '
               '1657 London edition (Wing H3826; Cambridge University Library copy; CC0). Original spelling and italics '
               'are retained; the long s is printed as s. Page numbers of the 1657 edition are kept as in-page anchors.</p>')
    out.append('<p><b>Illegible places.</b> The keyers could not read 838 places on the microfilm. They have been restored '
               'in three ways, in this order of evidence: (1) where this book\u2019s own vocabulary admits only one reading; '
               '(2) by comparing, word by word, the page images of the 1841 London reprint (T. Ward &amp; Co., '
               '\u201cReprinted from the Edition of 1657\u201d; Google Books, British Library copy), keeping the 1657 spelling; '
               '(3) where neither applies, from the context or the cited source. Readings of the third kind that the '
               'evidence does not fix are shown <span class="hc-conj">[in brackets]</span>: they are editorial conjectures, '
               'not the words of the 1657 edition. Every one of the last 29 illegible marks is listed with its evidence in the table below. '
               'The EarlyPrint machine-filled readings were checked and not used.</p>')
    out.append('<p class="hc-note-zh"><b>文本说明。</b>本书据 EEBO-TCP A45241，即 1657 年伦敦初版（剑桥大学图书馆藏本缩微胶片）的人工录入本，保留原书拼写与斜体，长 ſ 作 s。'
               '录入本有 838 处胶片上读不出的字，依证据强弱分三步补出：① 本书自身用词只容一种读法的；'
               '② 逐处对照 1841 年伦敦 T. Ward 重印本（扉页注明「据 1657 年版重印」，大英图书馆藏本）的页面影像判读，拼写仍按 1657 年；'
               '③ 以上都无从判定的，据上下文或所引出处推补。'
               '<b>凡用 <span class="hc-conj">[方括号]</span> 另色标出的，都是编者推补，不是 1657 年原书的文字</b>；鼠标移上去可见说明。'
               '这最后一步怎么补的，下表逐条交代。'
               'EarlyPrint 项目的机器补字经比对错误较多，未采用。逐条依据见 <code>hutcheson_raw/john/PROVENANCE.md</code>。</p>')
    tab, n = conj_table(pages)
    out.append(f'<h3 class="hc-conjhead">最后 29 个缺字记号逐条说明（共 {n} 个位置）</h3>')
    out.append('<p class="hc-note-zh">前两步（本书用词、1841 年本影像）补完之后，录入本里还剩 29 个缺字记号，分布在下表 '
               f'{n} 个位置（有的位置一个词里有两个记号）。下表逐条列出：在哪里、录入本原来是什么样（<code>•</code> 是一个读不出的字母，'
               '<code>▪</code> 是一个认不清的标点，<code>〈Greek〉</code> 是一段没录的希腊文）、现在作什么、把握多大、依据是什么。'
               '「把握」一栏：<b>1841 本吻合</b>＝重印本该处文字与残字完全吻合；<b>1841 本为据</b>＝按重印本补，残字无冲突；'
               '<b>1841 本为据·字母不合</b>＝按重印本的词义补，但残字字母与之不完全相合，1657 年原拼法不明；'
               '<b>经文为据</b>＝被引的经文原句；<b>回查正文</b>＝勘误表条目，按它所指的正文位置核出；'
               '<b>推断</b>＝没有直接证据，据上下文推定；<b>无依据</b>＝无法推定，只作说明。'
               '除「1841 本吻合」两条外，其余在正文里都以 <span class="hc-conj">[方括号]</span> 另色标出。'
               '点「位置」可跳到该页。</p>')
    out.append(tab)
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
