#!/usr/bin/env python3
"""
mhenry_en_split_pdf.py — 把 CCEL Vol 6（Acts–Revelation）按书卷拆分为 14 个单独 PDF。

源 PDF：~/Documents/论文/matthew_henry_en/mhc6_acts_revelation.pdf
输出  ：~/Documents/论文/matthew_henry_en/<book_id>.pdf

页码区间在 BOOKS 字典里硬编码，是按 mhc6_acts_revelation.pdf （1743 页）"标题页字母间空格"模式扫描得到的，
重新生成请跑 scripts/mhenry_en_locate_books.py（见 SKILL）。
"""

import pathlib
import sys

import pymupdf  # PyMuPDF

SRC = pathlib.Path.home() / "Documents/论文/matthew_henry_en/mhc6_acts_revelation.pdf"
OUT_DIR = SRC.parent

# (book_id, start_page_1_indexed, end_page_1_indexed, name_for_log)
BOOKS = [
    ("galatians",      934, 988,  "Galatians"),
    ("ephesians",      989, 1042, "Ephesians"),
    ("philippians",   1043, 1079, "Philippians"),
    ("colossians",    1080, 1112, "Colossians"),
    ("1thessalonians",1113, 1145, "1 Thessalonians"),
    ("2thessalonians",1146, 1165, "2 Thessalonians"),
    ("1timothy",      1166, 1204, "1 Timothy"),
    ("2timothy",      1205, 1233, "2 Timothy"),
    ("titus",         1234, 1269, "Titus"),
    ("james",         1399, 1448, "James"),
    ("1john",         1533, 1588, "1 John"),
    ("2john",         1589, 1595, "2 John"),
    ("3john",         1596, 1601, "3 John"),
    ("jude",          1602, 1617, "Jude"),
]


def main() -> None:
    if not SRC.exists():
        sys.exit(f"source PDF missing: {SRC}")
    src = pymupdf.open(SRC)
    n = len(src)
    print(f"source: {SRC.name}  pages: {n}")
    for book_id, start, end, name in BOOKS:
        if end > n or start < 1:
            sys.exit(f"page range out of bounds for {book_id}: {start}-{end} (PDF has {n})")
        out_path = OUT_DIR / f"{book_id}.pdf"
        new = pymupdf.open()
        new.insert_pdf(src, from_page=start - 1, to_page=end - 1)
        new.save(out_path)
        new.close()
        size_kb = out_path.stat().st_size // 1024
        print(f"  {book_id:18s} {name:18s} p{start}-{end} ({end - start + 1:3d}p)  → {out_path.name} [{size_kb} KB]")
    src.close()


if __name__ == "__main__":
    main()
