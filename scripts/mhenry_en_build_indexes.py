#!/usr/bin/env python3
"""
mhenry_en_build_indexes.py — 为 14 个 mhenry/<book>-en/ 目录生成 index.html。

每个 index.html 使用 layout: mhenry-en-book，front matter 包含 book_id、
英文名、中文名、章节数、续写者名（从 preface.md 的"Completed by ..."行取）。
"""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

BOOKS = [
    ("galatians",       "Galatians",        "加拉太书",          6),
    ("ephesians",       "Ephesians",        "以弗所书",          6),
    ("philippians",     "Philippians",      "腓立比书",          4),
    ("colossians",      "Colossians",       "歌罗西书",          4),
    ("1thessalonians",  "1 Thessalonians",  "帖撒罗尼迦前书",     5),
    ("2thessalonians",  "2 Thessalonians",  "帖撒罗尼迦后书",     3),
    ("1timothy",        "1 Timothy",        "提摩太前书",        6),
    ("2timothy",        "2 Timothy",        "提摩太后书",        4),
    ("titus",           "Titus",            "提多书",            3),
    ("james",           "James",            "雅各书",            5),
    ("1john",           "1 John",           "约翰一书",          5),
    ("2john",           "2 John",           "约翰二书",          1),
    ("3john",           "3 John",           "约翰三书",          1),
    ("jude",            "Jude",             "犹大书",            1),
]


def get_completer(book_dir: pathlib.Path) -> str:
    preface = book_dir / "preface.md"
    if not preface.exists():
        return ""
    text = preface.read_text(encoding="utf-8")
    m = re.search(r"Completed by ([^\n]+?)\.\s*$", text, re.M)
    return f"Completed by {m.group(1).strip()}." if m else ""


def build(book_id: str, name_en: str, name_zh: str, chapters: int) -> None:
    out = REPO / "mhenry" / f"{book_id}-en"
    if not out.is_dir():
        sys.exit(f"missing book dir: {out}")
    completer = get_completer(out)
    front = [
        "---",
        "layout: mhenry-en-book",
        f"book_id: {book_id}-en",
        f'book_name_en: "{name_en}"',
        f'book_name_zh: "{name_zh}"',
        f"total_chapters: {chapters}",
    ]
    if completer:
        front.append(f'completed_by: "{completer}"')
    front += ["---", ""]
    (out / "index.html").write_text("\n".join(front), encoding="utf-8")
    print(f"  {book_id}-en/index.html  chapters={chapters}  {completer}")


def main() -> None:
    for b in BOOKS:
        build(*b)


if __name__ == "__main__":
    main()
