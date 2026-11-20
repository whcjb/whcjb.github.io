#!/usr/bin/env python3
"""诺克斯《苦难者的堡垒：诗篇第六篇讲解》AGES PDF → knox/psalm6/（英文版）

    /usr/bin/python3 scripts/publish_knox_psalm6_en.py      # PyMuPDF 只装在系统 python 上

底本 ~/Documents/论文/knox/KNX_SPWK.pdf（AGES Digital Library，sabda.org alkitab-8/LIBRARY/KNX_SPWK.PDF）：
Select Practical Writings of John Knox（苏格兰自由教会大会出版委员会，Edinburgh 1845），第 73–100 页即本篇，
分 Part 1（1554 年 1 月 6 日写成）、Part 2（同年 2 月底自迪耶普寄出）两页；书首页放书名页、文本说明。

版面规则（逐页实测，与 extract_calvin_ages_psalm119.py 同一套 AGES 版式）：
  · 页顶 10pt 页码丢；8pt 以下 `<NNNNNN>` 经文锚点丢，引文出处照留。
  · 正文 x≈25、12pt；段内行距 14pt，段间 ≥ 20pt 新段；跨页：上页末行右缘 < 330 且以句末标点收尾 → 新段。
  · 红斜体 = 所讲经文 → *…*；藏青色缩进行（x ≥ 40）= 整段引经 → 引文块 .kx-quote；x≈43 的黑字 = 信末落款 → .kx-sign。
  · 16pt 绿 / 粗体居中 = 标题。
  · 7pt 红 `fNN` = 注号，注文在全书末 FOOTNOTES 区（ft19–ft24）。**AGES 注号印错**：正文里第二个「f19」实为 f20，
    其后 f20、f21 依次实为 f21、f22（注文「King Edward」对「him whom God hath taken from us」，「Alarming」对 horrible，
    「Human」对 manly 可证），所以按出现顺序配注文，本篇内重编 1–6。
"""
import json
import re
import subprocess
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path.home() / 'Documents' / '论文' / 'knox' / 'KNX_SPWK.pdf'
OUT = ROOT / 'knox' / 'psalm6'
META = ROOT / 'knox_raw' / 'psalm6' / 'en_meta.json'
PARTS = [('part-1', 'Part 1', 73, 84), ('part-2', 'Part 2', 84, 100)]   # 第 84 页上下两部分交界，按「PART 2.」标题切
NOTES = [  # 全书末 FOOTNOTES 区 ft19–ft24，按正文注号出现顺序
    'The original MS. from which the First Part of this Exposition was transcribed, commences with this sentence; '
    'but to make the whole complete, it has been judged advisable to include the preceding paragraphs from the '
    'earliest printed edition.',
    'King Edward.',
    'Alarming, Terrifying.',
    'Human.',
    'Pelagius, who is supposed to have been a native of Ireland, lived in the fifth century. His heresy produced '
    'such dissensions in the British church, as greatly accelerated the conquest of the country by the Saxons.',
    'Single combat.',
]
NAVY = 0x000080
PARA_GAP = 20


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def rows_of(page):
    spans = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                if not s['text'] or (s['size'] < 8.5 and s['text'].strip().startswith('<')):
                    continue
                if round(s['size']) == 10 and s['bbox'][1] < 35 and s['text'].strip().isdigit():
                    continue                                   # 页码
                spans.append((s['bbox'][1], s['bbox'][0], s))
    spans.sort(key=lambda t: (round(t[0]), t[1]))
    rows = []
    for y, x, s in spans:
        if rows and abs(rows[-1]['y'] - y) < 4:
            rows[-1]['spans'].append(s)
        else:
            rows.append(dict(y=y, spans=[s]))
    for r in rows:
        r['spans'].sort(key=lambda s: s['bbox'][0])
        r['x0'], r['x1'] = r['spans'][0]['bbox'][0], r['spans'][-1]['bbox'][2]
        r['text'] = ''.join(s['text'] for s in r['spans']).strip()
    return rows


def row_html(r, fn):
    out, ital = '', False
    for s in r['spans']:
        t = s['text']
        if s['size'] < 8.5 and re.fullmatch(r'\s*f\d+\s*', t):
            fn[0] += 1
            n = fn[0]
            out += f'<sup class="kx-fn"><a href="#fn-{n}" id="fnref-{n}">{n}</a></sup>'
            continue
        it = bool(s['flags'] & 2) and not (s['flags'] & 16) and t.strip() != ''
        if it != ital:
            out += '<em>' if it else '</em>'
            ital = it
        out += esc(t)
    if ital:
        out += '</em>'
    return re.sub(r'(\s+)</em>', r'</em>\1', re.sub(r'<em>(\s+)', r'\1<em>', out))


def kind(r):
    s0 = r['spans'][0]
    if round(s0['size']) >= 16 or (s0['flags'] & 16 and r['x0'] > 60):
        return 'head'
    if r['x0'] >= 40 and any(s['color'] == NAVY for s in r['spans']):
        return 'quote'
    if r['x0'] >= 35:
        return 'sign'
    return 'body'


def join(a, b):
    if not a:
        return b
    return a + b if a.endswith('-') else a.rstrip() + ' ' + b.lstrip()


def blocks(doc, p0, p1, y_from=0, y_to=1e9, fn=None):
    """p0–p1 页（1 起）→ [(kind, html)]；p0 页只取 y ≥ y_from，p1 页只取 y < y_to。"""
    out, cur, ck, prev = [], '', None, None
    for pno in range(p0 - 1, p1):
        first = True
        for r in rows_of(doc[pno]):
            if (pno == p0 - 1 and r['y'] < y_from) or (pno == p1 - 1 and r['y'] >= y_to):
                continue
            k = kind(r)
            h = row_html(r, fn)
            if k == 'body' and ck == 'body' and prev is not None:
                if first:
                    t = prev['text']
                    new = prev['x1'] < 330 and t[-1:] in '.?!:”’)'
                else:
                    new = r['y'] - prev['y'] > PARA_GAP
            else:
                new = not (k == 'quote' and ck == 'quote' and r['y'] - prev['y'] <= PARA_GAP) and \
                      not (k == 'head' and ck == 'head' and r['y'] - prev['y'] < 30)
            if new:
                if cur:
                    out.append((ck, cur.strip()))
                cur, ck = h, k
            else:
                cur = join(cur, h)
            prev, first = r, False
    if cur:
        out.append((ck, cur.strip()))
    return out


def render(bl):
    html = []
    for k, h in bl:
        h = re.sub(r'</em>(\s*)<em>', r'\1', re.sub(r'\s{2,}', ' ', h))
        if k == 'head':
            html.append(f'<h3 class="kx-sec">{h}</h3>')
        elif k == 'quote':
            html.append(f'<p class="kx-quote">{h}</p>')
        elif k == 'sign':
            html.append(f'<p class="kx-sign">{h}</p>')
        else:
            html.append(f'<p>{h}</p>')
    return '\n\n'.join(html)


def ystr(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    doc = fitz.open(PDF)
    # 第 73 页：书名页（「PART 1.」之上）；第 84 页：「PART 2.」标题处切开
    p73 = rows_of(doc[72])
    y_part1 = next(r['y'] for r in p73 if r['text'].startswith('PART 1'))
    y_part2 = next(r['y'] for r in rows_of(doc[83]) if r['text'].startswith('PART 2'))
    title_rows = [r for r in p73 if r['y'] < y_part1]
    fn = [0]
    parts = {
        'part-1': blocks(doc, 73, 84, y_from=y_part1 + 1, y_to=y_part2, fn=fn),
        'part-2': blocks(doc, 84, 100, y_from=y_part2 + 1, fn=fn),
    }
    assert fn[0] == len(NOTES), fn
    used = {}
    for slug, bl in parts.items():
        used[slug] = [int(n) for k, h in bl for n in re.findall(r'id="fnref-(\d+)"', h)]

    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    t0 = now()
    OUT.mkdir(parents=True, exist_ok=True)
    META.parent.mkdir(parents=True, exist_ok=True)
    base = '/knox/psalm6/'
    subs = {'part-1': 'To his beloved mother · the Argument · verse 1', 'part-2': 'Verses 2–10 · the closing letter'}
    for i, (slug, label, _, _) in enumerate(PARTS):
        meta.setdefault(slug, t0)
        fm = ['---', 'layout: knox-psalm6-chapter', 'book_id: psalm6', 'book_name: "Knox on Psalm 6"',
              f'title: {ystr("A Fort for the Afflicted · " + label)}', f'subtitle: {ystr(subs[slug])}',
              f'date: {meta[slug]}']
        if i > 0:
            fm += [f'prev_url: "{base}{PARTS[i - 1][0]}/"', f'prev_label: "{PARTS[i - 1][1]}"']
        if i + 1 < len(PARTS):
            fm += [f'next_url: "{base}{PARTS[i + 1][0]}/"', f'next_label: "{PARTS[i + 1][1]}"']
        fm.append('---')
        body = render(parts[slug])
        if used[slug]:
            body += '\n\n<div class="kx-notes">\n' + '\n'.join(
                f'<p id="fn-{n}"><a class="kx-back" href="#fnref-{n}">{n}</a>{esc(NOTES[n - 1])}</p>' for n in used[slug]
            ) + '\n</div>'
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 书首页：书名页 + 两部分入口 + 文本说明
    tl = [r['text'] for r in title_rows]              # 书名页：大字三行、红斜体副题四行、题词一行，按原书合排
    tp = (f'<p class="kx-tp-title">{esc(tl[0])}<br><small>{esc(tl[1])}</small><br>{esc(" ".join(tl[2:4]))}</p>\n'
          f'<p class="kx-tp-sub"><em>{esc(" ".join(tl[4:8]))}</em></p>\n'
          f'<p class="kx-tp-motto">{esc(tl[8])}</p>')
    assert len(tl) == 9 and tl[8].startswith('The patient'), tl
    hand = ROOT / 'knox_raw' / 'psalm6' / 'manual_pages' / 'title.html'    # 照 1845 年版第 106 页影像手排（old-book-ocr §5.6）
    if hand.exists():
        tp = '{% include titlepage-css.html %}\n' + hand.read_text(encoding='utf-8').strip()
    meta.setdefault('index', t0)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    idx = f'''---
layout: knox-psalm6-book
book_id: psalm6
book_name: "A Fort for the Afflicted"
author: "John Knox (c. 1514–1572)"
hero: "Psalm 6"
tagline: "John Knox · A Fort for the Afflicted, in an Exposition upon the Sixth Psalm"
edition: "Written 1554 · text of Select Practical Writings of John Knox (Free Church of Scotland, Edinburgh 1845)"
title: "Knox on Psalm 6"
date: {meta['index']}
---

<div class="kx-titlepage">
{tp}
</div>

<div class="kx-grid">
  <a class="kx-cell" href="{{{{ site.baseurl }}}}{base}part-1/"><span class="kx-tile"><span>Part</span>1</span><span class="kx-cap">Letter · Argument · Verse 1<br>6 January 1554</span></a>
  <a class="kx-cell" href="{{{{ site.baseurl }}}}{base}part-2/"><span class="kx-tile"><span>Part</span>2</span><span class="kx-cap">Verses 2–10 · Closing letter<br>from Dieppe, February 1554</span></a>
</div>

<div class="kx-note">
<p><b>About this text.</b> Knox wrote this exposition in 1554 for his mother-in-law, Elizabeth Bowes, then in deep
spiritual distress; the first part was finished on 6 January 1554 in England, the second at the end of February at Dieppe.
The text is that of <i>Select Practical Writings of John Knox</i>, issued by the Free Church of Scotland's committee for
the publication of the works of Scottish Reformers and Divines (Edinburgh, 1845), as given in the AGES Digital Library.
That edition's six footnotes are printed at the end of each part; in the AGES text the second and following note marks
are misnumbered, and they are here matched to their notes in order of occurrence.</p>
<p class="kx-note-zh"><b>文本说明。</b>诺克斯 1554 年为岳母伊丽莎白·鲍斯（Elizabeth Bowes）写下这篇讲解，当时她正陷在深重的属灵忧苦里。
第一部分 1554 年 1 月 6 日在英格兰写成，第二部分同年 2 月底在法国迪耶普写完寄出。正文据 AGES 数字图书馆所收
《诺克斯实用著作选》（苏格兰自由教会大会「苏格兰改教家与神学家著作出版委员会」编，爱丁堡 1845）。
该版的 6 条脚注排在各部分之末；AGES 本从第二个注号起印错，本站按出现顺序与注文对齐。</p>
</div>
'''
    (OUT / 'index.html').write_text(idx, encoding='utf-8')
    print(f'knox/psalm6: 2 页 + 书首页，注 {fn[0]} 条 → {OUT}')


if __name__ == '__main__':
    main()
