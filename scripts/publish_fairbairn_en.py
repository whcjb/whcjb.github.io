#!/usr/bin/env python3
"""费尔贝恩《教牧书信》(1874) 英文版发布：fairbairn_raw/pastoral/units.json → fairbairn/{1timothy,titus,2timothy}/

units.json 由 scripts/extract_fairbairn.py 生成（录入本按原书顺序重排、去掉嵌入经节的附录副本、
标出录入本缺文）。本脚本只管排版：

  fairbairn/1timothy/preface/ · introduction-1..4/ · appendix-a..c/   全书共用的前后附件
  fairbairn/<book>/text/                                              本卷希腊文与译文（两栏）
  fairbairn/<book>/<N>/                                               逐章注释
  fairbairn/<book>/index.html                                         本卷书首页

翻页顺序按原书：序言 → 导论 → 三卷经文与译文 → 提前、提多、提后注释 → 附录。
date 沿用 en_meta.json 里的原值，新页才写当前真实时间。

用法：python3 scripts/publish_fairbairn_en.py            # 试跑
      python3 scripts/publish_fairbairn_en.py --apply    # 写盘
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'fairbairn_raw' / 'pastoral'
OUT = ROOT / 'fairbairn'
META = RAW / 'en_meta.json'

AUTHOR = 'Patrick Fairbairn'
WORK = 'The Pastoral Epistles'
BOOKS = [('1timothy', '1 Timothy', 6), ('titus', 'Titus', 3), ('2timothy', '2 Timothy', 4)]
NAME = {b: n for b, n, _ in BOOKS}
NV = {'1timothy': [20, 15, 16, 16, 25, 21], 'titus': [16, 15, 15], '2timothy': [18, 26, 17, 22]}
SHARED = '1timothy'          # 序言、导论、附录放在提前目录下，三卷书首页都链过去
ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI']


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def p(h, cls=None):
    return f'<p class="{cls}">{h}</p>' if cls else f'<p>{h}</p>'


VER_RE = re.compile(r'^((?:<[^>]+>)*\s*)(Vers?\s*[.,]\s*[\d][\d\s,\-–]*\.)')


def vlabel(vv):
    if not vv:
        return ''
    if len(vv) == 1:
        return f'Ver. {vv[0]}.'
    return f'Vers. {vv[0]}–{vv[-1]}.' if vv == list(range(vv[0], vv[-1] + 1)) and len(vv) > 2 \
        else 'Vers. ' + ', '.join(map(str, vv)) + '.'


def chapter_body(book, ch, notes):
    es = [e for e in notes if e['book'] == book and e['ch'] == ch]
    # 原书没单独出条的经节：锚点挂在讲到它的前一条
    got = {v for e in es for v in e['vv']}
    extra = {}
    for v in range(1, NV[book][ch - 1] + 1):
        if v not in got:
            host = max((e for e in es if e['vv'] and e['vv'][0] < v), key=lambda e: e['vv'][0], default=es[0])
            extra.setdefault(id(host), []).append(v)
    seen, out = set(), []
    for e in es:
        vv = [v for v in sorted(set(e['vv']) | set(extra.get(id(e), []))) if v not in seen and v <= NV[book][ch - 1]]
        seen.update(vv)
        out += [f'<div class="commentary-anchor" id="{book}-{ch}-{v}"></div>' for v in vv]
        if e.get('missing'):
            out.append(p(f'<b class="fb-ver">{vlabel(e["vv"])}</b> The comment on this verse '
                         f'(original edition, {e["missing"]}) is wanting in the keyed text on which this '
                         f'edition is based.', 'fb-lost'))
            continue
        for k, h in enumerate(e['paras']):
            if k == 0 or VER_RE.match(h):
                h = VER_RE.sub(lambda m: f'{m.group(1)}<b class="fb-ver">{m.group(2).strip()}</b>', h, count=1)
            out.append(p(h))
    return '\n\n'.join(out)


VN_RE = re.compile(r'(?:(?<=\s)|^)(\d{1,2})\.?(?=\s)')


def text_body(book, text):
    d = text[book]
    out = []
    for k, (g, en) in enumerate(zip(d['greek'], d['english']), 1):
        g = VN_RE.sub(r'<sup class="fb-vn">\1</sup>', g)
        en = VN_RE.sub(r'<sup class="fb-vn">\1</sup>', en)
        out.append(f'<div class="fb-par" id="ch{k}">\n<h3>CHAPTER {ROMAN[k - 1]}</h3>\n'
                   f'<div class="fb-gk" lang="grc">{g}</div>\n<div class="fb-en">{en}</div>\n</div>')
    return '\n\n'.join(out)


def appx_title(head):
    """「Appendix A Page 119. The Peculiar Testimony for Gospel Times 1 Timothy 2:6」→ 正题。
    「Page N」是录入本给出的原书页码（附录在原书里被引用的那一页），不是本附录所在页。"""
    t = re.sub(r'^Appendix [ABC]\s*(Page \d+\.)?\s*', '', head).strip()
    return t


def pages(units):
    fr, text, notes = units['front'], units['text'], units['notes']
    pg = []
    pg.append(dict(book=SHARED, slug='preface', title='Preface', label='Preface',
                   body='\n\n'.join(p(h) for h in fr['preface'])))
    for s in fr['introduction']:
        pg.append(dict(book=SHARED, slug=f'introduction-{s["n"]}', title=f'Introduction, Section {s["n"]}',
                       label=f'Introduction § {s["n"]}', sub=s['title'],
                       body=f'<h2 class="fb-sec">{s["title"]}</h2>\n\n' + '\n\n'.join(p(h) for h in s['paras'])))
    for b, n, _ in BOOKS:
        pg.append(dict(book=b, slug='text', title=f'{n}: Text and Translation', label=f'{n}: Text',
                       body=text_body(b, text)))
    for b, n, nch in BOOKS:
        for c in range(1, nch + 1):
            pg.append(dict(book=b, slug=str(c), title=f'{n} {c}', label=f'{n} {c}', chapter=c,
                           body=chapter_body(b, c, notes)))
    for a in fr['appendices']:
        L = a['letter']
        body = [f'<h2 class="fb-sec">{appx_title(a["head"])}</h2>']
        for h in a['paras']:
            tx = re.sub(r'<[^>]+>', '', h)
            if tx.startswith('NOTE to p.'):
                body.append(f'<h2 class="fb-sec">{h}</h2>')
            else:
                body.append(p(h))
        pg.append(dict(book=SHARED, slug=f'appendix-{L.lower()}', title=f'Appendix {L}', label=f'Appendix {L}',
                       sub=appx_title(a['head']), body='\n\n'.join(body)))
    for i, x in enumerate(pg):
        x['prev'] = pg[i - 1] if i else None
        x['next'] = pg[i + 1] if i + 1 < len(pg) else None
    return pg


def url(x):
    return f'/fairbairn/{x["book"]}/{x["slug"]}/'


def page_md(x, date):
    fm = ['---', 'layout: fairbairn-chapter', f'book_id: {x["book"]}',
          f'book_name: "{WORK} · {NAME[x["book"]]}"', f'title: {yq(x["title"])}',
          f'subtitle: {yq((x["sub"] + " · " if x.get("sub") else "") + AUTHOR)}', f'date: {date}']
    if x.get('chapter'):
        fm.append(f'chapter: {x["chapter"]}')
    for k in ('prev', 'next'):
        if x[k]:
            fm += [f'{k}_url: "{url(x[k])}"', f'{k}_label: {yq(x[k]["label"])}']
    fm.append('---')
    return '\n'.join(fm) + '\n\n' + x['body'] + '\n'


def index_html(book, pg, units):
    name = NAME[book]
    nch = dict((b, c) for b, _, c in BOOKS)[book]
    sib = ' '.join(f'<b>{n}</b>' if b == book else f'<a href="{{{{ site.baseurl }}}}/fairbairn/{b}/">{n}</a>'
                   for b, n, _ in BOOKS)
    li = lambda x, t=None: (f'  <li><a href="{{{{ site.baseurl }}}}{url(x)}">{t or x["title"]}'
                            + (f'<span class="fb-ref">{x["sub"]}</span>' if x.get('sub') else '') + '</a></li>')
    by = {(x['book'], x['slug']): x for x in pg}
    out = ['---', 'layout: fairbairn-book', f'book_id: {book}', f'book_name: "{WORK}"',
           f'title: "{WORK} · {name}"', f'author: "{AUTHOR} (1805–1874)"',
           'edition: "The Greek Text and Translation, with Introduction, Expository Notes, and Dissertations · '
           'Edinburgh: T. &amp; T. Clark, 1874"', '---', '',
           f'<p class="fb-siblings">{sib}</p>', '',
           '<h2 class="fb-group">Preface and Introduction</h2>', '<ul class="fb-toc">']
    out += [li(by[(SHARED, s)]) for s in ['preface'] + [f'introduction-{n}' for n in range(1, 5)]]
    out += ['</ul>', f'<h2 class="fb-group">The Greek Text and Translation of {name}</h2>', '<ul class="fb-toc">',
            li(by[(book, 'text')]), '</ul>',
            f'<h2 class="fb-group">Expository Notes on {name}</h2>', '<ul class="fb-chgrid">']
    out += [f'  <li><a href="{{{{ site.baseurl }}}}/fairbairn/{book}/{c}/">{name} {c}</a></li>'
            for c in range(1, nch + 1)]
    out += ['</ul>', '<h2 class="fb-group">Appendices</h2>', '<ul class="fb-toc">']
    out += [li(by[(SHARED, f'appendix-{L}')]) for L in 'abc']
    out += ['</ul>', about(units), '']
    return '\n'.join(out)


def about(units):
    moved = units['log']['moved']
    rows = []
    names = {'1timothy': '1 Tim.', 'titus': 'Tit.', '2timothy': '2 Tim.'}
    for e in units['notes']:
        if e.get('missing'):
            rows.append(f'<tr><td>{names[e["book"]]} {e["ch"]}:{e["vv"][0]}</td><td>录入本缺此节注释（原书 {e["missing"]}）</td>'
                        f'<td>页面注明缺文，未从扫描本补</td></tr>')
    mv = {'1-timothy-1#verse-8': ('1 Tim. 2:8', '录入本挂在 1 Tim. 1:8 名下'),
          '2-timothy-2#verses-9-10': ('1 Tim. 2:9–10', '录入本挂在 2 Tim. 2:9–10 名下'),
          '1-timothy-1#verse-15': ('1 Tim. 5:15', '录入本挂在 1 Tim. 1:15 名下')}
    for m in moved:
        src = m.split(' → ')[0]
        if src in mv:
            rows.append(f'<tr><td>{mv[src][0]}</td><td>{mv[src][1]}</td><td>按原书位置移回本节</td></tr>')
    L = units['log']
    return '\n'.join([
        '<div class="fb-note">',
        '<p><b>About this text.</b> The text follows a modern keyed transcription (the e-Sword / BibleSupport '
        'module, from a 2008 Libronix edition, as published on StudyLight.org). In it the author\'s footnotes '
        'have been worked into the text in parentheses, and the appendices are also repeated under the verses '
        'that refer to them. The keyed text has been checked against a scan of the 1874 Edinburgh edition '
        '(Princeton Theological Seminary copy, Internet Archive <i>pastoralepistle00fair</i>), used only to '
        'restore the order of the book: three comments filed under the wrong verse have been put back in their '
        'place, the repeated appendices removed from the verse comments, and five comments missing from the keyed '
        'text are marked where they stand. The wording is that of the keyed text throughout.</p>',
        '<p class="fb-note-zh"><b>文本说明。</b>本书正文据现代人工录入本（e-Sword / BibleSupport 模块，出自 2008 年 '
        'Libronix 本，经 StudyLight 刊布）。该本把作者的页脚注改作正文里的圆括号插注，又把三篇附录整篇重复嵌在'
        f'引到它们的经节之下（共 {L["appendix_paras"]} 段）。我们拿 1874 年爱丁堡初版的扫描本（普林斯顿神学院藏本，'
        '互联网档案馆 pastoralepistle00fair）作顺序证人，只用来恢复原书的次序：挂错经节的三条注释移回原处，'
        '嵌在经节下的附录副本删去（附录另有单页），录入本整节缺失的五处注释在原位注明。字句一律照录入本，'
        '未据扫描本改动；希腊文里被拆开的重音符号已按 Unicode 合并。</p>',
        '<table class="fb-edtab"><tr><th>位置</th><th>录入本</th><th>处理</th></tr>',
        *rows, '</table>', '</div>'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    units = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    pg = pages(units)
    bad = [x['slug'] for x in pg if '{{' in x['body'] or '{%' in x['body']]
    if bad:
        raise SystemExit(f'正文里有 Liquid 记号：{bad}')
    anchors = re.findall(r'id="(\w+)-(\d+)-(\d+)"', '\n'.join(x['body'] for x in pg))
    want = {(b, str(c), str(v)) for b, _, n in BOOKS for c in range(1, n + 1) for v in range(1, NV[b][c - 1] + 1)}
    miss = sorted(want - set(anchors))
    print(f'{len(pg)} 页；经节锚点 {len(set(anchors))}/{len(want)}；缺 {miss[:8]}', file=sys.stderr)
    if miss:
        raise SystemExit('有经节没有锚点')
    if not a.apply:
        return
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    for x in pg:
        key = f'{x["book"]}/{x["slug"]}'
        meta.setdefault(key, stamp)
        d = OUT / x['book']
        d.mkdir(parents=True, exist_ok=True)
        (d / f'{x["slug"]}.md').write_text(page_md(x, meta[key]), encoding='utf-8')
    for b, _, _ in BOOKS:
        (OUT / b / 'index.html').write_text(index_html(b, pg, units), encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'写入 {len(pg)} 页 + 书首页 3 → {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
