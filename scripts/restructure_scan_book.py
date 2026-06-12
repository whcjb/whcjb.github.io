#!/usr/bin/env python3
"""Generic restructure for any scanned commentary book.

Generalization of restructure_john_scan_chapter.py — takes:
  - book id (lowercase, e.g. 'colossians')
  - CUV book number (e.g. 51 for Colossians, 43 for John)
  - Chinese book name (e.g. '歌罗西书' for the chapter heading prefix
    and verse markers `约翰福音` style)
  - chapter→first-page mapping (derived from OCR `# 第N章` scan)
  - source raw dir (calvin_raw/<book>-scan/ocr/)
  - output dir (calvin/<book>/, after replace)

Usage:
  python3 scripts/restructure_scan_book.py \
      --book colossians --cuv-book 51 --book-cn 歌罗西书 \
      --raw-dir calvin_raw/colossians-scan \
      --out-dir calvin/colossians \
      --chapter 1
  python3 scripts/restructure_scan_book.py ... --all
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from restructure_john_scan_ch1 import (
    process_page, _join_cross_page, _strip_corrupt_marker,
    _split_first_sentence, _verse_for_opener,
    maybe_promote_verse_opener,
    split_long_paragraphs, _TERM_PUNCT,
)


REPO = Path("/Users/yanpeifa/Documents/whcjb.github.io")
CUV = json.load(open(REPO / "assets/cuv.json"))

TARGET_VERSES_PER_SECTION = 7

_CN_NUM = ['零','一','二','三','四','五','六','七','八','九','十',
           '十一','十二','十三','十四','十五','十六','十七','十八','十九',
           '二十','二十一','二十二','二十三','二十四','二十五']


def _cn(n: int) -> str:
    return _CN_NUM[n] if 0 <= n < len(_CN_NUM) else str(n)


def detect_chapter_first_pages(raw_dir: Path) -> dict[int, int]:
    """Scan OCR pages for chapter heading markers; return {ch_num: first_page}.

    Matches `# 第N章` OR bare `第N章` (some PDFs/OCR don't emit the
    leading `#`). Filters out lines that are TOC entries (have dots and
    page-numbers, e.g. `第一章………………11`).
    """
    # Trailing characters allowed after `第N章`:
    # - `*` (markdown emphasis OCR carryover)
    # - `①-⑳` (footnote markers OCR fuses to heading, e.g. page 18 of romans:
    #   `第一章①`)
    # - whitespace
    CN_RE = re.compile(
        r"^#?\s*第([一二三四五六七八九十]+)章[\*①-⑳\s]*$", re.MULTILINE
    )
    CN = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
          '十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,
          '十七':17,'十八':18,'十九':19,'二十':20,'二十一':21,'二十二':22,
          '二十三':23,'二十四':24,'二十五':25,'二十六':26,'二十七':27,
          '二十八':28,'二十九':29,'三十':30}
    chapter_start: dict[int, int] = {}
    pages = sorted((raw_dir / "ocr").glob("page_*.md"))
    for f in pages:
        p = int(re.search(r"page_(\d+)", f.name).group(1))
        text = f.read_text(encoding="utf-8")
        for m in CN_RE.finditer(text):
            ch = CN.get(m.group(1), 0)
            if ch and ch not in chapter_start:
                chapter_start[ch] = p
    return chapter_start


# ────────────────────────────────────────────────────────────────────────
# Per-chapter restructure (uses ch1's process_page with monkey-patched
# JOHN_1 to current chapter's verses, and book name for verse refs).
# ────────────────────────────────────────────────────────────────────────


_VERSE_PREFIX_RE_CACHE: dict[str, re.Pattern] = {}


def verse_prefix_re(book_cn: str) -> re.Pattern:
    if book_cn not in _VERSE_PREFIX_RE_CACHE:
        _VERSE_PREFIX_RE_CACHE[book_cn] = re.compile(
            r"^\*\*" + re.escape(book_cn) + r" \d+:(\d+)。\*\*"
        )
    return _VERSE_PREFIX_RE_CACHE[book_cn]


_BARE_VERSE_NUM_RE = re.compile(r"(?:^|[^0-9])(\d{1,3})\.\s*[一-鿿]")


def _looks_like_bible_fragment(text: str) -> bool:
    """Bible-text fragment heuristic.

    Match if any of:
      - Starts with `N. <CJK>` or `N、<CJK>` (verse marker w/ separator)
      - Starts with `N <CJK>` (digit + WHITESPACE + CJK) — OCR style for
        Ephesians-like books where verse number is separated by space
      - Starts with `N<CJK>` directly (digit fused to verse text)
      - Short paragraph with dense `、` list separators (4+ in <100 chars)
    """
    s = text.lstrip()
    if not s:
        return False
    if re.match(r"^\d{1,3}[.、,]\s*[一-鿿]", s):
        return True
    # Digit + whitespace + CJK (Ephesians style: `1 奉神旨意...`)
    if re.match(r"^\d{1,3}\s+[一-鿿]", s):
        return True
    # Bare digit fused to CJK (no separator) — single-verse Bible fragment
    if re.match(r"^\d{1,3}[一-鿿]", s):
        return True
    if len(s) < 100 and s.count("、") >= 4:
        return True
    return False


def _strip_bible_text_dumps(text: str, book_cn: str | None = None,
                              cuv_book: str | None = None,
                              chapter: int | None = None) -> str:
    """Drop OCR Bible-text passages (already rendered by scripture-box).

    Detection forms:
      1) Paragraph has >= 5 circled digits AND > 300 chars (John style).
      2) Paragraph has >= 4 bare `N.` verse markers (Colossians style).
      3) Paragraph starts with `N. <CJK>` / `N <CJK>` verse-marker AND
         body closely matches CUV verse text (or is very short < 80
         chars without commentary-style continuation).
         Without the CUV check, we'd drop verse-opener commentary
         paragraphs whose first 1–2 chars happen to look like the
         Bible fragment (e.g. `21 因为，他们虽然知道上帝保罗于此公然宣证...`
         where `因为，他们虽然知道上帝` looks like Bible text but the rest
         is Calvin's exposition).
      4) Standalone `<book_cn> N:N-N` Bible-ref heading line — drop
         (no-space form `加拉太书5:19-21` also accepted).
    """
    from restructure_john_scan_ch1 import _CIRCLE_TO_INT
    paras = re.split(r"\n{2,}", text)
    out: list[str] = []
    ref_re = None
    if book_cn:
        # Allow optional whitespace between book name and verse range
        ref_re = re.compile(
            rf"^{re.escape(book_cn)}\s*\d+:\d+(?:[-－—]\d+)?\s*$"
        )
    for p in paras:
        s = p.strip()
        if ref_re and ref_re.match(s):
            continue
        n_circles = sum(1 for c in p if c in _CIRCLE_TO_INT)
        if n_circles >= 5 and len(p) > 300:
            continue
        n_bare = len(_BARE_VERSE_NUM_RE.findall(p))
        if n_bare >= 4:
            continue
        # Form 3: Bible-text fragment — tighter check now.
        if "**" not in p and _looks_like_bible_fragment(p):
            drop = False
            # Sub-rule 3a: very short fragment (< 80 chars) — likely a
            # split Bible-text snippet (Galatians-style).
            if len(p) < 80:
                drop = True
            # Sub-rule 3b: paragraph content closely matches the CUV text
            # for the opener verse — definitely Bible, drop.
            elif cuv_book and chapter is not None:
                m = re.match(r"^\s*(\d{1,3})[. 、,]\s*", p)
                if m:
                    v = int(m.group(1))
                    body_after = p[m.end():].strip()
                    # Strict threshold: must really look like CUV text.
                    if _is_bible_verse_text(
                        body_after[:80], cuv_book, chapter, v, threshold=0.7
                    ):
                        drop = True
            if drop:
                continue
        out.append(p)
    return "\n\n".join(out)


def looks_like_bible_text_dump(para: str) -> bool:
    """OCR sometimes captures the chapter's Bible text passage as one big
    paragraph (with many ①②③… verse markers). The scripture-box already
    shows the clean CUV text — so this OCR'd Bible dump is redundant
    noise that, if promoted, becomes a fake commentary opener containing
    multiple verses.

    Detect: paragraph contains >= 5 circled digits AND length > 400.
    """
    from restructure_john_scan_ch1 import _CIRCLE_TO_INT
    n_circles = sum(1 for c in para if c in _CIRCLE_TO_INT)
    return n_circles >= 5 and len(para) > 400


def detect_paragraph_verse(para: str, chapter_verses: dict, book_cn: str) -> int | None:
    m = verse_prefix_re(book_cn).match(para)
    if m:
        return int(m.group(1))
    # OCR-style verse opener: `N <CJK>...` or `N **<CJK>...**` or `N. <CJK>`
    # (OCR doesn't preserve **{书卷} N:V。** bold prefix, so we detect the
    # leading digit-space pattern; optional `**` for bold lemma).
    m = re.match(r"^(\d{1,3})[ 、.]\s*\*{0,2}[一-鿿]", para)
    if m:
        v = int(m.group(1))
        if 1 <= v <= len(chapter_verses):
            return v
    if para.startswith(("[^", "<", "#")):
        return None
    stripped = _strip_corrupt_marker(para)
    first_sent, _ = _split_first_sentence(stripped)
    from restructure_john_scan_ch1 import _normalize_for_match
    first_clean = _normalize_for_match(first_sent)
    if len(first_clean) < 3:
        return None
    return _verse_for_opener(first_clean, chapter_verses)


def scripture_block(book_id: str, book_cn: str, chapter: int,
                     verses_range: tuple[int, int], cuv_book: str) -> str:
    a, b = verses_range
    ref = f"{book_cn} {chapter}:{a}-{b}"
    anchor_id = f"{book_id}-{chapter}-{a}-{b}"
    inner = "".join(f"<strong>{v}.</strong>{CUV[cuv_book][str(chapter)][str(v)]}"
                    for v in range(a, b + 1))
    return (
        f'<h2 class="scripture-anchor" id="{anchor_id}" data-ref="{ref}" style="display:none">{ref}</h2>\n\n'
        f'<div class="scripture-box" markdown="1">\n'
        f'<p class="scripture-ref">{ref}</p>\n\n'
        f'<p>{inner}</p>\n\n'
        f'</div>\n'
    )


def section_ranges(verses_count: int) -> list[tuple[int, int]]:
    n_sec = max(2, (verses_count + TARGET_VERSES_PER_SECTION - 1) // TARGET_VERSES_PER_SECTION)
    chunk = (verses_count + n_sec - 1) // n_sec
    ranges = []
    for i in range(n_sec):
        lo = i * chunk + 1
        hi = min((i + 1) * chunk, verses_count)
        if lo > verses_count:
            break
        ranges.append((lo, hi))
    return ranges


def patch_book_ref_format(book_cn: str):
    """Monkey-patch maybe_promote_verse_opener to use the given book name
    in its output. Returns the original function for later restore.

    The published reference format is `**{book_cn} {ch}:{v}。**`. We can't
    do this without modifying ch1 module — instead we wrap the call.
    """
    pass  # Use the function directly; book name passed at output time.


# Map full book name → 1-char abbreviation used in PDFs.
_BOOK_ABBR = {
    "约翰福音": "约", "马太福音": "太", "马可福音": "可", "路加福音": "路",
    "使徒行传": "徒", "罗马书": "罗",
    "哥林多前书": ["林前", "前"], "哥林多后书": ["林后", "后"],
    "加拉太书": "加", "以弗所书": "弗", "腓立比书": "腓", "歌罗西书": "西",
    "帖撒罗尼迦前书": "帖前", "帖撒罗尼迦后书": "帖后",
    "提摩太前书": "提前", "提摩太后书": "提后", "提多书": "提",
    "腓利门书": "门", "希伯来书": "来",
    "雅各书": "雅", "彼得前书": "彼前", "彼得后书": "彼后",
    "约翰一书": "约一", "约翰二书": "约二", "约翰三书": "约三",
    "犹大书": "犹", "启示录": "启",
    "创世记": "创", "出埃及记": "出",
    "诗篇": "诗", "以赛亚书": "赛", "耶利米书": "耶",
}


def _book_abbrs(book_cn: str) -> list[str]:
    """Return all known abbreviations for a book (incl. full name itself)."""
    out = [book_cn]
    abbr = _BOOK_ABBR.get(book_cn, [])
    if isinstance(abbr, str):
        out.append(abbr)
    else:
        out.extend(abbr)
    return out


def _is_bible_verse_text(text: str, cuv_book: str, ch: int, v: int,
                          threshold: float = 0.6) -> bool:
    """Heuristic: does `text` closely match CUV book {cuv_book} ch {ch}
    verse {v}? Used to filter out OCR-captured Bible text passages that
    follow a `弗 N：M` label (they aren't commentary — they're the verse
    itself, which the scripture-box already shows).

    Match: > threshold of the CUV verse's CJK characters appear in `text`
    (in order), AND text length is comparable (<2.5x verse length).
    """
    try:
        verse = CUV[cuv_book][str(ch)][str(v)]
    except (KeyError, IndexError):
        return False
    NOISE = re.compile(r"[，。、；：（）！？「」『』　\s\"“”'‘’·‧·…]")
    cuv_clean = NOISE.sub("", verse)
    text_clean = NOISE.sub("", text)
    if not cuv_clean or len(text_clean) > len(cuv_clean) * 2.5:
        return False
    # Order-preserving substring overlap
    i = j = 0
    matched = 0
    while i < len(cuv_clean) and j < len(text_clean):
        if cuv_clean[i] == text_clean[j]:
            matched += 1
            i += 1
            j += 1
        else:
            j += 1
    return matched / len(cuv_clean) >= threshold


def _convert_pending_verse_labels(text: str, book_cn: str,
                                    cuv_book: str | None = None,
                                    prev_tail: str = "") -> str:
    """Strip standalone `<abbr> N：M` page-top running-header labels.

    Across all scanned Calvin commentaries we've processed (John,
    Colossians, Galatians, Ephesians), the short standalone `<abbr> N：M`
    line is ALWAYS a per-page running header showing the current verse
    being discussed — never a structural section divider. The actual
    verse boundaries come from bold lemma openers like
    `**phrase（N）** ...` or `**N、phrase。** ...` which are handled by
    `maybe_promote_verse_opener`.

    Previously this function tried to use these labels as verse markers
    and ended up injecting `**book N:M。**` mid-sentence whenever a label
    appeared between a page break that split a paragraph (e.g. Eph 1:10
    was injected between '假使有人辯稱，' on page 16 and '外邦人被選' on
    page 17). Always-drop is both simpler and correct for our corpus.

    The `prev_tail` / `cuv_book` args are kept for API stability.
    """
    del cuv_book, prev_tail  # no longer used
    abbrs = _book_abbrs(book_cn)
    label_re = re.compile(
        r"^(?:" + "|".join(re.escape(a) for a in abbrs) + r")?\s*"
        r"(\d{1,3})\s*[：:]\s*(\d{1,3})\s*$"
    )
    paras = re.split(r"\n{2,}", text)
    out: list[str] = []
    for p in paras:
        s = p.strip()
        if s and "\n" not in s and len(s) < 20 and label_re.match(s):
            continue
        out.append(p)
    return "\n\n".join(out)


def _strip_fused_running_headers(text: str, book_cn: str,
                                   extra_header_alts: list[str] | None = None) -> str:
    """Strip OCR-fused running-header prefixes from line starts.

    When OCR doesn't put a newline between a page-top running header and
    the body content, we get lines like:
      `第一章加尔文文集`             ← two headers fused, no content
      `第一章骄傲地高抬自己，...`     ← header fused to body content
      `加尔文文集12 保罗既对此...`   ← header fused to verse-opener
      `罗马书注释`                   ← bare full-line header (no `#`)
      `第一章`                        ← bare chapter-running header

    Strategy: greedily match longest header chain at line start. Drop
    line if rest is empty; else keep only the rest.

    Header order (longest-first to avoid regex backtracking issues — e.g.
    `罗马书注释` matched before `罗马书` so we don't strip only `罗马书`
    and leak orphan `注释`).
    """
    # Longest-first ordering. Python re alternation tries left-to-right
    # so we must list longer patterns before shorter ones.
    # `extra_header_alts` lets per-book wrappers add OCR-quirk patterns
    # (e.g., romans wrapper adds `加尔文集` for that OCR's typo).
    header_alts = [
        rf"{re.escape(book_cn)}注释",       # `罗马书注释` (5)
        r"加尔文文集",                      # 5
        r"第[一二三四五六七八九十百〇零0-9]+章",  # 3+
        re.escape(book_cn),                  # `罗马书` (3) — shortest
    ]
    if extra_header_alts:
        # Insert before the shortest entry so longer patterns still beat them
        header_alts[-1:-1] = extra_header_alts
    chain_re = re.compile(rf"^((?:{'|'.join(header_alts)})+)")
    out_lines = []
    for line in text.splitlines():
        m = chain_re.match(line)
        if not m:
            out_lines.append(line)
            continue
        rest = line[m.end():]
        if not rest.strip():
            continue  # full-line header, drop
        out_lines.append(rest)
    return "\n".join(out_lines)


def _patch_running_headers(book_cn: str, extra_patterns: list[str] | None = None):
    """Add book-CN-specific running-header strip patterns to ch1mod.

    extra_patterns: list of user-supplied regex strings (from --strip-line).
    """
    import restructure_john_scan_ch1 as ch1mod
    saved = list(ch1mod.RUNNING_HDR_PATTERNS)
    extra = [
        re.compile(p) for p in (extra_patterns or [])
    ] + [
        # `# 加尔文文集·歌罗西书注释` style book-title page header
        re.compile(rf"^[-—]?\s*#\s*加尔文文集\s*[·•‧]\s*{re.escape(book_cn)}注释\s*$"),
        # `# 加尔文文集·保罗书信注释（上册）——` — series-level header in some
        # Calvin Chinese editions. Accepts leading `- `/em-dash and
        # trailing `——`/whitespace.
        re.compile(r"^[-—]?\s*#?\s*加尔文文集\s*[·•‧]\s*[^#\n]{1,40}注释(?:[（(][^#\n)）]{0,10}[)）])?[-—\s]*$"),
        # `# 歌罗西书注释`
        re.compile(rf"^#\s*{re.escape(book_cn)}注释\s*$"),
        # `# 歌罗西书·第N章` — per-page running header in scanned books
        re.compile(rf"^#?\s*{re.escape(book_cn)}\s*[·•‧]\s*第[一二三四五六七八九十]+章\s*$"),
        # `# 歌罗西书·纲要` (running header form, with `·`)
        re.compile(rf"^#?\s*{re.escape(book_cn)}\s*[·•‧]\s*纲要\s*$"),
        re.compile(rf"^#?\s*{re.escape(book_cn)}\s*[·•‧]\s*序言\s*$"),
        re.compile(rf"^#?\s*{re.escape(book_cn)}\s*[·•‧]\s*前言\s*$"),
        # `# 歌罗西书`
        re.compile(rf"^#\s*{re.escape(book_cn)}\s*$"),
        # Non-# prefixed variants
        re.compile(rf"^加尔文文集\s*[·•‧]\s*{re.escape(book_cn)}注释\s*$"),
        # Bare running-header forms (no `#`, no `·`) — common when OCR loses
        # markdown header structure. These standalone lines are ALWAYS
        # page headers, never content.
        re.compile(rf"^{re.escape(book_cn)}注释\s*$"),
        re.compile(r"^加尔文文集\s*$"),
        # Translator credit lines often appearing at chapter start
        re.compile(r"^[^\s#]{1,4}[译校].\s*$"),
    ]
    ch1mod.RUNNING_HDR_PATTERNS = ch1mod.RUNNING_HDR_PATTERNS + extra
    return saved


def _restore_running_headers(saved):
    import restructure_john_scan_ch1 as ch1mod
    ch1mod.RUNNING_HDR_PATTERNS = saved


def load_chapter_paragraphs(raw_dir: Path, page_lo: int, page_hi: int,
                              chapter_verses: dict, book_cn: str,
                              chapter: int = 1,
                              cuv_book: str | None = None,
                              extra_strip_patterns: list[str] | None = None) -> tuple[list[str], list]:
    import restructure_john_scan_ch1 as ch1mod
    saved_verses = ch1mod.JOHN_1
    saved_hdrs = _patch_running_headers(book_cn, extra_strip_patterns)
    ch1mod.JOHN_1 = chapter_verses
    try:
        body_parts: list[str] = []
        all_defs: list = []
        fn_counter = 0
        all_vr = (1, len(chapter_verses))
        prev_tail = ""
        for p in range(page_lo, page_hi + 1):
            f = raw_dir / f"ocr/page_{p:04d}.md"
            if not f.exists():
                continue
            raw_text = f.read_text(encoding="utf-8")
            raw_text = _strip_fused_running_headers(
                raw_text, book_cn,
                extra_header_alts=globals().get("_BOOK_EXTRA_HEADER_ALTS"),
            )
            raw_text = _strip_bible_text_dumps(raw_text, book_cn,
                                                cuv_book=cuv_book,
                                                chapter=chapter)
            raw_text = _convert_pending_verse_labels(
                raw_text, book_cn, cuv_book, prev_tail=prev_tail
            )
            page_paras = [q for q in re.split(r"\n{2,}", raw_text) if q.strip()]
            prev_tail = page_paras[-1].strip() if page_paras else prev_tail
            body, defs, fn_counter = process_page(
                raw_text, fn_counter, all_vr, book_cn, chapter
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
        text = "\n\n".join(p for p in body_parts if p)
        text = split_long_paragraphs(text)
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        return paras, all_defs
    finally:
        ch1mod.JOHN_1 = saved_verses
        _restore_running_headers(saved_hdrs)


def rebrand_verse_refs(text: str, book_cn: str) -> str:
    """The verse-opener promote in ch1 emits `**约翰福音 1:N。**`.
    Replace `约翰福音` with the actual book_cn for this book.
    """
    return text.replace("**约翰福音 ", f"**{book_cn} ")


def build_chapter_md(book_id: str, book_cn: str, cuv_book: str,
                       chapter: int, raw_dir: Path,
                       chapter_first: dict[int, int],
                       total_chapters: int,
                       header_img: str = "psalm-bg-mountain.jpg",
                       extra_strip_patterns: list[str] | None = None) -> str:
    chapter_verses = CUV[cuv_book][str(chapter)]
    sec_ranges = section_ranges(len(chapter_verses))

    page_lo = chapter_first[chapter]
    if (chapter + 1) in chapter_first:
        page_hi = chapter_first[chapter + 1] - 1
    else:
        # last chapter — go to last OCR'd page
        pages = sorted((raw_dir / "ocr").glob("page_*.md"))
        page_hi = int(re.search(r"page_(\d+)", pages[-1].name).group(1)) if pages else page_lo

    paras, all_defs = load_chapter_paragraphs(
        raw_dir, page_lo, page_hi, chapter_verses, book_cn, chapter, cuv_book,
        extra_strip_patterns=extra_strip_patterns,
    )
    # Drop Bible-text dumps (OCR captured full chapter Bible text in one
    # paragraph; scripture-box already renders the clean CUV version).
    paras = [p for p in paras if not looks_like_bible_text_dump(p)]
    # Rebrand the verse-ref format that ch1's promote produced
    paras = [rebrand_verse_refs(p, book_cn) for p in paras]

    # Bucket paragraphs by verse
    buckets: list[list[str]] = [[] for _ in sec_ranges]
    cur_sec = 0
    for p in paras:
        v = detect_paragraph_verse(p, chapter_verses, book_cn)
        if v is not None:
            for idx, (lo, hi) in enumerate(sec_ranges):
                if lo <= v <= hi:
                    cur_sec = idx
                    break
        buckets[cur_sec].append(p)

    prev_section = "preface" if chapter == 1 else (chapter - 1)
    prev_label = "序言" if chapter == 1 else f"第{_cn(chapter - 1)}章"
    next_section = (chapter + 1) if chapter < total_chapters else None
    next_label = f"第{_cn(chapter + 1)}章" if chapter < total_chapters else None

    fm = [
        "---",
        "layout: calvin-en",
        f"book_id: {book_id}",
        f'book_name: "{book_cn}"',
        f"chapter: {chapter}",
        f"header-img: {header_img}",
        f"date: {_now()}",
        f"prev_section: {prev_section}",
        f'prev_label: "{prev_label}"',
    ]
    if next_section is not None:
        fm += [
            f"next_section: {next_section}",
            f'next_label: "{next_label}"',
        ]
    fm.append("---\n\n")

    body = [f"# {book_cn} {chapter}\n"]
    for (lo, hi), paras_in_sec in zip(sec_ranges, buckets):
        body.append(f"## {book_cn} {chapter}:{lo}-{hi}\n")
        body.append(scripture_block(book_id, book_cn, chapter, (lo, hi), cuv_book))
        for p in paras_in_sec:
            body.append(p)
            body.append("")

    if all_defs:
        body.append("")
        for gid, text in all_defs:
            body.append(f"[^{gid}]: {text}")
            body.append("")

    return "\n".join(fm) + "\n".join(body) + "\n"


def build_preface_md(book_id: str, book_cn: str, raw_dir: Path,
                      preface_page_hi: int,
                      header_img: str = "psalm-bg-mountain.jpg") -> str:
    """Preface = pages 1 through preface_page_hi (one less than ch1 start)."""
    import restructure_john_scan_ch1 as ch1mod
    saved_hdrs = _patch_running_headers(book_cn)
    try:
        return _build_preface_md_inner(book_id, book_cn, raw_dir, preface_page_hi, header_img)
    finally:
        _restore_running_headers(saved_hdrs)


def _build_preface_md_inner(book_id: str, book_cn: str, raw_dir: Path,
                              preface_page_hi: int, header_img: str) -> str:
    fm = (
        "---\n"
        "layout: calvin-en\n"
        f"book_id: {book_id}\n"
        f'book_name: "{book_cn}"\n'
        "chapter: 0\n"
        f"header-img: {header_img}\n"
        'title: "序言"\n'
        f"date: {_now()}\n"
        'next_section: 1\n'
        'next_label: "第一章"\n'
        "---\n\n"
    )

    body_parts: list[str] = []
    all_defs: list = []
    fn_counter = 0
    for p in range(1, preface_page_hi + 1):
        f = raw_dir / f"ocr/page_{p:04d}.md"
        if not f.exists():
            continue
        body, defs, fn_counter = process_page(f.read_text(encoding="utf-8"), fn_counter, None)
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


def build_index_html(book_id: str, book_cn: str, total_chapters: int) -> str:
    return (
        "---\n"
        "layout: calvin-book\n"
        f"book_id: {book_id}\n"
        f"book_name: {book_cn}\n"
        f"chapters: {total_chapters}\n"
        "has_preface: true\n"
        "---\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="e.g. colossians")
    ap.add_argument("--cuv-book", required=True, help="CUV book index, e.g. 51")
    ap.add_argument("--book-cn", required=True, help="Chinese name, e.g. 歌罗西书")
    ap.add_argument("--raw-dir", required=True, help="e.g. calvin_raw/colossians-scan")
    ap.add_argument("--out-dir", required=True, help="e.g. calvin/colossians")
    ap.add_argument("--chapter", type=int, help="single chapter to process")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--header-img", default="psalm-bg-mountain.jpg")
    ap.add_argument("--strip-line", action="append", default=[],
                    help="Extra running-header regex to strip (repeatable)")
    ap.add_argument("--skip-relocate", action="store_true",
                    help="Skip post-build verse-commentary relocation")
    ap.add_argument("--skip-audit", action="store_true",
                    help="Skip final audit gate (exits non-zero on issues)")
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chapter_first = detect_chapter_first_pages(raw_dir)
    print(f"detected chapter boundaries: {chapter_first}")
    total_chapters = len(CUV[args.cuv_book])

    if not chapter_first:
        print("ERROR: no `# 第N章` markers found in OCR — re-OCR with markdown prompt?")
        return 1

    # Preface = pages before chapter 1
    preface_page_hi = chapter_first.get(1, 1) - 1
    if preface_page_hi >= 1:
        preface_md = build_preface_md(args.book, args.book_cn, raw_dir,
                                        preface_page_hi, args.header_img)
        (out_dir / "preface.md").write_text(preface_md, encoding="utf-8")
        print(f"  preface.md: {len(preface_md):,} chars")

    chapters_to_do = list(range(1, total_chapters + 1)) if args.all else [args.chapter]
    for ch in chapters_to_do:
        if ch not in chapter_first:
            print(f"  ch{ch:2d}: SKIP (no OCR page found)")
            continue
        content = build_chapter_md(
            args.book, args.book_cn, args.cuv_book, ch, raw_dir,
            chapter_first, total_chapters, args.header_img,
            extra_strip_patterns=args.strip_line,
        )
        (out_dir / f"{ch}.md").write_text(content, encoding="utf-8")
        n_box = content.count('class="scripture-box"')
        n_fn = len(re.findall(r"^\[\^[0-9]+\]: ", content, re.MULTILINE))
        n_v = len(set(re.findall(r"\*\*" + re.escape(args.book_cn) + r" \d+:(\d+)。\*\*", content)))
        print(f"  ch{ch:2d}: {n_box} boxes  {n_fn} fns  {n_v} verse markers")

    # Generate index.html
    (out_dir / "index.html").write_text(
        build_index_html(args.book, args.book_cn, total_chapters), encoding="utf-8"
    )
    print(f"  index.html: chapters={total_chapters}, has_preface=true")

    # Post-build: relocate misplaced verse-commentary paragraphs
    # (章内 + 跨章). OCR doesn't preserve `**{书卷} N:V。**` bold,
    # so heuristic bucketing in build_chapter_md will mis-assign segments.
    if not args.skip_relocate:
        import subprocess as _sub
        scripts_dir = Path(__file__).resolve().parent
        for script in (
            "relocate_misplaced_verse_commentary.py",
            "relocate_cross_chapter_verse.py",
        ):
            sp = scripts_dir / script
            if not sp.exists():
                print(f"  ⚠ {script} not found; skip")
                continue
            print(f"\n→ {script}")
            _sub.run([sys.executable, str(sp),
                       "--book-cn", args.book_cn,
                       "--dir", str(out_dir)], check=False)

    # Final audit gate
    if not args.skip_audit:
        rc = _audit_gate(out_dir, args.book_cn, args.cuv_book)
        if rc != 0:
            print("\n❌ audit gate FAILED — fix issues above before commit")
            return rc
        print("\n✅ audit gate passed")
    return 0


def _audit_gate(out_dir: Path, book_cn: str, cuv_book: str) -> int:
    """Return 0 if all checks pass, non-zero otherwise.

    Checks:
      1. No misplaced verse-openers (bare-digit segs outside section range)
      2. No running-header leak in body
      3. No CIRCLED-DIGIT prefix (un-promoted ①-⑳)
      4. No orphan footnote refs ([^N] in body but no [^N]: defn)
    """
    issues = 0
    hdr_re = re.compile(rf"^## {re.escape(book_cn)} (\d+):(\d+)(?:-(\d+))?")
    opener_re = re.compile(r"^(\d{1,3})[ 、.]\s*\*{0,2}[一-鿿]")
    leak_re = re.compile(
        rf"^(加尔文文集|{re.escape(book_cn)}注释|{re.escape(book_cn)}\s*[·•‧]\s*第[一二三四五六七八九十]+章)\s*$"
    )
    circled_re = re.compile(r"^[①-⑳]")

    chapter_verses = {int(ch): len(verses) for ch, verses in CUV[cuv_book].items()}

    for p in sorted(out_dir.glob("*.md")):
        if not p.stem.isdigit():
            continue
        ch = int(p.stem)
        max_v = chapter_verses.get(ch, 999)
        lines = p.read_text(encoding="utf-8").split("\n")
        secs = []
        for i, ln in enumerate(lines):
            m = hdr_re.match(ln)
            if m:
                secs.append((i, int(m.group(2)),
                             int(m.group(3)) if m.group(3) else int(m.group(2))))
        # Iterate sections
        for si, (start, lo, hi) in enumerate(secs):
            end = secs[si + 1][0] if si + 1 < len(secs) else len(lines)
            i = start + 1
            while i < end:
                ln = lines[i]
                if not ln.strip():
                    i += 1; continue
                if leak_re.match(ln.strip()):
                    print(f"  LEAK    {p.name}:{i+1}  {ln.strip()[:60]}")
                    issues += 1
                if circled_re.match(ln):
                    print(f"  CIRCLED {p.name}:{i+1}  {ln[:60]}")
                    issues += 1
                if ln.lstrip().startswith(('<h2', '<div', '<a ', '</div>', '<p ', '[^', '{:.')):
                    while i < end and lines[i].strip():
                        i += 1
                    continue
                ps = i
                while i < end and lines[i].strip():
                    i += 1
                m = opener_re.match(lines[ps])
                if m:
                    v = int(m.group(1))
                    if 1 <= v <= max_v and not (lo <= v <= hi):
                        print(f"  MISPLC  {p.name}:{ps+1}  section {lo}-{hi}, paragraph opens with v.{v}")
                        issues += 1
        # NOTE: orphan-fragment detection（孤立短段，疑似 Bible-dump
        # 误删后的尾巴）误报率太高（合理的 60-100 字短注释段也会触发），
        # 不放进必过 gate。如怀疑误删，跑下面手动脚本：
        #   python3 scripts/audit_orphan_fragments.py <dir>
        # 检查输出，若开头是续接词（"出于"/"且"/"但"...）人工核查 OCR 原文。

        # Orphan footnotes per file
        text = p.read_text(encoding="utf-8")
        body, _, fns = text.partition("\n## 脚注\n") if "## 脚注" in text else (text, "", "")
        refs = set(re.findall(r"\[\^(\d+)\]", body))
        # Exclude defn lines from refs
        body_refs = set()
        for ln in body.split("\n"):
            if re.match(r"^\[\^\d+\]:", ln):
                continue
            body_refs |= set(re.findall(r"\[\^(\d+)\]", ln))
        defs = set(re.findall(r"^\[\^(\d+)\]:", text, re.M))
        orphan = body_refs - defs
        if orphan:
            print(f"  ORPHAN  {p.name}  fn refs without defn: {sorted(orphan)[:10]}")
            issues += 1
    print(f"\nAudit: {issues} issue(s)")
    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
