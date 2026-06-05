#!/usr/bin/env python3
"""
Migrate unoptimized OT mhenry prefaces to haggai-style structure.

For each book listed below:
  1. Reads <book>/1.md and extracts its full chapter <style>...</style> block
     (the water-crystal theme with each book's own color palette).
  2. Reads <book>/preface.md and extracts:
       - the existing front-matter,
       - the existing preface decoration <style>...</style> block,
       - the body <p>...</p> paragraph(s).
  3. Writes a new <book>/preface.md combining:
       - the front-matter (preserved),
       - the chapter style block (from 1.md),
       - the haggai-style wrapper HTML (emblem + title-block + divider + body + closing),
       - the preface decoration style block (preserved, with title-block / body padding
         adjusted to match haggai's optimized layout).
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"

BOOKS: dict[str, str] = {
    # Pentateuch
    "genesis": "律法简介",
    "exodus": "律法简介",
    "leviticus": "律法简介",
    "numbers": "律法简介",
    "deuteronomy": "律法简介",
    # Historical
    "joshua": "历史简介",
    "judges": "历史简介",
    "ruth": "历史简介",
    "1samuel": "历史简介",
    "2samuel": "历史简介",
    "1kings": "历史简介",
    "2kings": "历史简介",
    "1chronicles": "历史简介",
    "2chronicles": "历史简介",
    "nehemiah": "历史简介",
    "esther": "历史简介",
    # Wisdom / Poetry
    "job": "智慧简介",
    "psalms": "智慧简介",
    "proverbs": "智慧简介",
    "ecclesiastes": "智慧简介",
    "songofsolomon": "智慧简介",
    # Prophets (major + remaining minor)
    "isaiah": "先知简介",
    "jeremiah": "先知简介",
    "lamentations": "先知简介",
    "ezekiel": "先知简介",
    "daniel": "先知简介",
    "hosea": "先知简介",
    "joel": "先知简介",
    "amos": "先知简介",
    "obadiah": "先知简介",
}

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
STYLE_BLOCK_RE = re.compile(r"<style>\s*\n(.*?)\n</style>", re.DOTALL)
BODY_P_RE = re.compile(r"<p>(.*?)</p>", re.DOTALL)
BOOK_NAME_RE = re.compile(r"^book_name:\s*(.*)$", re.MULTILINE)


def extract_chapter_style(book_dir: Path) -> str:
    """Return the first <style>...</style> block from 1.md, contents only."""
    ch1 = (book_dir / "1.md").read_text(encoding="utf-8")
    m = STYLE_BLOCK_RE.search(ch1)
    if not m:
        raise RuntimeError(f"No <style> block found in {book_dir / '1.md'}")
    return m.group(1)


def adjust_decoration_padding(decoration_css: str) -> str:
    """
    Match haggai's optimized padding values:
        .preface-title-block { padding: 0; }
        .preface-body        { padding: 0; }
    The unoptimized originals use 20px/24px which now produce double-padding
    once the wrap structure is in place.
    """
    # .preface-title-block padding
    decoration_css = re.sub(
        r"(\.preface-title-block\s*\{[^}]*?)padding:\s*[^;]+;",
        r"\1padding: 0;",
        decoration_css,
        count=1,
        flags=re.DOTALL,
    )
    # .preface-body padding (the bare class, not .preface-body p)
    decoration_css = re.sub(
        r"(\.preface-body\s*\{[^}]*?)padding:\s*[^;]+;",
        r"\1padding: 0;",
        decoration_css,
        count=1,
        flags=re.DOTALL,
    )
    return decoration_css


def build_preface(book_id: str, label: str) -> str:
    book_dir = MHENRY / book_id
    src = (book_dir / "preface.md").read_text(encoding="utf-8")

    fm_m = FRONT_MATTER_RE.match(src)
    if not fm_m:
        raise RuntimeError(f"No front matter in {book_dir / 'preface.md'}")
    fm_body = fm_m.group(1)
    rest = src[fm_m.end():]

    name_m = BOOK_NAME_RE.search(fm_body)
    if not name_m:
        raise RuntimeError(f"No book_name in {book_dir / 'preface.md'}")
    book_name = name_m.group(1).strip()

    deco_m = STYLE_BLOCK_RE.search(rest)
    if not deco_m:
        raise RuntimeError(f"No decoration <style> block in {book_dir / 'preface.md'}")
    decoration_css = deco_m.group(1)
    after_style = rest[deco_m.end():]

    body_m = BODY_P_RE.search(after_style)
    if not body_m:
        raise RuntimeError(f"No <p>...</p> body in {book_dir / 'preface.md'}")
    body_text = body_m.group(1).strip()

    chapter_css = extract_chapter_style(book_dir)
    decoration_css = adjust_decoration_padding(decoration_css)

    return (
        f"---\n{fm_body}\n---\n"
        f"\n"
        f"<style>\n{chapter_css}\n</style>\n"
        f"\n"
        f"<div class=\"preface-wrap\">\n"
        f"\n"
        f"<div class=\"preface-emblem\">✦</div>\n"
        f"\n"
        f"<div class=\"preface-title-block\">\n"
        f"  <div class=\"preface-label\">{label}</div>\n"
        f"  <div class=\"preface-book-name\">{book_name}</div>\n"
        f"  <div class=\"preface-sub\">马太亨利注释 · 书卷导言</div>\n"
        f"</div>\n"
        f"\n"
        f"<div class=\"preface-divider\"><span>◆</span></div>\n"
        f"\n"
        f"<div class=\"preface-body\">\n"
        f"<p>{body_text}</p>\n"
        f"</div>\n"
        f"\n"
        f"<div class=\"preface-closing\">✦ &ensp; ✦ &ensp; ✦</div>\n"
        f"\n"
        f"</div>\n"
        f"\n"
        f"<style>\n{decoration_css}\n</style>\n"
    )


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    only = [a for a in argv[1:] if not a.startswith("--")]

    targets = only if only else list(BOOKS.keys())
    for book_id in targets:
        if book_id not in BOOKS:
            print(f"[skip] unknown: {book_id}", file=sys.stderr)
            continue
        try:
            content = build_preface(book_id, BOOKS[book_id])
        except Exception as e:
            print(f"[fail] {book_id}: {e}", file=sys.stderr)
            continue
        out = MHENRY / book_id / "preface.md"
        if dry:
            print(f"[dry-run] would write {out} ({len(content)} chars)")
        else:
            out.write_text(content, encoding="utf-8")
            print(f"[ok] {book_id} → {out.relative_to(ROOT)} ({len(content)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
