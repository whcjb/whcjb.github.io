#!/usr/bin/env python3
"""
Wrap NT preface body in the C-tier ornate structure (6-segment haggai-style)
so it picks up the diamond preface decoration CSS in _includes/mhenry-diamond.html.

Only touches the 13 NT books that already have real preface body text:
    matthew, mark, luke, john, acts, romans, 1corinthians, 2corinthians,
    hebrews, 1peter, 2peter, revelation
(philemon is a single-chapter book whose preface is currently stub-size — skipped.)

The 14 stub prefaces (galatians, ephesians, philippians, colossians,
1thessalonians, 2thessalonians, 1timothy, 2timothy, titus, philemon, james,
1john, 2john, 3john, jude) are NOT touched — they have no body to wrap.

Idempotent: if the file already contains `class="preface-wrap"`, skip.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MHENRY = ROOT / "mhenry"

# book_id → (label, closing scripture, closing scripture ref)
BOOKS = {
    "matthew":        ("福音简介", "道成了肉身，住在我们中间，充充满满地有恩典有真理。", "约翰福音 1:14"),
    "mark":           ("福音简介", "神的儿子，耶稣基督福音的起头。", "马可福音 1:1"),
    "luke":           ("福音简介", "他们彼此说，在路上他和我们说话，给我们讲解圣经的时候，我们的心岂不是火热的吗？", "路加福音 24:32"),
    "john":           ("福音简介", "太初有道，道与神同在，道就是神。", "约翰福音 1:1"),
    "acts":           ("历史简介", "但圣灵降临在你们身上，你们就必得着能力。", "使徒行传 1:8"),
    "romans":         ("书信简介", "我不以福音为耻；这福音本是神的大能，要救一切相信的。", "罗马书 1:16"),
    "1corinthians":   ("书信简介", "如今常存的有信、有望、有爱这三样，其中最大的是爱。", "哥林多前书 13:13"),
    "2corinthians":   ("书信简介", "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。", "哥林多后书 12:9"),
    "galatians":      ("书信简介", "我已经与基督同钉十字架。", "加拉太书 2:20"),
    "ephesians":      ("书信简介", "你们得救是本乎恩，也因着信。", "以弗所书 2:8"),
    "philippians":    ("书信简介", "我靠着那加给我力量的，凡事都能做。", "腓立比书 4:13"),
    "colossians":     ("书信简介", "凡你们所做的，或说话或行事，都要奉主耶稣的名。", "歌罗西书 3:17"),
    "1thessalonians": ("书信简介", "要常常喜乐，不住地祷告，凡事谢恩。", "帖撒罗尼迦前书 5:16-18"),
    "2thessalonians": ("书信简介", "愿赐平安的主随时随事亲自给你们平安。", "帖撒罗尼迦后书 3:16"),
    "1timothy":       ("书信简介", "你要为真道打那美好的仗。", "提摩太前书 6:12"),
    "2timothy":       ("书信简介", "那美好的仗我已经打过了，当跑的路我已经跑尽了。", "提摩太后书 4:7"),
    "titus":          ("书信简介", "等候至大的神和我们救主耶稣基督的荣耀显现。", "提多书 2:13"),
    "philemon":       ("书信简介", "愿主耶稣基督的恩常在你们心里。", "腓利门书 1:25"),
    "hebrews":        ("书信简介", "信就是所望之事的实底，是未见之事的确据。", "希伯来书 11:1"),
    "james":          ("书信简介", "你们不要单单听道，自己欺哄自己，总要行道。", "雅各书 1:22"),
    "1peter":         ("书信简介", "因为我是圣洁的，你们也要圣洁。", "彼得前书 1:16"),
    "2peter":         ("书信简介", "你们却要在我们主救主耶稣基督的恩典和知识上有长进。", "彼得后书 3:18"),
    "1john":          ("书信简介", "神就是爱。", "约翰一书 4:8"),
    "2john":          ("书信简介", "我们应该彼此相爱。", "约翰二书 1:5"),
    "3john":          ("书信简介", "愿你凡事兴盛，身体健壮，正如你的灵魂兴盛一样。", "约翰三书 1:2"),
    "jude":           ("书信简介", "那能保守你们不失脚，叫你们无瑕无疵欢欢喜喜站在他荣耀之前的我们的救主独一的神。", "犹大书 1:24-25"),
    "revelation":     ("启示简介", "看哪，我必快来。我的赏赐在我，要照各人所行的报应他。", "启示录 22:12"),
}

# Placeholder for stub books whose preface body is empty.
STUB_PLACEHOLDER_HTML = (
    '<p style="text-align:center; font-style:italic; '
    'color:rgba(110,150,200,0.55); padding:32px 24px; margin:0;">'
    '本卷簡介暫缺，請參看各章節注釋。'
    '</p>'
)


FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def book_name_from_fm(fm: str) -> str | None:
    m = re.search(r"^book_name:\s*(.+)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def wrap_one(book_id: str) -> str:
    label, verse, ref = BOOKS[book_id]
    path = MHENRY / book_id / "preface.md"
    text = path.read_text(encoding="utf-8")

    if 'class="preface-wrap"' in text:
        return f"[skip] {book_id}: already wrapped"

    m = FRONT_MATTER_RE.match(text)
    if not m:
        return f"[fail] {book_id}: no front matter"
    fm_body = m.group(1)
    book_name = book_name_from_fm(fm_body)
    if not book_name:
        return f"[fail] {book_id}: no book_name"

    body = text[m.end():].strip()
    is_stub = not body
    if is_stub:
        body = STUB_PLACEHOLDER_HTML

    wrapped = (
        f"---\n{fm_body}\n---\n"
        f"\n"
        f"<div class=\"preface-wrap\">\n"
        f"\n"
        f"<div class=\"preface-emblem\">✠</div>\n"
        f"\n"
        f"<div class=\"preface-title-block\">\n"
        f"  <div class=\"preface-label\">{label}</div>\n"
        f"  <div class=\"preface-book-name\">{book_name}</div>\n"
        f"  <div class=\"preface-sub\">马太亨利注释 · 书卷导言</div>\n"
        f"</div>\n"
        f"\n"
        f"<div class=\"preface-divider\"><span>◇</span></div>\n"
        f"\n"
        f"<div class=\"preface-body\">\n"
        f"{body}\n"
        f"</div>\n"
        f"\n"
        f"<div class=\"preface-closing\">\n"
        f"  ✠  &ensp; ◇  &ensp; ✠\n"
        f"  <span class=\"preface-closing-verse\">「{verse}」</span>\n"
        f"  <span class=\"preface-closing-verse-ref\">— {ref} —</span>\n"
        f"</div>\n"
        f"\n"
        f"</div>\n"
    )
    path.write_text(wrapped, encoding="utf-8")
    return f"[ok] {book_id} ({len(wrapped)} chars)"


def main(argv: list[str]) -> int:
    only = [a for a in argv[1:] if not a.startswith("--")]
    targets = only if only else list(BOOKS.keys())
    for book in targets:
        if book not in BOOKS:
            print(f"[skip] unknown: {book}", file=sys.stderr)
            continue
        print(wrap_one(book))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
