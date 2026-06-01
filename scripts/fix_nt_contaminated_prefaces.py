#!/usr/bin/env python3
"""
Fix 3 NT prefaces whose body was over-extracted from PDF (chapter 1+ content
got stuffed in, and the tail was truncated).  Same pattern as the OT fix in
scripts/fix_contaminated_prefaces.py.

For each book:
  1. Open PDF, extract text between `start_phrase` and `end_phrase` (the real
     book-level preface).
  2. Strip page headers, join PDF hard-wrapped lines.
  3. Replace ONLY the `<div class="preface-body">…</div>` block in the .md.
  4. Remove any stale `<aside class="mhenry-footnotes">…</aside>` left over
     from the contaminated extraction.

Preserves: front matter, preface-wrap, emblem, title-block, divider, closing.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

import fitz  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"
PDF_DIR = Path.home() / "Documents" / "论文" / "matthew_henry"

SPECS = [
    # (book_id, pdf_filename, start_phrase, end_phrase)
    ("1corinthians",
     "46马太亨利完整圣经注释（哥林多前书）.pdf",
     "哥林多是希腊的主要城市之一",
     "哥林多前书第一章"),
    ("2corinthians",
     "47马太亨利完整圣经注释（哥林多后书）.pdf",
     "在前一封信中，使徒提到他从马其顿经过的时候",
     "哥林多后书第一章"),
    ("revelation",
     "66马太亨利完整圣经注释（启示录）.pdf",
     "尽管切尔顿、马吉安这些腐败之流拒绝接受",
     "启示录第一章"),
]


def clean_pdf_text(raw: str) -> str:
    # Drop common page header patterns
    raw = re.sub(r"马太亨利完整圣经注释[^\n]*\n", "", raw)
    raw = re.sub(r"^\s*\d+\s*$", "", raw, flags=re.MULTILINE)
    # Join hard-wrapped lines: glue line ending with non-terminator to next
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    joined: list[str] = []
    for line in lines:
        if joined and joined[-1] and joined[-1][-1] not in "。！？.!?":
            joined[-1] = joined[-1] + line
        else:
            joined.append(line)
    return "\n".join(joined).strip()


def extract_preface_text(spec) -> str:
    book_id, pdf_name, start, end = spec
    pdf_path = PDF_DIR / pdf_name
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    doc = fitz.open(pdf_path)
    full = "\n".join(p.get_text() for p in doc)
    # find both anchors
    s_idx = full.find(start)
    if s_idx < 0:
        raise RuntimeError(f"{book_id}: start anchor not found")
    # Search for end anchor flexibly — try with and without space variants
    # Try several plausible end markers
    candidates = [end, end.replace("第一章", "第 一 章"), end[len(end)-3:],  # "第一章" alone
                  "哥林多前書第一章" if "1cor" in book_id else end,
                  "哥林多後書第一章" if "2cor" in book_id else end,
                  "啟示錄第一章" if "rev" in book_id else end]
    e_idx = -1
    for cand in candidates:
        e_idx = full.find(cand, s_idx + len(start))
        if e_idx > 0:
            break
    if e_idx < 0:
        # Last resort: stop at first "第一章" after start
        m = re.search(r"\n\s*第\s*一?\s*章\s*\n", full[s_idx:])
        if m:
            e_idx = s_idx + m.start()
    if e_idx < 0:
        raise RuntimeError(f"{book_id}: end anchor not found")
    raw_section = full[s_idx:e_idx]
    return clean_pdf_text(raw_section)


BODY_BLOCK_RE = re.compile(
    r'<div class="preface-body">\s*\n.*?\n</div>',
    re.DOTALL,
)
ASIDE_BLOCK_RE = re.compile(
    r'\n\n?<aside class="mhenry-footnotes">.*?</aside>',
    re.DOTALL,
)


def fix_one(spec) -> str:
    book_id = spec[0]
    md_path = MHENRY / book_id / "preface.md"
    md = md_path.read_text(encoding="utf-8")
    if 'class="preface-body"' not in md:
        return f"[skip] {book_id}: no preface-body wrap (run ornate_nt_preface first)"

    preface_text = extract_preface_text(spec)
    # Split into paragraphs at sentence breaks if it's all one blob — keep as a
    # single <p> with embedded line breaks (matches matthew preface format).
    body_html = f'<div class="preface-body">\n<p>{preface_text}</p>\n</div>'

    new_md, n_body = BODY_BLOCK_RE.subn(body_html, md, count=1)
    if n_body == 0:
        return f"[fail] {book_id}: could not locate body block"
    new_md, n_aside = ASIDE_BLOCK_RE.subn("", new_md)
    md_path.write_text(new_md, encoding="utf-8")
    return f"[ok] {book_id}: body replaced ({len(preface_text):,} chars), removed {n_aside} stale aside(s)"


def main() -> int:
    targets = sys.argv[1:] if len(sys.argv) > 1 else [s[0] for s in SPECS]
    by_id = {s[0]: s for s in SPECS}
    for book_id in targets:
        if book_id not in by_id:
            print(f"[skip] unknown: {book_id}", file=sys.stderr)
            continue
        try:
            print(fix_one(by_id[book_id]))
        except Exception as e:
            print(f"[fail] {book_id}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
