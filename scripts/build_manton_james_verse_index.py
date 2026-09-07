#!/usr/bin/env python3
"""扫描 manton/james/<N>/index.md 的 per-verse 锚点，生成经文索引页。

锚点 `<div class="commentary-anchor" id="james-CH-V"></div>` 由
scripts/publish_manton_james.py 插在每个释经单元的经文头之后 ——
落在经文之后、释经正文之前，点胶囊直接看到注释而不是经文（step 07 §1）。

与 calvin 各卷的差别：曼顿章节是**子目录**（manton/james/1/index.md），
不是 calvin 的 `<N>.md`，扫描路径不同。

曼顿逐节讲完了雅各书全部 108 节，所以每一节都有胶囊；范围单元
（`Ver. 2-4`）在 publish 阶段已展开成逐节锚点，这里不会出现范围胶囊。

用法：python3 scripts/build_manton_james_verse_index.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / 'manton' / 'james'
OUT_PATH = SRC_DIR / 'verse-index' / 'index.html'

# 只认 per-verse 锚点 id="james-N-V"：尾部引号前不能再有 `-`，
# 所以 \d+ 自然排除了范围锚点（step 07 §4.2）
PER_VERSE_RE = re.compile(r'<div class="commentary-anchor" id="james-(\d+)-(\d+)"></div>')

ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}


def collect_anchors() -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for d in sorted(SRC_DIR.iterdir()):
        if not (d.is_dir() and d.name.isdigit()):
            continue
        ch_file = int(d.name)
        md = d / 'index.md'
        if not md.exists():
            continue
        text = md.read_text(encoding='utf-8')
        verses, seen = [], set()
        for m in PER_VERSE_RE.finditer(text):
            ch, v = int(m.group(1)), int(m.group(2))
            if ch != ch_file or v in seen:
                continue
            seen.add(v)
            verses.append(v)
        out[ch_file] = sorted(verses)
    return dict(sorted(out.items()))


def build_html(anchors: dict[int, list[int]]) -> str:
    total = sum(len(vs) for vs in anchors.values())
    rows = []
    for ch in sorted(anchors):
        verses = anchors[ch]
        if not verses:
            continue
        pills = [
            f'<a class="vi-pill" '
            f'href="{{{{ site.baseurl }}}}/manton/james/{ch}/#james-{ch}-{v}" '
            f'title="雅各书 {ch}:{v}">{v}</a>'
            for v in verses
        ]
        rows.append(
            '        <div class="vi-ch">\n'
            f'          <div class="vi-ch-name" title="雅各书 {ch}">{ch}</div>\n'
            '          <div class="vi-pills">\n            '
            + '\n            '.join(pills)
            + '\n          </div>\n'
            '        </div>'
        )

    return f'''---
layout: default
title: "曼顿《雅各书注释》— 经文索引"
sitemap: false
---

<style>
  .vi-wrap {{ font-family: Georgia, "Times New Roman", serif; color: #2c2c2c; }}
  .vi-back {{ margin: 28px 0 16px; font-size: 14px; }}
  .vi-back a {{ color: #5b2f4a; text-decoration: none; }}
  .vi-back a:hover {{ text-decoration: underline; }}

  .vi-title {{
    border-bottom: 2px solid #5b2f4a;
    padding-bottom: 8px; margin-bottom: 10px;
    font-size: 22px; letter-spacing: .02em; color: #1a1a1a;
  }}
  .vi-intro {{ color: #777; line-height: 1.55; font-size: 13px; margin: 0 0 18px; }}
  .vi-intro strong {{ color: #5b2f4a; font-weight: 600; }}

  .vi-list {{ border-top: 1px solid #ece8d8; }}
  .vi-ch {{
    display: flex; align-items: center; gap: 12px;
    padding: 8px 0; border-bottom: 1px solid #ece8d8;
  }}
  .vi-ch-name {{
    flex: 0 0 38px; font-size: 15px; font-weight: 700;
    color: #5b2f4a; text-align: center; font-family: Georgia, serif;
  }}
  .vi-pills {{
    flex: 1 1 auto; min-width: 0; display: flex; flex-wrap: nowrap; gap: 5px;
    overflow-x: auto; padding: 2px 0 6px;
    scrollbar-width: thin; scrollbar-color: #e0cfd8 transparent;
    -webkit-overflow-scrolling: touch;
  }}
  .vi-pills::-webkit-scrollbar {{ height: 5px; }}
  .vi-pills::-webkit-scrollbar-track {{ background: transparent; }}
  .vi-pills::-webkit-scrollbar-thumb {{ background: #e0cfd8; border-radius: 3px; }}
  .vi-pills::-webkit-scrollbar-thumb:hover {{ background: #c9a9b8; }}

  .vi-pill {{
    flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
    min-width: 30px; height: 26px; padding: 0 8px; border-radius: 13px;
    background: #f6eef2; border: 1px solid #e0cfd8; color: #5b2f4a;
    font-size: 12.5px; font-weight: 600; text-decoration: none;
    transition: all .12s ease;
  }}
  .vi-pill:hover {{
    background: #5b2f4a; border-color: #5b2f4a; color: #fff; text-decoration: none;
  }}

  @media (max-width: 640px) {{
    .vi-title {{ font-size: 19px; }}
    .vi-ch {{ gap: 8px; }}
    .vi-ch-name {{ flex: 0 0 28px; font-size: 14px; }}
    .vi-pill {{ min-width: 26px; height: 23px; padding: 0 6px;
                font-size: 11.5px; border-radius: 11px; }}
  }}
</style>

<div class="container vi-wrap" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div class="vi-back">
        <a href="{{{{ site.baseurl }}}}/manton/james/">&larr; 返回曼顿《雅各书注释》</a>
      </div>

      <h1 class="vi-title">托马斯·曼顿《雅各书注释》— 经文索引</h1>

      <p class="vi-intro">
        雅各书全书 <strong>{total}</strong> 节，曼顿逐节皆有讲解。点击节号胶囊跳转到该节的注释起始处。
        <br>曼顿把相邻数节合并讲解时（如 2:2&ndash;4），该组各节的胶囊都指向这一组注释的开头。
      </p>

      <div class="vi-list">
{chr(10).join(rows)}
      </div>

    </div>
  </div>
</div>
'''


def main():
    anchors = collect_anchors()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_html(anchors), encoding='utf-8')
    total = sum(len(vs) for vs in anchors.values())
    print(f'✓ 写入 {OUT_PATH}')
    for ch in sorted(anchors):
        print(f'  第 {ROMAN[ch]} 章：{len(anchors[ch])} 节')
    print(f'  per-verse 锚点总数：{total}')


if __name__ == '__main__':
    main()
