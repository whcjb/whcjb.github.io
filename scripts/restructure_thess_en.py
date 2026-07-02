#!/usr/bin/env python3
"""restructure_thess_en.py — 把 calvin/{1,2}thessalonians-en/*.md 从
旧 Ages 格式（或半改的 .calvin-parallel 中间态）重构为 1cor/2cor 那种
scripture-box 双语 table 结构。

支持多种输入形态：
  A. 纯裸格式:
       **N.** English
       <p style="text-align:right;">N. Latin</p>
  B. 半改中间态:
       <table class="scripture-table calvin-parallel">
       <tr><td><p><strong>N.</strong> English</p></td><td><p>N. Latin</p></td></tr>
       ...
       </table>
  C. Smushed 段落 (Latin_N + English_N+1):
       <p style="margin-left:2em;" markdown="1">**N.** Latin_N. M. English_M</p>

输出 (对齐 1cor gold):
       <div class="scripture-box scripture-box--bilingual" markdown="1">
       <p class="scripture-ref"><span class="ages-code">&lt;NNCCVV&gt;</span>
         <span class="book-name">TITLE</span> <span class="verse-range">C:V-V</span></p>
       <h2 class="scripture-anchor" id="book-c-v-v" data-ref="TITLE C:V-V"
         style="display:none">TITLE C:V-V</h2>
       <table class="scripture-bilingual">
       <tbody>
       <tr><td class="scripture-en">...</td><td class="scripture-la">...</td></tr>
       ...

用法：
    python3 scripts/restructure_thess_en.py 1thess           # 1 Thess 全 5 章
    python3 scripts/restructure_thess_en.py 2thess           # 2 Thess 全 3 章
    python3 scripts/restructure_thess_en.py 1thess 3         # 单章
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    '1thess': {
        'src_dir': ROOT / 'calvin/1thessalonians-en',
        'book_num': 52,
        'title': '1 Thessalonians',
        'upper': '1 THESSALONIANS',
        'anchor_prefix': '1-thessalonians',
    },
    '2thess': {
        'src_dir': ROOT / 'calvin/2thessalonians-en',
        'book_num': 53,
        'title': '2 Thessalonians',
        'upper': '2 THESSALONIANS',
        'anchor_prefix': '2-thessalonians',
    },
}


# Smushed <p margin-left> containing Latin_N + English_N+1
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
    s = re.sub(r'^\*\*(\d+)\.\*\*', r'<strong>\1.</strong>', s)
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


# Verse extraction patterns
ENG_STANDALONE_RE = re.compile(r'^\*\*(\d+)\.\*\*\s+(.+?)$', re.M)
ENG_INDENT_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">\*\*(\d+)\.\*\*\s+([^<]+?)</p>',
)
LATIN_RE = re.compile(
    r'<p style="text-align:right;" markdown="1">(\d+)\.\s+([^<]+?)</p>',
)
# 半改 .calvin-parallel 表格里的双列 pair
PARALLEL_ROW_RE = re.compile(
    r'<tr><td><p><strong>(\d+)\.</strong>\s*([^<]+?)</p></td>'
    r'<td><p>(\d+)\.\s+([^<]+?)</p></td></tr>',
)


def extract_verses(section_body: str) -> dict[int, dict]:
    verses: dict[int, dict] = {}

    def add(n, kind, text):
        verses.setdefault(n, {}).setdefault(kind, text.strip())

    # Sources A + C fragments
    for m in ENG_STANDALONE_RE.finditer(section_body):
        body = m.group(2).strip()
        if '<span style="color:#800000">' in body:
            continue  # skip commentary
        add(int(m.group(1)), 'en', body)
    for m in ENG_INDENT_RE.finditer(section_body):
        add(int(m.group(1)), 'en', m.group(2))
    for m in LATIN_RE.finditer(section_body):
        add(int(m.group(1)), 'la', m.group(2))

    # Source B: existing .calvin-parallel table rows
    for m in PARALLEL_ROW_RE.finditer(section_body):
        n_en = int(m.group(1))
        n_la = int(m.group(3))
        if n_en == n_la:
            add(n_en, 'en', m.group(2))
            add(n_en, 'la', m.group(4))

    return verses


def build_scripture_box(cfg, ch: int, v_from: int, v_to: int,
                          verses: dict[int, dict]) -> str:
    ages_code = f'{cfg["book_num"]}{ch:02d}{v_from:02d}'
    verse_range = f'{v_from}' if v_from == v_to else f'{v_from}-{v_to}'
    anchor_id = (f'{cfg["anchor_prefix"]}-{ch}-{v_from}'
                  if v_from == v_to
                  else f'{cfg["anchor_prefix"]}-{ch}-{v_from}-{v_to}')
    data_ref = f'{cfg["upper"]} {ch}:{verse_range}'

    lines = [
        '<div class="scripture-box scripture-box--bilingual" markdown="1">',
        (f'<p class="scripture-ref"><span class="ages-code">&lt;{ages_code}&gt;</span>'
         f'<span class="book-name">{cfg["title"]}</span> '
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
    lines += ['</tbody>', '</table>', '', '</div>']
    return '\n'.join(lines)


def restructure_file(cfg, path: Path) -> tuple[int, int]:
    text = path.read_text(encoding='utf-8')
    section_head_re = re.compile(
        rf'^{re.escape(cfg["upper"])} (\d+):(\d+)(?:-(\d+))?$', re.M
    )

    # Split smushed (source C)
    text, _ = SMUSHED_RE.subn(split_smushed, text)

    heads = list(section_head_re.finditer(text))
    if not heads:
        return 0, 0

    replacements = []
    n_verses_total = 0

    for i, m in enumerate(heads):
        head_start = m.start()
        head_end = m.end()
        ch = int(m.group(1))
        v_from = int(m.group(2))
        v_to = int(m.group(3)) if m.group(3) else v_from

        next_start = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head_end:next_start]

        # Find END of verse block: LAST occurrence of either
        #   <p text-align:right>N.</p>   OR   </tbody>\n</table>   (parallel)
        last_latin_end = None
        for lm in LATIN_RE.finditer(body):
            last_latin_end = lm.end()
        last_para_end = None
        m_end_para = re.search(r'</tbody>\s*</table>', body)
        if m_end_para:
            last_para_end = m_end_para.end()
        # Verse block ends at the later of the two
        candidates = [x for x in (last_latin_end, last_para_end) if x is not None]
        if not candidates:
            continue
        verse_end = max(candidates)
        verse_block = body[:verse_end]

        verses = extract_verses(verse_block)
        if not verses:
            continue

        n_paired = sum(1 for v in range(v_from, v_to + 1)
                        if verses.get(v, {}).get('en') and verses.get(v, {}).get('la'))
        n_verses_total += n_paired

        new_block = build_scripture_box(cfg, ch, v_from, v_to, verses)
        section_start = head_start
        section_end = head_end + verse_end
        replacements.append((section_start, section_end, new_block))

    new_text = text
    for start, end, repl in reversed(replacements):
        new_text = new_text[:start] + repl + new_text[end:]

    path.write_text(new_text, encoding='utf-8')
    return len(replacements), n_verses_total


def main():
    args = sys.argv[1:]
    if not args or args[0] not in BOOKS:
        print(__doc__)
        sys.exit(1)
    book_key = args[0]
    cfg = BOOKS[book_key]
    chapter_args = args[1:]

    if chapter_args:
        files = [cfg['src_dir'] / f'{c}.md' for c in chapter_args]
    else:
        files = sorted(cfg['src_dir'].glob('[0-9]*.md'))

    total_sec = total_v = 0
    for f in files:
        if not f.exists():
            print(f'  {f}: 不存在, 跳过')
            continue
        n_sec, n_v = restructure_file(cfg, f)
        print(f'  {f.name}: {n_sec} sections converted, {n_v} verses paired')
        total_sec += n_sec
        total_v += n_v
    print(f'\nTOTAL: {total_sec} sections, {total_v} verses paired')


if __name__ == '__main__':
    main()
