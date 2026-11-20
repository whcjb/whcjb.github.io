#!/usr/bin/env python3
"""knox_raw/psalm6/zh_chapters/part-N.md → knox/psalm6/zh/part-N.md（中文版）+ zh/index.html（中文书首页）。

与英文版共用 knox-psalm6-chapter / knox-psalm6-book 两个 layout，靠 `zh: true` 切换（中文页挂经文引用弹层，layout 里已接）。
页末注不经模型：六条注有四条是给古词作的英文释义，这里手写中文注（NOTES_ZH，与英文版 NOTES 一一对应）。
date 取 zh_meta.json 里该页译完的时刻。英文页、英文首页的 zh_url 由本脚本补进 front matter（publish_knox_psalm6_en.py 也会写）；
跑完回调 build_commentaries_index.py（历代解经入口有中文就指中文）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'knox_raw' / 'psalm6'
ZH_RAW = RAW / 'zh_chapters'
EN = ROOT / 'knox' / 'psalm6'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'
BASE = '/knox/psalm6'
BOOK = '诺克斯《诗篇第六篇讲解》'
PARTS = [('part-1', '第一部分', '致亲爱的母亲 · 本篇论旨 · 第 1 节'),
         ('part-2', '第二部分', '第 2–10 节 · 结尾书信')]
NOTES_ZH = [
    '本篇第一部分所据的原稿从这一句开始；为求完整，前面几段照最早的印本补入。',
    '即爱德华王。',
    '原文 horrible，古义：令人惊恐、骇人。',
    '原文 manly，古义：属人的。',
    '伯拉纠（Pelagius），据说生于爱尔兰，五世纪人。他的异端在不列颠教会里激起纷争，大大加速了撒克逊人征服这片土地。',
    '原文 singular battle，即单打独斗。',
]
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def add_zh_url(path, url):
    t = path.read_text(encoding='utf-8')
    if 'zh_url:' in t:
        return
    head, rest = t.split('\n---\n', 1)
    path.write_text(head + f'\nzh_url: "{url}"\n---\n' + rest, encoding='utf-8')


def main():
    done = [p for p in PARTS if (ZH_RAW / f'{p[0]}.md').exists()]
    if not done:
        sys.exit('zh_chapters 里没有任何已译的部分')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, (slug, title, sub) in enumerate(done):
        fm = ['---', 'layout: knox-psalm6-chapter', 'book_id: psalm6', f'book_name: "{BOOK}"',
              f'title: "苦难者的堡垒 · {title}"', f'subtitle: "{sub}"', f'date: {meta.get(slug, now)}']
        if k > 0:
            fm += [f'prev_url: "{BASE}/zh/{done[k - 1][0]}/"', f'prev_label: "{done[k - 1][1]}"']
        if k + 1 < len(done):
            fm += [f'next_url: "{BASE}/zh/{done[k + 1][0]}/"', f'next_label: "{done[k + 1][1]}"']
        fm += [f'en_url: "{BASE}/{slug}/"', 'zh: true', '---']
        body = (ZH_RAW / f'{slug}.md').read_text(encoding='utf-8').strip()
        body = ORIG_NAME.sub(r'<span class="kx-orig">（\1）</span>', body)
        used = [int(n) for n in re.findall(r'id="fnref-(\d+)"', body)]
        if used:
            body += '\n\n<div class="kx-notes">\n' + '\n'.join(
                f'<p id="fn-{n}"><a class="kx-back" href="#fnref-{n}">{n}</a>{NOTES_ZH[n - 1]}</p>' for n in used
            ) + '\n</div>'
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
        add_zh_url(EN / f'{slug}.md', f'{BASE}/zh/{slug}/')

    title = (RAW / 'manual_pages' / 'title.html').read_text(encoding='utf-8').strip()
    caps = {'part-1': '致母亲书 · 论旨 · 第 1 节<br>1554 年 1 月 6 日',
            'part-2': '第 2–10 节 · 结尾书信<br>1554 年 2 月，迪耶普'}
    cells = []
    for slug, t, _ in PARTS:
        ok = any(slug == d[0] for d in done)
        href = f'{BASE}/zh/{slug}/' if ok else f'{BASE}/{slug}/'
        cells.append(f'  <a class="kx-cell{"" if ok else " kx-en-only"}" href="{{{{ site.baseurl }}}}{href}">'
                     f'<span class="kx-tile"><span>部分</span>{slug[-1]}</span>'
                     f'<span class="kx-cap">{caps[slug]}{"" if ok else "<br>（暂只有英文）"}</span></a>')
    idx = f'''---
layout: knox-psalm6-book
book_id: psalm6
book_name: "苦难者的堡垒"
author: "约翰·诺克斯（John Knox，约 1514–1572）"
hero: "诗篇第六篇讲解"
tagline: "约翰·诺克斯 · 苦难者的堡垒 · A Fort for the Afflicted"
edition: "1554 年写成 · 据《诺克斯实用著作选》（苏格兰自由教会，爱丁堡 1845）"
title: "{BOOK}"
en_url: "{BASE}/"
zh: true
---

<div class="kx-titlepage">
{{% include titlepage-css.html %}}
{title}
<p class="tpg-note">《苦难者的堡垒：诗篇第六篇讲解》——大卫的十字架、哀诉与祷告。凡在基督旌旗下受撒但攻击、觉得罪担沉重压身的人，
都当读此书，必得极大的安慰。<br>「受大苦的人忍耐等候，从来不至羞愧。」</p>
</div>

<div class="kx-grid">
{chr(10).join(cells)}
</div>

<div class="kx-note">
<p class="kx-note-zh"><b>文本说明。</b>诺克斯 1554 年为岳母伊丽莎白·鲍斯（Elizabeth Bowes）写下这篇讲解，当时她正陷在深重的属灵忧苦里。
第一部分 1554 年 1 月 6 日在英格兰写成，第二部分同年 2 月底在法国迪耶普写完寄出。英文底本据 AGES 数字图书馆所收
《诺克斯实用著作选》（苏格兰自由教会大会「苏格兰改教家与神学家著作出版委员会」编，爱丁堡 1845）。
经文能对上和合本的照和合本；该版的 6 条脚注排在各部分之末，其中四条原是给古词作的释义，中译改写为说明原词古义。</p>
</div>
'''
    (OUT / 'index.html').write_text(idx, encoding='utf-8')
    add_zh_url(EN / 'index.html', f'{BASE}/zh/')

    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'build_commentaries_index.py 失败：{r.stderr[-400:]}')
    print(f'中文 {len(done)} 部分已写出 → {OUT}')


if __name__ == '__main__':
    main()
