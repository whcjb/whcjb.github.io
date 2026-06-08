#!/usr/bin/env python3
"""Convert Ages-format `<p>English</p>` + `<p>Latin</p>` sequential pairs
into proper parallel 2-column `<table class="scripture-table calvin-parallel">`
matching the PDF layout.

Also splits "smushed" paragraphs where PDF extraction mis-tagged a
`<p style="margin-left:2em">` block that actually contains Latin v(N) +
English v(N+1) merged together.

Usage:
    python3 scripts/fix_ages_parallel_table.py <file1.md> [file2.md ...]
    python3 scripts/fix_ages_parallel_table.py calvin/jude-en/1.md
    python3 scripts/fix_ages_parallel_table.py calvin/1john-en/*.md

Used to fix: jude, 1john, 1peter, 1thessalonians, 1timothy, 2peter,
2thessalonians, 2timothy, amos, habakkuk, haggai, harmony-law-*, hosea,
jeremiah-1, joel, malachi, obadiah, philemon, romans, zechariah,
zephaniah (any book where calvin_extract used ages_phil/ages_corinth/
ages_heb format).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Pattern 1: a `<p>` that has Latin v(N) + English v(N+1) smushed.
# PDF extraction sometimes mis-tagged the line as INDENT when it should
# have been RIGHT (Latin) followed by INDENT (English).
SMUSHED_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">'
    r'\*\*(\d+)\.\*\*\s*'
    r'([^<]+?)\s+(\d+)\.\s+'
    r'([A-Z(“"\'][^<]+?)</p>',
)

# Pattern 2: pair of <p>English</p> + <p>Latin</p>
PAIR_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">(\*\*\d+\.\*\*[^<]*?)</p>\n+'
    r'<p style="text-align:right;" markdown="1">(\d+\.[^<]*?)</p>',
    re.DOTALL,
)


def split_smushed(m: re.Match) -> str:
    n = int(m.group(1))
    latin_body = m.group(2).strip()
    m2 = int(m.group(3))
    english_body = m.group(4).strip()
    if m2 != n + 1:
        return m.group(0)
    return (
        f'<p style="text-align:right;" markdown="1">{n}. {latin_body}</p>\n\n'
        f'<p style="margin-left:2em;" markdown="1">**{m2}.** {english_body}</p>'
    )


def md_to_html(s: str) -> str:
    """Pre-convert markdown verse-prefix bold + inline italics to HTML so the
    table cell content doesn't need markdown='1' (which kramdown GFM
    doesn't honor reliably on <td>)."""
    # leading **N.** → <strong>N.</strong>
    s = re.sub(r'^\*\*(\d+\.)\*\*', r'<strong>\1</strong>', s)
    # any remaining **X** → <strong>X</strong>
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    # *X* → <em>X</em> (single-star italic)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


def group_and_replace(text: str) -> tuple[str, int]:
    """Find adjacent <p>en</p><p>lat</p> pairs and replace each group with
    one scripture-table. Returns (new_text, n_tables_created)."""
    matches = list(PAIR_RE.finditer(text))
    if not matches:
        return text, 0

    # Group adjacent matches (only whitespace between)
    groups = []
    current = [matches[0]]
    for m in matches[1:]:
        prev = current[-1]
        if text[prev.end():m.start()].strip() == '':
            current.append(m)
        else:
            groups.append(current)
            current = [m]
    groups.append(current)

    # Build replacements from end to start to preserve positions
    replacements = []
    for group in groups:
        rows = []
        for m in group:
            eng = md_to_html(m.group(1).strip())
            lat = md_to_html(m.group(2).strip())
            rows.append(
                f'<tr><td><p>{eng}</p></td><td><p>{lat}</p></td></tr>'
            )
        body = '\n'.join(rows)
        table = (
            '<table class="scripture-table calvin-parallel">\n'
            '<tbody>\n'
            f'{body}\n'
            '</tbody>\n'
            '</table>'
        )
        replacements.append((group[0].start(), group[-1].end(), table))

    new_text = text
    for start, end, repl in reversed(replacements):
        new_text = new_text[:start] + repl + new_text[end:]
    return new_text, len(replacements)


def fix_file(path: Path) -> tuple[int, int]:
    """Apply both fixes to one file. Returns (n_smushed_split, n_tables)."""
    text = path.read_text(encoding='utf-8')
    text, n_smushed = SMUSHED_RE.subn(split_smushed, text)
    text, n_tables = group_and_replace(text)
    path.write_text(text, encoding='utf-8')
    return n_smushed, n_tables


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total_smushed = total_tables = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f'  skip (not found): {path}')
            continue
        n_smushed, n_tables = fix_file(path)
        print(f'  {path}: split {n_smushed} smushed, created {n_tables} tables')
        total_smushed += n_smushed
        total_tables += n_tables
    print(f'TOTAL: {total_smushed} smushed split, {total_tables} tables created')


if __name__ == '__main__':
    main()
