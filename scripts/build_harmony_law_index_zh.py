#!/usr/bin/env python3
"""扫描律法合参(harmony-law-1/2/3/4) ZH 章节里的逐节锚点
(`<a class="verse-anchor" id="{slug}-{ch}-{v}">` 或 `scripture-anchor` 精确逐节 id),
构建摩西五经合参经文索引页, 与对观福音合参索引(build_harmony_index_zh.py)同构。

按 书卷(出/利/民/申) → 章 → 逐节 排布, 每节一个胶囊链到「卷X 第Y章」的该节锚点。
先跑 add_law_verse_anchors.py 确保每个注释头都有逐节锚点。
"""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
INDEX_PATH = ROOT / 'calvin' / 'harmony-law-index' / 'index.html'

VOL_DIRS = [
    ('卷一', 'harmony-law-1'),
    ('卷二', 'harmony-law-2'),
    ('卷三', 'harmony-law-3'),
    ('卷四', 'harmony-law-4'),
]

BOOK_LABEL = {
    'genesis': '创世记', 'exodus': '出埃及记', 'leviticus': '利未记',
    'numbers': '民数记', 'deuteronomy': '申命记',
}
BOOK_ORDER = ['genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy']
H2_ID = {b: b for b in BOOK_ORDER}

# 精确逐节 id: slug-章-节 (排除范围 slug-章-节-节)
ANCHOR_RE = re.compile(r'\bid="(genesis|exodus|leviticus|numbers|deuteronomy)-(\d+)-(\d+)"(?!-)')


def collect():
    """{book: {ch: [(v, vol_label, vol_id, harmony_ch), ...]}}"""
    book_map = defaultdict(lambda: defaultdict(list))
    for vol_label, vol_id in VOL_DIRS:
        vol_dir = ROOT / 'calvin' / vol_id
        if not vol_dir.exists():
            continue
        for path in sorted(vol_dir.glob('[0-9]*.md')):
            harmony_ch = int(path.stem)
            text = path.read_text(encoding='utf-8')
            seen = set()
            for m in ANCHOR_RE.finditer(text):
                book, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
                key = (book, ch, v)
                if key in seen:
                    continue
                seen.add(key)
                book_map[book][ch].append((v, vol_label, vol_id, harmony_ch))
    return book_map


def render(book_map):
    present = [b for b in BOOK_ORDER if b in book_map]
    nav = ' &middot; '.join(
        f'<a href="#{H2_ID[b]}">{BOOK_LABEL[b]}</a>' for b in present)

    o = []
    o.append('---')
    o.append('layout: default')
    o.append('title: "摩西五经合参 — 经文索引"')
    o.append('---')
    o.append('')
    o.append('<div class="container" style="padding-top: 70px;">')
    o.append('  <div class="row">')
    o.append('    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">')
    o.append('')
    o.append('      <div style="margin: 32px 0 24px;">')
    o.append('        <a href="{{ site.baseurl }}/calvin/">&larr; 返回书卷列表</a>')
    o.append('      </div>')
    o.append('')
    o.append('      <h1 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:16px;">')
    o.append('        加尔文《摩西五经合参》— 经文索引')
    o.append('      </h1>')
    o.append('')
    o.append('      <p style="color:#666; margin-bottom:24px;">')
    o.append('        本索引按出埃及记、利未记、民数记、申命记逐节列出有 Calvin 注释的经节。点击任一胶囊按钮直接跳转到对应注释段。')
    o.append('      </p>')
    o.append('')
    o.append(f'      <p class="verse-index-nav">{nav}</p>')
    o.append('')

    for book in present:
        o.append(f'<h2 id="{H2_ID[book]}">{BOOK_LABEL[book]}</h2>')
        o.append('')
        for ch in sorted(book_map[book].keys()):
            entries = sorted(set(book_map[book][ch]), key=lambda t: (t[0], t[1]))
            seen_v, unique = set(), []
            for e in entries:
                if e[0] in seen_v:
                    continue
                seen_v.add(e[0])
                unique.append(e)
            o.append('<div class="ch-row">')
            o.append(f'  <div class="ch-label">{BOOK_LABEL[book]} {ch}</div>')
            o.append('  <div class="ch-track">')
            for v, vol_label, vol_id, harmony_ch in unique:
                href = (f'{{{{ site.baseurl }}}}/calvin/{vol_id}/{harmony_ch}/'
                        f'#{book}-{ch}-{v}')
                loc = f'{vol_label} 第{harmony_ch}章'
                title = f'{BOOK_LABEL[book]} {ch}:{v} → {loc}'
                o.append(
                    f'    <a class="verse-pill" href="{href}" title="{title}">'
                    f'<span class="pill-verse">{v}</span>'
                    f'<span class="pill-loc">{loc}</span></a>')
            o.append('  </div>')
            o.append('</div>')
            o.append('')

    o.append('    </div>')
    o.append('  </div>')
    o.append('</div>')
    o.append('')
    o.append('''<style>
.verse-index-nav { margin: 24px 0; font-size: 15px; }
.verse-index-nav a { color: #0085a1; font-weight: bold; padding: 0 6px; }
.container h2[id] {
  margin-top: 36px; padding-bottom: 6px;
  border-bottom: 2px solid #0085a1; color: #0085a1;
}
.ch-row { display: flex; align-items: stretch; margin-bottom: 6px; gap: 12px; }
.ch-label {
  flex: 0 0 96px; font-family: Georgia, serif; font-weight: bold;
  font-size: 14px; color: #444; padding: 8px 4px; text-align: right;
  border-right: 2px solid #0085a1;
}
.ch-track {
  flex: 1 1 auto; display: flex; gap: 6px; overflow-x: auto;
  overflow-y: hidden; padding: 4px 8px 8px 8px; scrollbar-width: thin;
}
.ch-track::-webkit-scrollbar { height: 6px; }
.ch-track::-webkit-scrollbar-thumb { background: #c0d4d9; border-radius: 3px; }
.verse-pill {
  flex: 0 0 auto; display: inline-flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 4px 12px;
  background: #e8f5e9; border: 1px solid #a5d6a7; border-radius: 14px;
  color: #2e7d32; text-decoration: none; font-family: Georgia, serif;
  white-space: nowrap; transition: background 0.12s; min-width: 64px;
}
.verse-pill:hover {
  background: #4caf50; border-color: #4caf50; color: #fff; text-decoration: none;
}
.pill-verse { font-size: 14px; font-weight: bold; line-height: 1.2; }
.pill-loc { font-size: 10px; opacity: 0.75; margin-top: 1px; }
</style>''')
    return '\n'.join(o)


def main():
    book_map = collect()
    total = sum(sum(len(v) for v in chs.values()) for chs in book_map.values())
    print(f'Collected {total} verse anchors')
    for b in BOOK_ORDER:
        if b in book_map:
            c = sum(len(v) for v in book_map[b].values())
            print(f'  {BOOK_LABEL[b]}: {c} verses across {len(book_map[b])} chapters')
    text = render(book_map)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(text, encoding='utf-8')
    print(f'\nWrote {INDEX_PATH} ({len(text)} chars)')


if __name__ == '__main__':
    main()
