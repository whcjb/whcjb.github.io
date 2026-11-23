#!/usr/bin/env python3
"""布里奇斯《传道书释义》中文版：bridges_raw/ecclesiastes/zh_chapters/<页>.md → bridges/ecclesiastes/zh/

    python3 scripts/publish_bridges_ecclesiastes_zh.py        # translate_bridges_ecclesiastes.py 每译完一页自动调用

- 只发已译出的页；前后翻页只在已译的中文页之间连；
- 中文目录 zh/index.html：已译的页链中文，未译的灰显、链英文页（标「英文」）；右上角「English edition →」；
- 中文章节页不放「English →」（layout 在 page.zh 时不渲染），front matter 照写 en_url；
- date 取 zh_meta.json（该页译完的时刻），不取发布时刻；
- 发完重跑英文发布（给英文页补 zh_url →「中文版 →」）与 build_commentaries_index（历代解经入口改指中文目录）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'bridges_raw' / 'ecclesiastes'
ZH_SRC = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
EN = ROOT / 'bridges' / 'ecclesiastes'
OUT = EN / 'zh'
BASE = '/bridges/ecclesiastes'
ORDER = ['preface'] + [str(n) for n in range(1, 13)]
CN = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
BOOK_ZH = '传道书释义'


def label(slug):
    return '序言' if slug == 'preface' else f'第{CN[int(slug)]}章'


def en_last_verse(slug):
    m = re.search(r'^subtitle: "Ecclesiastes \d+:1–(\d+)"', (EN / f'{slug}.md').read_text(encoding='utf-8'), re.M)
    return m.group(1) if m else ''


def main():
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    done = [s for s in ORDER if (ZH_SRC / f'{s}.md').exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(done):
        body = (ZH_SRC / f'{s}.md').read_text(encoding='utf-8').strip()
        fm = ['---', 'layout: bridges-psalm119-chapter', 'zh: true', 'book_id: ecclesiastes', f'book_name: "{BOOK_ZH}"',
              f'title: "{label(s)}"']
        if s != 'preface':
            fm += [f'subtitle: "传道书 {s}:1–{en_last_verse(s)}"', f'chapter: {s}']
        fm += [f'date: {meta[s]}', f'en_url: "{BASE}/{s}/"']
        if i:
            fm += [f'prev_url: "{BASE}/zh/{done[i-1]}/"', f'prev_label: "{label(done[i-1])}"']
        if i + 1 < len(done):
            fm += [f'next_url: "{BASE}/zh/{done[i+1]}/"', f'next_label: "{label(done[i+1])}"']
        fm.append('---')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
    items = []
    for s in ORDER:
        sub = '' if s == 'preface' else f'{en_last_verse(s) and "1–" + en_last_verse(s)} 节'
        inner = f'<span class="bg-no">{label(s)}</span>{sub}' if sub else label(s)
        if s in done:
            items.append(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/zh/{s}/">{inner}</a></li>')
        else:
            items.append(f'  <li><a class="bg-other" href="{{{{ site.baseurl }}}}{BASE}/{s}/">{inner}<small>未译 · 英文</small></a></li>')
    (OUT / 'index.html').write_text(f'''---
layout: bridges-psalm119-book
zh: true
book_id: ecclesiastes
book_name: "{BOOK_ZH}"
author: "查理·毕列志（Charles Bridges，1794–1869）"
edition: "据 1860 年纽约 Robert Carter & Brothers 版译出"
title: "毕列志《{BOOK_ZH}》"
en_url: "{BASE}/"
---
<ul class="bg-toc">
{chr(10).join(items)}
</ul>
<div class="bg-note">
<p><b>文本说明。</b>据 Precept Austin 刊布的公有领域录入本译出（所据为 1860 年纽约 Robert Carter &amp; Brothers 版），
英文底本曾以 archive.org 所藏两份 1860 年扫描本校过。录入本未收作者脚注，中译亦缺。
传道书经文照录和合本；解经中引用的经文，能对上和合本的照和合本措辞。</p>
</div>
''', encoding='utf-8')
    for cmd in (['scripts/publish_bridges_ecclesiastes_en.py'], ['scripts/build_commentaries_index.py']):
        r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'{cmd[0]} 失败：{r.stderr[-400:]}')
    print(f'{len(done)} 页中文已发布：{", ".join(done)}')


if __name__ == '__main__':
    main()
