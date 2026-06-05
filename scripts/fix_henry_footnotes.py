#!/usr/bin/env python3
"""
Re-number footnotes sequentially in mhenry markdown files.

Each chapter may have multiple footnote scopes each starting at 1
(e.g. aside contains 1,2,1,2,3).  This script assigns a single
global sequence: 1,2,3,4,5.

Strategy
--------
Only files where the count of detected inline markers == count of aside
footnotes are fixed (both inline markers and aside entries are renumbered).
Files with a mismatch are skipped with a warning.

Detection heuristic for inline markers
---------------------------------------
  - Search body text with <div class="mh-verse">…</div> stripped (verse
    numbers inside scripture blocks are not footnote markers).
  - Match: (?<=[\u4e00-\u9fff])(\d{1,2})(?=[\u4e00-\u9fff，。；！？（])
  - Exclude if immediately preceding char is '第' (ordinal prefix).
  - Exclude if immediately following char is in '节章' (chapter/verse words).

Usage
-----
    python3 scripts/fix_henry_footnotes.py [path]

    path  – a single .md file or a directory (default: mhenry/)
"""

import re, sys
from pathlib import Path

# ── patterns ────────────────────────────────────────────────────────────────
_INLINE_RE = re.compile(
    r'(?<=[\u4e00-\u9fff])(\d{1,2})'
    r'(?=[\u4e00-\u9fff\uff0c\u3002\uff1b\uff01\uff1f\uff08])'
)
_VERSE_BLOCK_RE = re.compile(r'<div class="mh-verse">.*?</div>', re.DOTALL)
_ASIDE_ENTRY_RE = re.compile(r'<p><sup>(\d+)</sup>')


def _is_footnote_marker(text, m):
    prev = text[m.start() - 1] if m.start() > 0 else ''
    nxt  = text[m.end()]       if m.end() < len(text) else ''
    if prev == '第':
        return False
    if nxt in '节章':
        return False
    return True


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding='utf-8')

    aside_m = re.search(
        r'<aside class="mhenry-footnotes">(.*?)</aside>', text, re.DOTALL
    )
    if not aside_m:
        return False

    aside_nums = _ASIDE_ENTRY_RE.findall(aside_m.group(0))
    n = len(aside_nums)
    if n == 0:
        return False

    # already correctly numbered if aside is 1,2,...,n with no duplicates
    if aside_nums == [str(i) for i in range(1, n + 1)]:
        # aside OK – but inline markers may still need fixing; check below
        pass

    body     = text[: aside_m.start()]
    body_clean = _VERSE_BLOCK_RE.sub('', body)

    inline_ms = [
        m for m in _INLINE_RE.finditer(body_clean)
        if _is_footnote_marker(body_clean, m)
    ]

    if len(inline_ms) != n:
        print(
            f'  SKIP {path.name}: aside={n} footnotes, '
            f'inline markers={len(inline_ms)} (mismatch)'
        )
        return False

    # ── Renumber inline markers in body (reverse order to preserve offsets) ──
    # Build a mapping from clean-body position → new number,
    # then apply to the ORIGINAL body (positions may shift because verse blocks
    # were removed; we need to map positions back).

    # Rebuild the position map: original body → clean body
    # We do this by keeping track of removed ranges.
    verse_spans = [m.span() for m in _VERSE_BLOCK_RE.finditer(body)]

    def clean_pos_to_orig(clean_pos: int) -> int:
        """Map a position in body_clean back to a position in body."""
        orig_pos = clean_pos
        for vs, ve in verse_spans:
            vs_clean = vs  # before first removal this is the same
            # We process spans in order; adjust for previously removed text
            if vs <= orig_pos + (ve - vs):
                orig_pos += ve - vs
            else:
                break
        return orig_pos

    # Simpler: rebuild mapping once using re.sub tracking
    # Actually easiest: reconstruct body with placeholders and find positions.
    # But simplest of all: record what was removed and where.

    # Build offset list: list of (clean_start, orig_start, removed_len)
    offsets = []
    removed_so_far = 0
    for vs, ve in verse_spans:
        clean_start = vs - removed_so_far
        offsets.append((clean_start, vs, ve - vs))
        removed_so_far += ve - vs

    def to_orig(clean_pos: int) -> int:
        added = 0
        for cs, orig_s, rlen in offsets:
            if cs <= clean_pos:
                added += rlen
            else:
                break
        return clean_pos + added

    # Sort inline matches by clean position (already in order)
    new_body = body
    for new_num, m in reversed(list(enumerate(inline_ms, start=1))):
        # orig position in body
        orig_start = to_orig(m.start())
        orig_end   = to_orig(m.end())
        new_body = (
            new_body[:orig_start]
            + str(new_num)
            + new_body[orig_end:]
        )

    # ── Renumber aside entries ───────────────────────────────────────────────
    counter = [0]

    def _replace_aside(m):
        counter[0] += 1
        return f'<p><sup>{counter[0]}</sup>'

    new_aside = _ASIDE_ENTRY_RE.sub(_replace_aside, aside_m.group(0))

    new_text = new_body + new_aside + text[aside_m.end():]

    if new_text == text:
        return False

    path.write_text(new_text, encoding='utf-8')
    print(f'  Fixed {path}: {n} footnotes renumbered')
    return True


def main():
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if target.is_file():
            fix_file(target)
            return
        base = target
    else:
        base = Path(__file__).parent.parent / 'mhenry'

    files = sorted(base.rglob('*.md'))
    changed = skipped = 0
    for f in files:
        result = fix_file(f)
        if result:
            changed += 1
        # skipped counted inside fix_file via print

    print(f'\nDone: {changed} files updated')


if __name__ == '__main__':
    main()
