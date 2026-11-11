#!/usr/bin/env python3
"""加尔文讲章英文版发布：calvin_sermons_raw/<书>/units.json → calvin/<书>-sermons/

    python3 scripts/publish_calvin_sermons.py job
    python3 scripts/publish_calvin_sermons.py deuteronomy

一篇讲章一页 `<篇次>.md`；卷首各一页；书首页 index.html 按章列篇次。
date 沿用 en_meta.json 里的原值，新页才写当前真实时间（重跑不改时间）。
缺字记号（•／〈◊〉／〈…〉／▪）包成 .cs-gap 标红；申命记缺页处 .cs-lost 一段说明。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
CFG = {
    'job': dict(name='Job', cn='约伯记', title_en="Sermons upon the Book of Job",
                title_cn='加尔文《约伯记讲章》', year='1574', tcp='A69056', stc='STC 4445', total=159,
                printed='Imprinted at London by Henrie Binneman, for Lucas Harison and George Bishop, 1574',  # TCP 书目头 colophon
                preached=''),                       # 原书标题不记日期，不写
    'deuteronomy': dict(name='Deuteronomy', cn='申命记', title_en="Sermons upon the Fifth Book of Moses called Deuteronomy",
                        title_cn='加尔文《申命记讲章》', year='1583', tcp='A17698', stc='STC 4442', total=200,
                        printed='At London: Printed by Henry Middleton for George Bishop, 1583',
                        preached='1555-03-20 – 1556-07-15'),   # 取自第 1 篇与第 200 篇标题所记日期
    # 撒母耳记上：法文讲章原稿已佚，只存 1604 年日内瓦的拉丁文译本（David Claudus 译），本站据《加尔文全集》重排本
    '1samuel': dict(name='1 Samuel', cn='撒母耳记上', title_en='Homiliae in I. librum Samuelis',
                    title_cn='加尔文《撒母耳记上讲章》（拉丁文）', year='1604', total=107,
                    printed='Calvini Opera vol. XXIX–XXX (Brunsvigae, 1885–86), after the Geneva edition of 1604 (Gabriel Cartier)',
                    translator='Latin translation from the French by David Claudus',
                    preached=''),
}
FRONT_CN = {'title': '书名页', 'dedication': '献辞', 'to-the-reader': '致读者', 'to-the-reader-1': '致读者（一）',
            'to-the-reader-2': '致读者（二）', 'to-the-reader-3': '致读者（三）',
            'prolegomena': '全集编者导言（1885，拉丁文）',
            'prayer-before': '讲道前的祷告', 'prayer-after': '讲道后的祷告'}


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def ystr(s):
    return json.dumps(s, ensure_ascii=False)


def gapify(md):
    return TOK.sub(lambda m: f'<span class="cs-gap" title="TCP: illegible in source（底本此处读不出）">{m.group(0)}</span>', md)


def chap_label(name, s):
    return f'{name} {s["chapter"]}' + (f'–{s["chapter2"]}' if s.get('chapter2') else '')


def main():
    book = sys.argv[1]
    c = CFG[book]
    RAW = ROOT / 'calvin_sermons_raw' / book
    OUT = ROOT / 'calvin' / f'{book}-sermons'
    u = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    meta_f = RAW / 'en_meta.json'
    meta = json.loads(meta_f.read_text(encoding='utf-8')) if meta_f.exists() else {}
    t0 = now()
    OUT.mkdir(parents=True, exist_ok=True)
    base = f'/calvin/{book}-sermons/'
    pages = [('front', f) for f in u['front'] if not f['slug'].startswith('prayer')] + \
            [('sermon', s) for s in u['sermons']] + \
            [('front', f) for f in u['front'] if f['slug'].startswith('prayer')]

    def slug_of(kind, x):
        return x['slug'] if kind == 'front' else str(x['num'])

    def label_of(kind, x):
        if kind == 'front':
            return x['title']
        if book == '1samuel':
            return f'Homilia {x["num"]}'
        if x.get('absorbs'):                    # 并页（申命记缺页处）：两篇同页
            return f'Sermons {x["num"]} & ' + ' & '.join(map(str, x['absorbs']))
        return f'Sermon {x["num"]}'

    written = 0
    for i, (kind, x) in enumerate(pages):
        slug = slug_of(kind, x)
        meta.setdefault(slug, t0)
        if kind == 'front':
            title = x['title']
            sub = FRONT_CN.get(slug, '')
        else:
            title = f'{label_of(kind, x)} · {chap_label(c["name"], x)}'
            sub = x['head']
        fm = ['---', 'layout: calvin-sermon', f'book_id: {book}', f'book_name: {ystr(c["title_en"])}',
              f'book_cn: {ystr(c["title_cn"])}', f'title: {ystr(title)}', f'subtitle: {ystr(sub)}',
              f'date: {meta[slug]}']
        if kind == 'sermon':
            fm.append(f'sermon: {x["num"]}')
            if x.get('absorbs'):
                fm.append(f'absorbs: {ystr(x["absorbs"])}')
        if i > 0:
            pk, px = pages[i - 1]
            fm += [f'prev_url: {ystr(base + slug_of(pk, px) + "/")}', f'prev_label: {ystr(label_of(pk, px))}']
        if i + 1 < len(pages):
            nk, nx = pages[i + 1]
            fm += [f'next_url: {ystr(base + slug_of(nk, nx) + "/")}', f'next_label: {ystr(label_of(nk, nx))}']
        fm.append('---')
        body = gapify(x['md'])
        if kind == 'sermon' and x.get('absorbs'):
            ab = '、'.join(f'第 {a} 篇' for a in x['absorbs'])
            body = (f'<p class="cs-merge">This page also carries what survives of Sermon '
                    f'{", ".join(map(str, x["absorbs"]))}: its opening, with the heading, fell within the two pages '
                    f'wanting in the copy from which the keyed text was made.<br>本页同时载有{ab}的残存部分：'
                    f'该篇开头连同标题落在录入所据胶片本所缺的两页之内，其余正文接在下面缺页说明之后。</p>\n\n') + body
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
        written += 1
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')

    # ── 书首页 ──
    merged = {int(k): v for k, v in u['merged'].items()}
    by_ch = {}
    for s in u['sermons']:
        by_ch.setdefault(s['chapter'], []).append(('s', s['num']))
    for a, host in merged.items():
        ch = next(s['chapter'] for s in u['sermons'] if s['num'] == host)
        by_ch[ch].append(('m', a, host))
    lines = []
    lines.append('<h2 class="cs-group">Front Matter <span>卷首</span></h2>\n<ul class="cs-toc">')
    for f in u['front']:
        if not f['slug'].startswith('prayer'):
            lines.append(f'  <li><a href="{{{{ site.baseurl }}}}{base}{f["slug"]}/">{f["title"]}'
                         f'<span class="cs-ref">{FRONT_CN.get(f["slug"], "")}</span></a></li>')
    lines.append('</ul>')
    lines.append(f'<h2 class="cs-group">The Sermons <span>讲章 {c["total"]} 篇，按所讲章次排列</span></h2>')
    for ch in sorted(by_ch):
        items = sorted(by_ch[ch], key=lambda t: t[1])
        lines.append(f'<div class="cs-ch"><div class="cs-ch-h">{c["name"]} {ch}<span>第 {ch} 章</span></div><div class="cs-grid">')
        for it in items:
            if it[0] == 's':
                lines.append(f'<a href="{{{{ site.baseurl }}}}{base}{it[1]}/">{it[1]}</a>')
            else:
                lines.append(f'<a class="cs-merged" href="{{{{ site.baseurl }}}}{base}{it[2]}/" '
                             f'title="开头随缺页散失，余文并在第 {it[2]} 篇页内">{it[1]}</a>')
        lines.append('</div></div>')
    pr = [f for f in u['front'] if f['slug'].startswith('prayer')]
    if pr:
        lines.append('<h2 class="cs-group">Calvin\'s Prayers <span>加尔文讲道前后的祷告</span></h2>\n<ul class="cs-toc">')
        for f in pr:
            lines.append(f'  <li><a href="{{{{ site.baseurl }}}}{base}{f["slug"]}/">{f["title"]}'
                         f'<span class="cs-ref">{FRONT_CN[f["slug"]]}</span></a></li>')
        lines.append('</ul>')
    lines.append(about(book, c, u, merged))
    idx_meta = meta.setdefault('index', t0)
    meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    fm = ['---', 'layout: calvin-sermons-book', f'book_id: {book}', f'title: {ystr(c["title_cn"])}',
          f'book_name: {ystr(c["title_en"])}', f'book_cn: {ystr(c["title_cn"])}',
          f'edition: {ystr(c["printed"] + " · " + c.get("translator", "Translated out of French by Arthur Golding"))}',
          f'preached: {ystr(c["preached"])}', f'date: {idx_meta}', '---']
    (OUT / 'index.html').write_text('\n'.join(fm) + '\n\n' + '\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{book}: 写入 {written} 页 + 书首页 → {OUT}')


def about(book, c, u, merged):
    if book == '1samuel':
        return about_1sam(u)
    g = u['gaps']
    gl = g.get('letter', 0)
    gw = g.get('word', 0)
    gs = g.get('span', 0)
    en = (f'<p><b>About this text.</b> The text is the keyed transcription of the {c["year"]} London edition '
          f'(EEBO-TCP {c["tcp"]}, {c["stc"]}; released under CC0), in Arthur Golding\'s English translation from the French. '
          f'The spelling is that of the original; only the long s has been printed as s. Places the transcribers '
          f'could not read on the microfilm are shown in red: {gl} letters, {gw} words and {gs} longer passages. ')
    zh = (f'<p class="cs-note-zh"><b>文本说明。</b>本书正文据 {c["year"]} 年伦敦版的人工录入本（EEBO-TCP {c["tcp"]}，'
          f'{c["stc"]}，CC0 公共领域授权），即戈尔丁（Arthur Golding）自法文译出的英译本。拼法照录原书，只把长 s（ſ）'
          f'印作 s。录入者在胶片上读不出的地方以红色记号标出：缺字母 {gl} 个、缺整词 {gw} 处、缺一段以上 {gs} 处；'
          f'尚未据其他扫描本补全。')
    if book == 'deuteronomy':
        ms = '、'.join(f'第 {a} 篇（并在第 {h} 篇页内）' for a, h in merged.items())
        en += (f'The copy from which the transcription was made lacks two pages in 28 places; each is marked where it '
               f'falls. Nine of these gaps fall where one sermon ends and the next begins, so that the heading and '
               f'opening of the second sermon are lost and the remainder runs on in the page of the first; those '
               f'sermons are listed above in grey and lead to the page that carries them. Two headings are misnumbered '
               f'in the original (the second &ldquo;Lxx.&rdquo;, which by its date and place is Sermon 73) and are '
               f'printed as they stand. ')
        zh += (f'录入所据的胶片本有 28 处各缺两页，均在原处注明。其中 9 处缺页正好跨在两篇讲章之间，后一篇的标题与开头随之散失，'
               f'残存正文接在前一篇页内：{ms}；目录中以灰色标出，点开即进所在页。原书有一篇标题篇次印错'
               f'（第二个「Lxx.」，按日期与次序实为第 73 篇），标题照录。')
    else:
        en += ('Two headings are misnumbered in the original (Sermon 78 printed lxxvij., Sermon 112 printed Cij.) and the '
               'heading of Sermon 124 gives chapter xxxiiij. for xxxiij.; they are printed as they stand, and the sermons '
               'are numbered and grouped by their place in the book. ')
        zh += ('原书有几处标题印错：第 78 篇印作 lxxvij.、第 112 篇印作 Cij.，第 124 篇把第 33 章印成 xxxiiij.；标题照录，'
               '篇次与归章按书中实际次序。')
    en += 'The indexes at the end of the volume are not yet included.</p>'
    zh += '卷末索引暂未收录。</p>'
    return f'<div class="cs-note">\n{en}\n{zh}\n</div>'


def about_1sam(u):
    r = u.get('repair', {})
    en = ('<p><b>About this text.</b> Calvin preached on 1 Samuel in French; the sermons were taken down by a scribe, '
          'but the French text has not survived. What survives is the Latin translation by David Claudus, '
          '<i>Homiliae in I. librum Samuelis. Ex Gallicis Latinae factae</i> (Geneva: Gabriel Cartier, 1604), 107 homilies. '
          'The text given here is that of the reprint in <i>Calvini Opera</i> vols. XXIX–XXX (Corpus Reformatorum 57–58, '
          'Brunswick 1885–86), read from the scans in the University of Geneva open archive; the column numbers of that edition '
          'are marked in the margin. The editors\' footnotes are given at the end of each homily. '
          f'The Opera text was recognised by OCR and checked word by word against a second, independent OCR reading; '
          f'{r.get("fixed", 0)} words were corrected in all, {r.get("image", 0)} of them read directly from the page images '
          f'where the two readings and the lexicon could not decide; a further {r.get("confirmed", 0)} such words were found '
          f'on the page images to be printed exactly so (including misprints of the 1604 edition) and are kept. '
          f'{r.get("residue", 0)} words remain as the scan was read, where the image could not settle them. '
          'The indexes are not included.</p>')
    zh = ('<p class="cs-note-zh"><b>文本说明。</b>加尔文用法文讲撒母耳记上，由书记员当场记录，但法文原稿已经失传。'
          '现存的是 David Claudus 的拉丁文译本《Homiliae in I. librum Samuelis. Ex Gallicis Latinae factae》'
          '（日内瓦：Gabriel Cartier，1604），共 107 篇。本站正文据《加尔文全集》（Calvini Opera）第 29–30 卷'
          '（Corpus Reformatorum 第 57–58 卷，不伦瑞克 1885–86）的重排本，用日内瓦大学开放档案的扫描件识读；'
          '页边标的是全集本的栏码。全集编者的脚注排在各篇之末。'
          f'正文由 OCR 识读，并与另一份独立的 OCR 逐词对照，共改正 {r.get("fixed", 0)} 词，'
          f'其中两份读法与词典都判不了、对照页图读定的 {r.get("image", 0)} 词；'
          f'另有 {r.get("confirmed", 0)} 词看图确认原书就是这样印的（含 1604 年版的印错），照录；'
          f'仍有 {r.get("residue", 0)} 词看图也定不下来，暂照扫描件读出的样子录入。'
          '全集编者导言见卷首。卷末索引暂未收录。</p>')
    return f'<div class="cs-note">\n{en}\n{zh}\n</div>'


if __name__ == '__main__':
    main()
