#!/usr/bin/env python3
"""亚历山大注释的经文索引页 —— 每节一个胶囊，点进去直接落在那一节的注释上。

锚点是发布时就有的 `<span class="ax-anchor" id="<book>-<ch>-<v>"></span>`，
由 `publish_alexander_en.py` 插在节号之前，章顶的 verse-nav 也认它。
所以这里只扫一遍、按章归拢，不新建任何锚点。

**只取裸 id**（`isaiah-40-1`）。同一节再起一段的 `-2`/`-3` 后缀 id 不出胶囊，
否则同一节会冒出两个按钮——`\\d+` 不吃 `-`，正则天然排除。

`preface` / `introduction` 这些前置件没有节号锚点，自然不进索引。
印面自己就没有节标题的那几节（赛 4:1、64:11，记在 `ref_printed_as_is.tsv`）
也就没有胶囊——**宁可缺一节，也不要点过去落到隔壁节**。

配色用亚历山大自己的那套（`--ax-ink` 砖红），不沿用别家的
（[[feedback_book_style_isolation]]）。

验收不能只看「生成了多少胶囊」——胶囊指向的锚点在**渲染后的页面**里存不存在
是另一回事（锚点写在 markdown 里，kramdown 可能把它吞进 `<p>`，或者章节页
根本没建出来）。`--check` 就是照着 `_site/` 逐个胶囊核一遍，要先
`bundle exec jekyll build`。

用法：
    python3 scripts/build_alexander_verse_index.py            # 两本都建
    python3 scripts/build_alexander_verse_index.py --book isaiah
    bundle exec jekyll build --quiet && \
      python3 scripts/build_alexander_verse_index.py --check  # 逐个胶囊核落点
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    'isaiah': {'cn': '以赛亚书', 'en': 'Isaiah',
               'author_cn': '亚历山大', 'author_en': 'J. A. Alexander'},
    'psalms': {'cn': '诗篇', 'en': 'Psalms',
               'author_cn': '亚历山大', 'author_en': 'J. A. Alexander'},
}
# 行首那个标签：诗篇是「篇」不是「章」
UNIT = {'isaiah': 'Ch.', 'psalms': 'Ps.'}

INK, INK_DARK, RULE, PAPER = '#7d2f2f', '#5f2323', '#e2d2cc', '#fdfaf7'


def anchor_re(book):
    return re.compile(r'<span class="ax-anchor" id="'
                      + re.escape(book) + r'-(\d+)-(\d+)"></span>')


def collect(book):
    """{章: [节, …]}，按正文出现顺序去重。"""
    rx = anchor_re(book)
    out = defaultdict(list)
    for f in sorted((ROOT / 'alexander' / book).glob('[0-9]*.md'),
                    key=lambda p: int(p.stem)):
        for ch, v in rx.findall(f.read_text(encoding='utf-8')):
            out[int(ch)].append(int(v))
    for ch, vs in out.items():
        seen, uniq = set(), []
        for v in vs:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        out[ch] = uniq
    return dict(sorted(out.items()))


def build_html(book, anchors):
    meta = BOOKS[book]
    en_unit = UNIT[book]
    total = sum(len(v) for v in anchors.values())

    rows = []
    for ch in sorted(anchors):
        pills = '\n        '.join(
            f'<a class="ax-vi-pill" href="{{{{ site.baseurl }}}}'
            f'/alexander/{book}/{ch}/#{book}-{ch}-{v}">{v}</a>'
            for v in anchors[ch])
        rows.append(f'      <div class="ax-vi-row">\n'
                    f'        <div class="ax-vi-label">{en_unit} {ch}</div>\n'
                    f'        <div class="ax-vi-track">\n        {pills}\n'
                    f'        </div>\n      </div>')

    title = f'{meta["author_en"]} on {meta["en"]} — Verse Index'
    back = f'&larr; Back to {meta["author_en"]} on {meta["en"]}'
    intro = (f'{total} verses with a comment of their own, listed by '
             f'{"psalm" if book == "psalms" else "chapter"}. '
             f'Click a verse number to jump straight to its comment. '
             f'A number not listed is one Alexander discusses together with '
             f'its neighbour rather than under a heading of its own.')

    return f'''---
layout: default
title: "{title}"
sitemap: false
---

<style>
  .ax-vi {{ --ax-ink: {INK}; --ax-ink-dark: {INK_DARK};
            --ax-rule: {RULE}; --ax-paper: {PAPER};
            font-family: Georgia, 'Times New Roman', serif; color: #2c2c2c; }}
  .ax-vi-title {{ font-family: Georgia, serif; font-size: 25px; font-weight: bold;
    color: var(--ax-ink-dark); margin: 0 0 16px; padding-bottom: 10px;
    border-bottom: 2px solid var(--ax-ink); }}
  .ax-vi-intro {{ color: #666; line-height: 1.75; margin-bottom: 26px;
    font-size: 15px; }}
  .ax-vi-back {{ margin: 0 0 24px; }}
  .ax-vi-back a {{ color: var(--ax-ink); text-decoration: none; font-size: 13.5px; }}
  .ax-vi-back a:hover {{ color: var(--ax-ink-dark); }}
  .ax-vi-row {{ display: flex; align-items: flex-start; margin: 8px 0; }}
  .ax-vi-label {{ flex: 0 0 76px; padding-top: 6px; font-size: 14px;
    font-weight: bold; color: var(--ax-ink); }}
  .ax-vi-track {{ flex: 1; display: flex; flex-wrap: wrap; gap: 6px; padding: 4px 0; }}
  .ax-vi-pill {{ flex: 0 0 auto; display: inline-flex; align-items: center;
    justify-content: center; min-width: 32px; height: 28px; padding: 0 8px;
    border-radius: 14px; background: var(--ax-paper);
    border: 1px solid var(--ax-rule); color: var(--ax-ink);
    font-size: 13px; font-weight: bold; text-decoration: none;
    transition: all .15s ease; }}
  .ax-vi-pill:hover {{ background: var(--ax-ink); border-color: var(--ax-ink);
    color: var(--ax-paper) !important; text-decoration: none; }}
  @media (max-width: 600px) {{ .ax-vi-label {{ flex-basis: 58px; font-size: 13px; }} }}
</style>

<div class="container ax-vi" style="padding-top: 70px;">
  <div class="row">
    <div class="col-lg-9 col-lg-offset-1 col-md-10 col-md-offset-1">

      <div class="ax-vi-back">
        <a href="{{{{ site.baseurl }}}}/alexander/{book}/">{back}</a>
      </div>

      <h1 class="ax-vi-title">{title}</h1>

      <p class="ax-vi-intro">{intro}</p>

{chr(10).join(rows)}

    </div>
  </div>
</div>
'''


def check(book):
    """逐个胶囊去渲染后的页面里找它的落点。返回落空的清单。"""
    site = ROOT / '_site' / 'alexander' / book
    idx = site / 'verse-index' / 'index.html'
    if not idx.exists():
        raise SystemExit(f'✗ {idx.relative_to(ROOT)} 不在——先 bundle exec jekyll build')
    pills = re.findall(r'href="/alexander/' + re.escape(book)
                       + r'/(\d+)/#([a-z0-9-]+)"', idx.read_text(encoding='utf-8'))
    ids, bad = {}, []
    for ch, aid in pills:
        if ch not in ids:
            f = site / ch / 'index.html'
            ids[ch] = set(re.findall(r'id="([^"]+)"',
                                     f.read_text(encoding='utf-8'))) if f.exists() else set()
        if aid not in ids[ch]:
            bad.append(f'{ch}#{aid}')
    print(f'{book}: 胶囊 {len(pills)} 个，落空 {len(bad)} 个'
          + ('' if not bad else '：' + '、'.join(bad[:8])))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', choices=sorted(BOOKS))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        bad = sum((check(b) for b in ([a.book] if a.book else sorted(BOOKS))), [])
        return 1 if bad else 0
    for book in ([a.book] if a.book else sorted(BOOKS)):
        anchors = collect(book)
        if not anchors:
            print(f'{book}: 一个节号锚点也没有，跳过')
            continue
        out = ROOT / 'alexander' / book / 'verse-index' / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(build_html(book, anchors), encoding='utf-8')
        print(f'{book}: {len(anchors)} 章 {sum(len(v) for v in anchors.values())} 节'
              f' → {out.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
