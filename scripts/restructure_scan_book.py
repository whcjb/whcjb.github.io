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
    CN_RE = re.compile(r"^#?\s*第([一二三四五六七八九十]+)章\*?\s*$", re.MULTILINE)
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


def _strip_bible_text_dumps(text: str, book_cn: str | None = None) -> str:
    """Drop paragraphs from raw OCR that look like the chapter's Bible
    text passage. Two detection forms:
      1) Many circled-digit verse markers in close proximity: paragraph
         has >= 5 circled digits AND > 300 chars (John/Colossians style).
      2) Many bare `N.` verse markers + paragraph length: >= 5 bare
         numbered markers AND > 200 chars (Galatians style — OCR prompt
         asked for cleaner output so verses come as `1. 作使徒... 2. 和`).

    Also drops the Bible-reference heading line that often precedes the
    dump (e.g. `加拉太书 1:1-5` alone on a line).

    scripture-box already renders the clean CUV version, so these OCR'd
    Bible dumps are redundant.
    """
    from restructure_john_scan_ch1 import _CIRCLE_TO_INT
    paras = re.split(r"\n{2,}", text)
    out: list[str] = []
    # Pattern for `<book_cn> N:N-N` standalone Bible-ref heading
    ref_re = None
    if book_cn:
        ref_re = re.compile(rf"^{re.escape(book_cn)}\s+\d+:\d+(?:[-－—]\d+)?\s*$")
    for p in paras:
        s = p.strip()
        if ref_re and ref_re.match(s):
            continue  # drop bare bible-ref heading
        n_circles = sum(1 for c in p if c in _CIRCLE_TO_INT)
        if n_circles >= 5 and len(p) > 300:
            continue
        n_bare = len(_BARE_VERSE_NUM_RE.findall(p))
        # Bible-text dump: 4+ bare `N. CJK` markers in close succession.
        # 4 is a safer threshold than 5 because Calvin commentary doesn't
        # typically enumerate 4 sequential CJK-starting items as `1. X
        # 2. Y 3. Z 4. W` in one paragraph; whereas a Bible passage with
        # 4 consecutive verses on one OCR'd line fits this pattern. The
        # scripture-box already renders the clean CUV.
        if n_bare >= 4:
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


def _patch_running_headers(book_cn: str):
    """Add book-CN-specific running-header strip patterns to ch1mod."""
    import restructure_john_scan_ch1 as ch1mod
    saved = list(ch1mod.RUNNING_HDR_PATTERNS)
    extra = [
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
        # Translator credit lines often appearing at chapter start
        re.compile(r"^[^\s#]{1,4}[译校].\s*$"),
    ]
    ch1mod.RUNNING_HDR_PATTERNS = ch1mod.RUNNING_HDR_PATTERNS + extra
    return saved


def _restore_running_headers(saved):
    import restructure_john_scan_ch1 as ch1mod
    ch1mod.RUNNING_HDR_PATTERNS = saved


def load_chapter_paragraphs(raw_dir: Path, page_lo: int, page_hi: int,
                              chapter_verses: dict, book_cn: str) -> tuple[list[str], list]:
    import restructure_john_scan_ch1 as ch1mod
    saved_verses = ch1mod.JOHN_1
    saved_hdrs = _patch_running_headers(book_cn)
    ch1mod.JOHN_1 = chapter_verses
    try:
        body_parts: list[str] = []
        all_defs: list = []
        fn_counter = 0
        all_vr = (1, len(chapter_verses))
        for p in range(page_lo, page_hi + 1):
            f = raw_dir / f"ocr/page_{p:04d}.md"
            if not f.exists():
                continue
            raw_text = f.read_text(encoding="utf-8")
            raw_text = _strip_bible_text_dumps(raw_text, book_cn)
            body, defs, fn_counter = process_page(
                raw_text, fn_counter, all_vr
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
                       header_img: str = "psalm-bg-mountain.jpg") -> str:
    chapter_verses = CUV[cuv_book][str(chapter)]
    sec_ranges = section_ranges(len(chapter_verses))

    page_lo = chapter_first[chapter]
    if (chapter + 1) in chapter_first:
        page_hi = chapter_first[chapter + 1] - 1
    else:
        # last chapter — go to last OCR'd page
        pages = sorted((raw_dir / "ocr").glob("page_*.md"))
        page_hi = int(re.search(r"page_(\d+)", pages[-1].name).group(1)) if pages else page_lo

    paras, all_defs = load_chapter_paragraphs(raw_dir, page_lo, page_hi, chapter_verses, book_cn)
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
            chapter_first, total_chapters, args.header_img
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
