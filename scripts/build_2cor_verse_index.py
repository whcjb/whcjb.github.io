#!/usr/bin/env python3
"""扫描 calvin/2corinthians/*.md 找 `<div class="commentary-anchor" id="2corinthians-N-V">`
per-verse 锚点，生成 calvin/2corinthians/verse-index/index.html 细化到节的注释索引。

每个有 Calvin 注释的经节 → 一个 pill，链接 `/calvin/2corinthians/<ch>/#2corinthians-<ch>-<v>`，
点击直跳到注释段（不是经文块）。

索引页不收录到 _data/calvin_books.yml（不在书卷列表展示），
仅通过哥林多后书首页按钮访问。
"""
from __future__ import annotations
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC_DIR = ROOT / 'calvin' / '2corinthians'
OUT_PATH = ROOT / 'calvin' / '2corinthians' / 'verse-index' / 'index.html'

# per-verse anchor only (exclude range anchors like 2corinthians-1-1-3 with hyphen prefix)
ANCHOR_RE = re.compile(r'<div class="commentary-anchor" id="2corinthians-(\d+)-(\d+)"></div>')


def collect_anchors() -> dict[int, list[int]]:
    """Return {chapter: [verse, ...]} sorted."""
    out: dict[int, set[int]] = defaultdict(set)
    for path in sorted(SRC_DIR.glob('*.md')):
        if not path.stem.isdigit():
            continue
        ch_file = int(path.stem)
        text = path.read_text(encoding='utf-8')
        for m in ANCHOR_RE.finditer(text):
            ch = int(m.group(1))
            v = int(m.group(2))
            if ch == ch_file:
                out[ch].add(v)
    return {ch: sorted(verses) for ch, verses in sorted(out.items())}


def build_html(anchors: dict[int, list[int]]) -> str:
    total_pills = sum(len(vs) for vs in anchors.values())
    rows = []
    for ch in sorted(anchors.keys()):
        verses = anchors[ch]
        pills = []
        for v in verses:
            pills.append(
                f'<a class="verse-pill" '
                f'href="{{{{ site.baseurl }}}}/calvin/2corinthians/{ch}/#2corinthians-{ch}-{v}" '
                f'title="哥林多后书 {ch}:{v}">'
                f'<span class="pill-verse">{v}</span></a>'
            )
        rows.append(
            f'<div class="ch-row">\n'
            f'  <div class="ch-label">哥林多后书 {ch}</div>\n'
            f'  <div class="ch-track">\n'
            f'    ' + '\n    '.join(pills) + '\n'
            f'  </div>\n'
            f'</div>'
        )

    return f'''---
layout: default
title: "哥林多后书注释 — 经文索引"
sitemap: false
---

<style>
  .ch-row {{ display:flex; align-items:flex-start; margin:8px 0; }}
  .ch-label {{
    flex:0 0 110px; font-weight:600; color:#0085a1;
    padding-top:6px; font-size:14px;
  }}
  .ch-track {{
    flex:1; display:flex; flex-wrap:nowrap; overflow-x:auto;
    gap:6px; padding:4px 8px;
    scrollbar-width:thin;
  }}
  .ch-track::-webkit-scrollbar {{ height:6px; }}
  .ch-track::-webkit-scrollbar-thumb {{ background:#ddd; border-radius:3px; }}
  .verse-pill {{
    flex:0 0 auto;
    display:inline-flex; align-items:center; justify-content:center;
    min-width:32px; height:28px; padding:0 8px;
    border-radius:14px; background:#e8f4f6; color:#0085a1;
    font-size:13px; font-weight:600; text-decoration:none;
    transition:all .15s ease;
  }}
  .verse-pill:hover {{
    background:#0085a1; color:#fff; text-decoration:none;
  }}
  .verse-index-intro {{ color:#666; margin-bottom:24px; line-height:1.7; }}
  .verse-index-back {{ margin:32px 0 24px; }}
</style>

<div class="container" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div class="verse-index-back">
        <a href="{{{{ site.baseurl }}}}/calvin/2corinthians/">&larr; 返回哥林多后书注释</a>
      </div>

      <h1 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:16px;">
        加尔文《哥林多后书注释》— 经文索引
      </h1>

      <p class="verse-index-intro">
        本索引按章逐节列出有 Calvin 注释的经节，共 {total_pills} 节。
        点击任一胶囊按钮直接跳转到对应注释段。未列出的节号表示 Calvin 未对该节单独作注。
      </p>

      {chr(10).join(rows)}

    </div>
  </div>
</div>
'''


def main():
    anchors = collect_anchors()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_html(anchors), encoding='utf-8')
    n_ch = len(anchors)
    n_v = sum(len(v) for v in anchors.values())
    print(f'wrote {OUT_PATH.relative_to(ROOT)} — {n_ch} chapters, {n_v} verses')


if __name__ == '__main__':
    main()
