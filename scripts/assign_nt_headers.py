#!/usr/bin/env python3
"""
Assign a unique landscape header image to every NT preface / chapter / book-index page.

Image pool (NT-exclusive, downloaded from Unsplash 2026-06):
    nt-bg-001.jpg … nt-bg-132.jpg                     (132)

The old OT pool (mhenry-land-* / psalm-bg-*) is *not* used by NT — OT and NT
keep distinct image sets so themes don't leak across testaments.

Assignment strategy (deterministic, idempotent):
    book_offset = sha1(book_id) % POOL_SIZE
    chapter k of book b → POOL[ (book_offset + k) % POOL_SIZE ]
    preface              → POOL[ (book_offset + 0)  % POOL_SIZE ]
    index.html           → POOL[ (book_offset + 1)  % POOL_SIZE ]
    1.md                 → POOL[ (book_offset + 2)  % POOL_SIZE ]
    2.md                 → POOL[ (book_offset + 3)  % POOL_SIZE ]
    …

Touches only files with `book_id:` in the front matter and only those whose
book_id is one of the 27 NT books. Idempotent: re-running with the same pool
produces identical output.
"""

from __future__ import annotations
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"
IMG_DIR = ROOT / "img"

NT_BOOKS = [
    "matthew", "mark", "luke", "john", "acts",
    "romans", "1corinthians", "2corinthians", "galatians", "ephesians",
    "philippians", "colossians", "1thessalonians", "2thessalonians",
    "1timothy", "2timothy", "titus", "philemon",
    "hebrews", "james",
    "1peter", "2peter", "1john", "2john", "3john", "jude",
    "revelation",
]


def build_pool() -> list[str]:
    pool: list[str] = []
    for i in range(1, 200):                       # nt-bg-001 ..
        name = f"nt-bg-{i:03d}.jpg"
        if (IMG_DIR / name).exists():
            pool.append(name)
    return pool


def book_offset(book_id: str, pool_size: int) -> int:
    h = hashlib.sha1(book_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % pool_size


def chapter_num(path: Path) -> int:
    """preface → 0, index.html → 1, N.md → N+1."""
    name = path.name
    if name == "preface.md":
        return 0
    if name == "index.html":
        return 1
    m = re.match(r"^(\d+)\.md$", name)
    if not m:
        return -1
    return int(m.group(1)) + 1


def update_header(path: Path, new_img: str) -> bool:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return False
    fm = m.group(1)
    if not re.search(r"^book_id:", fm, re.MULTILINE):
        return False
    book_id_m = re.search(r"^book_id:\s*(\S+)", fm, re.MULTILINE)
    if not book_id_m or book_id_m.group(1) not in NT_BOOKS:
        return False

    if re.search(r"^header-img:\s*", fm, re.MULTILINE):
        new_fm = re.sub(
            r"^header-img:.*$", f"header-img: {new_img}", fm, count=1, flags=re.MULTILINE
        )
    else:
        new_fm = fm + f"\nheader-img: {new_img}"
    new_text = text.replace(f"---\n{fm}\n---", f"---\n{new_fm}\n---", 1)
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv

    pool = build_pool()
    if not pool:
        print("[fail] empty image pool", file=sys.stderr)
        return 1
    print(f"[info] image pool size: {len(pool)}")

    total = 0
    changed = 0
    by_book: dict[str, list[tuple[Path, str]]] = {b: [] for b in NT_BOOKS}

    for book in NT_BOOKS:
        bdir = MHENRY / book
        if not bdir.is_dir():
            continue
        off = book_offset(book, len(pool))
        files: list[Path] = []
        if (bdir / "preface.md").exists():
            files.append(bdir / "preface.md")
        if (bdir / "index.html").exists():
            files.append(bdir / "index.html")
        chapter_files = sorted(
            (p for p in bdir.glob("*.md") if re.match(r"^\d+\.md$", p.name)),
            key=lambda p: int(p.stem),
        )
        files.extend(chapter_files)

        for f in files:
            slot = chapter_num(f)
            if slot < 0:
                continue
            img = pool[(off + slot) % len(pool)]
            by_book[book].append((f, img))
            total += 1
            if dry:
                continue
            if update_header(f, img):
                changed += 1

    if dry:
        for book, pairs in by_book.items():
            if not pairs:
                continue
            print(f"\n=== {book} (offset={book_offset(book, len(pool))}) ===")
            for p, img in pairs:
                print(f"  {p.relative_to(ROOT)} → {img}")
        print(f"\n[dry-run] would touch {total} files")
    else:
        print(f"[ok] processed {total} files, updated {changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
