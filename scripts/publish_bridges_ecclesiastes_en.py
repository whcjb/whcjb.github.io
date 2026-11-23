#!/usr/bin/env python3
"""布里奇斯《传道书释义》英文版：bridges_raw/ecclesiastes/src/preceptaustin.html → bridges/ecclesiastes/

    python3 scripts/publish_bridges_ecclesiastes_en.py

底本：Precept Austin 所刊录入本（标 Public Domain），据 New York: Robert Carter & Brothers, 1860。
  - Monergism Books 2022 电子版是同一份录入（逐词比对只差 Precept Austin 把「Ib.」「Chap.」展开成了书卷名），
    但它文末声明版权、禁止转载，不用。
  - 两份录入都删掉了原书脚注，正文里只剩孤立的角标数字（「mastered it.2」「name4」），共 73 处，这里一并去掉。
    角标判据：紧贴在字母或收尾标点后的 1–2 位数，后面不接数字、冒号、连字号——经文出处「12:24」「Ps. 51」都不会命中。
  - 原书没有斜体保留下来（录入本里经文段也是平排），照录。
处理：
  - 段：<p> 与 <br> 都是分段（录入本用 <br> 分隔同一 <p> 里的几段）；
  - 以「N. 」起头的段是经文段，可能连排几节（「4. … 5. … 6. …」），按节号拆出 <span class="bg-vnum">；
  - 一章一页，序言一页；书末索引（INDEX）不收。
"""
import html
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'bridges_raw' / 'ecclesiastes' / 'src' / 'preceptaustin.html'
OUT = ROOT / 'bridges' / 'ecclesiastes'
BASE = '/bridges/ecclesiastes'
BOOK = 'Bridges on Ecclesiastes'
# 逗号后只认「字母/引号 + 逗号 + 数字」（「love,3」）；冒号不认——「22:30」的 30 会被误删
# 录入本的硬伤，每条必须原样命中一次：
#   - 漏掉的节号（Monergism 版同样漏），按 KJV 分节补回；
#   - 拼写扫描（全书词对 /usr/share/dict/words，低频未登录词逐个看上下文）查出的录入错字。
#     只收「不可能是原书写法」的：古拼法（phrenzy、recompence、secresies、merchandize）、
#     拉丁词、estuations（aestuation 本有其词）、「a stern chubbishness」（拿不准原字）一概不动。
FIXES = [('what is man the better? For who knoweth', 'what is man the better? 12. For who knoweth'),   # 6:12
         ('The thing that hath, been,', 'The thing that hath been,'),                               # 1:9
         ('Is there anthing whereof', 'Is there anything whereof'),                                 # 1:10
         ('Our buisness is', 'Our business is'),
         ('his dcceptable words', 'his acceptable words'),
         ('All ecclesiastial revolutions', 'All ecclesiastical revolutions'),
         ('the excercise, the more', 'the exercise, the more'),
         ('appeared to be iminent', 'appeared to be imminent'),
         ('Things instrinsically excellent', 'Things intrinsically excellent'),
         ('in mumutual forbearance', 'in mutual forbearance'),
         ('come not thou into his secrect', 'come not thou into his secret'),
         ('an unchangable, covenant-keeping', 'an unchangeable, covenant-keeping'),
         ('‘vcnom must there be', '‘venom must there be'),
         ('Natural widsom', 'Natural wisdom'),
         ('(lb. 8:22)', '(Ib. 8:22)')]
FN = re.compile(r"(?:(?<=[A-Za-z.;!?’”'\"\)—])|(?<=[A-Za-z’”],))\d{1,2}(?![\d:–\-])(?=[\s,.;—)’”]|$)")


def paras(src):
    a = src.find('PREFACE</')
    a = src.rfind('<p', 0, a)
    z = src.find('INDEX', a)
    out = []
    for p in re.findall(r'(?s)<(?:p|h2)[^>]*>(.*?)</(?:p|h2)>', src[a:z]):
        segs = [html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ') for s in re.split(r'<br\s*/?>', p)]
        segs = [re.sub(r'\s+', ' ', s).strip() for s in segs]
        segs = [s for s in segs if s]
        if not segs:
            continue
        if re.match(r'^Hinton Martell Rectory', segs[0]):       # 序言落款三行
            out.append(('sign', '<br>'.join(segs)))
            continue
        out += [('p', s) for s in segs]
    return out


def verse_html(t):
    """「4. text 5. text」→ 每节一个节号。节号只在句末标点或段首之后认，免得把正文数字当节号。"""
    parts = re.split(r'(?:^|(?<=[.;:?!’”)—]) )(\d{1,2})\. ', t)
    out, first = [], None
    for k in range(1, len(parts), 2):
        n, body = parts[k], parts[k + 1].strip()
        first = first or n
        out.append(f'<span class="bg-vnum" id="v{n}">{n}</span>{body}')
    return first, ' '.join(out), int(parts[-2])


def main():
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    pages, cur, removed = [], None, 0
    src = SRC.read_text(encoding='utf-8')
    for a, b in FIXES:
        assert src.count(a) == 1, a
        src = src.replace(a, b)
    for kind, t in paras(src):
        if t == 'PREFACE':
            cur = dict(slug='preface', label='Preface', sub='', out=[]); pages.append(cur); continue
        if t == 'EXPOSITION OF ECCLESIASTES':
            continue
        m = re.fullmatch(r'CHAPTER (\d+)', t)
        if m:
            n = int(m.group(1))
            cur = dict(slug=str(n), label=f'Chapter {n}', n=n, out=[], last=0); pages.append(cur); continue
        if kind == 'sign':
            cur['out'].append(f'<p class="bg-center">{t}</p>'); continue
        t, k = FN.subn('', t)
        removed += k
        t = html.escape(t, quote=False)
        if cur.get('n') and re.match(r'^\d{1,2}\. ', t):
            _, body, last = verse_html(t)
            cur['last'] = max(cur['last'], last)
            cur['out'].append(f'<p class="bg-verse">{body}</p>')
        else:
            cur['out'].append(f'<p>{t}</p>')
    for p in pages:
        if 'n' in p:
            p['sub'] = f'Ecclesiastes {p["n"]}:1–{p["last"]}'
    OUT.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pages):
        f = OUT / f'{p["slug"]}.md'
        m = re.search(r'^date: (.+)$', f.read_text(encoding='utf-8'), re.M) if f.exists() else None
        fm = ['---', 'layout: bridges-psalm119-chapter', 'book_id: ecclesiastes', f'book_name: "{BOOK}"',
              f'title: "{p["label"]}"'] + ([f'subtitle: "{p["sub"]}"'] if p['sub'] else []) + \
             [f'date: {m.group(1) if m else stamp}']
        if 'n' in p:
            fm.append(f'chapter: {p["n"]}')
        if i:
            fm += [f'prev_url: "{BASE}/{pages[i-1]["slug"]}/"', f'prev_label: "{pages[i-1]["label"]}"']
        if i + 1 < len(pages):
            fm += [f'next_url: "{BASE}/{pages[i+1]["slug"]}/"', f'next_label: "{pages[i+1]["label"]}"']
        fm.append('---')
        f.write_text('\n'.join(fm) + '\n\n' + '\n\n'.join(p['out']) + '\n', encoding='utf-8')
    toc = '\n'.join(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{p["slug"]}/">'
                    + (f'<span class="bg-no">{p["label"]}</span>Verses 1–{p["last"]}' if 'n' in p else p['label'])
                    + '</a></li>' for p in pages)
    (OUT / 'index.html').write_text(f'''---
layout: bridges-psalm119-book
book_id: ecclesiastes
book_name: "An Exposition of the Book of Ecclesiastes"
author: "Charles Bridges (1794–1869)"
edition: "New York: Robert Carter & Brothers, 1860"
title: "{BOOK}"
---
<ul class="bg-toc">
{toc}
</ul>
<div class="bg-note">
<p><b>About this text.</b> The text follows the public-domain transcription of the 1860 New York edition (Robert Carter &amp; Brothers)
published by Precept Austin. The transcription does not preserve the author’s footnotes; the stray reference figures it left in the text
have been removed. Where the printed book has “Ib.” or “Chap.” in Scripture references, the transcription gives the name of the book.
The index at the end of the volume is not reproduced.</p>
<p class="bg-note-zh"><b>文本说明。</b>正文据 Precept Austin 刊布的公有领域录入本，所据为 1860 年纽约 Robert Carter &amp; Brothers 版。
录入本未收作者脚注，正文残留的注号已删去；原书经文出处中的「Ib.」「Chap.」，录入本已改写为书卷名。书末索引未收。</p>
</div>
''', encoding='utf-8')
    print(len(pages), 'pages;', removed, 'stray footnote figures removed')


if __name__ == '__main__':
    main()
