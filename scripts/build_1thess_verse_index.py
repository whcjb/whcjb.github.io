#!/usr/bin/env python3
"""扫描 calvin/1thessalonians/*.md 提取 per-verse commentary-anchor 锚点
（`<div class="commentary-anchor" id="1thessalonians-CH-V"></div>`，由
(publish_1thess_zh add_verse_anchors_in_body) 在每个 `**N.**` 注释段前插入），
生成 calvin/1thessalonians/verse-index/index.html 经文段索引页。

每节一个胶囊，点击直接跳到该节注释段。若 Calvin 未对某节单独作注（如
1:1），则该节不显示胶囊——避免出现 "点 14 跳到 7" 的错位。

索引页不收录到 _data/calvin_books.yml（不在书卷列表展示），
仅通过帖撒罗尼迦前书首页按钮访问。
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC_DIR = ROOT / 'calvin' / '1thessalonians'
OUT_PATH = ROOT / 'calvin' / '1thessalonians' / 'verse-index' / 'index.html'

# 仅匹配 per-verse 锚点 id="1thessalonians-N-V"，跳过 range 锚点 id="1thessalonians-N-S-E"
# 关键：尾部 \" 之前不能再有 -，否则就是 range
PER_VERSE_RE = re.compile(
    r'<div class="commentary-anchor" id="1thessalonians-(\d+)-(\d+)"></div>'
)


def collect_anchors() -> dict[int, list[int]]:
    """Return {chapter: [verse, ...]} sorted by chapter then verse."""
    out: dict[int, list[int]] = {}
    for path in sorted(SRC_DIR.glob('*.md')):
        if not path.stem.isdigit():
            continue
        ch_file = int(path.stem)
        text = path.read_text(encoding='utf-8')
        verses: list[int] = []
        seen: set[int] = set()
        for m in PER_VERSE_RE.finditer(text):
            ch = int(m.group(1))
            v = int(m.group(2))
            if ch != ch_file or v in seen:
                continue
            seen.add(v)
            verses.append(v)
        verses.sort()
        out[ch_file] = verses
    return dict(sorted(out.items()))


def build_html(anchors: dict[int, list[int]]) -> str:
    total = sum(len(vs) for vs in anchors.values())
    rows: list[str] = []
    for ch in sorted(anchors.keys()):
        verses = anchors[ch]
        if not verses:
            continue
        pills: list[str] = []
        for v in verses:
            aid = f'1thessalonians-{ch}-{v}'
            pills.append(
                f'<a class="vi-pill" '
                f'href="{{{{ site.baseurl }}}}/calvin/1thessalonians/{ch}/#{aid}" '
                f'title="帖撒罗尼迦前书 {ch}:{v}">{v}</a>'
            )
        rows.append(
            f'        <div class="vi-ch">\n'
            f'          <div class="vi-ch-name" title="帖撒罗尼迦前书 {ch}">{ch}</div>\n'
            f'          <div class="vi-pills">\n            '
            + '\n            '.join(pills)
            + '\n          </div>\n'
            f'        </div>'
        )

    return f'''---
layout: default
title: "帖撒罗尼迦前书注释 — 经文索引"
sitemap: false
---

<style>
  .vi-wrap {{
    font-family: Georgia, "Times New Roman", serif;
    color: #2c2c2c;
  }}
  .vi-back {{ margin: 28px 0 16px; font-size: 14px; }}
  .vi-back a {{ color: #0085a1; text-decoration: none; }}
  .vi-back a:hover {{ text-decoration: underline; }}

  .vi-title {{
    border-bottom: 2px solid #0085a1;
    padding-bottom: 8px;
    margin-bottom: 10px;
    font-size: 22px;
    letter-spacing: 0.02em;
    color: #1a1a1a;
  }}
  .vi-intro {{
    color: #777;
    line-height: 1.55;
    font-size: 13px;
    margin: 0 0 18px;
  }}
  .vi-intro strong {{ color: #2e7d32; font-weight: 600; }}

  .vi-list {{
    border-top: 1px solid #ece8d8;
  }}
  .vi-ch {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #ece8d8;
  }}
  .vi-ch-name {{
    flex: 0 0 38px;
    font-size: 15px;
    font-weight: 700;
    color: #2e7d32;
    text-align: center;
    font-family: Georgia, serif;
  }}
  .vi-pills {{
    flex: 1 1 auto;
    min-width: 0;
    display: flex;
    flex-wrap: nowrap;
    gap: 5px;
    overflow-x: auto;
    padding: 2px 0 6px;
    scrollbar-width: thin;
    scrollbar-color: #c8e6c9 transparent;
    -webkit-overflow-scrolling: touch;
  }}
  .vi-pills::-webkit-scrollbar {{ height: 5px; }}
  .vi-pills::-webkit-scrollbar-track {{ background: transparent; }}
  .vi-pills::-webkit-scrollbar-thumb {{
    background: #c8e6c9;
    border-radius: 3px;
  }}
  .vi-pills::-webkit-scrollbar-thumb:hover {{ background: #a5d6a7; }}

  .vi-pill {{
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 30px;
    height: 26px;
    padding: 0 8px;
    border-radius: 13px;
    background: #e8f5e9;
    border: 1px solid #c8e6c9;
    color: #2e7d32;
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    transition: all .12s ease;
  }}
  .vi-pill:hover {{
    background: #4caf50;
    border-color: #4caf50;
    color: #fff;
    text-decoration: none;
  }}

  @media (max-width: 640px) {{
    .vi-title {{ font-size: 19px; }}
    .vi-ch {{ gap: 8px; }}
    .vi-ch-name {{ flex: 0 0 28px; font-size: 14px; }}
    .vi-pill {{ min-width: 26px; height: 23px; padding: 0 6px; font-size: 11.5px; border-radius: 11px; }}
  }}
</style>

<div class="container vi-wrap" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div class="vi-back">
        <a href="{{{{ site.baseurl }}}}/calvin/1thessalonians/">&larr; 返回帖撒罗尼迦前书注释</a>
      </div>

      <h1 class="vi-title">加尔文《帖撒罗尼迦前书注释》— 经文索引</h1>

      <p class="vi-intro">
        共 <strong>{total}</strong> 节经文有 Calvin 注释，按章列出。点击节号胶囊跳转到对应注释段。
        <br>未列出的节号表示 Calvin 未对该节单独作注，可参看相邻节的注释。
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
    html = build_html(anchors)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding='utf-8')
    total = sum(len(vs) for vs in anchors.values())
    print(f'✓ 写入 {OUT_PATH}')
    print(f'  章数：{len(anchors)}，per-verse 锚点总数：{total}')


if __name__ == '__main__':
    main()
