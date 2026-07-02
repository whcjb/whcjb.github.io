#!/usr/bin/env python3
"""restructure_1thess_en.py — 把 calvin/1thessalonians-en/*.md 从旧
Ages 格式重构为 1cor/2cor 那种 scripture-box 双语 table 格式。

旧格式 (per section):
    1 THESSALONIANS 1:2-5
    **2.** English v2 ...
    <p style="margin-left:2em;" markdown="1">**2.** Latin_v2, 3. English_v3 ...</p>
    <p style="margin-left:2em;" markdown="1">**3.** Latin_v3, 4. English_v4 ...</p>
    ...
    <p style="text-align:right;" markdown="1">5. Latin_v5 ...</p>
    **2.** <span style="color:#800000">*commentary*</span> ...

新格式 (对齐 1cor):
    <div class="scripture-box scripture-box--bilingual" markdown="1">
    <p class="scripture-ref"><span class="ages-code">&lt;520102&gt;</span><span class="book-name">1 Thessalonians</span> <span class="verse-range">1:2-5</span></p>
    <h2 class="scripture-anchor" id="1-thessalonians-1-2-5" data-ref="1 THESSALONIANS 1:2-5" style="display:none">1 THESSALONIANS 1:2-5</h2>

    <table class="scripture-bilingual">
    <tbody>
    <tr><td class="scripture-en"><strong>2.</strong> English v2</td><td class="scripture-la"><strong>2.</strong> Latin v2</td></tr>
    <tr><td class="scripture-en"><strong>3.</strong> English v3</td><td class="scripture-la"><strong>3.</strong> Latin v3</td></tr>
    ...
    </tbody>
    </table>

    </div>

    <!-- PAGE N -->
    **2.** <span style="color:#800000">*commentary*</span> ...

用法：
    python3 scripts/restructure_1thess_en.py                    # 全 5 章
    python3 scripts/restructure_1thess_en.py 1 2                # 单章
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / 'calvin/1thessalonians-en'
BOOK_NUM = 52          # 1 Thessalonians 在 Ages 编号中 = 52
BOOK_TITLE = '1 Thessalonians'
DISPLAY_TITLE_UPPER = '1 THESSALONIANS'


# Section heading: "1 THESSALONIANS 1:1" or "1 THESSALONIANS 1:2-5"
SECTION_HEAD_RE = re.compile(
    rf'^{re.escape(DISPLAY_TITLE_UPPER)} (\d+):(\d+)(?:-(\d+))?$',
    re.M,
)

# Smushed paragraph split (from fix_ages_parallel_table.py)
SMUSHED_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">'
    r'(?:\*\*(\d+)\.\*\*|(\d+)\.\s*[—–-]?)\s*'
    r'([^<]+?)\s+(\d+)\.\s+'
    r'([A-Z(“"\'][^<]+?)</p>',
)


def split_smushed(m: re.Match) -> str:
    n = int(m.group(1) or m.group(2))
    latin_body = m.group(3).strip()
    m2 = int(m.group(4))
    english_body = m.group(5).strip()
    if m2 != n + 1:
        return m.group(0)
    return (
        f'<p style="text-align:right;" markdown="1">{n}. {latin_body}</p>\n\n'
        f'<p style="margin-left:2em;" markdown="1">**{m2}.** {english_body}</p>'
    )


def md_to_html(s: str) -> str:
    """Convert leading **N.** and inline *X* / **Y** to HTML."""
    s = re.sub(r'^\*\*(\d+)\.\*\*', r'<strong>\1.</strong>', s)
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


# Verse patterns (both bare and wrapped)
# English: line starts with **N.** OR is a <p margin-left>...**N.**...</p>
ENG_STANDALONE_RE = re.compile(r'^\*\*(\d+)\.\*\*\s+(.+?)$', re.M)
ENG_INDENT_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">\*\*(\d+)\.\*\*\s+([^<]+?)</p>',
)
LATIN_RE = re.compile(
    r'<p style="text-align:right;" markdown="1">(\d+)\.\s+([^<]+?)</p>',
)


def extract_verses(section_body: str) -> dict[int, dict]:
    """Return {verse_num: {'en': str, 'la': str}} from a section body."""
    verses: dict[int, dict] = {}

    def add(n, kind, text):
        verses.setdefault(n, {}).setdefault(kind, text.strip())

    # English standalone (bare **N.** at line start)
    for m in ENG_STANDALONE_RE.finditer(section_body):
        n = int(m.group(1))
        body = m.group(2).strip()
        # Skip commentary lines: usually followed by <span style="color:#800000">
        # But here we scan the entire section incl. commentary; filter by
        # rule: verse-body English does NOT contain <span color:#800000>
        if '<span style="color:#800000">' in body:
            continue
        add(n, 'en', body)

    # English in indent block
    for m in ENG_INDENT_RE.finditer(section_body):
        add(int(m.group(1)), 'en', m.group(2))

    # Latin
    for m in LATIN_RE.finditer(section_body):
        add(int(m.group(1)), 'la', m.group(2))

    return verses


def build_scripture_box(ch: int, v_from: int, v_to: int, verses: dict[int, dict]) -> str:
    """Build the scripture-box HTML block."""
    ages_code = f'{BOOK_NUM}{ch:02d}{v_from:02d}'
    verse_range = f'{v_from}' if v_from == v_to else f'{v_from}-{v_to}'
    anchor_id = (f'1-thessalonians-{ch}-{v_from}'
                  if v_from == v_to
                  else f'1-thessalonians-{ch}-{v_from}-{v_to}')
    data_ref = f'{DISPLAY_TITLE_UPPER} {ch}:{verse_range}'

    lines = [
        '<div class="scripture-box scripture-box--bilingual" markdown="1">',
        (f'<p class="scripture-ref"><span class="ages-code">&lt;{ages_code}&gt;</span>'
         f'<span class="book-name">{BOOK_TITLE}</span> '
         f'<span class="verse-range">{ch}:{verse_range}</span></p>'),
        (f'<h2 class="scripture-anchor" id="{anchor_id}" '
         f'data-ref="{data_ref}" style="display:none">{data_ref}</h2>'),
        '',
        '<table class="scripture-bilingual">',
        '<tbody>',
    ]
    for v in range(v_from, v_to + 1):
        d = verses.get(v, {})
        en = md_to_html(d.get('en', f'[MISSING v{v} English]'))
        la = md_to_html(d.get('la', f'[MISSING v{v} Latin]'))
        lines.append(
            f'<tr><td class="scripture-en"><strong>{v}.</strong> {en}</td>'
            f'<td class="scripture-la"><strong>{v}.</strong> {la}</td></tr>'
        )
    lines += [
        '</tbody>',
        '</table>',
        '',
        '</div>',
    ]
    return '\n'.join(lines)


def restructure_file(path: Path) -> tuple[int, int]:
    """Return (n_sections_converted, n_verses_paired)."""
    text = path.read_text(encoding='utf-8')

    # 1. Split smushed <p margin-left> containing Latin_N + English_N+1
    text, n_smushed = SMUSHED_RE.subn(split_smushed, text)

    # 2. Locate all section heads and their spans
    heads = list(SECTION_HEAD_RE.finditer(text))
    if not heads:
        return 0, 0

    # 3. Build replacements from END to START to preserve indices
    replacements = []
    n_verses_total = 0

    for i, m in enumerate(heads):
        head_start = m.start()
        head_end = m.end()
        ch = int(m.group(1))
        v_from = int(m.group(2))
        v_to = int(m.group(3)) if m.group(3) else v_from

        # Section body: from head_end to next-section-head OR next commentary
        # start (line starting with **N.** followed by <span color:#800000>).
        # Simplest: find the block until either next section head OR the
        # first commentary marker.
        next_start = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head_end:next_start]

        # Verse block ends at the LAST Latin `<p style="text-align:right">`
        # in this section. Anything after is commentary.
        last_latin_end = None
        for lm in LATIN_RE.finditer(body):
            last_latin_end = lm.end()
        if last_latin_end is None:
            # No Latin found in section; skip this section (data issue)
            continue
        verse_block = body[:last_latin_end]
        after_verses = body[last_latin_end:]

        # Extract verses from verse_block
        verses = extract_verses(verse_block)
        if not verses:
            continue

        # Only include verses in [v_from, v_to] range
        n_paired = sum(1 for v in range(v_from, v_to + 1)
                        if verses.get(v, {}).get('en') and verses.get(v, {}).get('la'))
        n_verses_total += n_paired

        new_block = build_scripture_box(ch, v_from, v_to, verses)
        # Replacement: full section head + verse_block → new_block
        section_start = head_start
        section_end = head_end + len(verse_block)
        replacements.append((section_start, section_end, new_block))

    # Apply replacements from end to start
    new_text = text
    for start, end, repl in reversed(replacements):
        new_text = new_text[:start] + repl + new_text[end:]

    path.write_text(new_text, encoding='utf-8')
    return len(replacements), n_verses_total


def main():
    args = sys.argv[1:]
    if args:
        files = [SRC_DIR / f'{c}.md' for c in args]
    else:
        files = sorted(SRC_DIR.glob('[0-9]*.md'))

    total_sec = total_v = 0
    for f in files:
        if not f.exists():
            print(f'  {f}: 不存在, 跳过')
            continue
        n_sec, n_v = restructure_file(f)
        print(f'  {f.name}: {n_sec} sections converted, {n_v} verses paired')
        total_sec += n_sec
        total_v += n_v
    print(f'\nTOTAL: {total_sec} sections, {total_v} verses paired')


if __name__ == '__main__':
    main()
