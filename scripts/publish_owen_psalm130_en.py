#!/usr/bin/env python3
"""欧文《诗篇 130 篇实践讲解》英文版：CCEL ThML → owen/psalm130/

    python3 scripts/publish_owen_psalm130_en.py

底本 owen_raw/psalm130/src/psalm130.xml（CCEL psalm130，ThML；正文是 Goold 编《欧文全集》第 6 卷，
斜体、希腊文、希伯来文、页码、经文出处都已标记；CCEL 注明「ThML markup added. Text has not been proof-read.」）。
分页：卷首（Goold 的编者说明、致读者）各一页；诗篇本文与释义概要一页；其后欧文按经节分组的各章（div3）每章一页，
没有分章的「第七、八节」整组一页。div4（「规则一」等）在章内作小标题。书名页、出版许可与 CCEL 索引不收。
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
    front = {'Prefatory Note': 'prefatory-note', 'To the Reader': 'to-the-reader'}
    n = 0
    for p in pages:
        if p['title'] in front:
            p['slug'] = front[p['title']]
        else:
            n += 1
            p['slug'] = str(n)
    for i, p in enumerate(pages):
        old = OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', old.read_text(encoding='utf-8'), re.M) if old.exists() else None
        sub = '' if p['group'] == p['title'] else p['group']
        fm = ['---', 'layout: owen-psalm130-chapter', 'book_id: psalm130', f'book_name: "{BOOK}"',
              f'title: "{p["title"]}"'] + ([f'subtitle: "{sub}"'] if sub else []) + [f'date: {m.group(1) if m else stamp}']
        if i:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["title"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["title"]}"']
        fm.append('---')
        old.write_text('\n'.join(fm) + '\n\n' + p['html'] + '\n', encoding='utf-8')
    # 书首页
    toc, last = [], None
    for p in pages:
        if p['group'] != last:
            if last is not None:
                toc.append('</ul>')
            toc += [f'<h2 class="op-group">{html.escape(p["group"])}</h2>', '<ul class="op-toc">']
            last = p['group']
        toc.append(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">{html.escape(p["title"])}</a></li>')
    toc.append('</ul>')
    (OUT / 'index.html').write_text(f'''---
layout: owen-psalm130-book
book_id: psalm130
book_name: "A Practical Exposition upon Psalm CXXX"
author: "John Owen (1616–1683)"
edition: "First published 1668; text of The Works of John Owen, ed. W. H. Goold, vol. 6"
title: "{BOOK}"
---

{chr(10).join(toc)}

<div class="op-note">
<p><b>About this text.</b> The text is the Christian Classics Ethereal Library edition of Owen’s <i>A Practical Exposition upon Psalm CXXX</i>,
from <i>The Works of John Owen</i>, edited by William H. Goold, vol. 6. Italics, Greek, Hebrew and the footnotes follow that edition;
the title page, imprimatur and CCEL’s indexes are not reproduced.</p>
<p class="op-note-zh"><b>文本说明。</b>正文据 CCEL（基督教经典电子图书馆）录入本，所据为 Goold 编《欧文全集》第 6 卷；斜体、希腊文、希伯来文、脚注照该本。
书名页、出版许可与 CCEL 所附索引未收。</p>
</div>
''', encoding='utf-8')
    print(len(pages), 'pages')


if __name__ == '__main__':
    main()
