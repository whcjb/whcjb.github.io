#!/usr/bin/env python3
"""Move files in _uncategorized/ to the right book dir by re-parsing the
title line stored in each file's header (line 1: '标题：...')."""

from __future__ import annotations
import sys
from pathlib import Path

# Re-use parse_title and BOOK_KEYWORDS from fetch.py
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fetch import parse_title, OUT_DIR  # type: ignore

UNCAT = OUT_DIR / "_uncategorized"

def main():
    if not UNCAT.is_dir():
        print("no _uncategorized/ dir")
        return
    moved = 0
    still_uncat = 0
    for p in sorted(UNCAT.glob("*.txt")):
        try:
            first = p.read_text(encoding="utf-8").splitlines()[0]
        except Exception as e:
            print(f"[fail] {p.name}: {e}", file=sys.stderr)
            continue
        if not first.startswith("标题："):
            print(f"[skip] {p.name}: no title header")
            continue
        title = first[len("标题："):].strip()
        meta = parse_title(title)
        slug = meta["book_slug"]
        if slug == "_uncategorized":
            still_uncat += 1
            print(f"[unmatched] {p.name}  ←  title={title[:60]}")
            continue
        dst_dir = OUT_DIR / slug
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / p.name
        if dst.exists():
            print(f"[exists]  {dst.relative_to(OUT_DIR.parent)}  (skip move)")
            continue
        p.rename(dst)
        print(f"[ok] → {slug}/  {p.name}")
        moved += 1
    print(f"\nmoved {moved}, still uncategorized {still_uncat}")
    # If empty, remove dir
    remaining = list(UNCAT.iterdir())
    if not remaining:
        UNCAT.rmdir()
        print("removed empty _uncategorized/")

if __name__ == "__main__":
    main()
