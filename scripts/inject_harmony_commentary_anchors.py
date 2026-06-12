#!/usr/bin/env python3
"""Inject `<a class="commentary-anchor" id="<slug>-comm"></a>` between
scripture-box and commentary in every harmony chapter md.

EN/ZH harmony chapter md structure per section:

    ## SECTION HEADER

    <div class="scripture-box ...">
    ...
    </div>

    [^N] [^M]
    {:.scripture-fnref-stub}


    **Book Ch:V.** *commentary opener.* ...

The anchor goes RIGHT BEFORE the first commentary paragraph, so harmony
index links `#slug-comm` scroll to the commentary text (not the
scripture-box top).

The slug derives from the EN section header form. For ZH chapters, the
section header itself has been translated (e.g., `## 马太福音 21:10-22`)
— we recompute the equivalent EN slug by reverse-mapping book names.

Usage:
    python3 scripts/inject_harmony_commentary_anchors.py BOOK
    python3 scripts/inject_harmony_commentary_anchors.py all
"""
import argparse
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')

BOOKS = [
    'harmony-1', 'harmony-1-en',
    'harmony-2', 'harmony-2-en',
    'harmony-3', 'harmony-3-en',
]

# ZH → EN book name (uppercase). Used to compute kramdown-compatible slug
# from ZH headers like "## 马太福音 21:10-22；马可福音 11:11-24".
ZH_TO_EN_BOOK = {
    '马太福音': 'MATTHEW',
    '马可福音': 'MARK',
    '路加福音': 'LUKE',
    '约翰福音': 'JOHN',
}


def normalize_header_to_en(header):
    """Convert a section header (EN or ZH) to canonical EN form for slug.

    "## MATTHEW 21:10-22; MARK 11:11-24"
       → "MATTHEW 21:10-22; MARK 11:11-24"
    "## 马太福音 21:10-22；马可福音 11:11-24"
       → "MATTHEW 21:10-22; MARK 11:11-24"
    """
    s = re.sub(r'^##\s*', '', header).strip()
    # Replace Chinese book names with EN uppercase
    for zh, en in ZH_TO_EN_BOOK.items():
        s = s.replace(zh, en)
    # Full-width punctuation → half-width
    s = s.replace('；', '; ').replace('：', ':').replace('，', ', ')
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def slugify(header_en):
    """Match kramdown's H2 slug rules: lowercase, drop `:` `;` `,` `.` `(` `)`,
    spaces→`-`, collapse hyphens. E.g.,
        "MATTHEW 27:33-38; MARK 15:22-28; LUKE 23:33-34, 38"
          → "matthew-2733-38-mark-1522-28-luke-2333-34-38"
    """
    s = header_en.lower()
    # Drop punctuation that kramdown discards
    s = re.sub(r'[:;,.()]', '', s)
    # Whitespace → hyphen
    s = re.sub(r'\s+', '-', s)
    # Collapse consecutive hyphens
    s = re.sub(r'-+', '-', s).strip('-')
    return s


# Section header (ZH or EN)
HDR_RE = re.compile(
    r'^##\s+(?:MATTHEW|MARK|LUKE|JOHN|马太福音|马可福音|路加福音|约翰福音)\b[^\n]*$',
    re.M,
)
# scripture-box closing
BOX_END_RE = re.compile(r'^</div>\s*$', re.M)
# fnref-stub follow-on (optional after box)
STUB_RE = re.compile(r'^\[\^.*\n\{:\.scripture-fnref-stub\}\s*$', re.M)
# Already-injected anchor (section-level or per-verse)
EXISTING_ANCHOR_RE = re.compile(
    r'<a class="(?:commentary|verse)-anchor" id="[^"]+"></a>\s*\n?'
)

# Per-verse commentary marker — e.g. `**Matthew 21:12.**` or `**马太福音 21:12。**`
# (note ZH uses 「。」full-stop, EN uses ASCII `.`)
VERSE_HDR_RE = re.compile(
    r'\*\*'
    r'(MATTHEW|MARK|LUKE|JOHN|马太福音|马可福音|路加福音|约翰福音)'
    r'\s+(\d+):(\d+)[.。]'
    r'\*\*'
)

BOOK_ABBR = {
    'MATTHEW': 'matt', '马太福音': 'matt',
    'MARK':    'mark', '马可福音': 'mark',
    'LUKE':    'luke', '路加福音': 'luke',
    'JOHN':    'john', '约翰福音': 'john',
}


def process_file(path: Path) -> int:
    """Inject anchors after each scripture-box section. Returns # inserted."""
    text = path.read_text(encoding='utf-8')
    # Remove any pre-existing commentary-anchors (re-run safe)
    text = EXISTING_ANCHOR_RE.sub('', text)
    # Cleanup leftover blank lines from removal
    text = re.sub(r'\n{3,}', '\n\n', text)

    lines = text.split('\n')
    out_lines = []
    i = 0
    inserted = 0
    current_slug = None
    expecting_anchor = False  # set after </div>, waiting to inject before next non-blank/non-stub line

    while i < len(lines):
        ln = lines[i]
        if HDR_RE.match(ln):
            # New section header — compute slug
            en_form = normalize_header_to_en(ln)
            current_slug = slugify(en_form)
            expecting_anchor = False
            out_lines.append(ln)
        elif ln.strip() == '</div>' and current_slug:
            # End of scripture-box; arm anchor injection
            out_lines.append(ln)
            expecting_anchor = True
        elif expecting_anchor:
            stripped = ln.strip()
            # Skip blank lines AND fnref-stub lines (`[^...]\n{:.scripture-fnref-stub}`)
            if not stripped:
                out_lines.append(ln)
            elif stripped.startswith('[^') or stripped == '{:.scripture-fnref-stub}':
                out_lines.append(ln)
            else:
                # First non-blank, non-stub line after </div> → inject anchor
                out_lines.append(f'<a class="commentary-anchor" id="{current_slug}-comm"></a>')
                out_lines.append('')
                out_lines.append(ln)
                inserted += 1
                expecting_anchor = False
                current_slug = None
        else:
            out_lines.append(ln)
        i += 1

    new = '\n'.join(out_lines)

    # Second pass: insert per-verse anchors before each `**Book X:Y.**` marker
    def inject_verse_anchor(m):
        book, ch, v = m.group(1), m.group(2), m.group(3)
        abbr = BOOK_ABBR.get(book, '')
        if not abbr:
            return m.group(0)
        return (f'<a class="verse-anchor" id="{abbr}-{ch}-{v}"></a>\n\n'
                + m.group(0))
    new = VERSE_HDR_RE.sub(inject_verse_anchor, new)

    if new != text:
        # Need to chmod if locked (zh raw is 444)
        mode = path.stat().st_mode & 0o777
        if mode == 0o444:
            path.chmod(0o644)
        path.write_text(new, encoding='utf-8')
        if mode == 0o444:
            path.chmod(0o444)
    return inserted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', help='harmony-N or harmony-N-en or "all"')
    args = ap.parse_args()
    targets = BOOKS if args.book == 'all' else [args.book]
    for book in targets:
        d = ROOT / 'calvin' / book
        if not d.exists():
            print(f'skip {book}: dir not found')
            continue
        for path in sorted(d.glob('*.md')):
            if not path.stem.isdigit():
                continue
            n = process_file(path)
            print(f'{book}/{path.name}: {n} anchors injected')


if __name__ == '__main__':
    main()
