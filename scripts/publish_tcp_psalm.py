#!/usr/bin/env python3
"""EEBO-TCP 录入本的诗篇单篇专书 → <作者>/<书>/（英文版）。各书一份 BOOKS 配置，共用这一套提取与发布。

    python3 scripts/publish_tcp_psalm.py reynolds-psalm110
    python3 scripts/publish_tcp_psalm.py all

源文件 <作者>_raw/<书>/src/<TCP>.xml（取自 github textcreationpartnership/<TCP>，CC0）。
每书一对独立 layout（_layouts/<作者>-<书>-chapter.html / -book.html），由本脚本按 LAYOUT_* 模板生成，
类名前缀与配色各书不同（每本书独立样式，用户既定规矩）；生成后可单独手改，再跑本脚本不覆盖已有 layout（--layouts 强制）。

分页（BOOKS[...]['units']）：
  · ('divs', path)：path 指到的那一层 div 一个一页（如考珀 22 个字母、史密斯各节）。
  · ('pages', path, N)：同上，但一个 div 超过 N 个印本页就按段落、照印本页码约 N 页一切（雷诺兹第 1–4 节）。
各页页首可挂卷首目录里落在本页页码范围内的条目（contents='toc'）。
TCP 读不出的字照 tcp_tei 记号录入、页面标红（.<P>-gap）。date 沿用 en_meta.json 原值，新页才写当前真实时间。
"""
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcp_tei as tt                    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEI = tt.TEI
TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
FRONT_LABEL = {'title_page': ('title', 'Title Page', '书名页'), 'dedication': ('dedication', 'The Epistle Dedicatory', '献辞'),
               'to_the_reader': ('to-the-reader', 'To the Reader', '致读者'), 'errata': ('errata', 'Errata', '勘误表'),
               'Psalm_n51': ('the-psalm', 'The Contents: Psalm 51', '全篇经文'),
               'table_of_doctrines': ('doctrines', 'The Table of the Principal Doctrines', '要义一览'),
               'diagram': ('method', 'The Method of the Psalm', '全篇纲目'), 'prayer': ('prayers', 'Prayers', '祷文')}

BOOKS = {
    'reynolds-psalm110': dict(
        tcp='A10650', author='reynolds', book='psalm110', P='ry', c0='#23503a', c1='#34794f', psalm=110,
        cls='ReynoldsPs110',
        hero='Psalm 110', short='Reynolds on Psalm 110',
        title_en='An Explication of the Hundred and Tenth Psalm',
        tagline='Edward Reynolds · An Explication of the Hundreth and Tenth Psalme',
        edition='London: Felix Kyngston for Robert Bostocke, 1632 · STC 20927',
        year='1632',
        front=['title_page', 'dedication', 'to_the_reader'], back=['errata'],
        units=('pages', 'body/div', 30), contents='toc',
        about_en='Reynolds preached these sermons on Psalm 110 as preacher at Lincoln\'s Inn and published them in 1632. '
                 'Each verse of the psalm is one part of the book; the long expositions of verses 1–4 are here divided into '
                 'pages of about thirty printed pages each, and each page is headed by the entries of Reynolds\'s own table '
                 'of contents that fall within it.',
        about_zh='雷诺兹任林肯律师学院讲道人时讲诗篇 110 篇，1632 年出版。原书按经节分部；第 1–4 节讲得很长，本站按原书页码约三十页一切，'
                 '各页页首列出作者卷首目录里落在本页的条目。',
        omitted_en='The index of Scripture places is not included.', omitted_zh='卷末经文索引未收。'),
    'cowper-psalm119': dict(
        tcp='A19498', author='cowper', book='psalm119', P='cw', c0='#6b6128', c1='#a49746', psalm=119,
        short='Cowper on Psalm 119', hero='Psalm 119',
        title_en="A Holy Alphabet for Sion's Scholars",
        tagline="William Cowper · A Holy Alphabet for Sion's Scholars",
        edition='London: H. Lownes for John Budge, 1613 · STC 5926', year='1613',
        front=['title_page', 'dedication'], back=[], body_back=['prayer'],
        units=('divs', 'body/div/div'), acrostic=True,
        notes={'v73-80': 'Verse 80 is not expounded in the original edition: the exposition of verse 79 ends on '
                         'p. 197 and Caph begins on p. 198. 原书漏讲第 80 节：第 79 节讲到第 197 页结束，第 198 页即接 CAPH。'},
        about_en='Cowper, minister at Perth and from 1612 Bishop of Galloway, published this verse-by-verse commentary '
                 'on the whole of Psalm 119 in 1613 (its running title is The Anatomie of a Christian); each of the '
                 'twenty-two letters of the Hebrew alphabet is '
                 'one page here. Verse 80 is passed over in the original edition (verse 79 ends on p. 197, Caph begins on p. 198). '
                 'The marginal summaries of the original are given beside the text.',
        about_zh='考珀先任珀斯牧师，1612 年起任加洛韦主教；这部逐节注解全篇诗篇 119 篇的书 1613 年出版（书眉题作「基督徒剖析」）；本站按希伯来字母每八节一页，共 22 页。'
                 '原书漏讲第 80 节（第 79 节讲到第 197 页，第 198 页即接下一字母）。原书页边的提要排在正文旁。',
        omitted_en="The author's two prayers before his evening doctrine are given after the exposition; the table of "
                   'principal points is not included.',
        omitted_zh='作者晚间讲道前常用的两篇祷文附在讲解之后；卷末要点索引未收。'),
    'smith-psalm51': dict(
        tcp='A12516', author='smith', book='psalm51', P='sm', c0='#27707a', c1='#3aa0af', psalm=51,
        short='Smith on Psalm 51', hero='Psalm 51',
        title_en="David's Repentance: A Plain and Familiar Exposition of the 51. Psalm",
        tagline="Samuel Smith · Dauids Repentance",
        edition='Second edition, amplified · London: Nicholas Okes, 1614 · STC 22841.7', year='1614',
        front=['title_page', 'dedication', 'to_the_reader', 'Psalm_n51', 'table_of_doctrines'], back=[],
        units=('divs', 'body/div/div'), verse_from_head=True,
        about_en='Smith, minister of Roxwell in Essex, first preached this exposition of Psalm 51 to his congregation and '
                 'published it, as he says, in the spare hours of a long sickness; this second edition of 1614 was '
                 '"profitably amplified by the Authour". Each part of the book, from the title of the psalm to the last '
                 'verse, is one page here.',
        about_zh='史密斯任埃塞克斯郡罗克斯韦尔牧师，先在会众中讲这篇诗篇，后来照他自己说，是在久病不能讲道的空闲里整理出版；'
                 '1614 年这第二版由作者「增订」。本站从诗题到末节，原书每部分一页。',
        omitted_en='', omitted_zh=''),
}

LAYOUT_CHAPTER = r'''---
layout: default
---
{%- comment -%}
  __CLS__ 正文页。由 scripts/publish_tcp_psalm.py 生成（BOOKS['__KEY__']），底本 EEBO-TCP __TCP__（CC0）。
  ⚠️ 不复用别家 layout（每本书独立样式）；配色 __C0__ / __C1__，类名 __P__- 前缀。
  - 本页所含目录条目 → `.__P__-contents`；所讲经文 → `.__P__-text`；页边旁注 → `.__P__-margin`；印本页码 → `.__P__-pb`（#pN）。
  - 录入本读不出的字 → `.__P__-gap`（标红）。目前只有英文版，不接经文弹层（模块只认中文书卷名）。
{%- endcomment -%}

<div class="container __P__-wrap" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">
      <div class="__P__-chrome"><a href="{{ site.baseurl }}/__AUTHOR__/__BOOK__/">&larr; {{ page.book_name }}</a></div>
      <h1 class="__P__-title">{{ page.title }}</h1>
      {% if page.subtitle %}<p class="__P__-subtitle">{{ page.subtitle }}</p>{% endif %}
      <div class="__P__-nav">
        {% if page.prev_url %}<a href="{{ site.baseurl }}{{ page.prev_url }}">&larr; {{ page.prev_label }}</a>{% else %}<span></span>{% endif %}
        {% if page.next_url %}<a href="{{ site.baseurl }}{{ page.next_url }}">{{ page.next_label }} &rarr;</a>{% else %}<span></span>{% endif %}
      </div>
      <div class="__P__-content">
        {{ content }}
      </div>
      {% if page.date %}<div class="__P__-stamp">Published {{ page.date | date: "%Y-%m-%d %H:%M" }}</div>{% endif %}
      <div class="__P__-nav __P__-nav-foot">
        {% if page.prev_url %}<a href="{{ site.baseurl }}{{ page.prev_url }}">&larr; {{ page.prev_label }}</a>{% else %}<span></span>{% endif %}
        {% if page.next_url %}<a href="{{ site.baseurl }}{{ page.next_url }}">{{ page.next_label }} &rarr;</a>{% else %}<span></span>{% endif %}
      </div>
    </div>
  </div>
</div>

<style>
.__P__-wrap { --ink: __C1__; --ink-dark: __C0__; --rule: __RULE__; --paper: __PAPER__; --body: #2d2b28; }
.__P__-wrap .__P__-chrome, .__P__-wrap .__P__-nav { font-size: 13px; display: flex; justify-content: space-between; gap: 12px;
  align-items: center; font-family: Georgia, "Times New Roman", serif; }
.__P__-wrap .__P__-chrome { margin: 18px 0 22px; }
.__P__-wrap .__P__-chrome a, .__P__-wrap .__P__-nav a { color: var(--ink-dark); text-decoration: none; }
.__P__-wrap .__P__-chrome a:hover, .__P__-wrap .__P__-nav a:hover { text-decoration: underline; }
.__P__-wrap .__P__-title { font-family: Georgia, "Times New Roman", serif; font-size: 28px; font-weight: normal;
  color: var(--ink-dark); text-align: center; margin: 10px 0 4px; line-height: 1.3; }
.__P__-wrap .__P__-subtitle { text-align: center; font-size: 14px; color: #8a857e; margin: 0 0 6px;
  font-family: Georgia, "Times New Roman", serif; font-style: italic; }
.__P__-wrap .__P__-nav { margin: 14px 0 26px; }
.__P__-wrap .__P__-nav-foot { margin-top: 44px; padding-top: 16px; border-top: 1px solid var(--rule); }
.__P__-wrap .__P__-content { font-family: Georgia, "Times New Roman", serif; font-size: 17px; line-height: 1.85; color: var(--body); }
.__P__-wrap .__P__-content p { margin: 0 0 16px; text-align: justify; }
.__P__-wrap .__P__-content h3, .__P__-wrap .__P__-content h4 { font-size: 18px; font-weight: normal; text-align: center;
  color: var(--ink-dark); margin: 26px 0 18px; line-height: 1.5; }
.__P__-wrap .__P__-contents { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
  padding: 12px 18px 6px; margin: 0 0 26px; font-size: 14.5px; line-height: 1.65; color: #4a4640; }
.__P__-wrap .__P__-contents-h { font-size: 12px; letter-spacing: .1em; color: var(--ink-dark); margin-bottom: 6px; }
.__P__-wrap .__P__-contents-h span { letter-spacing: 0; color: #a39d94; margin-left: 4px; }
.__P__-wrap .__P__-contents ul { margin: 0 0 6px; padding-left: 18px; }
.__P__-wrap .__P__-contents li { margin: 0 0 4px; }
.__P__-wrap .__P__-contents li small { color: #a39d94; margin-left: 4px; }
.__P__-wrap .__P__-text { border-left: 3px solid var(--ink); background: var(--paper); padding: 10px 16px; margin: 0 0 22px; }
.__P__-wrap .__P__-text p { margin: 0 0 6px; text-align: left; font-style: italic; }
.__P__-wrap .__P__-dropcap { float: left; font-size: 3em; line-height: .85; margin: 4px 7px 0 0; color: var(--ink-dark); }
.__P__-wrap .__P__-quote { text-align: center !important; font-style: italic; }
.__P__-wrap .__P__-closer { text-align: right !important; font-style: italic; }
.__P__-wrap .__P__-trailer { text-align: center !important; letter-spacing: .1em; }
.__P__-wrap .__P__-item { margin: 0 0 8px 24px !important; text-align: left !important; }
.__P__-wrap .__P__-poem { margin: 0 0 16px 28px; }
.__P__-wrap .__P__-poem p, .__P__-wrap .__P__-l { margin: 0 !important; text-align: left !important; }
.__P__-wrap .__P__-table { border-collapse: collapse; margin: 0 auto 16px; font-size: 14px; }
.__P__-wrap .__P__-table td { border: 1px solid var(--rule); padding: 3px 8px; vertical-align: top; }
.__P__-wrap .__P__-margin { display: block; margin: 2px 0 8px; padding-left: 10px; border-left: 2px solid var(--rule);
  font-size: 13px; line-height: 1.55; color: #857f76; font-style: normal; text-align: left; }
@media (min-width: 1200px) {
  .__P__-wrap .__P__-margin { float: right; clear: right; width: 150px; margin: 4px -182px 8px 16px; padding-left: 8px; }
}
.__P__-wrap .__P__-pb { scroll-margin-top: 80px; }
.__P__-wrap .__P__-pb[data-p]::before { content: "p." attr(data-p); font-size: 10.5px; color: #b5afa6; font-style: normal;
  margin: 0 4px; border: 1px solid var(--rule); border-radius: 3px; padding: 0 3px; vertical-align: 1px; }
.__P__-wrap .__P__-gap { color: #c0392b; cursor: help; }
.__P__-wrap .__P__-lost { font-size: 14px; color: #a0522d; border: 1px dashed #e0b8a0; border-radius: 4px; padding: 8px 12px; }
.__P__-wrap .__P__-stamp { text-align: right; color: #aaa59d; font-size: 12px; margin-top: 30px; font-family: Georgia, serif; }
@media (max-width: 767px) {
  .__P__-wrap .__P__-title { font-size: 23px; }
  .__P__-wrap .__P__-content { font-size: 16px; }
}
</style>
'''

LAYOUT_BOOK = r'''---
layout: default
---
{%- comment -%}
  __CLS__ 书卷首页。由 scripts/publish_tcp_psalm.py 生成（BOOKS['__KEY__']）：卷首各页 + 正文方格（悬停看本页首条目录）+ 文本说明。
  ⚠️ 不复用别家 layout；配色 __C0__ / __C1__。目前只有英文版。
{%- endcomment -%}

<div class="container __P__-book" style="padding-top:80px; max-width:900px;">
  <div class="__P__-hero">
    <h1>{{ page.hero | default: page.book_name }}</h1>
    <div class="__P__-tagline">{{ page.tagline }}</div>
    <div class="__P__-edition">{{ page.edition }}</div>
  </div>
  {{ content }}
</div>

<style>
.__P__-book .__P__-hero { text-align: center; margin-bottom: 8px; }
.__P__-book .__P__-hero h1 { font-family: Georgia, "Songti SC", serif; color: __C0__; font-size: 30px; letter-spacing: .04em; }
.__P__-book .__P__-tagline { color: __C1__; font-size: 14px; letter-spacing: .06em; margin-top: 6px; }
.__P__-book .__P__-edition { color: #9a9a92; font-size: 12px; margin-top: 6px; }
.__P__-book .__P__-sec-hd { margin: 30px 0 12px; font-size: 12px; font-weight: bold; letter-spacing: .14em;
  color: #8f8a82; text-transform: uppercase; text-align: center; }
.__P__-book .__P__-sec-hd-main { margin-top: 40px; }
.__P__-book .__P__-fronts { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.__P__-book .__P__-fronts a { border: 1.5px dashed __C1__; border-radius: 8px; padding: 8px 16px; color: __C1__;
  font-family: Georgia, serif; font-size: 14px; text-decoration: none; text-align: center; }
.__P__-book .__P__-fronts a span { display: block; font-size: 11px; color: #9a948b; }
.__P__-book .__P__-fronts a:hover { background: __C1__; color: #fff; }
.__P__-book .__P__-fronts a:hover span { color: #eee; }
.__P__-book .__P__-sub { margin: 26px 0 10px; font-family: Georgia, serif; font-size: 16px; color: __C0__; text-align: center; }
.__P__-book .__P__-sub span { display: block; font-size: 12px; color: #9a948b; margin-top: 2px; }
.__P__-book .__P__-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.__P__-book .__P__-grid a { display: block; border: 1px solid __RULE__; border-radius: 6px; background: __PAPER__; padding: 8px 8px 7px;
  text-align: center; font-family: Georgia, serif; font-size: 16px; color: __C1__; text-decoration: none; line-height: 1.25; }
.__P__-book .__P__-grid a small { display: block; font-size: 11px; color: #958f86; margin-top: 4px; line-height: 1.35; }
.__P__-book .__P__-grid a:hover { background: __C1__; color: #fff; }
.__P__-book .__P__-grid a:hover small { color: #eee; }
.__P__-book .__P__-note { text-align: center; color: #8a8a82; font-size: 13px; line-height: 1.8; max-width: 640px; margin: 40px auto 0; }
.__P__-book .__P__-note p { margin: 0 0 10px; }
@media (max-width: 600px) { .__P__-book .__P__-grid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); } }
</style>
'''


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def ystr(s):
    return json.dumps(s, ensure_ascii=False)


def mix(c, w):
    """c 与白色按 w（白的比例）混合，给淡色 rule / paper。"""
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02x%02x%02x' % tuple(round(x + (255 - x) * w) for x in (r, g, b))


def write_layouts(key, c, force=False):
    sub = {'__CLS__': c['short'], '__KEY__': key, '__TCP__': c['tcp'], '__C0__': c['c0'], '__C1__': c['c1'],
           '__P__': c['P'], '__AUTHOR__': c['author'], '__BOOK__': c['book'],
           '__RULE__': mix(c['c1'], .85), '__PAPER__': mix(c['c1'], .96)}
    for kind, tpl in (('chapter', LAYOUT_CHAPTER), ('book', LAYOUT_BOOK)):
        f = ROOT / '_layouts' / f'{c["author"]}-{c["book"]}-{kind}.html'
        if f.exists() and not force:
            continue
        s = tpl
        for k, v in sub.items():
            s = s.replace(k, v)
        f.write_text(s, encoding='utf-8')


# ── TEI 渲染 ──
def render(r, e, P, skip_head=False):
    out = []
    for c in e:
        if skip_head and c.tag == TEI + 'head':
            continue
        if c.tag == TEI + 'epigraph':
            inner = []
            tt.blocks(r, c, inner)
            txt = '\n\n'.join(x[-1] for x in inner if x[0] != 'pb' and isinstance(x[-1], str))
            out.append(('text', txt.strip()))
            continue
        if c.tag == TEI + 'div':                   # 子 div（逐节）自己递归，epigraph 才能走上面的经文框
            out.extend(render(r, c, P))
            continue
        tt.block(r, c, out, 3)
    return out


def gapify(md, P):
    return TOK.sub(lambda m: f'<span class="{P}-gap" title="TCP: illegible in source（底本此处读不出）">{m.group(0)}</span>', md)


def first_page(item):
    """段落元组里第一个印本页码（pb 元组或行内 data-p）。"""
    s = item[1] if item[0] == 'pb' else (item[-1] if isinstance(item[-1], str) else '')
    m = re.search(r'data-p="(\d+)"', s)
    return int(m.group(1)) if m else None


def toc_entries(r, toc):
    """卷首目录（list > label + item[页码] 嵌套）→ [(条目, 页码)]。"""
    out = []

    def walk(lst, prefix=''):
        kids = [k for k in lst if k.tag in (TEI + 'label', TEI + 'item')]
        i = 0
        while i < len(kids):
            k = kids[i]
            if k.tag == TEI + 'label':
                lab = tt.norm(r, r.inline(k))
                it = kids[i + 1] if i + 1 < len(kids) and kids[i + 1].tag == TEI + 'item' else None
                pg = None
                if it is not None:
                    direct = (it.text or '') + ''.join((h.text or '') + (h.tail or '') for h in it if h.tag == TEI + 'hi')
                    m = re.search(r'(\d+)', direct)
                    pg = int(m.group(1)) if m else None
                    m2 = re.search(r'(\d+)\s*$', lab)
                    if pg is None and m2:
                        pg = int(m2.group(1))
                lab = re.sub(r'<span class="[a-z]+-dropcap">(\w)</span>(\w)', lambda m: m.group(1) + m.group(2).lower(), lab)
                out.append((re.sub(r'\s*(Pag\.?|p\.)\s*\d*\.?\s*$', '', lab), pg))
                if it is not None:
                    for sub in it.iter(TEI + 'list'):
                        walk(sub)
                        break
                i += 2 if it is not None else 1
            else:
                i += 1
    for lst in toc.findall(TEI + 'list'):
        walk(lst)
    # 没有页码的条目沿用后一条的页码（「Christs sitting … noteth,」下面才有页码）
    for j in range(len(out) - 2, -1, -1):
        if out[j][1] is None:
            out[j] = (out[j][0], out[j + 1][1])
    return [(lab, pg) for lab, pg in out if lab]


def find(root, path):
    """'body/div' → body 下的 div 列表；'body/div/div' 再下一层。"""
    parts = path.split('/')
    cur = [root.find(f'.//{TEI}{parts[0]}')]
    for p in parts[1:]:
        cur = [c for x in cur for c in x if c.tag == TEI + p]
    return cur


def verse_label(e, r):
    n = e.get('n')
    if n:
        return n.replace(',', '–')
    return ''


def build(key):
    c = BOOKS[key]
    P = c['P']
    RAW = ROOT / f'{c["author"]}_raw' / c['book']
    OUT = ROOT / c['author'] / c['book']
    BASE = f'/{c["author"]}/{c["book"]}/'
    root = ET.parse(RAW / 'src' / f'{c["tcp"]}.xml').getroot()
    for el in root.iter():
        for a in ('text', 'tail'):
            v = getattr(el, a)
            if v and '*' in v:
                setattr(el, a, v.replace('*', '&#42;'))
    r = tt.R(P, c['year'])
    text = root.find(f'.//{TEI}text')
    fronts, backs, toc = [], [], []
    for sect, keep, acc in (('front', c['front'], fronts), ('back', c['back'], backs)):
        e = text.find(TEI + sect)
        if e is None:
            continue
        for d in e:
            if d.tag != TEI + 'div':
                continue
            ty = d.get('type')
            if ty == 'table_of_contents' and c.get('contents') == 'toc':
                toc = toc_entries(r, d)
            if ty in keep:
                slug, en, zh = FRONT_LABEL[ty]
                acc.append(dict(slug=slug, title=en, zh=zh, md=tt.to_md(P, render(r, d, P))))
    for ty in c.get('body_back', []):           # 正文层里的附录（考珀的两篇祷文）并成一页，排在讲解之后
        ds = [d for d in text.find(TEI + 'body').iter(TEI + 'div') if d.get('type') == ty]
        if ds:
            slug, en, zh = FRONT_LABEL[ty]
            items = []
            for d in ds:
                items += render(r, d, P)
            backs.insert(0, dict(slug=slug, title=en, zh=zh, md=tt.to_md(P, items)))
    units = []
    kind = c['units'][0]
    for d in find(text, c['units'][1]):
        if d.tag != TEI + 'div' or d.get('type') in c.get('body_back', []):
            continue
        v = verse_label(d, r)
        if c.get('verse_from_head'):               # 「VERSE. 12.13.」→ 12–13；诗题（THE TEXT. To him that excelleth）→ title
            h = d.find(TEI + 'head')
            ht = tt.text_of(h) if h is not None else ''
            if h is None:
                ht = re.sub(r'\s+', ' ', ''.join(d.itertext()))[:120]
            m = re.search(r'VERS[E]?\W*\s*(\d+(?:[.,:]\d+)*)', ht.replace('ſ', 's'))
            ns = [int(x) for x in re.findall(r'\d+', m.group(1))] if m else []
            v = 'title' if not ns else (f'{ns[0]}–{ns[-1]}' if len(ns) > 1 else str(ns[0]))
        if c.get('acrostic'):                      # 诗篇 119：字母名作页名，八节一页
            i = len(units)
            v = f'{8 * i + 1}–{8 * i + 8}'
            name = tt.text_of(d.find(TEI + 'head')).replace('ſ', 's').rstrip('.').replace(' ', '').title()
            units.append(dict(verse=v, part=None, items=render(r, d, P), pages=None, name=name))
            continue
        items = render(r, d, P)
        if kind == 'pages':
            N = c['units'][2]
            pages = [first_page(x) for x in items]
            known = [p for p in pages if p]
            p0, p1 = known[0], known[-1]
            nchunks = max(1, round((p1 - p0 + 1) / N))
            if nchunks == 1:
                units.append(dict(verse=v, part=None, items=items, pages=(p0, p1)))
                continue
            step = (p1 - p0 + 1) / nchunks
            chunks, cur, cur_p0, k = [], [], p0, 1
            last_p = p0
            for x, p in zip(items, pages):
                if p:
                    last_p = p
                if k < nchunks and x[0] not in ('pb',) and last_p >= p0 + k * step and cur and \
                        not str(x[-1]).startswith('#'):
                    chunks.append((cur, cur_p0, last_p))
                    cur, cur_p0, k = [], last_p, k + 1
                cur.append(x)
            chunks.append((cur, cur_p0, p1))
            for j, (its, a, b) in enumerate(chunks):
                units.append(dict(verse=v, part=j + 1, nparts=len(chunks), items=its, pages=(a, b)))
        else:
            units.append(dict(verse=v, part=None, items=items, pages=None))
    # 页码范围：下一单元起页之前
    for i, u in enumerate(units):
        u['md'] = gapify(tt.to_md(P, u.pop('items')), P)
        if not u['pages']:
            ps = [int(x) for x in re.findall(r'data-p="(\d+)"', u['md'])]
            u['pages'] = (ps[0], ps[-1]) if ps else None
        u['slug'] = 'the-title' if u['verse'] == 'title' else \
            f'v{u["verse"].replace("–", "-")}' + (f'-{u["part"]}' if u['part'] else '')
        note = c.get('notes', {}).get(u['slug'])
        if note:
            u['md'] = f'<p class="{P}-lost">{note}</p>\n\n' + u['md']
    for i, u in enumerate(units):
        if u['pages'] and i + 1 < len(units) and units[i + 1]['pages']:
            u['pages'] = (u['pages'][0], units[i + 1]['pages'][0] - (0 if units[i + 1]['md'].lstrip().startswith(
                f'<span class="{P}-pb"') else 0))
        u['contents'] = [(lab, pg) for lab, pg in toc if u['pages'] and pg and u['pages'][0] <= pg < (
            units[i + 1]['pages'][0] if i + 1 < len(units) and units[i + 1]['pages'] else 10 ** 6)]
    publish(key, c, fronts, units, backs, r.gaps, OUT, BASE, RAW)


def publish(key, c, fronts, units, backs, gaps, OUT, BASE, RAW):
    P = c['P']
    meta_f = RAW / 'en_meta.json'
    meta = json.loads(meta_f.read_text(encoding='utf-8')) if meta_f.exists() else {}
    t0 = now()
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [('front', f) for f in fronts] + [('unit', u) for u in units] + [('front', f) for f in backs]

    def vref(u):
        if u['verse'] == 'title':
            return f'Psalm {c["psalm"]}, the title'
        return f'Psalm {c["psalm"]}:{u["verse"]}' if u['verse'] else f'Psalm {c["psalm"]}'

    def label_of(k, x):
        if k == 'front':
            return x['title']
        if x.get('name'):
            return x['name']
        if x['verse'] == 'title':
            return 'The Title'
        return f'Verse{"s" if "–" in x["verse"] else ""} {x["verse"]}' + (f' · Part {x["part"]}' if x['part'] else '')

    for i, (k, x) in enumerate(pages):
        slug = x['slug']
        meta.setdefault(slug, t0)
        if k == 'front':
            title, sub, body = x['title'], x['zh'], gapify(x['md'], P)
        else:
            title = (f'{x["name"]} · ' if x.get('name') else '') + vref(x) + \
                (f' · Part {x["part"]} of {x["nparts"]}' if x['part'] else '')
            sub = (f'pp. {x["pages"][0]}–{x["pages"][1]} of the {c["year"]} edition' if x['pages'] else '')
            body = ''
            if x['contents']:
                body = (f'<div class="{P}-contents">\n<div class="{P}-contents-h">Contents of this page · 本页目录'
                        f'<span>（据作者卷首目录，页码指 {c["year"]} 年原书）</span></div>\n<ul>\n' +
                        '\n'.join(f'<li>{em(lab)}<small>p. {pg}</small></li>' for lab, pg in x['contents']) +
                        '\n</ul>\n</div>\n\n')
            body += x['md']
        fm = ['---', f'layout: {c["author"]}-{c["book"]}-chapter', f'book_id: {c["book"]}', f'book_name: {ystr(c["short"])}',
              f'title: {ystr(title)}', f'subtitle: {ystr(sub)}', f'date: {meta[slug]}']
        if i > 0:
            pk, px = pages[i - 1]
            fm += [f'prev_url: {ystr(BASE + px["slug"] + "/")}', f'prev_label: {ystr(label_of(pk, px))}']
        if i + 1 < len(pages):
            nk, nx = pages[i + 1]
            fm += [f'next_url: {ystr(BASE + nx["slug"] + "/")}', f'next_label: {ystr(label_of(nk, nx))}']
        fm.append('---')
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    L = [f'<div class="{P}-sec-hd">Front Matter</div>', f'<div class="{P}-fronts">']
    for f in fronts + backs:
        L.append(f'  <a href="{{{{ site.baseurl }}}}{BASE}{f["slug"]}/">{f["title"]}<span>{f["zh"]}</span></a>')
    L += ['</div>', f'<div class="{P}-sec-hd {P}-sec-hd-main">The Exposition</div>', f'<div class="{P}-grid">']
    for u in units:
        cap = (re.sub(r'^\d+\s+', '', plain(u['contents'][0][0]))[:60] if u['contents'] else '')
        pp = f'pp. {u["pages"][0]}–{u["pages"][1]}' if u['pages'] else ''
        tip = ' · '.join(plain(lab) for lab, _ in u['contents'][:6]).replace('"', '&quot;')
        if u.get('name'):
            cap = f'vv. {u["verse"]}'
        L.append(f'  <a href="{{{{ site.baseurl }}}}{BASE}{u["slug"]}/" title="{tip}">{label_of("unit", u)}'
                 f'<small>{cap}{"<br>" if cap and pp else ""}{pp}</small></a>')
    L.append('</div>')
    en = (f'<p><b>About this text.</b> {c["about_en"]} The text is the keyed transcription of the {c["year"]} edition '
          f'(EEBO-TCP {c["tcp"]}; released under CC0), with the spelling of the original; only the long s is printed as s. '
          f'Places the transcribers could not read are shown in red ({gaps.get("letter", 0)} letters, {gaps.get("word", 0)} words, '
          f'{gaps.get("span", 0)} longer passages, {gaps.get("foreign", 0)} Greek or Hebrew passages left untranscribed). '
          f'{c["omitted_en"]}</p>')
    zh = (f'<p class="{P}-note-zh"><b>文本说明。</b>{c["about_zh"]}本站正文据 {c["year"]} 年版的人工录入本（EEBO-TCP {c["tcp"]}，'
          f'CC0 公共领域授权），拼法照录原书，只把长 s（ſ）印作 s。录入者读不出的地方以红色标出：缺字母 {gaps.get("letter", 0)} 个、'
          f'缺整词 {gaps.get("word", 0)} 处、缺一段以上 {gaps.get("span", 0)} 处，另有希腊文、希伯来文 {gaps.get("foreign", 0)} 处未录。'
          f'{c["omitted_zh"]}</p>')
    L.append(f'<div class="{P}-note">\n{en}\n{zh}\n</div>')
    meta.setdefault('index', t0)
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    fm = ['---', f'layout: {c["author"]}-{c["book"]}-book', f'book_id: {c["book"]}', f'book_name: {ystr(c["title_en"])}',
          f'hero: {ystr(c["hero"])}', f'tagline: {ystr(c["tagline"])}', f'edition: {ystr(c["edition"])}',
          f'title: {ystr(c["short"])}', f'date: {meta["index"]}', '---']
    (OUT / 'index.html').write_text('\n'.join(fm) + '\n\n' + '\n'.join(L) + '\n', encoding='utf-8')
    print(f'{key}: 卷首/卷末 {len(fronts) + len(backs)} 页，正文 {len(units)} 页 → {OUT}；缺字 {gaps}')
    for u in units:
        print(f'   {u["slug"]:10} {u["pages"]}  目录 {len(u["contents"])} 条  {len(u["md"]) // 1000}k')


def em(s):
    return re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)


def plain(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s).replace('*', '')).strip()


def main():
    keys = list(BOOKS) if sys.argv[1] == 'all' else [sys.argv[1]]
    for k in keys:
        write_layouts(k, BOOKS[k], force='--layouts' in sys.argv)
        build(k)


if __name__ == '__main__':
    main()
