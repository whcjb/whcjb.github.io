#!/usr/bin/env python3
"""
Convert the Ages-format intermediate produced by `ages_phil` extractor
(`[H1] / [H2] / [BODY] / [FOOTNOTE] / [TABLE_LEFT] / [TABLE_RIGHT]` tags)
into publish-ready Markdown.

Usage:
    python3 scripts/structured_to_md.py <input_structured.txt> <output.md>

Handles:
 - Strips leading page-number BODY items (`[BODY] N` matching the current page)
 - `[H1]/[H2]` → `# /` ## ` Markdown headings
 - `[BODY] text` → paragraph (with Ages Greek transliteration → Unicode)
 - `[FOOTNOTE] FtN text` → `[^fN]: text` footnote definition
 - `[FOOTNOTE] <NNNNNN>JOHN N:M` → `## JOHN N:M` scripture-section H2
 - Inline `[FOOTNOTE] (<NNNNNN>Book N:M.)` → inline cross-reference cleaned
 - `[TABLE_LEFT] / [TABLE_RIGHT]` → grouped into `<table class="calvin-scripture">`
 - Spaced-caps cleanup (`B o o k s` → `Books`, `TRANSLATOR'SPREFACE` keeps as-is)
 - Page boundaries preserved as `<!-- PAGE N -->`
"""

from __future__ import annotations
import re
import sys
import unicodedata
from pathlib import Path

# ── Ages Greek transliteration → Unicode ─────────────────────────────────
_GCOMB = {'j': '̓', '>': '́', '<': '̀', '~': '͂', '|': 'ͅ'}
_GBASE = {
    'a': 'α', 'b': 'β', 'g': 'γ', 'd': 'δ', 'e': 'ε', 'z': 'ζ', 'h': 'η', 'q': 'θ',
    'i': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ', 'o': 'ο', 'p': 'π',
    'r': 'ρ', 's': 'σ', 't': 'τ', 'u': 'υ', 'v': 'ς', 'f': 'φ', 'c': 'χ', 'y': 'ψ', 'w': 'ω',
    'A': 'Α', 'B': 'Β', 'G': 'Γ', 'D': 'Δ', 'E': 'Ε', 'Z': 'Ζ', 'H': 'Η', 'Q': 'Θ',
    'I': 'Ι', 'K': 'Κ', 'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 'X': 'Ξ', 'O': 'Ο', 'P': 'Π',
    'R': 'Ρ', 'S': 'Σ', 'T': 'Τ', 'U': 'Υ', 'V': 'Σ', 'F': 'Φ', 'C': 'Χ', 'Y': 'Ψ', 'W': 'Ω',
}
_GVOWELS = set('aehiouwAEHIOUW')
_GDIPH = {'a': 'iu', 'e': 'iu', 'o': 'iu', 'h': 'u', 'u': 'i',
          'A': 'IU', 'E': 'IU', 'O': 'IU', 'H': 'U', 'U': 'I'}


def _ages_token(tok: str) -> str:
    res = []
    i = 0
    n = len(tok)
    pend = ''
    while i < n:
        ch = tok[i]
        if ch not in _GBASE:
            i += 1
            continue
        base = _GBASE[ch]
        i += 1
        comb = pend
        pend = ''
        if ch in _GVOWELS:
            if i < n and tok[i] == 'j':
                comb += _GCOMB['j']; i += 1
            if i < n and tok[i] in '><~':
                acc = tok[i]
                nxt = tok[i + 1] if i + 1 < n else ''
                if nxt in _GVOWELS and nxt in _GDIPH.get(ch, ''):
                    pend = _GCOMB[acc]; i += 1
                else:
                    comb += _GCOMB[acc]; i += 1
            if i < n and tok[i] == '|':
                comb += _GCOMB['|']; i += 1
            elif i + 1 < n and tok[i] == '\\' and tok[i + 1] == '|':
                comb += _GCOMB['|']; i += 2
        res.append(unicodedata.normalize('NFC', base + comb))
    return ''.join(res)


_AGES_GR_PAT = re.compile(
    r'(<[a-zA-Z/!][^>]*>)'                                # group 1: HTML tag
    r'|([a-zA-Z][a-zA-Z><~j|\\]*'
    r'(?:[><~]|\\[|]|\|)'
    r'[a-zA-Z><~j|\\]*)'                                  # group 2: Ages Greek token
)


def convert_ages_greek(text: str) -> str:
    def _repl(m):
        if m.group(1):
            return m.group(1)
        tok = m.group(2)
        c = _ages_token(tok.replace('\\|', '|'))
        if any('Ͱ' <= x <= 'Ͽ' or 'ἀ' <= x <= '῿' for x in c):
            return c
        return tok
    return _AGES_GR_PAT.sub(_repl, text)


# ── Spaced-caps cleanup (B o o k s → Books) ──────────────────────────────
def collapse_spaced_caps(text: str) -> str:
    """Collapse 'B o o k s' / 'T H E A G E S' style spaced-out heading text.

    Detects runs of ≥ 3 single-letter "words" separated by single spaces and
    glues them together. Handles mixed case (heading first-letter caps).
    """
    def _glue(m):
        # m.group(0) is like "B o o k s" → "Books"
        return ''.join(m.group(0).split())
    # 3+ single-letter (A-Za-z) tokens joined by single spaces
    text = re.sub(r'\b(?:[A-Za-z] ){2,}[A-Za-z]\b', _glue, text)
    # Also collapse all-caps acronym-style 'T H E' → 'THE'
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\b([A-Z]) ([A-Z]+)', r'\1\2', text)
    return text


# ── Scripture-ref detection ──────────────────────────────────────────────
SCRIPTURE_SECTION_RE = re.compile(
    r'^\s*<\d{6,7}>\s*([A-Z][A-Za-z]*(?:\s\d)?[A-Z\s]*?\d+:\d+(?:[-,]\d+)?)\s*$'
)

# Inline scripture cross-references like "(<540416>1 Timothy 4:16.)"
INLINE_REF_RE = re.compile(r'<\d{6,7}>')


# ── Footnote definition detection ────────────────────────────────────────
FN_DEF_RE = re.compile(r'^\s*([fF][tT]?\d+)\s+(.*)$', re.DOTALL)


def normalize_fn_label(label: str) -> str:
    """Ft18 → f18 (so refs in body match definitions)."""
    return re.sub(r'^ft', 'f', label.lower())


def format_inline(text: str) -> str:
    """Apply inline transformations: strip Ages markers, convert refs, Greek."""
    # Strip Ages scripture-code wrappers `[<NNNNNN>]` or `<NNNNNN>`
    text = INLINE_REF_RE.sub('', text)
    # Bracketed footnote refs `[fN]` or `[FtN]` → `[^fN]`
    text = re.sub(r'\[([fF][tT]?\d+)\]', lambda m: f'[^{normalize_fn_label(m.group(1))}]', text)
    # Bare footnote refs `fN` (Ages PDF style: ". f8 In Scripture...") → `[^fN]`
    # Anchored by word boundaries and a preceding space/punct to avoid matching
    # English words that happen to contain "fN".
    text = re.sub(r'(?<=[\s\.,;:\)\!\?])f(\d{1,3})\b', r'[^f\1]', text)
    # Pipe-escape for Kramdown table safety
    text = re.sub(r'(?<!\\)\|', r'\\|', text)
    # Greek transliteration → Unicode
    text = convert_ages_greek(text)
    return text


def bold_leading_verse_num(text: str) -> str:
    """Convert leading `N. Capital` to `**N.** Capital` (skill §6).

    Kramdown parses paragraph-leading `N. ` as ordered list item; bolding
    prevents that and matches the Calvin verse-number convention.
    """
    return re.sub(r'^(\d+)\. (?=[A-Z])', r'**\1.** ', text)


# ── Main converter ───────────────────────────────────────────────────────
PAGE_HEADER_RE = re.compile(r'^--- PAGE (\d+) ---\s*$')
TAG_RE = re.compile(r'^\[([A-Z0-9_]+)\]\s*(.*)$', re.DOTALL)


def convert(structured_path: Path, out_path: Path) -> None:
    text = structured_path.read_text(encoding='utf-8')
    lines = text.split('\n')

    out: list[str] = []
    current_page = 0
    in_table = False
    table_left: list[str] = []
    table_right: list[str] = []
    table_header: str | None = None
    pending_blockquote_continuation = False

    def flush_table():
        nonlocal in_table, table_left, table_right, table_header
        if not (table_left or table_right):
            in_table = False
            table_header = None
            return
        # Render as HTML table (Ages two-column scripture format)
        out.append('')
        out.append('<table class="calvin-scripture">')
        if table_header:
            out.append(f'<thead><tr><th colspan="2" style="text-align:center">{table_header}</th></tr></thead>')
        out.append('<tbody>')
        rows = max(len(table_left), len(table_right))
        for i in range(rows):
            lcell = table_left[i] if i < len(table_left) else ''
            rcell = table_right[i] if i < len(table_right) else ''
            out.append(f'<tr><td>{lcell}</td><td>{rcell}</td></tr>')
        out.append('</tbody>')
        out.append('</table>')
        out.append('')
        in_table = False
        table_left = []
        table_right = []
        table_header = None

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue

        # Page boundary
        pm = PAGE_HEADER_RE.match(line)
        if pm:
            flush_table()
            current_page = int(pm.group(1))
            out.append('')
            out.append(f'<!-- PAGE {current_page} -->')
            out.append('')
            i += 1
            continue

        tm = TAG_RE.match(line)
        if not tm:
            i += 1
            continue

        tag, content = tm.group(1), tm.group(2).strip()

        # Strip the leading "page-number" BODY item (e.g. "[BODY] 47" at top of page 47)
        if tag == 'BODY' and content.strip().isdigit() and int(content.strip()) == current_page:
            i += 1
            continue

        # Tables
        if tag in ('TABLE_LEFT', 'TABLE_RIGHT'):
            if not in_table:
                in_table = True
            cell_html = format_inline(content)
            cell_html = re.sub(r'\\\|', '|', cell_html)  # un-escape pipes inside HTML cells
            if tag == 'TABLE_LEFT':
                table_left.append(cell_html)
            else:
                table_right.append(cell_html)
            i += 1
            continue
        elif in_table:
            flush_table()

        if tag == 'H1':
            cleaned = collapse_spaced_caps(content)
            cleaned = format_inline(cleaned)
            out.append('')
            out.append(f'# {cleaned}')
            out.append('')
        elif tag == 'H2':
            cleaned = collapse_spaced_caps(content)
            cleaned = format_inline(cleaned)
            out.append('')
            out.append(f'## {cleaned}')
            out.append('')
        elif tag == 'FOOTNOTE':
            # Try to detect three sub-types:
            # (a) Scripture-section header: starts with <NNNNNN>BOOK N:M (alone on line)
            # (b) Footnote definition: starts with FtN or fN (alphanumeric label)
            # (c) Inline cross-reference: bare <NNNNNN>... (often closes a body sentence)
            sec_m = SCRIPTURE_SECTION_RE.match(line.replace('[FOOTNOTE]', '').strip())
            if sec_m:
                ref = sec_m.group(1).strip()
                out.append('')
                out.append(f'## {ref}')
                out.append('')
            else:
                fn_m = FN_DEF_RE.match(content)
                if fn_m and not fn_m.group(2).startswith('<'):
                    label = normalize_fn_label(fn_m.group(1))
                    body = format_inline(fn_m.group(2))
                    out.append('')
                    out.append(f'[^{label}]: {body}')
                    out.append('')
                else:
                    # Inline cross-reference fragment — fold into preceding paragraph
                    body = format_inline(content)
                    # If previous output line is a paragraph (non-empty, no markers), append
                    # in place; otherwise emit as its own line.
                    j = len(out) - 1
                    while j >= 0 and not out[j].strip():
                        j -= 1
                    if j >= 0 and not out[j].lstrip().startswith(('#', '<', '[^', '>')):
                        out[j] = out[j].rstrip() + ' ' + body
                    else:
                        out.append('')
                        out.append(body)
                        out.append('')
        elif tag in ('BODY', 'VERSE'):
            body = format_inline(content)
            body = bold_leading_verse_num(body)
            out.append('')
            out.append(body)
            out.append('')
        else:
            # Unknown tag — emit raw for debugging
            out.append(f'<!-- UNKNOWN-TAG {tag}: {content[:80]} -->')

        i += 1

    flush_table()

    # Collapse multiple blank lines to single
    result = '\n'.join(out)
    result = re.sub(r'\n{3,}', '\n\n', result)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result + '\n', encoding='utf-8')


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: structured_to_md.py <input.txt> <output.md>', file=sys.stderr)
        return 1
    inp = Path(sys.argv[1])
    out = Path(sys.argv[2])
    convert(inp, out)
    sz = out.stat().st_size
    n_lines = sum(1 for _ in out.open(encoding='utf-8'))
    print(f'[ok] {inp.name} → {out.relative_to(out.parent.parent)}')
    print(f'    {sz:,} bytes, {n_lines:,} lines')
    return 0


if __name__ == '__main__':
    sys.exit(main())
