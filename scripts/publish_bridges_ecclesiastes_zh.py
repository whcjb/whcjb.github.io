#!/usr/bin/env python3
"""布里奇斯《传道书释义》中文版：bridges_raw/ecclesiastes/zh_chapters/<页>.md → bridges/ecclesiastes/zh/

    python3 scripts/publish_bridges_ecclesiastes_zh.py        # translate_bridges_ecclesiastes.py 每译完一页自动调用

版式照毕列志《箴言书注释》（用户 2026-11-23）：layout bridges-chapter / bridges-book——整屏背景图、毛玻璃正文卡、
解经单元（经文块置顶 + 「注释」竖排按钮展开）、每单元首段首字下沉、经文楷体。
  - 一个单元 = 一段经文（可连排几节）+ 其后直到下一段经文的全部解经；锚点 #ec-章-起-止；
  - 经文块每节一行「N 和合本经文」；编者所补节号（6:12）写「[12]」；
  - 序言没有经文，只有正文；首段首字下沉；
  - 背景图：目录 bridges-eccl-bg-01，序言 02，第 N 章 N+2（scripts/fetch_bridges_headers.py --book ecclesiastes
    --source commons 下载，来源记 _data/bridges_eccl_image_provenance.yml）。

- 只发已译出的页；前后翻页只在已译的中文页之间连；
- 中文目录（书卷首页）右上角「English edition →」；中文章节页不放「English →」，front matter 照写 en_url；
- date 取 zh_meta.json（该页译完的时刻），不取发布时刻；
- 发完重跑英文发布（给英文页补 zh_url →「中文版 →」）与 build_commentaries_index（历代解经入口指中文目录）。
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
BOOK_ZH = '传道书释义'
AUTHOR = '查理·毕列志（Charles Bridges）'

RE_P = re.compile(r'<p( class="([^"]+)")?>(.*?)</p>', re.S)
RE_VN = re.compile(r'<span class="ec-vn" id="v(\d+)">([^<]*)</span>\s*')


def label(slug):
    return '序言' if slug == 'preface' else f'第 {slug} 章'


def bg(slug):
    return f'bridges-eccl-bg-{2 if slug == "preface" else int(slug) + 2:02d}.jpg'


def lead(p):
    """首段加首字下沉；段首是引号、书名号、括号的不下沉（下沉的会是标点）。"""
    inner = RE_P.match(p).group(3)
    if p.startswith('<p>') and not re.match(r'[“‘「『《〈（(]', inner):
        return '<p class="bridges-lead">' + inner + '</p>'
    return p


def units(slug, body):
    paras = [m.group(0) for m in RE_P.finditer(body)]
    out, cur = [], None
    if slug == 'preface':
        return '\n\n'.join([lead(paras[0])] + paras[1:])
    for p in paras:
        m = RE_P.match(p)
        if m.group(2) == 'ec-verse':
            if cur:
                out.append(cur)
            parts = RE_VN.split(m.group(3))          # ['', vnum, 显示号, 文, vnum, 显示号, 文…]
            vv = []
            for k in range(1, len(parts), 3):
                shown = parts[k + 1].strip().rstrip('.')
                vv.append((int(parts[k]), shown, parts[k + 2].strip()))
            cur = dict(vv=vv, body=[])
        else:
            if cur is None:
                raise SystemExit(f'[{slug}] 第一段经文之前有正文：{p[:80]}')
            cur['body'].append(p)
    out.append(cur)
    html = []
    for u in out:
        a, b = u['vv'][0][0], u['vv'][-1][0]
        ref = f'{a}' if a == b else f'{a}-{b}'
        verses = '\n\n'.join(f'{shown} {text}' for _, shown, text in u['vv'])
        body = '\n\n'.join([lead(u['body'][0])] + u['body'][1:]) if u['body'] else ''
        html.append(f'''<div class="bridges-unit" id="ec-{slug}-{ref}" data-ref="传道书 {slug}:{ref}">
<div class="bridges-unit-head" markdown="1">

<div class="bridges-scripture" markdown="1">

{verses}

</div>

</div>

<div class="bridges-body" markdown="1">

{body}

</div>
</div>''')
    return '\n\n'.join(html)


def main():
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    done = [s for s in ORDER if (ZH_SRC / f'{s}.md').exists()]
    OUT.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(done):
        body = (ZH_SRC / f'{s}.md').read_text(encoding='utf-8').strip()
        fm = ['---', 'layout: bridges-chapter', 'book_id: ecclesiastes', f'book_name: {BOOK_ZH}',
              f'book_url: {BASE}/zh/', f'author: "{AUTHOR}"', f'header-img: {bg(s)}',
              f'title: "{BOOK_ZH} · {label(s)}"',
              f'hero: "{"序言" if s == "preface" else f"传道书第 {s} 章"}"', f'date: {meta[s]}']
        fm += ['section: preface'] if s == 'preface' else [f'chapter: {s}', 'total_chapters: 12']
        fm.append(f'en_url: "{BASE}/{s}/"')
        if i:
            fm += [f'prev_url: {BASE}/zh/{done[i-1]}/', f'prev_label: "{label(done[i-1])}"']
        if i + 1 < len(done):
            fm += [f'next_url: {BASE}/zh/{done[i+1]}/', f'next_label: "{label(done[i+1])}"']
        fm.append('---')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + units(s, body) + '\n', encoding='utf-8')
    (OUT / 'index.html').write_text(f'''---
layout: bridges-book
book_id: ecclesiastes
book_name: {BOOK_ZH}
author: "{AUTHOR}"
chapters: 12
preface_label: 序言
header-img: bridges-eccl-bg-01.jpg
title: "{BOOK_ZH}"
en_url: "{BASE}/"
epigraph: '敬畏神，谨守他的诫命，这是人所当尽的本分。<cite>—— 传道书 12:13</cite>'
pill_cols: 6
source_note: |
  英文原著 <em>An Exposition of the Book of Ecclesiastes</em>（New York: Robert Carter &amp; Brothers, 1860）。<br>
  据 Precept Austin 公有领域录入本译出，并以 archive.org 所藏 1860 年扫描本校勘；录入本未收原书脚注。经文照录和合本。<br>
  背景图：维基共享资源（Wikimedia Commons）特色图片，CC BY-SA 等授权。
---
''', encoding='utf-8')
    for cmd in (['scripts/publish_bridges_ecclesiastes_en.py'], ['scripts/build_commentaries_index.py']):
        r = subprocess.run([sys.executable, *cmd], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'{cmd[0]} 失败：{r.stderr[-400:]}')
    print(f'{len(done)} 页中文已发布：{", ".join(done)}')


if __name__ == '__main__':
    main()
