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
# Smushed paragraph: a `<p>` containing Latin v(N) + English v(N+1).
# Accept both `**N.**` (bold) and `N.` (no bold) verse prefixes — the
# PDF extractor sometimes drops the bold formatting on continuation lines.
SMUSHED_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">'
    r'(?:\*\*(\d+)\.\*\*|(\d+)\.\s*[—–-]?)\s*'    # **N.** or N. (with optional dash)
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
    # group(1) is **N.** form, group(2) is bare N. form
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


def wrap_bare_verse_lines(text: str) -> tuple[str, int]:
    """Some verse lines lost their `<p>` wrapper during extraction (the
    line appears unwrapped as `19. *And* we know that ...` between the
    scripture-anchor h2 and the Latin paragraph). Wrap them in proper
    `<p style="margin-left:2em;">` so PAIR_RE can later pair them.

    Detection: a bare line starting with `N. ` (optional em-dash), where
    the NEXT non-blank line is a `<p text-align:right;>N. ...</p>`
    (Latin partner).
    """
    BARE_PAIR_RE = re.compile(
        r'^(\d+)\.\s*(?:[—–-]\s*)?([*A-Z“"\'][^\n]+\.)\s*\n+'
        r'(?=<p style="text-align:right;" markdown="1">(\d+)\.)',
        re.M,
    )
    count = 0
    def wrap(m: re.Match) -> str:
        nonlocal count
        n = m.group(1)
        latin_n = m.group(3)
        if int(n) != int(latin_n):
            return m.group(0)  # not a real pair, skip
        body = m.group(2).strip()
        count += 1
        return f'<p style="margin-left:2em;" markdown="1">**{n}.** {body}</p>\n\n'

    return BARE_PAIR_RE.sub(wrap, text), count


def fix_file(path: Path) -> tuple[int, int, int]:
    """Apply all fixes. Returns (n_bare_wrapped, n_smushed_split, n_tables).
    Order matters: SMUSHED first (so Latin halves become standalone
    text-align:right <p>), THEN bare-verse wrap (which uses the Latin
    text-align:right partner as the trigger), then PAIR for table."""
    text = path.read_text(encoding='utf-8')
    text, n_smushed = SMUSHED_RE.subn(split_smushed, text)
    text, n_bare = wrap_bare_verse_lines(text)
    text, n_tables = group_and_replace(text)
    path.write_text(text, encoding='utf-8')
    return n_bare, n_smushed, n_tables


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total_bare = total_smushed = total_tables = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f'  skip (not found): {path}')
            continue
        n_bare, n_smushed, n_tables = fix_file(path)
        print(f'  {path}: wrapped {n_bare} bare verses, '
              f'split {n_smushed} smushed, created {n_tables} tables')
        total_bare += n_bare
        total_smushed += n_smushed
        total_tables += n_tables
    print(f'TOTAL: wrapped {total_bare}, split {total_smushed} smushed, '
          f'{total_tables} tables created')


if __name__ == '__main__':
    main()
