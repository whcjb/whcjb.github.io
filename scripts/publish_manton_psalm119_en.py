#!/usr/bin/env python3
"""曼顿《诗篇 119 篇讲章》（190 篇）英文版：CCEL ThML（《曼顿全集》Nichol 版第 6–8 卷）→ manton/psalm119/

    python3 scripts/publish_manton_psalm119_en.py

底本 manton_raw/psalm119/src/manton06.xml、07、08（CCEL，含第 1–158 篇与卷首两篇〈致读者〉）。
CCEL 注明未经校对，有零星 OCR 错字。第 159–190 篇在全集第 9 卷，CCEL 没有；待 Monergism ePub 补
（放进 src/ 后在 epub_sermons() 里接上）。每篇讲章一页，slug 即篇号；卷首〈致读者〉各一页。
"""
import html
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_owen_psalm130_en import inline as owen_inline  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'manton_raw' / 'psalm119' / 'src'
OUT = ROOT / 'manton' / 'psalm119'
BASE = '/manton/psalm119'
BOOK = 'Manton on Psalm 119'
TOTAL = 190


def roman(s):
    v = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    n = 0
    for i, c in enumerate(s):
        n += -v[c] if i + 1 < len(s) and v[c] < v[s[i + 1]] else v[c]
    return n


def inline(x):
    return owen_inline(x).replace('op-sc', 'mp-sc').replace('op-he', 'mp-he')


def render(div, notes):
    out = []

    def note(m):
        notes.append(inline(re.sub(r'</?p[^>]*>', '', m.group(1))))
        return f'\x00{len(notes)}\x00'
    div = re.sub(r'<note[^>]*>(.*?)</note>', note, div, flags=re.S)
    for m in re.finditer(r'<(p|blockquote|h3|h4)\b([^>]*)>(.*?)</\1>', div, re.S):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if tag in ('h3', 'h4'):
            t = inline(inner)
            if t:
                out.append(f'<h3 class="mp-sub">{t}</h3>')
            continue
        if tag == 'blockquote':
            out.append(f'<blockquote>{inline(re.sub(r"</?p[^>]*>", " ", inner))}</blockquote>')
            continue
        body = inline(inner)
        if not body:
            continue
        cls = (re.search(r'class="([^"]*)"', attrs) or [None, ''])[1]
        if cls == 'center':
            out.append(f'<p class="mp-center">{body}</p>')
        elif cls == 'right':
            out.append(f'<p class="mp-right">{body}</p>')
        else:
            out.append(f'<p>{body}</p>')
    return out


def fn(h, notes):
    h = re.sub(r'\x00(\d+)\x00', r'<sup class="mp-fn"><a href="#fn-\1" id="fnref-\1">\1</a></sup>', h)
    if notes:
        h += '\n\n<div class="mp-notes">\n' + '\n'.join(
            f'<p id="fn-{k}"><a class="mp-back" href="#fnref-{k}">{k}</a>{t}</p>' for k, t in enumerate(notes, 1)) + '\n</div>'
    return h


def ccel_pages():
    front, sermons = [], {}
    for v in ('06', '07', '08'):
        s = (SRC / f'manton{v}.xml').read_text(encoding='utf-8')
        body = s[s.find('<ThML.body'):]
        for m in re.finditer(r'<div2\b([^>]*)>(.*?)</div2>', body, re.S):
            title = html.unescape(re.search(r'title="([^"]*)"', m.group(1)).group(1)).strip()
            h2 = re.search(r'<h2\b[^>]*>\s*SERMON\s+([IVXLC]+)\.?', m.group(2))
            inner = re.sub(r'<h[12]\b.*?</h[12]>', '', m.group(2), flags=re.S)
            notes = []
            # 标题写法不一：「Sermon I. …」「Sermond XLII. …」「XXXVII. …」，还有只有经文的（第 48 篇）→ 篇号以 h2 为准
            ms = re.match(r'(?:Sermond?\s+)?([IVXLC]+)\.\s*(.*)$', title)
            num = h2.group(1) if h2 else (ms.group(1) if ms else None)
            if num:
                n = roman(num)
                text = ms.group(2) if ms else title
                text = re.sub(r'—\s*Ver(se)?s?\.?.*$', '', text).strip()
                sermons[n] = dict(slug=str(n), title=f'Sermon {num}', sub=text, vol=int(v),
                                  html=fn('\n\n'.join(render(inner, notes)), notes))
            elif title.startswith('To the Reader') and v == '06':
                front.append(dict(slug=f'to-the-reader-{len(front) + 1}', title='To the Reader', sub='', vol=6,
                                  html=fn('\n\n'.join(render(inner, notes)), notes)))
    return front, sermons


def epub_sermons():
    """第 159–190 篇：Monergism ePub（src/mon/x/text/chapter-*.xhtml，用户 2026-11-17 从 Monergism 下载）。

    底本同为 Nichol 版全集，但 Monergism 重排时去掉了斜体，经文出处改成现代写法（Acts 14:17）；
    标记只有 h1（SERMON N）、p.quote（篇首经文）、p.division（分论标题，CCEL 本里是普通段）、p。"""
    out = {}
    for f in sorted((SRC / 'mon' / 'x' / 'text').glob('chapter-*.xhtml')):
        s = f.read_text(encoding='utf-8')
        m = re.search(r'<h1[^>]*>SERMON ([IVXLC]+)</h1>', s)
        if not m or roman(m.group(1)) < 159:
            continue
        n = roman(m.group(1))
        paras, sub = [], ''
        for pm in re.finditer(r'<p( class="([^"]*)")?>(.*?)</p>', s[m.end():], re.S):
            t = re.sub(r'\s+', ' ', pm.group(3)).strip()
            if not t:
                continue
            if pm.group(2) == 'quote':
                sub = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'—\s*VER(SE)?S?\.?.*$', '', t, flags=re.I))).strip()
                q = re.sub(r'(—\s*VER)', r'</em>\1', t, count=1, flags=re.I) if re.search(r'—\s*VER', t, re.I) else t + '</em>'
                paras.append(f'<p class="mp-center"><em>{q}</p>')
            else:
                paras.append(f'<p>{t}</p>')
        out[n] = dict(slug=str(n), title=f'Sermon {m.group(1)}', sub=sub, vol=9, src='mon', html='\n\n'.join(paras))
    return out


def main():
    front, sermons = ccel_pages()
    sermons.update(epub_sermons())
    missing = [n for n in range(1, TOTAL + 1) if n not in sermons]
    pages = front + [sermons[n] for n in sorted(sermons)]
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    OUT.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pages):
        old = OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', old.read_text(encoding='utf-8'), re.M) if old.exists() else None
        fm = ['---', 'layout: manton-psalm119-chapter', 'book_id: psalm119', f'book_name: "{BOOK}"',
              f'title: "{p["title"]}"'] + ([f'subtitle: "{html.escape(p["sub"])}"'] if p['sub'] else []) \
            + [f'date: {m.group(1) if m else stamp}']
        if i:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["title"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["title"]}"']
        fm.append('---')
        old.write_text('\n'.join(fm) + '\n\n' + p['html'] + '\n', encoding='utf-8')
    toc_f = '\n'.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">{p["title"]}</a></li>' for p in front)
    cells = []
    for n in range(1, TOTAL + 1):
        if n in sermons:
            cells.append(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{n}/"><span class="mp-no">Sermon {n}</span>'
                         f'{html.escape(sermons[n]["sub"])}</a></li>')
        else:
            cells.append(f'  <li><span class="mp-missing"><span class="mp-no">Sermon {n}</span>to be added</span></li>')
    mon = sorted(n for n in sermons if sermons[n].get('src') == 'mon')
    monote = (f'<p>Sermons {mon[0]}–{mon[-1]} (vol. 9 of the Works, not in the CCEL edition) follow the Monergism Books e-text '
              f'of the same Nichol edition; that e-text has no italics and gives Scripture references in modern form.</p>\n'
              f'<p class="mp-note-zh">第 {mon[0]}–{mon[-1]} 篇（全集第 9 卷，CCEL 未收）据 Monergism 电子书，所据同为 Nichol 版；'
              f'该本没有斜体，经文出处改作现代写法。</p>') if mon else ''
    gap = monote + (f'<p>Sermons {missing[0]}–{missing[-1]} (vol. 9 of the Works) are not in the CCEL edition and will be added '
           f'from another transcription.</p>\n<p class="mp-note-zh">第 {missing[0]}–{missing[-1]} 篇在全集第 9 卷，CCEL 没有收，另据录入本补上。</p>'
           if missing else '')
    (OUT / 'index.html').write_text(f'''---
layout: manton-psalm119-book
book_id: psalm119
book_name: "One Hundred and Ninety Sermons on the Hundred and Nineteenth Psalm"
author: "Thomas Manton (1620–1677)"
edition: "First published 1681; text of The Complete Works of Thomas Manton, D.D. (London: James Nisbet, 1872–1873), vols. 6–9"
title: "{BOOK}"
---

<ul class="mp-toc mp-front">
{toc_f}
</ul>
<h2 class="mp-group">Sermons <small>(one sermon on each verse; some verses have two or more)</small></h2>
<ul class="mp-toc">
{chr(10).join(cells)}
</ul>

<div class="mp-note">
<p><b>About this text.</b> Sermons 1–158 follow the Christian Classics Ethereal Library edition of
<i>The Complete Works of Thomas Manton</i>, vols. 6–8 (London: James Nisbet, 1872–1873). That edition has not been proof-read by CCEL
and contains occasional scanning errors.</p>
{gap}
<p class="mp-note-zh"><b>文本说明。</b>第 1–158 篇据 CCEL（基督教经典电子图书馆）所刊《曼顿全集》第 6–8 卷（伦敦 James Nisbet，1872–1873）；
该本 CCEL 注明未经校对，有零星扫描错字。</p>
</div>
''', encoding='utf-8')
    print(len(front), 'front +', len(sermons), 'sermons; missing', f'{missing[0]}–{missing[-1]}' if missing else 'none')


if __name__ == '__main__':
    main()
