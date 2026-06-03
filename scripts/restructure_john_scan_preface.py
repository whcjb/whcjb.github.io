#!/usr/bin/env python3
"""Restructure calvin/john-scan/preface.md — matches ch1 quality.

Applies the full ch1 cleaning pipeline to preface pages (1-12):
- Strip running headers + page numbers + `---` HRs
- Per-page footnote extraction → kramdown `[^N]: text` at end
- Inline circled-digit refs → kramdown `[^N]` (per-page local→global)
- Strip bare-digit prefixes
- Cross-page mid-sentence join
- Verse-opener promotion is skipped (no verses in preface)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Reuse ch1's pipeline pieces.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from restructure_john_scan_ch1 import (
    process_page, _join_cross_page, _TERM_PUNCT,
)


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
PREFACE_PAGE_RANGE = (1, 12)


def build_preface_md() -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        'book_id: john-scan\n'
        'book_name: "约翰福音（扫描版）"\n'
        "chapter: 0\n"
        "header-img: psalm-bg-mountain.jpg\n"
        'title: "序言"\n'
        "date: 2026-06-03 18:00\n"
        'next_section: 1\n'
        'next_label: "第一章"\n'
        "---\n\n"
    )

    body_parts: list[str] = []
    all_defs: list[tuple[int, str]] = []
    fn_counter = 0
    # Use a deliberately wide "verse_range" None so the verse-opener promote
    # step is a no-op for preface. process_page still runs all other steps
    # (running-header strip, fn extract, circled-digit refs, etc.).
    for p in range(PREFACE_PAGE_RANGE[0], PREFACE_PAGE_RANGE[1] + 1):
        f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        body, defs, fn_counter = process_page(
            f.read_text(encoding="utf-8"), fn_counter, None
        )
        if not body:
            all_defs.extend(defs)
            continue
        if body_parts:
            merged_prev, body = _join_cross_page(body_parts[-1], body)
            body_parts[-1] = merged_prev
        if body:
            body_parts.append(body)
        all_defs.extend(defs)

    body_md = "\n\n".join(p for p in body_parts if p)

    out = [fm, body_md, ""]
    if all_defs:
        out.append("")
        for gid, text in all_defs:
            out.append(f"[^{gid}]: {text}")
            out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    out_path = REPO / "calvin/john-scan/preface.md"
    content = build_preface_md()
    out_path.write_text(content, encoding="utf-8")
    n_fn = content.count("\n[^")
    n_h1 = content.count("\n# ")
    n_h2 = content.count("\n## ")
    print(f"wrote {out_path} ({len(content):,} chars)")
    print(f"  h1: {n_h1}  h2: {n_h2}  fn refs+defs: {n_fn}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
