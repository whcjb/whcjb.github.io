#!/usr/bin/env python3
"""Restructure calvin/john-scan/1.md to match calvin/john-en/1.md layout.

Targets every check in pdf-pipeline:refs:audit-gates:
  - Gate 1: no ****, <<<END, split italics
  - Gate 5: footnote refs/defs paired in kramdown `[^N]` / `[^N]: text` form
  - Gate 6: no paragraph > 1500 chars
  - Plus scripture-anchor h2 before each scripture-box for verse-nav JS
  - Plus drops the manual `## 脚注` heading (kramdown auto-renders fn section)

Reads:
  - assets/cuv.json (clean CUV Chinese Bible text)
  - calvin_raw/john-scan/ocr/page_NNNN.md (per-page OCR)

Writes:
  - calvin/john-scan/1.md
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
CUV = json.load(open(REPO / "assets/cuv.json"))
JOHN_1 = CUV["43"]["1"]


# 6 scripture-box sections — page ranges match Calvin's commentary structure.
# Content-aligned page ranges — boundaries chosen by locating the first
# OCR page on which each section's lead-verse commentary opener begins:
#   v6  「有一个人」     → page 25
#   v14 「道成了肉身」  → page 33
#   v19 「约翰所作的见证 / 问。」  → page 44 (verse opener for v19 about priest inquiry)
#   v29 「看哪，神的羔羊」 → page 49
#   v35 「再次日，约翰同两个门徒」 → page 56
SECTIONS = [
    {"verses": (1, 5),   "title": "太初有道、生命与光",                  "pages": (16, 24)},
    {"verses": (6, 13),  "title": "施洗约翰为光作见证；信子者得作神的儿女",  "pages": (25, 32)},
    {"verses": (14, 18), "title": "道成了肉身；从他丰满的恩典里我们都领受了", "pages": (33, 43)},
    {"verses": (19, 28), "title": "约翰回答祭司：我不是基督",              "pages": (44, 48)},
    {"verses": (29, 34), "title": "看哪，神的羔羊！圣灵仿佛鸽子降下",        "pages": (49, 55)},
    {"verses": (35, 51), "title": "首批门徒；耶稣呼召拿但业",                "pages": (56, 65)},
]


_CIRCLE_DIGITS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
_CIRCLE_TO_INT: dict[str, int] = {}
for i, ch in enumerate(_CIRCLE_DIGITS, 1):
    _CIRCLE_TO_INT[ch] = i


def _strip_leading_circle(s: str) -> str:
    s = s.lstrip()
    while s and s[0] in _CIRCLE_TO_INT:
        s = s[1:].lstrip()
    return s


# ────────────────────────────────────────────────────────────────────────
# Bible verse scripture-box (one per section, with hidden anchor h2)
# ────────────────────────────────────────────────────────────────────────

def scripture_block(verses_range: tuple[int, int]) -> str:
    a, b = verses_range
    ref = f"约翰福音 1:{a}-{b}"
    anchor_id = f"john-1-{a}-{b}"
    inner = "".join(f"<strong>{v}.</strong>{JOHN_1[str(v)]}" for v in range(a, b + 1))
    return (
        f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref}" style="display:none">{ref}</h2>\n\n'
        f'<div class="scripture-box" markdown="1">\n'
        f'<p class="scripture-ref">{ref}</p>\n\n'
        f'<p>{inner}</p>\n\n'
        f'</div>\n'
    )


# ────────────────────────────────────────────────────────────────────────
# Per-page: identify footnote defs, build local circled→global map
# ────────────────────────────────────────────────────────────────────────

RUNNING_HDR_PATTERNS = [
    re.compile(r"^#\s*加尔文文集.*约翰福音注释\s*$"),
    re.compile(r"^#\s*约翰福音注释\s*$"),
    re.compile(r"^#\s*第[一二三四五六七八九十百零〇0-9]+\s*章\s*\*?\s*$"),
    re.compile(r"^\d{1,3}\s*$"),
    # Horizontal rules — the PDF often has a separator line between body
    # and footnote section, OCR'd as `---`. Strip these so they don't
    # leak into body text or block cross-page paragraph joining.
    re.compile(r"^-{3,}\s*$"),
    re.compile(r"^—{3,}\s*$"),  # em-dash variant
]

_FN_DEF_RE = re.compile(r"^([" + _CIRCLE_DIGITS + r"])[ 　](.+)$")


def find_john_verse(opener_text: str, chapter_verses: dict[str, str]) -> int | None:
    head = _strip_leading_circle(opener_text)
    head = re.sub(r"[，。、；：（）\s]", "", head)[:8]
    if not head:
        return None
    for vstr, text in chapter_verses.items():
        ct = re.sub(r"[，。、；：（）　\s]", "", text)
        if ct.startswith(head):
            return int(vstr)
    return None


def fix_inline_h2(line: str, john_1: dict[str, str]) -> str:
    """OCR sometimes puts the verse-opener line as `## XXX...` (a long h2).
    Convert to verse-anchor bold form for verse-nav JS pickup.
    """
    if not line.startswith("## "):
        return line
    content = line[3:].strip()
    if len(content) <= 40:
        return line
    period = content.find("。")
    if period == -1 or period > 60:
        opener, rest = content[:30], content[30:]
    else:
        opener, rest = content[: period + 1], content[period + 1 :]
    v = find_john_verse(opener, john_1)
    opener_clean = _strip_leading_circle(opener)
    if v is not None:
        return f"**约翰福音 1:{v}。** *{opener_clean}* {rest}"
    return f"**{opener_clean}** {rest}"


_NOISE_CHARS_RE = re.compile(r"[，。、；：（）！？「」『』　\s\"“”'‘’·‧·…]")


def _normalize_for_match(s: str) -> str:
    """Normalize Chinese text for fuzzy matching between OCR and CUV.
    - Strip noise chars (punctuation, whitespace, middle dots)
    - Unify 上帝 ↔ 神 (Calvin uses 上帝, CUV uses 神; treat as equivalent)
    """
    s = _NOISE_CHARS_RE.sub("", s)
    s = s.replace("上帝", "神")
    return s


def _strip_corrupt_marker(para: str) -> str:
    """Strip OCR-corrupted verse markers from paragraph start.

    Patterns seen:
      ①太初有道 ...               (single circled digit, valid)
      ⑤0耶稣对他说 ...             (㊿ rendered as ⑤0)
      ⑤1你们将要 ...               (verse 51 rendered as ⑤1)
      0耶稣对他说 ...               (leading bare digit)
      1你们将要 ...
    """
    p = para
    # Drop one circled digit + optional 0-9 digits (e.g. ⑤0, ⑤1)
    if p and p[0] in _CIRCLE_TO_INT:
        p = p[1:]
        while p and p[0].isdigit():
            p = p[1:]
        return p.lstrip()
    # Drop leading bare 0-9 digit (corrupt marker like "0耶稣" "1你们")
    if p and p[0].isdigit() and len(p) > 1 and not p[1].isdigit():
        return p[1:].lstrip()
    return p


def _split_first_sentence(text: str) -> tuple[str, str]:
    """Return (first_sentence, rest). The first sentence ends at the first
    of 。？！, or includes up to first 30 chars if no terminator.
    """
    m = re.search(r"[。？！]", text)
    if m and m.start() <= 30:
        return text[: m.start() + 1], text[m.start() + 1 :]
    return text[:30], text[30:]


def _verse_for_opener(opener_clean: str, john_1: dict[str, str],
                       verse_range: tuple[int, int] | None = None) -> int | None:
    """Find verse whose text contains opener_clean as substring.

    opener_clean is expected to have been already passed through
    `_normalize_for_match`. CUV verse texts are normalized on the fly.

    If `verse_range` is given (e.g. (35, 51) for section 6), only verses
    in that range are considered.

    Tries the full opener first; if no match, progressively shortens
    from the right (removes one CJK char at a time, min 4 chars) to
    accommodate cases where Calvin uses an alternative transliteration
    (e.g. "伯大巴喇" vs CUV "伯大尼") — the shared prefix
    「这是在约旦河外」 still matches.
    """
    min_len = 2 if verse_range else 3
    if len(opener_clean) < min_len:
        return None

    candidates = [opener_clean]
    # Shorter prefixes (longest first) — try down to 4 chars or min_len.
    cutoff = max(min_len, 4)
    for n in range(len(opener_clean) - 1, cutoff - 1, -1):
        candidates.append(opener_clean[:n])

    for opener in candidates:
        matches: list[int] = []
        for vstr, text in john_1.items():
            v = int(vstr)
            if verse_range is not None and not (verse_range[0] <= v <= verse_range[1]):
                continue
            if opener in _normalize_for_match(text):
                matches.append(v)
        if not matches:
            continue
        if len(matches) == 1:
            return matches[0]
        threshold = 2 if verse_range else 3
        if len(opener) >= threshold:
            return min(matches)
    return None


def _maybe_match_elided(body: str, john_1: dict[str, str],
                         verse_range: tuple[int, int] | None) -> int | None:
    """Handle Calvin's elided citations like '我们遇见了……耶稣。'.

    Split on `……` (ellipsis) and try to match the first chunk.
    """
    if "……" not in body[:30] and "…" not in body[:30]:
        return None
    head = re.split(r"…+", body[:30])[0]
    head_clean = _normalize_for_match(head)
    if len(head_clean) >= 3:
        return _verse_for_opener(head_clean, john_1, verse_range)
    return None


# OCR pattern: `**N、opener。** rest` (bold-wrapped) OR
# `N、opener。 rest` (no bold) — both have explicit verse number N + 、/./, +
# opener phrase. Galatians OCR sometimes wraps with **, sometimes not.
# We recognize either form and rewrite directly without needing CUV fuzzy
# match (verse number is given by N).
_BOLD_VERSE_OPENER_RE = re.compile(
    r"^\*\*\s*(\d{1,3})\s*[、.,]\s*([^\*]+?)\s*\*\*\s*(.*)$",
    re.DOTALL,
)
_BARE_VERSE_OPENER_RE = re.compile(
    r"^(\d{1,3})[、.,]\s*([^。？！]{2,40}[。？！])\s*(.*)$",
    re.DOTALL,
)
# OCR pattern: `**phrase（N）** rest` (Ephesians scan style) — verse N is
# embedded as parenthetical at the end of the bold lemma. Accepts both
# full-width `（N）` and half-width `(N)` (OCR sometimes flips them, cf.
# `**藉祂的血得蒙救贖(7)**`).
_PAREN_VERSE_OPENER_RE = re.compile(
    r"^\*\*\s*([^\*\n（(]+?)\s*[（(]\s*(\d{1,3})\s*[)）]\s*\*\*\s*(.*)$",
    re.DOTALL,
)


def maybe_promote_verse_opener(para: str, john_1: dict[str, str],
                                 verse_range: tuple[int, int] | None = None,
                                 book_cn: str = "约翰福音",
                                 chapter: int = 1) -> str:
    """Detect a paragraph opening with a verse quote → rewrite as
    `**{book_cn} {ch}:N。** *quote。* commentary` for verse-nav JS pickup.

    Forms recognized:
      1) `**N、phrase。** rest`  (OCR bold-wrapped, verse N explicit)
      2) `①phrase。 rest`        (leading circled digit, fuzzy match)
      3) `phrase。 rest`          (no marker, fuzzy match to CUV)

    `verse_range` (lo, hi): only accept v in range (disambiguates short
    openers like '拉比').
    """
    if not para or para.startswith("[^"):
        return para
    # Already in promoted form — skip
    if re.match(rf"^\*\*{re.escape(book_cn)} \d+:\d+。\*\*", para):
        return para
    if len(para) < 12:
        return para

    # Form 1: `**N、phrase。** rest` — bold-wrapped, verse N explicit
    m = _BOLD_VERSE_OPENER_RE.match(para)
    if m:
        n_str, opener, rest = m.group(1), m.group(2).strip(), m.group(3).lstrip()
        v = int(n_str)
        max_v = len(john_1)
        if 1 <= v <= max_v and (verse_range is None or
                                  verse_range[0] <= v <= verse_range[1]):
            return f"**{book_cn} {chapter}:{v}。** *{opener}。* {rest}".rstrip()

    # Form 1.5: `**phrase（N）** rest` — bold lemma with verse N in parens
    # at end. Ephesians scan-OCR style.
    m = _PAREN_VERSE_OPENER_RE.match(para)
    if m:
        opener, n_str, rest = m.group(1).strip(), m.group(2), m.group(3).lstrip()
        v = int(n_str)
        max_v = len(john_1)
        if 1 <= v <= max_v and (verse_range is None or
                                  verse_range[0] <= v <= verse_range[1]):
            return f"**{book_cn} {chapter}:{v}。** *{opener}* {rest}".rstrip()

    # Form 2: `N、phrase。 rest` — no bold, but explicit N + 、/./, + phrase
    m = _BARE_VERSE_OPENER_RE.match(para)
    if m:
        n_str, opener_with_punct, rest = m.group(1), m.group(2).strip(), m.group(3).lstrip()
        v = int(n_str)
        max_v = len(john_1)
        if 1 <= v <= max_v and (verse_range is None or
                                  verse_range[0] <= v <= verse_range[1]):
            return f"**{book_cn} {chapter}:{v}。** *{opener_with_punct}* {rest}".rstrip()

    body = _strip_corrupt_marker(para)
    first_sent, rest = _split_first_sentence(body)
    first_clean = _normalize_for_match(first_sent)

    v = _verse_for_opener(first_clean, john_1, verse_range)
    if v is None:
        # Try elided form (Calvin's `X……Y。` quoted)
        v = _maybe_match_elided(body, john_1, verse_range)
    if v is None:
        body_clean = _normalize_for_match(body)[:10]
        if len(body_clean) >= 4:
            v = _verse_for_opener(body_clean, john_1, verse_range)
    if v is None:
        return para

    return f"**{book_cn} {chapter}:{v}。** *{first_sent}* {rest}".rstrip()


# ────────────────────────────────────────────────────────────────────────
# Page-level processing with fn mapping
# ────────────────────────────────────────────────────────────────────────

def process_page(text: str, fn_counter: int,
                  verse_range: tuple[int, int] | None = None,
                  book_cn: str = "约翰福音",
                  chapter: int = 1) -> tuple[str, list[tuple[int, str]], int]:
    """Process one OCR'd page.

    Returns:
      body_md - body text with `[^N]` kramdown refs in place of `①②③`
      fn_defs - list of (global_id, text) tuples for this page's footnotes
      next_counter - updated global fn counter

    Strategy:
      1) Normalize lines (drop running headers, transform long `## ` lines).
      2) Promote verse-opener paragraphs (restricted to `verse_range` if set).
      3) Extract footnote def paragraphs (split multi-line concat blocks).
      4) Assign sequential global IDs to defs.
      5) In remaining body, replace circled digits with `[^N]` refs using
         per-page-local→global mapping.
    """
    # Step 1: line-level normalization
    out_lines: list[str] = []
    for line in text.splitlines():
        if any(p.match(line.rstrip()) for p in RUNNING_HDR_PATTERNS):
            continue
        out_lines.append(fix_inline_h2(line.rstrip(), JOHN_1))
    text2 = re.sub(r"\n{3,}", "\n\n", "\n".join(out_lines)).strip()

    # Step 2-3: paragraph promote + fn extract
    paras = re.split(r"\n{2,}", text2)
    body_paras: list[str] = []
    fn_defs: list[tuple[int, str]] = []      # (global_id, text)
    local_to_global: dict[int, int] = {}     # page-local fn number → global id

    for p in paras:
        if not p:
            continue
        promoted = maybe_promote_verse_opener(p, JOHN_1, verse_range, book_cn, chapter)
        if promoted != p or promoted.startswith("**约翰福音"):
            body_paras.append(promoted)
            continue
        # Check if it's a footnote-def block
        first = p.splitlines()[0]
        m = _FN_DEF_RE.match(first)
        if not m:
            body_paras.append(p)
            continue
        # Multi-line fn block: split each line that starts with circled digit
        cur_lines: list[str] = []
        cur_local: int | None = None
        for line in p.splitlines():
            mline = _FN_DEF_RE.match(line)
            if mline:
                if cur_lines and cur_local is not None:
                    fn_counter += 1
                    local_to_global[cur_local] = fn_counter
                    fn_defs.append((fn_counter, " ".join(cur_lines).strip()))
                circ = mline.group(1)
                cur_local = _CIRCLE_TO_INT[circ]
                cur_lines = [mline.group(2)]
            else:
                cur_lines.append(line.strip())
        if cur_lines and cur_local is not None:
            fn_counter += 1
            local_to_global[cur_local] = fn_counter
            fn_defs.append((fn_counter, " ".join(cur_lines).strip()))

    body = "\n\n".join(body_paras)

    # Step 5: replace inline circled digits in body with `[^N]` refs.
    # We process digits in descending order so larger numbers don't
    # accidentally match a substring of smaller ones (though circled
    # digits are single Unicode chars, this is just defensive).
    def replace_circle(ch: str) -> str:
        local = _CIRCLE_TO_INT.get(ch)
        if local is None:
            return ch
        g = local_to_global.get(local)
        if g is None:
            # Orphan ref — no matching def on this page. Strip.
            return ""
        return f"[^{g}]"

    body = "".join(replace_circle(c) if c in _CIRCLE_TO_INT else c for c in body)

    return body, fn_defs, fn_counter


_TERM_PUNCT = "。？！」』\""


def _join_cross_page(prev: str, cur: str) -> tuple[str, str]:
    """If prev page ends mid-sentence (no terminal punctuation on last
    paragraph) and cur page starts with a non-marker, non-footnote, non-
    promoted continuation, merge prev's last paragraph with cur's first
    paragraph.
    """
    if not prev or not cur:
        return prev, cur
    prev_paras = re.split(r"\n{2,}", prev)
    cur_paras = re.split(r"\n{2,}", cur)
    if not prev_paras or not cur_paras:
        return prev, cur
    last = prev_paras[-1].rstrip()
    first = cur_paras[0].lstrip()
    if not last or not first:
        return prev, cur
    # Skip if last already ends with terminal punctuation
    if last[-1] in _TERM_PUNCT:
        return prev, cur
    # Skip if first paragraph is a promoted opener, anchor, fn def, scripture-box
    if (first.startswith("**约翰福音")
            or first.startswith("<")
            or first.startswith("[^")
            or first.startswith("# ")
            or first.startswith("## ")):
        return prev, cur
    # Skip if first starts with a circled digit (likely a new section/fn)
    if first[0] in _CIRCLE_TO_INT:
        return prev, cur
    # Merge: append first to last
    prev_paras[-1] = last + first
    cur_paras = cur_paras[1:]
    return "\n\n".join(prev_paras), "\n\n".join(cur_paras)


def load_pages(start: int, end: int, fn_counter: int,
                verse_range: tuple[int, int] | None = None) -> tuple[str, list[tuple[int, str]], int]:
    body_parts: list[str] = []
    all_defs: list[tuple[int, str]] = []
    for p in range(start, end + 1):
        f = REPO / f"calvin_raw/john-scan/ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        body, defs, fn_counter = process_page(
            f.read_text(encoding="utf-8"), fn_counter, verse_range
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
    return "\n\n".join(p for p in body_parts if p), all_defs, fn_counter


# ────────────────────────────────────────────────────────────────────────
# Long-paragraph splitting (Gate 6)
# ────────────────────────────────────────────────────────────────────────

def split_long_paragraphs(text: str, max_len: int = 1400) -> str:
    """Split paragraphs longer than max_len at sentence boundaries (。).

    Targets pdf-pipeline Gate 6: no line > 1500 chars (we use 1400 as a
    safer threshold).
    """
    paras = re.split(r"\n{2,}", text)
    out: list[str] = []
    for p in paras:
        if len(p) <= max_len or "\n" in p.strip():
            out.append(p)
            continue
        # Split into sentences keeping the 。 attached.
        sentences = re.split(r"(?<=。)", p)
        chunks: list[str] = []
        cur = ""
        for s in sentences:
            if len(cur) + len(s) > max_len and cur:
                chunks.append(cur)
                cur = s
            else:
                cur += s
        if cur:
            chunks.append(cur)
        out.extend(chunks)
    return "\n\n".join(out)


# ────────────────────────────────────────────────────────────────────────
# Main assemble
# ────────────────────────────────────────────────────────────────────────

def _is_section_continuation(prev_last: str, cur_first: str) -> bool:
    """True iff the previous section ends mid-sentence (no terminator) and
    the current section's first paragraph is plain prose (not a verse
    opener, anchor, scripture-box, fn def, heading). Covers cases like
    `...可以说是满` + `满地赐下，使我们都得以饱足...` split across the
    section 3 (page 39) → section 4 (page 40) boundary.
    """
    if not prev_last or not cur_first:
        return False
    if prev_last[-1] in _TERM_PUNCT:
        return False
    if (cur_first.startswith("**约翰福音")
            or cur_first.startswith("<")
            or cur_first.startswith("[^")
            or cur_first.startswith("#")):
        return False
    # First char must be a CJK character (typical mid-sentence start)
    if not ("一" <= cur_first[0] <= "鿿"):
        return False
    return True


def build_chapter_md() -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        'book_id: john-scan\n'
        'book_name: "约翰福音（扫描版）"\n'
        "chapter: 1\n"
        "header-img: psalm-bg-mountain.jpg\n"
        f"date: {_now()}\n"
        'prev_section: preface\n'
        'prev_label: "序言"\n'
        'next_section: 2\n'
        'next_label: "第二章"\n'
        "---\n\n"
    )
    body = ["# 约翰福音 1 —— 道成肉身\n"]
    all_defs: list[tuple[int, str]] = []
    fn_counter = 0
    # Two-pass: build raw section bodies, then stitch cross-section
    # continuations (move section N's first continuation paragraph to
    # end of section N-1's commentary).
    section_bodies: list[str] = []
    section_headers: list[str] = []
    for sec in SECTIONS:
        v_lo, v_hi = sec["verses"]
        section_headers.append(
            f'## 约翰福音 1:{v_lo}-{v_hi} —— {sec["title"]}\n\n'
            + scripture_block(sec["verses"])
        )
        comm, sec_defs, fn_counter = load_pages(*sec["pages"], fn_counter, sec["verses"])
        section_bodies.append(split_long_paragraphs(comm))
        all_defs.extend(sec_defs)

    # Forward migration: if section N's LAST paragraph is a verse opener
    # for a verse in section N+1's range, move it forward.
    # After moving, also check if it should be joined with the next
    # section's then-current first paragraph (cross-page continuation
    # that happened to straddle the section boundary).
    for i in range(len(section_bodies) - 1):
        next_v_lo, next_v_hi = SECTIONS[i + 1]["verses"]
        while True:
            cur = section_bodies[i]
            if not cur:
                break
            cur_paras = re.split(r"\n{2,}", cur)
            last_para = cur_paras[-1].rstrip() if cur_paras else ""
            if not last_para:
                break
            stripped = _strip_corrupt_marker(last_para)
            first_sent, _ = _split_first_sentence(stripped)
            first_clean = _normalize_for_match(first_sent)
            v = _verse_for_opener(first_clean, JOHN_1)
            if v is None or not (next_v_lo <= v <= next_v_hi):
                break
            promoted = maybe_promote_verse_opener(
                last_para, JOHN_1, (next_v_lo, next_v_hi)
            )
            next_paras = re.split(r"\n{2,}", section_bodies[i + 1])
            # If promoted ends mid-sentence and next_paras[0] starts with
            # mid-sentence continuation, join them.
            if (next_paras and promoted
                    and promoted[-1] not in _TERM_PUNCT
                    and _is_section_continuation(promoted, next_paras[0].lstrip())):
                promoted = promoted + next_paras[0].lstrip()
                next_paras = next_paras[1:]
            section_bodies[i + 1] = "\n\n".join([promoted] + next_paras)
            section_bodies[i] = "\n\n".join(cur_paras[:-1])

    # Stitch continuations: keep moving section N's first paragraph back
    # to section N-1 while either of two conditions holds:
    #   1) Mid-sentence continuation (prev_last lacks terminator + cur_first
    #      starts with plain CJK char)
    #   2) Cur_first is a verse opener for a verse BELONGING to section N-1
    #      (e.g. v27 commentary that spans pages, with its continuation
    #      ending up in section 5 when it actually belongs to section 4)
    for i in range(1, len(section_bodies)):
        prev_v_lo, prev_v_hi = SECTIONS[i - 1]["verses"]
        while True:
            cur = section_bodies[i]
            prev = section_bodies[i - 1]
            if not cur or not prev:
                break
            cur_paras = re.split(r"\n{2,}", cur)
            prev_paras = re.split(r"\n{2,}", prev)
            if not cur_paras or not prev_paras:
                break
            prev_last = prev_paras[-1].rstrip()
            cur_first = cur_paras[0].lstrip()

            should_merge = False
            # Rule 1: mid-sentence continuation
            if _is_section_continuation(prev_last, cur_first):
                should_merge = True
            else:
                # Rule 2: cur_first looks like a verse opener whose verse
                # number falls in prev section's range.
                stripped = _strip_corrupt_marker(cur_first)
                first_sent, _ = _split_first_sentence(stripped)
                first_clean = _normalize_for_match(first_sent)
                v = _verse_for_opener(first_clean, JOHN_1)
                if v is not None and prev_v_lo <= v <= prev_v_hi:
                    should_merge = True

            if not should_merge:
                break
            # Merge: append cur_first as a SEPARATE paragraph if rule 2
            # (verse opener) or in-place join if rule 1 (no terminator).
            if prev_last and prev_last[-1] not in _TERM_PUNCT:
                prev_paras[-1] = prev_last + cur_first
            else:
                # Re-promote with the prev section's verse_range now that
                # the paragraph is in the correct section — verse 27 etc.
                # didn't get promoted on first pass because it was inside
                # section 5 (range 29-34) which excluded it.
                prev_range = SECTIONS[i - 1]["verses"]
                cur_first_promoted = maybe_promote_verse_opener(
                    cur_first, JOHN_1, prev_range
                )
                prev_paras.append(cur_first_promoted)
            section_bodies[i - 1] = "\n\n".join(prev_paras)
            section_bodies[i] = "\n\n".join(cur_paras[1:])

    for hdr, sec_body in zip(section_headers, section_bodies):
        body.append(hdr)
        body.append(sec_body)
        body.append("")

    # Footnote definitions — kramdown auto-renders them as a numbered list
    # at the very bottom with backlinks. Two leading newlines before defs
    # avoid the setext-h2 ambiguity (—— vs ---).
    if all_defs:
        body.append("")
        for gid, text in all_defs:
            body.append(f"[^{gid}]: {text}")
            body.append("")
    return fm + "\n".join(body) + "\n"


def main() -> int:
    out = REPO / "calvin/john-scan/1.md"
    content = build_chapter_md()
    out.write_text(content, encoding="utf-8")
    n_sections = content.count("## 约翰福音 1:")
    n_boxes = content.count('class="scripture-box"')
    n_anchors = content.count('class="scripture-anchor"')
    n_fn_refs = len(set(re.findall(r"\[\^(\d+)\](?!:)", content)))
    n_fn_defs = len(re.findall(r"^\[\^(\d+)\]: ", content, re.MULTILINE))
    long_lines = [
        (i + 1, len(line))
        for i, line in enumerate(content.splitlines())
        if i > 20 and len(line) > 1500
    ]
    print(f"wrote {out} ({len(content):,} chars)")
    print(f"  sections={n_sections}  boxes={n_boxes}  anchors={n_anchors}")
    print(f"  fn refs unique={n_fn_refs}  fn defs={n_fn_defs}")
    print(f"  long lines>1500: {len(long_lines)} {long_lines[:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
