#!/usr/bin/env python3
"""生成贺智注释的经文索引页 —— 每节一个胶囊，点击直跳该节注释段。

扫 hodge/<book>/[0-9]*.md（英文）与 hodge/<book>/zh/[0-9]*.md（中文）里的
per-verse 锚点 `<div class="commentary-anchor" id="<book>-<ch>-<v>"></div>`
（由 scripts/add_hodge_verse_anchors.py 注入），产出：

    hodge/<book>/verse-index/index.html        英文
    hodge/<book>/zh/verse-index/index.html     中文

只取裸 id（`2corinthians-1-6`）。同一节再起一段的 `-2/-3` 后缀 id 不出胶囊，
避免同一节冒出两个按钮。

用法:
    python3 scripts/build_hodge_verse_index.py
    python3 scripts/build_hodge_verse_index.py --book 2corinthians
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    '1corinthians': {'cn': '哥林多前书', 'en': '1 Corinthians', 'chapters': 16},
    '2corinthians': {'cn': '哥林多后书', 'en': '2 Corinthians', 'chapters': 13},
}

# 裸 per-verse id 才要；`-2`/`-3` 重复段后缀不进索引（\d+ 不吃 -，天然排除）
def anchor_re(book):
    return re.compile(
        r'<div class="commentary-anchor" id="' + re.escape(book) + r'-(\d+)-(\d+)"></div>')


def collect(book, zh):
    d = ROOT / 'hodge' / book / ('zh' if zh else '')
    rx = anchor_re(book)
    out = defaultdict(list)
    if not d.is_dir():
        return out
    for f in sorted(d.glob('[0-9]*.md'), key=lambda p: int(p.stem)):
        for ch, v in rx.findall(f.read_text(encoding='utf-8')):
            out[int(ch)].append(int(v))
    for ch in out:
        seen, uniq = set(), []
        for v in out[ch]:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        out[ch] = uniq
    return out


def build_html(book, zh, anchors):
    meta = BOOKS[book]
    seg = 'zh/' if zh else ''
    total = sum(len(v) for v in anchors.values())

    rows = []
    for ch in sorted(anchors):
        pills = '\n        '.join(
            f'<a class="vi-pill" href="{{{{ site.baseurl }}}}/hodge/{book}/{seg}{ch}/'
            f'#{book}-{ch}-{v}">{v}</a>'
            for v in anchors[ch])
        label = f'第 {ch} 章' if zh else f'Ch. {ch}'
        rows.append(
            f'      <div class="vi-row">\n'
            f'        <div class="vi-label">{label}</div>\n'
            f'        <div class="vi-track">\n        {pills}\n        </div>\n'
            f'      </div>')

    if zh:
        title = f'贺智《{meta["cn"]}注释》— 经文索引'
        back = f'&larr; 返回贺智《{meta["cn"]}注释》'
        intro = (f'本索引按章逐节列出贺智作注的经节，共 {total} 节。'
                 f'点击任一节号直接跳到该节的注释段。'
                 f'未列出的节号表示贺智未对该节单独立段作注（多半并入相邻节一并讨论）。')
    else:
        title = f'Hodge on {meta["en"]} — Verse Index'
        back = f'&larr; Back to Hodge on {meta["en"]}'
        intro = (f'{total} verses with commentary, listed by chapter. '
                 f'Click a verse number to jump straight to its comment. '
                 f'Numbers not listed are treated together with an adjacent verse.')

    return f'''---
layout: default
title: "{title}"
sitemap: false
---

<style>
  .vi-wrap {{ font-family: 'Georgia', 'Times New Roman', serif; color:#2c2c2c; }}
  .vi-row {{ display:flex; align-items:flex-start; margin:8px 0; }}
  .vi-label {{ flex:0 0 92px; padding-top:6px; font-size:14px; font-weight:600; color:#8a6d3b; }}
  .vi-track {{
    flex:1; display:flex; flex-wrap:wrap; gap:6px; padding:4px 8px;
  }}
  .vi-pill {{
    flex:0 0 auto; display:inline-flex; align-items:center; justify-content:center;
    min-width:32px; height:28px; padding:0 8px; border-radius:14px;
    background:#f3ecdc; border:1px solid #d8c9a4; color:#8a6d3b;
    font-size:13px; font-weight:600; text-decoration:none; transition:all .15s ease;
  }}
  .vi-pill:hover {{ background:#8a6d3b; border-color:#8a6d3b; color:#fff; text-decoration:none; }}
  .vi-intro {{ color:#666; margin-bottom:24px; line-height:1.75; }}
  .vi-back {{ margin:32px 0 24px; }}
  .vi-back a {{ color:#8a6d3b; text-decoration:none; font-size:13.5px; }}
  .vi-title {{
    font-size:24px; color:#8a6d3b; font-weight:600; letter-spacing:.03em;
    border-bottom:2px solid #8a6d3b; padding-bottom:9px; margin:0 0 16px;
  }}
</style>

<div class="container vi-wrap" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div class="vi-back">
        <a href="{{{{ site.baseurl }}}}/hodge/{book}/{seg}">{back}</a>
      </div>

      <h1 class="vi-title">{title}</h1>

      <p class="vi-intro">{intro}</p>

{chr(10).join(rows)}

    </div>
  </div>
</div>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book')
    a = ap.parse_args()
    books = [a.book] if a.book else list(BOOKS)

    for book in books:
        for zh in (False, True):
            anchors = collect(book, zh)
            if not anchors:
                print(f'{book}/{"zh" if zh else "en"}: 无锚点，跳过')
                continue
            out = ROOT / 'hodge' / book / ('zh' if zh else '') / 'verse-index' / 'index.html'
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(build_html(book, zh, anchors), encoding='utf-8')
            n = sum(len(v) for v in anchors.values())
            print(f'{book}/{"zh" if zh else "en"}: {len(anchors)} 章 {n} 节 → '
                  f'{out.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
