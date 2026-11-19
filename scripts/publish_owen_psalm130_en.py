#!/usr/bin/env python3
"""欧文《诗篇 130 篇实践讲解》英文版：CCEL ThML → owen/psalm130/

    python3 scripts/publish_owen_psalm130_en.py

底本 owen_raw/psalm130/src/psalm130.xml（CCEL psalm130，ThML；正文是 Goold 编《欧文全集》第 6 卷，
斜体、希腊文、希伯来文、页码、经文出处都已标记；CCEL 注明「ThML markup added. Text has not been proof-read.」）。
分章：卷首（Goold 的编者说明、致读者）各一章；诗篇本文与释义概要一章；其后欧文按经节分组的各章（div3）每章一章，
没有分章的「第七、八节」整组一章，共 41 章，原样存 owen_raw/psalm130/en_chapters/（翻译脚本从这里取原文）。
div4（「规则一」等）在章内作小标题。书名页、出版许可与 CCEL 索引不收。

分页（用户 2026-11-19：「不要分这么细」）：按 PAGES 把各章并成页，原来的章在页内作小标题 `.op-sec`。
一组经节一页；第四节有 22 章，照欧文自己在章首交代的论证步骤分五页（见 PAGES 注释）。
"""
import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'owen_raw' / 'psalm130' / 'src' / 'psalm130.xml'
OUT = ROOT / 'owen' / 'psalm130'
BASE = '/owen/psalm130'
BOOK = 'Owen on Psalm 130'
SKIP = {'Title Page', 'Imprimatur', 'Title'}
CH_DIR = ROOT / 'owen_raw' / 'psalm130' / 'en_chapters'
FRONT = ['prefatory-note', 'to-the-reader']

# 合并分页：(slug, 英文组名, 英文页名, 中文页名, 起章, 止章)；页名与组名相同的不另立副题。
# 第四节五页的分界都是欧文自己的转折（第 14 章立三条命题、四步论证并讲完第一步）：
#   15 章「第二，这一显明是伟大、圣洁、奥秘的」（16 为挪开反驳插入，17、18 是同一论证另两个根据）；
#   19 章「第四……还须略加印证」，20–26 章是明证一至十二；
#   27 章「还须先交代两件事」→ 28 章「劝人相信之前」→ 29 章「转入直接应用」→ 30 章守则；
#   31 章「第二项总体应用的第二部分」：化解使人不能坚定的不安与反驳。
PAGES = [
    ('psalm', 'Psalm CXXX', 'Psalm CXXX', '诗篇 130 篇', 1, 3),
    ('v1-2', 'Verses First and Second', 'Verses First and Second', '第一、二节', 4, 8),
    ('v3', 'Verse Third', 'Verse Third', '第三节', 9, 12),
    ('v4-1', 'Verse Fourth', 'The Words and Propositions', '字句与命题', 13, 14),
    ('v4-2', 'Verse Fourth', 'The Greatness and Rareness of the Discovery', '这显明伟大而稀有', 15, 18),
    ('v4-3', 'Verse Fourth', 'Its Supportment and Evidences', '赦免之恩的扶持与明证', 19, 26),
    ('v4-4', 'Verse Fourth', 'Application: Exhortation to Believe', '应用一：劝人相信', 27, 30),
    ('v4-5', 'Verse Fourth', 'Application: Answering Discouragements', '应用二：化解不安与反驳', 31, 34),
    ('v5-6', 'Verses Fifth and Sixth', 'Verses Fifth and Sixth', '第五、六节', 35, 38),
    ('v7-8', 'Verses Seventh and Eighth', 'Verses Seventh and Eighth', '第七、八节', 39, 39),
]
V4_NO = {'v4-1': '一', 'v4-2': '二', 'v4-3': '三', 'v4-4': '四', 'v4-5': '五'}
V4_NO_EN = {'v4-1': 'I', 'v4-2': 'II', 'v4-3': 'III', 'v4-4': 'IV', 'v4-5': 'V'}


# 书首页目录（版式仿欧文《希伯来书》首页 _includes/owen-hebrews-index.html：居中分区标题、虚线小方块、纸底大方块）
# 方块：(slug, 上方小字, 大字)；方块下注页名或章数，悬停列出该页所含各章。
TILES = {'psalm': ('Psalm', '130'), 'v1-2': ('Verses', '1–2'), 'v3': ('Verse', '3'),
         'v5-6': ('Verses', '5–6'), 'v7-8': ('Verses', '7–8'),
         **{k: ('Verse 4', v) for k, v in V4_NO.items()}}
TOC_ROWS = [('全篇与第一至三节', 'Psalm CXXX · Verses 1–3', ['psalm', 'v1-2', 'v3']),
            ('第四节 · 按欧文的论证分五部分', 'Verse 4 · in five parts, following Owen’s argument', list(V4_NO)),
            ('第五至八节', 'Verses 5–8', ['v5-6', 'v7-8'])]


def toc_html(zh, titles, ch_titles, done=None):
    """titles: {slug: 页名}；ch_titles: {章号: 章名}（悬停提示）；done: 已出中文的页（中文版用，None 表示全可点）。"""
    base = BASE + ('/zh' if zh else '')
    rng = {pg[0]: (pg[4], pg[5]) for pg in PAGES}

    def link(slug):
        return (base if done is None or slug in done else BASE) + f'/{slug}/'
    out = [f'<div class="op-sec-hd">{"卷首 &middot; Front Matter" if zh else "Front Matter"}</div>', '<div class="op-grid">']
    for f, lab in zip(FRONT, ('Note', 'Reader')):
        out.append(f'  <a class="op-tile op-tile-front" href="{{{{ site.baseurl }}}}{link(f)}"><span>{lab}</span>{html.escape(titles[f])}</a>')
    out += ['</div>', f'<div class="op-sec-hd op-sec-hd-main">{"逐节讲解 &middot; Exposition" if zh else "Exposition"}</div>']
    for sub_zh, sub_en, slugs in TOC_ROWS:
        out += [f'<div class="op-sub">{sub_zh if zh else sub_en}</div>', '<div class="op-grid">']
        for slug in slugs:
            a, b = rng[slug]
            tip = ' · '.join(ch_titles[str(k)] for k in range(a, b + 1))
            cap = titles[slug] if slug in V4_NO or slug == 'psalm' else (f'{b - a + 1} 章' if zh else f'{b - a + 1} chapter{"s" if b > a else ""}')
            if slug == 'psalm':
                cap = '经文 · 释义 · 总旨' if zh else 'Text · Paraphrase · Scope'
            pend = '' if done is None or slug in done else ' op-tile-pending'
            lab, big = TILES[slug]
            out.append(f'  <a class="op-cell{pend}" href="{{{{ site.baseurl }}}}{link(slug)}" title="{html.escape(tip)}">'
                       f'<span class="op-tile op-tile-ch"><span>{lab}</span>{big}</span>'
                       f'<span class="op-cap">{html.escape(cap)}</span></a>')
        out.append('</div>')
    return '\n'.join(out)


def page_order():
    """发布顺序：卷首两章 + 合并页。"""
    return FRONT + [pg[0] for pg in PAGES]


def renumber_notes(h, off):
    """把一章的脚注号整体加 off（并页后全页连续编号，id 不撞）。"""
    if not off:
        return h
    bump = lambda m: m.group(1) + str(int(m.group(2)) + off)
    h = re.sub(r'(#fn-|#fnref-|id="fn-|id="fnref-)(\d+)', bump, h)
    h = re.sub(r'(<sup class="op-fn"><a [^>]*>)(\d+)(?=</a>)', bump, h)
    return re.sub(r'(<a class="op-back" [^>]*>)(\d+)(?=</a>)', bump, h)


def merge_chapters(chs, page_title):
    """[(章号, 章名, 正文 HTML)] → 一页正文：页首小目录 + 各章以 `.op-sec` 小标题分开，脚注连续编号。
    章名与页名相同的那章（如「第七、八节」）不另立标题。"""
    out, toc, off = [], [], 0
    for n, title, body in chs:
        body = renumber_notes(body, off)
        off += len(re.findall(r'<p id="fn-\d+"', body))
        if title != page_title:
            out.append(f'<h2 class="op-sec" id="s{n}">{html.escape(title)}</h2>')
            toc.append(f'<a href="#s{n}">{html.escape(title)}</a>')
        out.append(body)
    head = f'<nav class="op-sects">{"".join(toc)}</nav>\n\n' if len(toc) > 1 else ''
    return head + '\n\n'.join(out)


def split_md(path):
    """md → (front matter 文本, 正文)。"""
    t = path.read_text(encoding='utf-8')
    _, fm, body = t.split('---\n', 2)
    return fm, body.strip()


def inline(x):
    """ThML 段内 → 页面 HTML。"""
    x = re.sub(r'<pb[^>]*/>', '', x)
    x = re.sub(r'<scripRef[^>]*>(.*?)</scripRef>', r'\1', x, flags=re.S)
    x = re.sub(r'<name[^>]*>(.*?)</name>', r'\1', x, flags=re.S)
    x = re.sub(r'<(em|i)( [^>]*)?>', '<em>', x)
    x = re.sub(r'</(em|i)>', '</em>', x)
    x = re.sub(r'<span class="sc"[^>]*>(.*?)</span>', r'<span class="op-sc">\1</span>', x, flags=re.S)
    x = re.sub(r'<span lang="HE"[^>]*>(.*?)</span>‎?', r'<span class="op-he" lang="he" dir="rtl">\1</span>', x, flags=re.S)
    x = re.sub(r'<span lang="EL"[^>]*>(.*?)</span>', r'<span lang="el">\1</span>', x, flags=re.S)
    x = re.sub(r'<span lang="LA"[^>]*>(.*?)</span>', r'\1', x, flags=re.S)
    x = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', x, flags=re.S)
    x = re.sub(r'<br ?/>', '<br>', x)
    x = re.sub(r' id="[^"]*"', '', x)
    return re.sub(r'\s+', ' ', x).strip()


def render(div, notes):
    """一个 div 的正文（不含下级 div 的标题处理由调用方决定）→ HTML 段落列表。"""
    out = []

    def note(m):
        notes.append(inline(re.sub(r'</?p[^>]*>', '', m.group(1))))
        k = len(notes)
        return f'\x00{k}\x00'
    div = re.sub(r'<note[^>]*>(.*?)</note>', note, div, flags=re.S)
    for m in re.finditer(r'<(p|argument|h3|h4|verse|div4)\b([^>]*)>(.*?)</\1>', div, re.S):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if tag == 'div4':
            t = re.search(r'title="([^"]*)"', attrs).group(1)
            out.append(f'<h3 class="op-sub">{html.escape(t.rstrip("."))}</h3>')
            out += render(inner, notes)
            continue
        if tag == 'verse':
            ls = [inline(l) for l in re.findall(r'<l[^>]*>(.*?)</l>', inner, re.S)]
            out.append('<p class="op-verse">' + '<br>'.join(ls) + '</p>')
            continue
        if tag in ('h3', 'h4'):
            continue                         # div4 的标题已由 title 属性给出
        body = inline(inner)
        if not body:
            continue
        cls = re.search(r'class="([^"]*)"', attrs)
        cls = cls.group(1) if cls else ''
        if tag == 'argument':
            out.append(f'<p class="op-arg">{body}</p>')
        elif 'Center' in cls:
            out.append(f'<p class="op-center">{body}</p>')
        elif 'Right' in cls:
            out.append(f'<p class="op-right">{body}</p>')
        else:
            out.append(f'<p>{body}</p>')
    return out


def fn(html_, notes):
    html_ = re.sub(r'\x00(\d+)\x00', lambda m: f'<sup class="op-fn"><a href="#fn-{m.group(1)}" id="fnref-{m.group(1)}">{m.group(1)}</a></sup>', html_)
    if notes:
        html_ += '\n\n<div class="op-notes">\n' + '\n'.join(
            f'<p id="fn-{k}"><a class="op-back" href="#fnref-{k}">{k}</a>{t}</p>' for k, t in enumerate(notes, 1)) + '\n</div>'
    return html_


def main():
    s = SRC.read_text(encoding='utf-8')
    body = s[s.find('<ThML.body'):s.find('<div1 title="Indexes"')]
    pages = []
    # 二级、三级分块：把 div3 从 div2 里切出；div2 自身在第一个 div3 之前的部分另成一页
    for m2 in re.finditer(r'<div2\b([^>]*)>(.*?)</div2>', body, re.S):
        t2 = re.search(r'shorttitle="([^"]*)"', m2.group(1)).group(1)
        if t2 in SKIP:
            continue
        inner = m2.group(2)
        subs = list(re.finditer(r'<div3\b([^>]*)>(.*?)</div3>', inner, re.S))
        head = inner[:subs[0].start()] if subs else inner
        if re.search(r'<(p|verse|argument)\b', head):
            notes = []
            pages.append(dict(group=t2, title=t2, html=fn('\n\n'.join(render(head, notes)), notes)))
        for m3 in subs:
            t3 = re.search(r'shorttitle="([^"]*)"', m3.group(1)).group(1)
            notes = []
            pages.append(dict(group=t2, title=t3, html=fn('\n\n'.join(render(m3.group(2), notes)), notes)))
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    OUT.mkdir(parents=True, exist_ok=True)
    CH_DIR.mkdir(parents=True, exist_ok=True)
    front = {'Prefatory Note': 'prefatory-note', 'To the Reader': 'to-the-reader'}
    n = 0
    for p in pages:
        if p['title'] in front:
            p['slug'] = front[p['title']]
        else:
            n += 1
            p['slug'] = str(n)
    assert n == PAGES[-1][5], f'章数 {n} 与 PAGES 对不上'
    # 1) 分章原文（翻译脚本的底本）；date 沿用旧文件
    for p in pages:
        dst = CH_DIR / f'{p["slug"]}.md'
        old = dst if dst.exists() else OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', old.read_text(encoding='utf-8'), re.M) if old.exists() else None
        p['date'] = m.group(1) if m else stamp
        sub = '' if p['group'] == p['title'] else p['group']
        fm = ['---', 'layout: owen-psalm130-chapter', 'book_id: psalm130', f'book_name: "{BOOK}"',
              f'title: "{p["title"]}"'] + ([f'subtitle: "{sub}"'] if sub else []) + [f'date: {p["date"]}', '---']
        dst.write_text('\n'.join(fm) + '\n\n' + p['html'] + '\n', encoding='utf-8')
    by = {p['slug']: p for p in pages}
    # 2) 发布页：卷首两章各一页，其余按 PAGES 并页
    out = [dict(slug=f, title=by[f]['title'], sub='', html=by[f]['html'], date=by[f]['date']) for f in FRONT]
    for slug, group, title, _, a, b in PAGES:
        chs = [by[str(k)] for k in range(a, b + 1)]
        sub = f'{group} ({V4_NO_EN[slug]})' if slug in V4_NO_EN else ''
        out.append(dict(slug=slug, title=title, sub=sub, date=max(c['date'] for c in chs),
                        html=merge_chapters([(int(c['slug']), c['title'], c['html']) for c in chs], title)))
    for i, p in enumerate(out):
        fm = ['---', 'layout: owen-psalm130-chapter', 'book_id: psalm130', f'book_name: "{BOOK}"',
              f'title: "{p["title"]}"'] + ([f'subtitle: "{p["sub"]}"'] if p['sub'] else []) + [f'date: {p["date"]}']
        if i:
            fm += [f'prev_url: "{BASE}/{out[i-1]["slug"]}/"', f'prev_label: "{out[i-1]["title"]}"']
        if i + 1 < len(out):
            fm += [f'next_url: "{BASE}/{out[i+1]["slug"]}/"', f'next_label: "{out[i+1]["title"]}"']
        if (OUT / 'zh' / f'{p["slug"]}.md').exists():
            fm.append(f'zh_url: "{BASE}/zh/{p["slug"]}/"')
        fm.append('---')
        (OUT / f'{p["slug"]}.md').write_text('\n'.join(fm) + '\n\n' + p['html'] + '\n', encoding='utf-8')
    for old in OUT.glob('*.md'):                     # 旧的逐章页
        if old.stem.isdigit():
            old.unlink()
    # 书首页
    toc = [toc_html(False, {p['slug']: p['title'] for p in out}, {p['slug']: p['title'] for p in pages})]
    (OUT / 'index.html').write_text(f'''---
layout: owen-psalm130-book
book_id: psalm130
book_name: "A Practical Exposition upon Psalm CXXX"
author: "John Owen (1616–1683)"
hero: "Psalm 130"
tagline: "John Owen · A Practical Exposition upon Psalm CXXX"
edition: "First published 1668 · text of The Works of John Owen, ed. W. H. Goold, vol. 6"
title: "{BOOK}"
{'zh_url: "' + BASE + '/zh/"' + chr(10) if (OUT / 'zh' / 'index.html').exists() else ''}---

{chr(10).join(toc)}

<div class="op-note">
<p><b>About this text.</b> The text is the Christian Classics Ethereal Library edition of Owen’s <i>A Practical Exposition upon Psalm CXXX</i>,
from <i>The Works of John Owen</i>, edited by William H. Goold, vol. 6. Italics, Greek, Hebrew and the footnotes follow that edition;
the title page, imprimatur and CCEL’s indexes are not reproduced.</p>
<p class="op-note-zh"><b>文本说明。</b>正文据 CCEL（基督教经典电子图书馆）录入本，所据为 Goold 编《欧文全集》第 6 卷；斜体、希腊文、希伯来文、脚注照该本。
书名页、出版许可与 CCEL 所附索引未收。</p>
</div>
''', encoding='utf-8')
    print(len(pages), 'chapters →', len(out), 'pages')


if __name__ == '__main__':
    main()
