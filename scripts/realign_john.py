#!/usr/bin/env python3
"""
Re-extract John chapters from PDF into Matthew-style structure.

The current mhenry/john/*.md is malformed three ways:
  - some chapters wrap whole content in a single <div class="mh-overview"> blob
  - some use `<div class="mh-verse">第N-N节</div>` (range label) and put the
    actual scripture inside <p> tags within the body
  - paragraphs are explicitly <p>…</p> wrapped (other NT books use markdown blank-line)

Goal: per-chapter format identical to mhenry/matthew/1.md —
  ## 第N章
  <div class="mh-overview">overview text</div>
  <div class="mh-unit">
    <div class="mh-verse">1 …actual scripture… N …</div>
    <div class="mh-unit-body">

    commentary paragraphs separated by blank lines

    </div>
  </div>
  …

Re-extracted from /Users/yanpeifa/Documents/论文/matthew_henry/马太亨利圣经注释-约翰福音.pdf
(385-page clean version with TOC chapter map).
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

import fitz  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"
PDF = Path.home() / "Documents/论文/matthew_henry/马太亨利圣经注释-约翰福音.pdf"

# PDF page ranges (1-indexed) for each chapter, derived by scanning each page
# for the "第N章" heading (TOC numbers in this PDF are off by 1 for several
# chapters because the heading sits at the bottom of the prior page).
CHAPTER_PAGES = {
    1: (3, 25), 2: (26, 36), 3: (37, 51), 4: (52, 70), 5: (71, 88),
    6: (89, 111), 7: (112, 129), 8: (130, 157), 9: (158, 175), 10: (176, 190),
    11: (191, 213), 12: (214, 234), 13: (235, 252), 14: (253, 268), 15: (269, 279),
    16: (280, 295), 17: (296, 315), 18: (316, 334), 19: (335, 353), 20: (354, 370),
    21: (371, 385),
}

PAGE_HEADER_RE = re.compile(r"马太亨利圣经注释\s*-?\s*约翰福音\s*\n\s*\d+\s*\n")
CHAPTER_HEADING_RE = re.compile(r"^\s*第\s*\d+\s*章\s*$")
VERSE_RANGE_RE = re.compile(r"(?:^|\n)\s*约\s*\d+\s*[:：]\s*(\d+)\s*[-－]\s*(\d+)\s*(?:\n|$)")


def extract_chapter_text(ch: int) -> str:
    doc = fitz.open(PDF)
    start, end = CHAPTER_PAGES[ch]
    raw = "".join(doc[p].get_text() for p in range(start - 1, end))
    raw = PAGE_HEADER_RE.sub("\n", raw)
    return raw


def squash_lines(text: str) -> str:
    """Re-join PDF hard-wrapped lines: if a line doesn't end with sentence
    terminator and isn't followed by a structural marker, join it to the next."""
    structural_markers = (
        CHAPTER_HEADING_RE,
        re.compile(r"^约\s*\d+\s*[:：]\s*\d+\s*[-－]\s*\d+\s*$"),
        re.compile(r"^[IVX]+\."),
        re.compile(r"^\d+\.\s"),
        re.compile(r"^\(\d+\.?\)"),
        re.compile(r"^\[\d+\.?\]"),
        re.compile(r"^第\d+\s*节"),
    )

    def is_structural(s: str) -> bool:
        return any(p.match(s) for p in structural_markers)

    out_lines: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            if out_lines and out_lines[-1] != "":
                out_lines.append("")
            continue
        # Structural marker → its own paragraph
        if is_structural(line):
            out_lines.append(line)
            continue
        # Only verse-range markers (约N:M-K) and chapter headings stand alone —
        # the following line is treated as scripture / overview start.
        # Other "structural" lines (I., 1., (1)) may have continuations that
        # need joining.
        if out_lines and out_lines[-1]:
            prev = out_lines[-1]
            standalone = (CHAPTER_HEADING_RE.match(prev)
                          or re.match(r"^约\s*\d+\s*[:：]\s*\d+\s*[-－]\s*\d+\s*$", prev))
            if standalone:
                out_lines.append(line)
                continue
        # If previous line ended with terminator, treat as new para
        if out_lines and out_lines[-1] and out_lines[-1][-1] in "。！？.!?":
            out_lines.append(line)
        elif out_lines and out_lines[-1]:
            out_lines[-1] = out_lines[-1] + line
        else:
            out_lines.append(line)
    # Collapse multiple blank lines
    result = []
    prev_blank = False
    for l in out_lines:
        if not l:
            if not prev_blank and result:
                result.append("")
            prev_blank = True
        else:
            result.append(l)
            prev_blank = False
    return "\n".join(result).strip()


def split_chapter_overview(text: str, ch: int) -> tuple[str, str]:
    """Return (overview, rest). Overview = text between '第N章' and the first
    verse-range marker (约N:M-K).

    The PDF page where chapter N starts often also carries the trailing
    paragraph of chapter N-1, so we drop everything before '第N章'."""
    heading = re.search(rf"第\s*{ch}\s*章", text)
    if heading:
        text = text[heading.end():]
    m = VERSE_RANGE_RE.search(text)
    if not m:
        return text.strip(), ""
    return text[:m.start()].strip(), text[m.start():]


def split_into_sections(text: str) -> list[tuple[str, int, int, str]]:
    """Split the post-overview part into (verse_range_label, min_v, max_v, body).
    body is the raw text containing scripture + commentary for this section."""
    positions = []
    for m in re.finditer(r"(?:^|\n)\s*(约\s*\d+\s*[:：]\s*(\d+)\s*[-－]\s*(\d+))\s*\n", text):
        positions.append((m.start(), m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.end()))
    sections = []
    for i, (start, label, lo, hi, body_start) in enumerate(positions):
        body_end = positions[i+1][0] if i+1 < len(positions) else len(text)
        body = text[body_start:body_end].strip()
        sections.append((label, lo, hi, body))
    return sections


def split_scripture_commentary(body: str, lo: int, hi: int) -> tuple[str, str]:
    """Within a section body, find where scripture verses end and commentary begins.

    Heuristic: scripture spans verses lo..hi. We locate the position of the LAST
    verse marker '{hi} ' that's followed by reasonable verse text, then find the
    paragraph break after it (the next blank line or the first paragraph that
    starts with a non-verse marker).
    """
    # Find all "<num> " positions in order
    verse_marks = []
    for m in re.finditer(r"(?:(?<=\s)|(?<=^))(\d+)(?=\s)", body):
        n = int(m.group(1))
        if lo <= n <= hi:
            verse_marks.append((n, m.start()))
    if not verse_marks:
        return "", body
    # We need a contiguous run starting at lo (or close to it) up to hi.
    # Take the last occurrence of `hi` after the contiguous run.
    last_pos = None
    expected = lo
    seen = set()
    for n, pos in verse_marks:
        if n == expected:
            last_pos = pos
            seen.add(n)
            expected = n + 1
            if expected > hi:
                break
    if last_pos is None:
        return "", body
    # Now find the end of the last verse's sentence: next `\n` or end of "。"
    tail = body[last_pos:]
    end_m = re.search(r"。\s*\n", tail)
    if end_m:
        sep = last_pos + end_m.end()
    else:
        # Fall back: end at next 。 or at end of body
        period_m = re.search(r"。\s*", tail)
        sep = last_pos + (period_m.end() if period_m else len(tail))
    scripture = body[:sep].strip()
    commentary = body[sep:].strip()
    return scripture, commentary


def normalize_scripture(s: str) -> str:
    """Collapse internal whitespace to single space; preserve verse-num spacing."""
    s = re.sub(r"\s+", " ", s).strip()
    return s


def render_chapter(ch: int, header_img: str, date: str) -> str:
    raw = extract_chapter_text(ch)
    text = squash_lines(raw)
    overview, rest = split_chapter_overview(text, ch)
    sections = split_into_sections(rest)

    parts = [
        "---",
        "layout: mhenry-chapter",
        "book_id: john",
        "book_name: 约翰福音",
        f"chapter: {ch}",
        "total_chapters: 21",
        f"header-img: {header_img}",
        f"date: {date}",
        "---",
        "",
        f"## 第{['','一','二','三','四','五','六','七','八','九','十','十一','十二','十三','十四','十五','十六','十七','十八','十九','二十','二十一'][ch]}章",
        "",
        '<div class="mh-overview">',
        overview if overview else "",
        "</div>",
        "",
    ]

    for label, lo, hi, body in sections:
        scripture, commentary = split_scripture_commentary(body, lo, hi)
        scripture = normalize_scripture(scripture) if scripture else f"{label}"
        parts.append('<div class="mh-unit">')
        parts.append('<div class="mh-verse">')
        parts.append(scripture)
        parts.append("</div>")
        parts.append('<div class="mh-unit-body">')
        parts.append("")
        # Commentary: keep as-is from squash_lines, paragraphs separated by blank lines
        parts.append(commentary.strip() if commentary else "")
        parts.append("")
        parts.append("</div>")
        parts.append("</div>")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    only = [a for a in argv[1:] if not a.startswith("--") and a.isdigit()]

    chapters = [int(x) for x in only] if only else sorted(CHAPTER_PAGES.keys())
    for ch in chapters:
        target = MHENRY / "john" / f"{ch}.md"
        if not target.exists():
            print(f"[skip] {target}: missing existing file", file=sys.stderr)
            continue
        # Read existing front matter to preserve header-img + date
        existing = target.read_text(encoding="utf-8")
        m_img = re.search(r"^header-img:\s*(\S+)", existing, re.MULTILINE)
        m_date = re.search(r"^date:\s*(.+)$", existing, re.MULTILINE)
        if not m_img or not m_date:
            print(f"[skip] {target}: incomplete front matter", file=sys.stderr)
            continue
        out = render_chapter(ch, m_img.group(1).strip(), m_date.group(1).strip())
        unit_marker = '<div class="mh-unit">'
        if dry:
            print(f"[dry-run] ch {ch}: {len(out)} chars, {out.count(unit_marker)} units")
        else:
            target.write_text(out, encoding="utf-8")
            n_units = out.count(unit_marker)
            print(f"[ok] john/{ch}.md  {len(out)} chars  {n_units} units")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
