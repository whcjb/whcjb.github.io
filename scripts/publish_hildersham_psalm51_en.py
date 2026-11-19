#!/usr/bin/env python3
"""希尔德沙姆《诗篇 51 篇讲义 152 讲》英文版发布：hildersham_raw/psalm51/units.json → hildersham/psalm51/

    python3 scripts/extract_hildersham.py && python3 scripts/publish_hildersham_psalm51_en.py

一讲一页 `<讲次>.md`；卷首 title / dedication / errata 各一页；书首页 index.html 按所讲经节分组列讲次。
各讲页首放作者自编的本讲提要（原书卷首「The Contents of the whole Booke」）。
date 沿用 en_meta.json 里的原值，新页才写当前真实时间（重跑不改时间）。
TCP 读不出的字（•／〈◊〉／〈…〉／〈Greek〉／▪）包成 .hd-gap 标红。
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'hildersham_raw' / 'psalm51'
OUT = ROOT / 'hildersham' / 'psalm51'
BASE = '/hildersham/psalm51/'
TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
VLABEL = {'title': 'The Title', '1-2': 'Verses 1–2', '3': 'Verse 3', '4': 'Verse 4', '5': 'Verse 5', '6': 'Verse 6',
          '7': 'Verse 7'}
VREF = {'title': 'Psalm 51, title', '1-2': 'Psalm 51:1–2'}
FRONT_CN = {'title': '书名页', 'dedication': '献辞', 'errata': '勘误表'}


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def ystr(s):
    return json.dumps(s, ensure_ascii=False)


def gapify(md):
    return TOK.sub(lambda m: f'<span class="hd-gap" title="TCP: illegible in source（底本此处读不出）">{m.group(0)}</span>', md)


def em(s):
    """提要条目：*…* → <em>（kramdown 不解析 <li markdown="1">，直接给 HTML）"""
    return re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)


def plain(s):
    return re.sub(r'\s+', ' ', s.replace('*', '')).strip()


def main():
    u = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    meta_f = RAW / 'en_meta.json'
    meta = json.loads(meta_f.read_text(encoding='utf-8')) if meta_f.exists() else {}
    t0 = now()
    OUT.mkdir(parents=True, exist_ok=True)
    pages = [('front', f) for f in u['front'] if f['slug'] != 'errata'] + [('lec', x) for x in u['lectures']] + \
            [('front', f) for f in u['front'] if f['slug'] == 'errata']

    def slug_of(k, x):
        return x['slug'] if k == 'front' else str(x['num'])

    def label_of(k, x):
        return x['title'] if k == 'front' else f'Lecture {x["num"]}'

    for i, (k, x) in enumerate(pages):
        slug = slug_of(k, x)
        meta.setdefault(slug, t0)
        if k == 'front':
            title, sub, body = x['title'], FRONT_CN.get(slug, ''), x['md']
        else:
            v = x['verses']
            title = f'Lecture {x["num"]} · {VREF.get(v, "Psalm 51:" + v)}'
            sub = plain(x['head'])
            body = ''
            if x['contents']:
                body = ('<div class="hd-contents">\n<div class="hd-contents-h">The Contents · 本讲提要'
                        '<span>（作者自编，页码指 1635 年原书）</span></div>\n<ul>\n' +
                        '\n'.join(f'<li>{em(c)}</li>' for c in x['contents']) + '\n</ul>\n</div>\n\n')
            body += x['md']
        fm = ['---', 'layout: hildersham-psalm51-chapter', 'book_id: psalm51', 'book_name: "Hildersham on Psalm 51"',
              f'title: {ystr(title)}', f'subtitle: {ystr(sub)}', f'date: {meta[slug]}']
        if k == 'lec':
            fm.append(f'lecture: {x["num"]}')
        if i > 0:
            pk, px = pages[i - 1]
            fm += [f'prev_url: {ystr(BASE + slug_of(pk, px) + "/")}', f'prev_label: {ystr(label_of(pk, px))}']
        if i + 1 < len(pages):
            nk, nx = pages[i + 1]
            fm += [f'next_url: {ystr(BASE + slug_of(nk, nx) + "/")}', f'next_label: {ystr(label_of(nk, nx))}']
        fm.append('---')
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + gapify(body) + '\n', encoding='utf-8')

    # ── 书首页 ──
    by = {}
    for x in u['lectures']:
        by.setdefault(x['verses'], []).append(x)
    L = ['<div class="hd-sec-hd">Front Matter</div>', '<div class="hd-fronts">']
    for f in u['front']:
        L.append(f'  <a href="{{{{ site.baseurl }}}}{BASE}{f["slug"]}/">{f["title"]}<span>{FRONT_CN[f["slug"]]}</span></a>')
    L += ['</div>', '<div class="hd-sec-hd hd-sec-hd-main">The Lectures</div>']
    for v, xs in by.items():
        d0, d1 = re.search(r'\d{4}|M[DCLXVI]+', xs[0]['head']), re.search(r'\d{4}', xs[-1]['head'])
        L.append(f'<div class="hd-sub">{VLABEL[v]}<span>第 {xs[0]["num"]}–{xs[-1]["num"]} 讲 · {len(xs)} 讲</span></div>')
        L.append('<div class="hd-grid">')
        for x in xs:
            tip = plain(re.sub(r'<[^>]+>', '', x['contents'][0]))[:140] if x['contents'] else ''
            m = re.search(r'\b(Sept|Octo|Nov|Nou|Dec|Ian|Feb|Mar|Apr|May|Iun|Iul|Aug)', plain(x['head']))
            date = plain(x['head'])[m.start():] if m else ''
            L.append(f'  <a href="{{{{ site.baseurl }}}}{BASE}{x["num"]}/" title="{tip.replace(chr(34), "&quot;")}">'
                     f'{x["num"]}<small>{date}</small></a>')
        L.append('</div>')
    g = u['gaps']
    L.append(f'''<div class="hd-note">
<p><b>About this text.</b> Hildersham preached these lectures at Ashby-de-la-Zouch, Leicestershire, on Wednesdays from
28 September 1625 to 1631, reaching the seventh verse of the psalm before his death in 1632; his son Samuel published them in
1635. The text is the keyed transcription of that edition (EEBO-TCP A03343, STC 13459; released under CC0), with the spelling
of the original; only the long s is printed as s. Each lecture is headed by the author's own summary of it from the table at
the front of the book. Places the transcribers could not read are shown in red ({g.get("letter", 0)} letters, {g.get("word", 0)}
words, {g.get("span", 0)} longer passages, and {g.get("foreign", 0)} Greek or Hebrew words left untranscribed). The headings of
four lectures are misnumbered in the original (two are printed LXXI and two CXVI, the second of each being 70 and 117) and
Lecture 57 is printed after Lecture 60; the lectures are here numbered and ordered by their dates and the author's table.
The index of Scripture places and the general index are not included.</p>
<p class="hd-note-zh"><b>文本说明。</b>这些讲义是希尔德沙姆 1625 年 9 月 28 日起在莱斯特郡阿什比-德拉祖什每周三所讲，讲到 1631 年，
讲至本篇第 7 节；他 1632 年去世，1635 年由儿子塞缪尔出版。本站正文据该版的人工录入本（EEBO-TCP A03343，STC 13459，
CC0 公共领域授权），拼法照录原书，只把长 s（ſ）印作 s。各讲页首是作者自编的逐讲提要（原书卷首）。录入者读不出的地方以红色标出：
缺字母 {g.get("letter", 0)} 个、缺整词 {g.get("word", 0)} 处、缺一段以上 {g.get("span", 0)} 处，另有希腊文、希伯来文 {g.get("foreign", 0)} 处未录。
原书有四讲标题讲次印错（两个 LXXI、两个 CXVI，后一个分别实为第 70、117 讲），第 57 讲印在第 60 讲之后；本站按日期与作者提要定讲次、排次序。
卷末经文索引与总索引未收。</p>
</div>''')
    meta.setdefault('index', t0)
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    fm = ['---', 'layout: hildersham-psalm51-book', 'book_id: psalm51', 'book_name: "CLII Lectures upon Psalm LI"',
          'author: "Arthur Hildersham (1563–1632)"', 'hero: "Psalm 51"',
          'tagline: "Arthur Hildersham · CLII Lectures upon Psalme LI"',
          'edition: "Preached at Ashby-de-la-Zouch, 1625–1631 · London: George Miller for Edward Brewster, 1635"',
          'title: "Hildersham on Psalm 51"', f'date: {meta["index"]}', '---']
    (OUT / 'index.html').write_text('\n'.join(fm) + '\n\n' + '\n'.join(L) + '\n', encoding='utf-8')
    print(f'hildersham/psalm51: {len(pages)} 页 + 书首页 → {OUT}')


if __name__ == '__main__':
    main()
