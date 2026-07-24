#!/usr/bin/env python3
"""
将 mhenry/ 下所有 <div class="mh-verse">…</div> 块内的繁体经文转为简体（OpenCC t2s），
并把 OT 各章/前言里 inline `.mh-unit > .mh-verse` 的 font-family 改为以 KaiTi/楷体 为主。

NT 卷的 `.mh-verse` 样式在 `_includes/mhenry-diamond.html`，由另外步骤手工修改一次即可。

用法：
    python3 scripts/mhenry_verse_to_simplified.py --dry-run           # 全量预览
    python3 scripts/mhenry_verse_to_simplified.py --dry-run haggai    # 单卷预览
    python3 scripts/mhenry_verse_to_simplified.py haggai              # 单卷写入
    python3 scripts/mhenry_verse_to_simplified.py                     # 全量写入
"""

import argparse
import pathlib
import re
import sys

try:
    import opencc
except ImportError:
    sys.stderr.write("需要 opencc：pip install opencc-python-reimplemented\n")
    sys.exit(1)

REPO = pathlib.Path(__file__).resolve().parent.parent
MHENRY = REPO / "mhenry"

CC = opencc.OpenCC("t2s")

VERSE_BLOCK_RE = re.compile(r'(<div class="mh-verse">)(.*?)(</div>)', re.DOTALL)

# 匹配 `.mh-unit > .mh-verse { … font-family: "X", "Y", …, serif !important; … }`
# 仅替换该规则内的 font-family，不动其他规则。
VERSE_FONT_RE = re.compile(
    r'(\.mh-unit\s*>\s*\.mh-verse\s*\{[^}]*?font-family:\s*)'
    r'("[^"]+"(?:\s*,\s*"[^"]+")*\s*,\s*serif\s*!important)',
    re.DOTALL,
)

NEW_FONT = '"LXGW WenKai", "STKaiti", "KaiTi", "楷体", serif !important'


def convert_verses(text: str) -> tuple[str, int]:
    n = 0

    def _conv(m: re.Match) -> str:
        nonlocal n
        body = m.group(2)
        new_body = CC.convert(body)
        if new_body != body:
            n += 1
        return f"{m.group(1)}{new_body}{m.group(3)}"

    return VERSE_BLOCK_RE.sub(_conv, text), n


def update_font(text: str) -> tuple[str, int]:
    n = 0

    def _sub(m: re.Match) -> str:
        nonlocal n
        existing = m.group(2)
        if existing == NEW_FONT:
            return m.group(0)
        n += 1
        return f"{m.group(1)}{NEW_FONT}"

    return VERSE_FONT_RE.sub(_sub, text), n


def process_file(path: pathlib.Path, dry_run: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    new_text = text
    new_text, verses_changed = convert_verses(new_text)
    new_text, font_changed = update_font(new_text)
    if new_text != text and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return verses_changed, font_changed


def iter_targets(book_filter: list[str]) -> list[pathlib.Path]:
    if book_filter:
        roots = [MHENRY / b for b in book_filter]
        for r in roots:
            if not r.is_dir():
                sys.stderr.write(f"[warn] {r} 不存在，跳过\n")
        roots = [r for r in roots if r.is_dir()]
    else:
        roots = [d for d in MHENRY.iterdir() if d.is_dir()]
    files: list[pathlib.Path] = []
    for r in roots:
        files.extend(sorted(r.glob("*.md")))
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*", help="可选：限定 book_id（如 haggai matthew）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = iter_targets(args.books)
    total_files = 0
    total_verse_changes = 0
    total_font_changes = 0
    for f in files:
        verses, fonts = process_file(f, args.dry_run)
        if verses or fonts:
            total_files += 1
            total_verse_changes += verses
            total_font_changes += fonts
            rel = f.relative_to(REPO)
            print(f"  {rel}  verses={verses}  font={fonts}")

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(
        f"\n{mode}files changed: {total_files}, "
        f"verse blocks rewritten: {total_verse_changes}, "
        f"font-family rules updated: {total_font_changes}"
    )


if __name__ == "__main__":
    main()
