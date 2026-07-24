#!/usr/bin/env python3
"""
mhenry_en_extract_chapters.py — 把 14 卷拆分后的 PDF 抽取为按章组织的英文 markdown。

输入：~/Documents/论文/matthew_henry_en/<book_id>.pdf
输出：mhenry/<book_id>-en/
       ├─ preface.md   （CHAP. I. 之前的英文导言）
       ├─ 1.md … N.md  （每章）
       └─ index.html    （由 mhenry_en_build_indexes.py 生成）

关键模式：每章起始为单独一行 `CHAP. <Roman>.`，常常紧跟在
`<B O O K   N A M E>.` 之后；preface 是首章 marker 之前的全部正文。
每页底部有 "页码\nMatthew Henry\nCommentary on the Whole Bible Volume VI (...)"
形式的运行页脚，要剥掉。
"""

import argparse
import datetime
import pathlib
import re
import sys

import pymupdf

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = pathlib.Path.home() / "Documents/论文/matthew_henry_en"

# 用罗马数字 → 阿拉伯
ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
    "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12,
    "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17,
    "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21, "XXII": 22,
}

BOOKS = {
    "galatians":       "Galatians",
    "ephesians":       "Ephesians",
    "philippians":     "Philippians",
    "colossians":      "Colossians",
    "1thessalonians":  "1 Thessalonians",
    "2thessalonians":  "2 Thessalonians",
    "1timothy":        "1 Timothy",
    "2timothy":        "2 Timothy",
    "titus":           "Titus",
    "james":           "James",
    "1john":           "1 John",
    "2john":           "2 John",
    "3john":           "3 John",
    "jude":            "Jude",
}

BOOK_NAME_ZH = {
    "galatians":       "加拉太书",
    "ephesians":       "以弗所书",
    "philippians":     "腓立比书",
    "colossians":      "歌罗西书",
    "1thessalonians":  "帖撒罗尼迦前书",
    "2thessalonians":  "帖撒罗尼迦后书",
    "1timothy":        "提摩太前书",
    "2timothy":        "提摩太后书",
    "titus":           "提多书",
    "james":           "雅各书",
    "1john":           "约翰一书",
    "2john":           "约翰二书",
    "3john":           "约翰三书",
    "jude":            "犹大书",
}

CHAP_RE = re.compile(r"\bCHAP\.\s+([IVX]+)\.")

# 行首的"运行页脚"区块：数字单独一行 + Matthew Henry + Commentary line（可能跨行）
FOOTER_RE = re.compile(
    r"\n\s*\d+\s*\n+Matthew Henry\s*\n+Commentary on the Whole Bible Volume VI[^\n]*\n+",
)


def now_stamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def page_text(doc: pymupdf.Document, idx_1_based: int) -> str:
    return doc[idx_1_based - 1].get_text()


def get_chapter_starts(doc: pymupdf.Document) -> list[tuple[int, str, int]]:
    """
    Returns [(page_1_based, roman, char_pos_in_concat_text)] sorted by chapter number.
    char_pos is char offset inside the concatenated text we will build.
    """
    return []  # populated by build_full_text below


def build_full_text(doc: pymupdf.Document) -> tuple[str, dict[int, int]]:
    """
    Concatenate all page text with sentinel offsets. Returns:
        text: the concatenated text
        page_offsets: {page_1_based: char_offset_where_page_starts}
    """
    pieces = []
    offsets = {}
    cursor = 0
    for i in range(len(doc)):
        offsets[i + 1] = cursor
        pt = doc[i].get_text()
        pieces.append(pt)
        cursor += len(pt)
    return "".join(pieces), offsets


def split_into_chapters(full_text: str) -> dict[int, tuple[int, int]]:
    """
    Returns {chapter_num: (start_char, end_char)} based on CHAP. <Roman>. markers.
    Preface is implied to be text [0 : start_of_chap_1).
    """
    marks: list[tuple[int, int]] = []  # (start_char, chapter_num)
    for m in CHAP_RE.finditer(full_text):
        n = ROMAN.get(m.group(1))
        if n is None:
            continue
        marks.append((m.start(), n))
    if not marks:
        return {}
    bounds: dict[int, tuple[int, int]] = {}
    for i, (start, n) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(full_text)
        bounds[n] = (start, end)
    return bounds


def clean_footer(text: str) -> str:
    """Strip CCEL running footers from the text."""
    return FOOTER_RE.sub("\n\n", text)


def clean_title_repeat(text: str, book_label: str) -> str:
    """
    Drop the per-chapter `<B O O K   L A B E L>.\n` line that often precedes
    `CHAP. II.` etc. We're keeping it on the FIRST chapter for orientation, but
    inside-chapter repeats are noise.
    """
    # Build the spaced book name regex from the label
    spaced = r"\s*".join(re.escape(c) for c in book_label.upper() if c != " ")
    pat = re.compile(rf"\n{spaced}\.\s*\n+(?=CHAP\.)")
    return pat.sub("\n\n", text)


def clean_block(text: str, book_label: str) -> str:
    text = clean_footer(text)
    text = clean_title_repeat(text, book_label)
    # collapse 3+ blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def write_chapter_md(
    out_dir: pathlib.Path,
    book_id: str,
    book_name_en: str,
    book_name_zh: str,
    chapter_num: int,
    total_chapters: int,
    body: str,
) -> None:
    front = [
        "---",
        "layout: mhenry-en-chapter",
        f"book_id: {book_id}-en",
        f'book_name_en: "{book_name_en}"',
        f'book_name_zh: "{book_name_zh}"',
        f"chapter: {chapter_num}",
        f"total_chapters: {total_chapters}",
        f'title: "Chapter {chapter_num}"',
        f"date: {now_stamp()}",
        "---",
        "",
        f"# CHAPTER {chapter_num}",
        "",
    ]
    out = "\n".join(front) + body.strip() + "\n"
    (out_dir / f"{chapter_num}.md").write_text(out, encoding="utf-8")


def write_preface_md(
    out_dir: pathlib.Path,
    book_id: str,
    book_name_en: str,
    book_name_zh: str,
    total_chapters: int,
    body: str,
) -> None:
    front = [
        "---",
        "layout: mhenry-en-chapter",
        f"book_id: {book_id}-en",
        f'book_name_en: "{book_name_en}"',
        f'book_name_zh: "{book_name_zh}"',
        f"total_chapters: {total_chapters}",
        "is_preface: true",
        f'title: "Preface"',
        f"date: {now_stamp()}",
        "---",
        "",
        f"# {book_name_en}",
        "",
        "_An Exposition, with Practical Observations, by Matthew Henry — completed by his ministerial colleagues._",
        "",
    ]
    out = "\n".join(front) + body.strip() + "\n"
    (out_dir / "preface.md").write_text(out, encoding="utf-8")


def process_book(book_id: str, book_name_en: str, book_name_zh: str) -> None:
    pdf = SRC_DIR / f"{book_id}.pdf"
    if not pdf.exists():
        sys.exit(f"missing split PDF: {pdf}")
    doc = pymupdf.open(pdf)
    text, _ = build_full_text(doc)
    bounds = split_into_chapters(text)
    if not bounds:
        sys.exit(f"no CHAP. markers found in {pdf}")

    total = max(bounds)
    out_dir = REPO / "mhenry" / f"{book_id}-en"
    out_dir.mkdir(parents=True, exist_ok=True)

    first_start = min(s for s, _ in bounds.values())
    preface_body = clean_block(text[:first_start], book_name_en)
    write_preface_md(out_dir, book_id, book_name_en, book_name_zh, total, preface_body)

    for n in sorted(bounds):
        s, e = bounds[n]
        body = clean_block(text[s:e], book_name_en)
        write_chapter_md(
            out_dir, book_id, book_name_en, book_name_zh,
            chapter_num=n, total_chapters=total, body=body,
        )

    print(f"  {book_id:18s} → {out_dir.relative_to(REPO)}/  preface + {total} chapters")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*", help="可选 book_id 子集，缺省=全部 14 卷")
    args = ap.parse_args()
    targets = args.books or list(BOOKS.keys())
    for bid in targets:
        if bid not in BOOKS:
            sys.exit(f"unknown book_id: {bid}")
        process_book(bid, BOOKS[bid], BOOK_NAME_ZH[bid])


if __name__ == "__main__":
    main()
