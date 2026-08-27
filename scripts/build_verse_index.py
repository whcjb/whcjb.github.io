#!/usr/bin/env python3
"""为中文注释书生成「按章逐节」的经文索引页（pdf-pipeline Step 7）。

扫描 calvin/<book>/*.md 里的 per-verse 锚点
    <div class="commentary-anchor" id="<book>-CH-V"></div>
生成 calvin/<book>/verse-index/index.html，每节一个胶囊，点击跳到该节注释段。

与 build_acts_verse_index.py 等价，但参数化书名——8 卷各 clone 一份 200 行脚本
不好维护，逻辑完全相同，差别只有 book_id / 中文书名。

三条用户底线（07-verse-index.md §0，写错要被打回）：
  1. 胶囊必须跳到**注释**，不是经文块 → 依赖 publish 脚本里的
     relocate_anchors_in_body 把 id 从 <h2 scripture-anchor> 挪到经文块之后；
  2. 一个胶囊一节，不准 `5-8` 这种范围胶囊；
  3. 必须节级精度，不准链到范围锚点（会跳到范围首节，后面全对不齐）。

所以**范围锚点一律跳过**：Calvin 没对某节单独作注就不给胶囊，
宁可缺一节，也不要点了跳错地方。

⚠️ 前置条件：calvin/<book>/*.md 里必须已有 commentary-anchor。
   若 `grep -c commentary-anchor` 为 0，先确认 publish_<book>_zh.py 里
   已调用 relocate_anchors_in_body 并重跑 publish。

用法:
    python3 scripts/build_verse_index.py daniel
    python3 scripts/build_verse_index.py            # 处理所有已配置的书
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# book_id → 中文书名
BOOKS = {
    'daniel': '但以理书',
    'ezekiel': '以西结书',
    'hosea': '何西阿书',
    'joel': '约珥书',
    'malachi': '玛拉基书',
    'lamentations': '耶利米哀歌',
    'amos': '阿摩司书',
    'obadiah': '俄巴底亚书',
    'jonah': '约拿书',
    'micah': '弥迦书',
    'nahum': '那鸿书',
    'habakkuk': '哈巴谷书',
    'zephaniah': '西番雅书',
    'haggai': '哈该书',
    'zechariah': '撒迦利亚书',
}

CSS = '''<style>
  .vi-wrap { font-family: Georgia, "Times New Roman", serif; color: #2c2c2c; }
  .vi-back { margin: 28px 0 16px; font-size: 14px; }
  .vi-back a { color: #0085a1; text-decoration: none; }
  .vi-back a:hover { text-decoration: underline; }
  .vi-title { border-bottom: 2px solid #0085a1; padding-bottom: 8px;
              margin-bottom: 10px; font-size: 22px; letter-spacing: 0.02em; color: #1a1a1a; }
  .vi-intro { color: #777; line-height: 1.55; font-size: 13px; margin: 0 0 18px; }
  .vi-intro strong { color: #2e7d32; font-weight: 600; }
  .vi-list { border-top: 1px solid #ece8d8; }
  .vi-ch { display: flex; align-items: center; gap: 12px; padding: 8px 0;
           border-bottom: 1px solid #ece8d8; }
  .vi-ch-name { flex: 0 0 38px; font-size: 15px; font-weight: 700; color: #2e7d32;
                text-align: center; font-family: Georgia, serif; }
  .vi-pills { flex: 1 1 auto; min-width: 0; display: flex; flex-wrap: nowrap; gap: 5px;
              overflow-x: auto; padding: 2px 0 6px; scrollbar-width: thin;
              scrollbar-color: #c8e6c9 transparent; -webkit-overflow-scrolling: touch; }
  .vi-pills::-webkit-scrollbar { height: 5px; }
  .vi-pills::-webkit-scrollbar-track { background: transparent; }
  .vi-pills::-webkit-scrollbar-thumb { background: #c8e6c9; border-radius: 3px; }
  .vi-pills::-webkit-scrollbar-thumb:hover { background: #a5d6a7; }
  .vi-pill { flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
             min-width: 30px; height: 26px; padding: 0 8px; border-radius: 13px;
             background: #e8f5e9; border: 1px solid #c8e6c9; color: #2e7d32;
             font-size: 12.5px; font-weight: 600; text-decoration: none; transition: all .12s ease; }
  .vi-pill:hover { background: #4caf50; border-color: #4caf50; color: #fff; text-decoration: none; }
  @media (max-width: 640px) {
    .vi-title { font-size: 19px; }
    .vi-ch { gap: 8px; }
    .vi-ch-name { flex: 0 0 28px; font-size: 14px; }
    .vi-pill { min-width: 26px; height: 23px; padding: 0 6px; font-size: 11.5px; border-radius: 11px; }
  }
</style>'''


def collect(book: str) -> dict[int, list[int]]:
    """{章: [节, ...]}。只收单节锚点，范围锚点（id 尾部多一段）跳过。"""
    src = ROOT / 'calvin' / book
    per_verse = re.compile(
        r'<div class="commentary-anchor" id="' + re.escape(book) + r'-(\d+)-(\d+)"></div>')
    out: dict[int, list[int]] = {}
    for path in sorted(src.glob('*.md')):
        if not path.stem.isdigit():
            continue
        ch_file = int(path.stem)
        verses, seen = [], set()
        for m in per_verse.finditer(path.read_text(encoding='utf-8')):
            ch, v = int(m.group(1)), int(m.group(2))
            if ch != ch_file or v in seen:
                continue
            seen.add(v)
            verses.append(v)
        out[ch_file] = sorted(verses)
    return dict(sorted(out.items()))


def build_html(book: str, name: str, anchors: dict[int, list[int]]) -> str:
    total = sum(len(v) for v in anchors.values())
    rows = []
    for ch in sorted(anchors):
        verses = anchors[ch]
        if not verses:
            continue
        pills = '\n            '.join(
            f'<a class="vi-pill" href="{{{{ site.baseurl }}}}/calvin/{book}/{ch}/#{book}-{ch}-{v}"'
            f' title="{name} {ch}:{v}">{v}</a>' for v in verses)
        rows.append(
            '        <div class="vi-ch">\n'
            f'          <div class="vi-ch-name" title="{name} {ch}">{ch}</div>\n'
            '          <div class="vi-pills">\n            '
            + pills + '\n          </div>\n        </div>')
    body = '\n'.join(rows)
    return f'''---
layout: default
title: "{name}注释 — 经文索引"
sitemap: false
---

{CSS}

<div class="container vi-wrap" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div class="vi-back">
        <a href="{{{{ site.baseurl }}}}/calvin/{book}/">&larr; 返回{name}注释</a>
      </div>

      <h1 class="vi-title">加尔文《{name}注释》— 经文索引</h1>

      <p class="vi-intro">
        共 <strong>{total}</strong> 节经文有 Calvin 注释，按章列出。点击节号胶囊跳转到对应注释段。
        <br>未列出的节号表示 Calvin 未对该节单独作注，可参看相邻节的注释。
      </p>

      <div class="vi-list">
{body}
      </div>

    </div>
  </div>
</div>
'''


def main():
    todo = sys.argv[1:] or list(BOOKS)
    for book in todo:
        if book not in BOOKS:
            print(f'  未知书 {book!r}，已知：{", ".join(BOOKS)}', file=sys.stderr)
            continue
        src = ROOT / 'calvin' / book
        if not src.is_dir():
            print(f'  {book}: calvin/{book}/ 不存在，跳过（尚未发布中译）')
            continue
        if not any('commentary-anchor' in p.read_text(encoding='utf-8')
                   for p in src.glob('[0-9]*.md')):
            print(f'  {book}: 没有 commentary-anchor，先跑 publish（需含 relocate_anchors_in_body）')
            continue
        anchors = collect(book)
        if not sum(len(v) for v in anchors.values()):
            # 一个单节锚点都没有（如 obadiah：14 个锚点全是范围级）。
            # 空索引页没有意义，也别留个死链在书首页上——不生成就不会有按钮，
            # layout 是按「索引页是否存在」决定显不显示入口的。
            print(f'  – {book}: 没有单节锚点（锚点都是范围级），跳过')
            continue
        out = src / 'verse-index' / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_html(book, BOOKS[book], anchors), encoding='utf-8')
        total = sum(len(v) for v in anchors.values())
        print(f'  ✓ {book}: {len(anchors)} 章 / {total} 个节级胶囊 → {out.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
