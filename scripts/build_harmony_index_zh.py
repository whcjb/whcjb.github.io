#!/usr/bin/env python3
"""Scan harmony-1/2/3 ZH chapter md files for `<a class="verse-anchor"
id="<book>-<ch>-<v>"></a>` markers, then build the ZH harmony index page.

Each verse with commentary gets ONE pill linking to its specific anchor.
Layout groups by book → chapter → ordered verses.
"""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
INDEX_PATH = ROOT / 'calvin' / 'harmony-index' / 'index.html'

# Volume → chapters
VOL_DIRS = [
    ('卷一', 'harmony-1', 'harmony-1'),
    ('卷二', 'harmony-2', 'harmony-2'),
    ('卷三', 'harmony-3', 'harmony-3'),
]

BOOK_LABEL = {
    'matt': '马太福音',
    'mark': '马可福音',
    'luke': '路加福音',
    'john': '约翰福音',
}

# Iteration order for the index sections
BOOK_ORDER = ['matt', 'mark', 'luke', 'john']

# h2 anchor for each book section (matches original EN index + CSS selectors)
H2_ID = {'matt': 'matthew', 'mark': 'mark', 'luke': 'luke', 'john': 'john'}

ANCHOR_RE = re.compile(
    r'<a class="verse-anchor" id="(matt|mark|luke|john)-(\d+)-(\d+)"></a>'
)


def collect_anchors():
    """Return {book: {ch_int: [(verse_int, vol_label, vol_id, harmony_ch_int), ...]}}.

    Each entry is a (verse, vol_label, vol_id, harmony_ch) tuple. If the
    same verse appears in multiple harmony volumes (rare), we list both.
    """
    book_map = defaultdict(lambda: defaultdict(list))
    for vol_label, vol_id, _ in VOL_DIRS:
        vol_dir = ROOT / 'calvin' / vol_id
        if not vol_dir.exists():
            continue
        for path in sorted(vol_dir.glob('*.md')):
            if not path.stem.isdigit():
                continue
            harmony_ch = int(path.stem)
            text = path.read_text(encoding='utf-8')
            seen_in_file = set()  # avoid duplicates within same file
            for m in ANCHOR_RE.finditer(text):
                book, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
                key = (book, ch, v)
                if key in seen_in_file:
                    continue
                seen_in_file.add(key)
                book_map[book][ch].append((v, vol_label, vol_id, harmony_ch))
    return book_map


def vol_chap_label(vol_label, harmony_ch):
    return f'{vol_label} 第{harmony_ch}章'


def render_index(book_map):
    # Compute existing books present
    present_books = [b for b in BOOK_ORDER if b in book_map]
    nav = ' &middot; '.join(
        f'<a href="#{H2_ID[b]}">{BOOK_LABEL[b]}</a>' for b in present_books
    )

    out = []
    out.append('---')
    out.append('layout: default')
    out.append('title: "共观福音注释 — 经文索引"')
    out.append('---')
    out.append('')
    out.append('<div class="container" style="padding-top: 70px;">')
    out.append('  <div class="row">')
    out.append('    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">')
    out.append('')
    out.append('      <div style="margin: 32px 0 24px;">')
    out.append('        <a href="{{ site.baseurl }}/calvin/">&larr; 返回书卷列表</a>')
    out.append('      </div>')
    out.append('')
    out.append('      <h1 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:16px;">')
    out.append('        加尔文《共观福音注释》— 经文索引')
    out.append('      </h1>')
    out.append('')
    out.append('      <p style="color:#666; margin-bottom:24px;">')
    out.append('        本索引按马太、马可、路加三福音逐节列出有 Calvin 注释的经节。点击任一胶囊按钮直接跳转到对应注释段（非经文块）。')
    out.append('      </p>')
    out.append('')
    out.append(f'      <p class="verse-index-nav">{nav}</p>')
    out.append('')

    for book in present_books:
        out.append(f'<h2 id="{H2_ID[book]}">{BOOK_LABEL[book]}</h2>')
        out.append('')
        chapters = sorted(book_map[book].keys())
        for ch in chapters:
            verses = sorted(set(book_map[book][ch]), key=lambda t: (t[0], t[1]))
            # Deduplicate by verse — keep first occurrence (lowest vol number)
            seen_v = set()
            unique = []
            for entry in verses:
                v = entry[0]
                if v in seen_v:
                    continue
                seen_v.add(v)
                unique.append(entry)
            out.append('<div class="ch-row">')
            out.append(f'  <div class="ch-label">{BOOK_LABEL[book]} {ch}</div>')
            out.append('  <div class="ch-track">')
            for v, vol_label, vol_id, harmony_ch in unique:
                href = (f'{{{{ site.baseurl }}}}/calvin/{vol_id}/{harmony_ch}/'
                        f'#{book}-{ch}-{v}')
                loc = vol_chap_label(vol_label, harmony_ch)
                title = f'{BOOK_LABEL[book]} {ch}:{v} → {loc}'
                out.append(
                    f'    <a class="verse-pill" href="{href}" title="{title}">'
                    f'<span class="pill-verse">{v}</span>'
                    f'<span class="pill-loc">{loc}</span></a>'
                )
            out.append('  </div>')
            out.append('</div>')
            out.append('')

    out.append('    </div>')
    out.append('  </div>')
    out.append('</div>')
    out.append('')
    # CSS — 与英文版 harmony-index-en 一致（绿色 pill + 滚动 ch-track）
    out.append('''<style>
.verse-index-nav {
  margin: 24px 0;
  font-size: 15px;
}
.verse-index-nav a {
  color: #0085a1;
  font-weight: bold;
  padding: 0 6px;
}
h2[id="matthew"], h2[id="mark"], h2[id="luke"], h2[id="john"] {
  margin-top: 36px;
  padding-bottom: 6px;
  border-bottom: 2px solid #0085a1;
  color: #0085a1;
}
.ch-row {
  display: flex;
  align-items: stretch;
  margin-bottom: 6px;
  gap: 12px;
}
.ch-label {
  flex: 0 0 90px;
  font-family: Georgia, serif;
  font-weight: bold;
  font-size: 14px;
  color: #444;
  padding: 8px 4px;
  text-align: right;
  border-right: 2px solid #0085a1;
}
.ch-track {
  flex: 1 1 auto;
  display: flex;
  gap: 6px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 8px 8px 8px;
  scrollbar-width: thin;
}
.ch-track::-webkit-scrollbar { height: 6px; }
.ch-track::-webkit-scrollbar-thumb { background: #c0d4d9; border-radius: 3px; }
.verse-pill {
  flex: 0 0 auto;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  background: #e8f5e9;
  border: 1px solid #a5d6a7;
  border-radius: 14px;
  color: #2e7d32;
  text-decoration: none;
  font-family: Georgia, serif;
  white-space: nowrap;
  transition: background 0.12s;
  min-width: 64px;
}
.verse-pill:hover {
  background: #4caf50;
  border-color: #4caf50;
  color: #fff;
  text-decoration: none;
}
.pill-verse {
  font-size: 14px;
  font-weight: bold;
  line-height: 1.2;
}
.pill-loc {
  font-size: 10px;
  opacity: 0.75;
  margin-top: 1px;
}
a.verse-anchor { display: inline-block; width: 0; height: 0; scroll-margin-top: 80px; }
</style>''')
    return '\n'.join(out)


def main():
    book_map = collect_anchors()
    total = sum(sum(len(v) for v in chs.values()) for chs in book_map.values())
    print(f'Collected {total} verse anchors')
    for book in BOOK_ORDER:
        if book in book_map:
            count = sum(len(v) for v in book_map[book].values())
            print(f'  {BOOK_LABEL[book]}: {count} verses across {len(book_map[book])} chapters')
    text = render_index(book_map)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(text, encoding='utf-8')
    print(f'\nWrote {INDEX_PATH} ({len(text)} chars)')


if __name__ == '__main__':
    main()
