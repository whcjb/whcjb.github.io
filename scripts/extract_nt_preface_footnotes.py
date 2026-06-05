#!/usr/bin/env python3
"""
Extract footnote definitions embedded in NT preface body and move them into
an <aside class="mhenry-footnotes"> block after </div class="preface-body">.

Footnote pattern inside the preface body:
  A contiguous run of N lines that each
    - start with a single digit (1-9, optionally a second digit),
    - followed immediately by a non-digit Chinese character,
    - end with a sentence terminator (。 or ！ or ？),
  and whose leading digits form the sequence 1, 2, 3, ..., N.

The lines flanking the footnote block typically split a sentence mid-word
(in matthew/preface.md: "...存留半点，除" + footnotes + "了经上所记的..."),
so when re-stitching we just concat the previous and following lines without
inserting space.

Idempotent: if file already contains `class="mhenry-footnotes"`, skip.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"

NT_BOOKS = [
    "matthew", "mark", "luke", "john", "acts",
    "romans", "1corinthians", "2corinthians", "hebrews",
    "1peter", "2peter", "revelation",
]

FN_LINE_RE = re.compile(r"^(\d{1,2})([^\d\s][^\n]*[。！？\.!?])\s*$")


def extract_footnotes(body_text: str) -> tuple[str, list[tuple[int, str]]]:
    """Return (cleaned_body, footnotes).

    Detect a contiguous run of N lines forming a numbered sequence 1..N.
    Remove those lines from body and concatenate flanking lines.
    """
    lines = body_text.split("\n")
    n = len(lines)
    # Find longest contiguous run starting at some index where line N matches
    # pattern with leading digits in strict 1..k sequence.
    best_start = best_end = -1
    best_count = 0
    i = 0
    while i < n:
        m = FN_LINE_RE.match(lines[i])
        if not m or int(m.group(1)) != 1:
            i += 1
            continue
        # Try to grow a 1..k sequence
        run = [(i, m)]
        j = i + 1
        expected = 2
        while j < n:
            mm = FN_LINE_RE.match(lines[j])
            if not mm or int(mm.group(1)) != expected:
                break
            run.append((j, mm))
            expected += 1
            j += 1
        if len(run) >= 2 and len(run) > best_count:
            best_count = len(run)
            best_start = run[0][0]
            best_end = run[-1][0]
        i = j if len(run) >= 2 else i + 1

    if best_count == 0:
        return body_text, []

    footnotes: list[tuple[int, str]] = []
    for idx in range(best_start, best_end + 1):
        m = FN_LINE_RE.match(lines[idx])
        if m:
            footnotes.append((int(m.group(1)), m.group(2).strip()))

    # Stitch: concatenate the line immediately before the block with the line
    # immediately after, since the original sentence was split.
    pre = lines[:best_start]
    post = lines[best_end + 1:]
    if pre and post:
        # Join the last pre-line and the first post-line into one (concat, no space)
        stitched = pre[:-1] + [pre[-1] + post[0]] + post[1:]
    elif pre:
        stitched = pre
    else:
        stitched = post
    return "\n".join(stitched), footnotes


def render_aside(footnotes: list[tuple[int, str]]) -> str:
    items = "\n".join(
        f"<p><sup>{n}</sup> {text}</p>" for n, text in footnotes
    )
    return f'<aside class="mhenry-footnotes">\n{items}\n</aside>'


def process_book(book_id: str) -> str:
    path = MHENRY / book_id / "preface.md"
    if not path.exists():
        return f"[skip] {book_id}: no preface.md"
    text = path.read_text(encoding="utf-8")
    if 'class="mhenry-footnotes"' in text:
        return f"[skip] {book_id}: already has aside"
    if 'class="preface-body"' not in text:
        return f"[skip] {book_id}: not wrapped yet"

    # Locate the preface-body block
    body_open_re = re.compile(r'<div class="preface-body">\s*\n')
    body_close_re = re.compile(r'\n</div>')
    open_m = body_open_re.search(text)
    if not open_m:
        return f"[fail] {book_id}: no preface-body open"
    close_m = body_close_re.search(text, open_m.end())
    if not close_m:
        return f"[fail] {book_id}: no preface-body close"

    body_inner = text[open_m.end():close_m.start()]

    # Strip outer <p>...</p> for analysis but keep it for re-assembly
    p_open_re = re.compile(r'^\s*<p>', re.DOTALL)
    p_close_re = re.compile(r'</p>\s*$', re.DOTALL)
    po = p_open_re.match(body_inner)
    pc = p_close_re.search(body_inner)
    if po and pc:
        inner_text = body_inner[po.end():pc.start()]
        wrap_p = True
    else:
        inner_text = body_inner
        wrap_p = False

    cleaned, footnotes = extract_footnotes(inner_text)
    if not footnotes:
        return f"[skip] {book_id}: no footnotes detected"

    if wrap_p:
        new_body_inner = "<p>" + cleaned + "</p>"
    else:
        new_body_inner = cleaned

    aside = render_aside(footnotes)
    new_text = (
        text[:open_m.end()] + new_body_inner + "\n</div>\n\n" + aside + text[close_m.end():]
    )
    path.write_text(new_text, encoding="utf-8")
    return f"[ok] {book_id}: extracted {len(footnotes)} footnotes ({[n for n,_ in footnotes]})"


def main(argv: list[str]) -> int:
    only = [a for a in argv[1:] if not a.startswith("--")]
    targets = only if only else NT_BOOKS
    for book in targets:
        print(process_book(book))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
