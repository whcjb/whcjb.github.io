#!/usr/bin/env python3
"""Assemble per-page OCR markdown into one book-level raw file.

Reads `<raw_dir>/ocr/page_NNNN.md` files, normalizes them, and writes
`<raw_dir>/calvin_<book>_zh.md`.

Normalization:
- Drop running-header pages (lines matching common book-title patterns).
- Insert a `<!-- PAGE NNN -->` marker between page contents.
- Collapse 3+ blank lines to 2.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Common Chinese running-header noise (book title appearing on every page).
# Caller can extend via --strip-line.
DEFAULT_STRIP_PATTERNS = [
    r"^#\s*加尔文文集.*约翰福音注释\s*$",
    r"^#\s*约翰福音注释\s*$",
    r"^加尔文文集.*约翰福音注释\s*$",
    r"^约翰福音注释\s*$",
]


def normalize_page(text: str, strip_res: list[re.Pattern]) -> str:
    # Drop lines matching any strip pattern (running headers).
    out_lines = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if any(p.match(stripped) for p in strip_res):
            continue
        out_lines.append(stripped)
    # Collapse 3+ consecutive blank lines to 2.
    text = "\n".join(out_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True,
                    help="e.g. calvin_raw/john-scan (expects ocr/ subdir)")
    ap.add_argument("--book", required=True,
                    help="e.g. john (output filename suffix)")
    ap.add_argument("--strip-line", action="append", default=[],
                    help="Extra regex to strip (running header). Repeatable.")
    ap.add_argument("--no-default-strip", action="store_true",
                    help="Skip the default running-header strip patterns.")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    ocr_dir = raw_dir / "ocr"
    if not ocr_dir.is_dir():
        print(f"[assemble] missing dir: {ocr_dir}", file=sys.stderr)
        return 1

    patterns = [] if args.no_default_strip else list(DEFAULT_STRIP_PATTERNS)
    patterns += args.strip_line
    strip_res = [re.compile(p) for p in patterns]

    pages = sorted(ocr_dir.glob("page_*.md"))
    if not pages:
        print(f"[assemble] no page_*.md found under {ocr_dir}", file=sys.stderr)
        return 1

    out_parts: list[str] = []
    for p in pages:
        page_num = int(re.search(r"page_(\d+)", p.name).group(1))
        text = p.read_text(encoding="utf-8")
        text = normalize_page(text, strip_res)
        if not text:
            continue
        out_parts.append(f"<!-- PAGE {page_num} -->\n\n{text}")

    out_path = raw_dir / f"calvin_{args.book}_zh.md"
    out_path.write_text("\n\n".join(out_parts) + "\n", encoding="utf-8")
    print(f"[assemble] {len(pages)} pages → {out_path} ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
