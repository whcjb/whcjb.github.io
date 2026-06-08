#!/usr/bin/env python3
"""Wrap Acts (English-only, single column) scripture references in a
scripture-box matching the PDF: cyan header + bordered box around
verse text.

Input pattern:
    ## Acts 1:1-2

    **1.** The former speech... **2.** Even until that day...

    That he may pass over unto those things...  (commentary starts)

Output:
    <h2 class="scripture-anchor" id="acts-1-1-2" ...>Acts 1:1-2</h2>

    <div class="scripture-box" markdown="1">
    <p class="scripture-ref">Acts 1:1-2</p>

    **1.** The former speech... **2.** Even until that day...

    </div>

    That he may pass over unto those things...
"""
import re
import sys
from pathlib import Path


HEADER_VERSE_RE = re.compile(
    r'^## Acts (\d+):([0-9,\s\-–]+)\n+'             # ## Acts 1:1-2
    r'(\*\*\d+\.\*\*[^\n]+)\n',                      # verse text line (bold-prefixed)
    re.M,
)


def slug(ch: str, vs: str) -> str:
    vs = vs.replace(' ', '').replace('–', '-').replace(',', '-')
    return f'acts-{ch}-{vs}'


def wrap_section(m: re.Match) -> str:
    ch = m.group(1)
    vs = m.group(2).strip()
    verse_line = m.group(3).strip()
    anchor = slug(ch, vs)
    ref = f'Acts {ch}:{vs}'
    return (
        f'<h2 class="scripture-anchor" id="{anchor}" data-ref="{ref}" '
        f'style="display:none">{ref}</h2>\n\n'
        f'<div class="scripture-box" markdown="1">\n'
        f'<p class="scripture-ref">{ref}</p>\n\n'
        f'{verse_line}\n\n'
        f'</div>\n'
    )


def fix_file(path: Path) -> int:
    text = path.read_text(encoding='utf-8')
    new_text, n = HEADER_VERSE_RE.subn(wrap_section, text)
    if n > 0:
        path.write_text(new_text, encoding='utf-8')
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    total = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.exists():
            continue
        n = fix_file(p)
        print(f'  {p}: wrapped {n} sections')
        total += n
    print(f'TOTAL: {total} scripture sections wrapped')


if __name__ == '__main__':
    main()
