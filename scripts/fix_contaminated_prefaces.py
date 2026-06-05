#!/usr/bin/env python3
"""
Fix prefaces whose <p>...</p> body was over-extracted from the PDF
(includes chapter 1, 2, 3 content). Replaces the body content with the
cleanly-extracted preface text from /tmp/mhenry_prefaces/.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"
SRC = Path("/tmp/mhenry_prefaces")

BOOKS = ["job", "psalms", "proverbs", "ecclesiastes", "songofsolomon"]

BODY_BLOCK_RE = re.compile(
    r'(<div class="preface-body">\s*\n<p>)(.*?)(</p>\s*\n</div>)',
    re.DOTALL,
)


def main() -> int:
    for book in BOOKS:
        md_path = MHENRY / book / "preface.md"
        src_path = SRC / f"{book}_preface.txt"
        if not src_path.exists():
            print(f"[skip] {book}: no source at {src_path}", file=sys.stderr)
            continue
        new_body = src_path.read_text(encoding="utf-8").strip()
        # Convert paragraph separators (single \n that follows a sentence terminator)
        # into <br/> so the rendered text preserves the paragraph breaks the PDF had.
        # The CSS handles text-indent on <p>, but we only have one <p>, so use <br>.
        # Each line in the source ends with terminator; join with <br/> for visual break.
        lines = [l for l in new_body.split("\n") if l.strip()]
        # Use <br/> between paragraphs but keep them in one <p> so first-letter
        # drop-cap styling still applies to the very first character only.
        joined = "<br/>".join(lines)
        src = md_path.read_text(encoding="utf-8")
        m = BODY_BLOCK_RE.search(src)
        if not m:
            print(f"[fail] {book}: body block pattern not matched", file=sys.stderr)
            continue
        new_src = src[: m.start()] + m.group(1) + joined + m.group(3) + src[m.end():]
        md_path.write_text(new_src, encoding="utf-8")
        print(f"[ok] {book}: {len(joined)} chars body, total {len(new_src)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
