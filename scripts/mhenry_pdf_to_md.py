#!/usr/bin/env python3
"""
mhenry_pdf_to_md.py — Convert Matthew Henry commentary PDF to mhenry site .md files.

Usage:
    python3 scripts/mhenry_pdf_to_md.py <pdf_path> <book_id> <book_name_zh> <header_img> [<preface_pages>] [<chapter_pages>...]

Examples:
    # Zechariah: preface on page 2, chapters on pages 3-6,7-10,...
    python3 scripts/mhenry_pdf_to_md.py ~/Documents/论文/matthew_henry/马太亨利完整圣经注释-撒迦利亚书.pdf \\
        zechariah 撒迦利亚书 mhenry-land-38.jpg \\
        2:2 1:3:6 2:7:10 3:11:14 4:15:18 5:19:21 6:22:25 7:26:29 8:30:35 9:36:40 10:41:44 11:45:48 12:49:54 13:55:57 14:58:64

    # Haggai: preface on page 2, chapter 1 on pages 3-5, chapter 2 on pages 6-11
    python3 scripts/mhenry_pdf_to_md.py ~/Documents/论文/matthew_henry/马太亨利完整圣经注释-哈该书.pdf \\
        haggai 哈该书 mhenry-land-37.jpg \\
        2:2 1:3:5 2:6:11

Format for section args:
    preface:  "<preface>:<start_page>:<end_page>"  or "<preface>:<single_page>"
    chapters: "<chapter_num>:<start_page>:<end_page>"  or "<chapter_num>:<single_page>"
    Pages are 1-indexed.

The script:
 1. Extracts text from PDF pages using PyMuPDF (font-aware).
 2. For non-text PDFs, falls back to OCR via http://10.192.2.11:8765/ocr.
 3. Detects structure: date labels, scripture blocks, roman sections, footnotes.
 4. Groups into mh-unit / mh-l1 blocks and outputs .md files.
"""

import os
import re
import sys
import base64
import json
from pathlib import Path
from datetime import datetime

try:
    import fitz
except ImportError:
    sys.exit("Missing PyMuPDF: pip install pymupdf")

PDF_DIR = os.path.expanduser("~/Documents/论文/matthew_henry")
OUT_BASE = os.path.join(os.path.dirname(__file__), "..", "mhenry")
OCR_SERVER = "http://10.192.2.11:8765"

# ── Text extraction ─────────────────────────────────────────────────────────

HEADER_RE = re.compile(
    r"^马太亨利[完整圣经注释 \-–—]+"       # mhenry header
    r"|^第\d+页\s*$"                        # page number like "第3页"
    r"|^\d{1,4}\s*$"                        # standalone page numbers like "1019"
    r"|^第[一二三四五六七八九十百]+章\s*$"   # chapter heading (handled separately)
    r"|^简介\s*$"                           # 简介 title
    r"|^来源[:：]"                           # source URL like "来源:古旧福音..."
    r"|^https?://"                          # bare URLs
    r"|^约翰福音第\d{1,2}\s*章"              # John chapter heading
)


STRUCT_START_RE = re.compile(
    r"^(I{1,3}|IV|VI{0,3}|VII|VIII|IX|X{0,3}I{0,3}V?)\."  # Roman numeral
    r"|^\d{1,2}\."                                           # Numbered point
    r"|^[（(]\d{1,2}[）)]"                                   # Bracketed point
    r"|^\[\d{1,2}\.\]"                                       # [1.] marker
)


def merge_short_blocks(blocks_text, fonts_list):
    """Merge consecutive split-line blocks into paragraphs.

    Two modes:
    - If avg block length < 60 (line-per-block PDF like John 1121-page), use aggressive merge:
      merge everything except structural markers and verse refs.
    - Otherwise moderate: merge only if current block doesn't end with sentence punctuation.
    """
    if not blocks_text:
        return []
    avg_len = sum(len(t) for t in blocks_text) / max(1, len(blocks_text))
    aggressive = avg_len < 60

    merged = []
    current = blocks_text[0]
    current_fonts = set(fonts_list[0])
    SENTENCE_END = set("\u3002\uff01\uff1f\u300d\u300f\u201d")

    for i in range(1, len(blocks_text)):
        t = blocks_text[i]
        if not t.strip():
            continue
        t_stripped = t.strip()
        starts_struct = bool(STRUCT_START_RE.match(t_stripped))
        starts_verse_ref = bool(re.match(r"^(约翰福音|约)\s*\d{1,2}:\d", t_stripped))
        current_stripped = current.strip()
        current_is_label = (
            bool(re.match(r"^(约翰福音|约)\s*\d{1,2}:\d", current_stripped))
            or bool(re.search(r"\u4e2d\u524d\d+\s*\u5e74\uff09\s*$", current_stripped))  # "（主前xxx年）" at end
        )
        starts_label = starts_verse_ref or bool(re.search(r"\u4e2d\u524d\d+\s*\u5e74\uff09\s*$", t_stripped))
        # In aggressive mode: merge unless current or next block is a structural marker or label
        if aggressive:
            if not starts_struct and not starts_label and not current_is_label:
                current = current.rstrip() + t.lstrip()
                current_fonts |= set(fonts_list[i])
            else:
                merged.append((current, current_fonts))
                current = t
                current_fonts = set(fonts_list[i])
        else:
            last_char = current.rstrip()[-1] if current.rstrip() else ""
            if last_char not in SENTENCE_END and not starts_struct and not starts_label and not current_is_label:
                current = current.rstrip() + t.lstrip()
                current_fonts |= set(fonts_list[i])
            else:
                merged.append((current, current_fonts))
                current = t
                current_fonts = set(fonts_list[i])

    merged.append((current, current_fonts))
    return merged


def get_page_paras(page):
    """Extract paragraphs from a page with font info."""
    blocks = page.get_text("dict")["blocks"]
    raw_texts = []
    raw_fonts = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        block_text = ""
        block_fonts = set()
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                t = span["text"]
                if t.strip():
                    block_text += t
                    block_fonts.add(span["font"])
        text = block_text.strip()
        if text and not HEADER_RE.match(text):
            raw_texts.append(text)
            raw_fonts.append(block_fonts)

    # Merge short consecutive blocks to reconstruct paragraphs
    merged = merge_short_blocks(raw_texts, raw_fonts)
    result = []
    for text, fonts in merged:
        text = text.strip()
        if not text:
            continue
        # Split John-style "约1:15-18  15 约翰为他作见证..." into label + scripture
        m = re.match(r"^((?:约翰福音|约)\s*\d{1,2}:\d{1,3}[^\s]{0,20})\s+(\d{1,3}\s+[\u4e00-\u9fff\u300c\u300e\uff08].*)", text, re.DOTALL)
        if m:
            result.append({"text": m.group(1).strip(), "fonts": fonts})
            result.append({"text": m.group(2).strip(), "fonts": fonts, "_is_scripture_hint": True})
            continue
        # Split Zechariah-style "事件标题（主前NNN年）N 经文..." into label + body
        m = re.match(r"^(.{5,60}\uff08\u4e3b[\u524d\u540e]\d+\s*\u5e74\uff09)\s*(\d{1,3}\s+[\u4e00-\u9fff\u300c\u300e].*)", text, re.DOTALL)
        if m:
            result.append({"text": m.group(1).strip(), "fonts": fonts})
            result.append({"text": m.group(2).strip(), "fonts": fonts})
            continue
        result.append({"text": text, "fonts": fonts})
    return result


def ocr_page(page, server=OCR_SERVER):
    """OCR a page image via the remote Qwen server."""
    try:
        import requests
    except ImportError:
        return None
    pix = page.get_pixmap(dpi=150)
    b64 = base64.b64encode(pix.tobytes("png")).decode()
    try:
        resp = requests.post(f"{server}/ocr", json={"image": b64}, timeout=180)
        resp.raise_for_status()
        text = resp.json()["text"]
        # remove inter-character spaces from OCR artifact
        text = re.sub(r"(?<=[\u4e00-\u9fff]) +(?=[\u4e00-\u9fff])", "", text)
        return text
    except Exception as e:
        print(f"  OCR error: {e}", file=sys.stderr)
        return None


def is_text_page(page, min_chars=100):
    """Check if a page has enough readable text (not image-only)."""
    text = page.get_text("text")
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars >= min_chars


def extract_pages(pdf, start, end, use_ocr=False, server=OCR_SERVER):
    """Extract paragraphs from pages [start, end] (1-indexed).
    Returns list of para dicts. Falls back to OCR if text extraction is poor."""
    paras = []
    for pg_idx in range(start - 1, end):
        page = pdf[pg_idx]
        if use_ocr or not is_text_page(page):
            raw = ocr_page(page, server)
            if raw:
                # Convert raw OCR text to para dicts (no font info)
                for line in raw.split("\n"):
                    line = line.strip()
                    if line and not HEADER_RE.match(line):
                        paras.append({"text": line, "fonts": set()})
        else:
            paras.extend(get_page_paras(page))
    return paras


# ── Paragraph classification ─────────────────────────────────────────────────

DATE_LABEL_RE  = re.compile(r".{4,50}（主[前后]\d+\s*年）\s*$")
# John-style verse references: "约1:15-18" or "约 20:1-10" or "约翰福音3:1-5"
JOHN_LABEL_RE  = re.compile(r"^(约翰福音|约)\s*\d{1,2}:\d{1,3}")
# Real footnotes: digit directly followed by Chinese char (not colon/period/space/bracket)
# "1钦定本..." or "1约翰·莱福特..."  — NOT "1.先知..." or "1：万军..."
FOOTNOTE_RE   = re.compile(r"^(\d{1,2})([\u4e00-\u9fff·])")
OVERVIEW_RE   = re.compile(r"^本章|^这一章|^本篇|^本书|^本段")
ROMAN_RE      = re.compile(r"^(I{1,3}|IV|VI{0,3}|VII|VIII|IX|X{0,3}I{0,3}V?)\.")
VERSE_NUM_RE  = re.compile(r"^(\d{1,3})\s+[\u4e00-\u9fff「『（]")

def is_scripture(para):
    """Scripture detection: KaiTi-only (Zechariah style) or standalone verse block starting with number."""
    if "KaiTi" in para["fonts"] and "FangSong" not in para["fonts"] and "SimSun" not in para["fonts"]:
        return True
    # John style: no font differentiation; scripture starts with verse numbers
    t = para["text"].strip()
    if VERSE_NUM_RE.match(t) and para.get("_is_scripture_hint", False):
        return True
    return False

def classify(para):
    t = para["text"].strip()
    if is_scripture(para):
        return "scripture"
    if DATE_LABEL_RE.match(t):
        return "date_label"
    # John-style verse reference label (short standalone "约1:15-18")
    if JOHN_LABEL_RE.match(t) and len(t) < 150:
        return "date_label"
    fn = FOOTNOTE_RE.match(t)
    # A real footnote is short and the first Chinese char is NOT preceded by colon
    # Also exclude lines that start with a date like "1：xxx" (cross-references)
    if fn and len(t) < 350 and not re.match(r"^\d{1,2}[：:（\(]", t):
        return "footnote"
    if OVERVIEW_RE.match(t):
        return "overview"
    return "body"


def extract_verse_range(scripture_text):
    """Extract first and last verse numbers from a scripture block text."""
    nums = re.findall(r"(?<![0-9：:])(\d{1,3})\s+[\u4e00-\u9fff「『（]", scripture_text)
    if nums:
        first = int(nums[0])
        last  = int(nums[-1])
        if first == last:
            return f"第{first}节"
        return f"第{first}-{last}节"
    return ""


def label_to_verse_range(label):
    """Convert a John-style label like '约1:15-18' to '第15-18节'."""
    m = re.search(r":(\d+)[－\-–](\d+)", label)
    if m:
        return f"第{m.group(1)}-{m.group(2)}节"
    m = re.search(r":(\d+)", label)
    if m:
        return f"第{m.group(1)}节"
    return label


# ── HTML rendering ────────────────────────────────────────────────────────────

def html_escape(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_body_para(t):
    """Wrap a body paragraph as HTML, detecting roman sections and numbered points."""
    t = t.strip()
    if not t:
        return ""

    # Roman section heading: I. II. etc.
    m = ROMAN_RE.match(t)
    if m:
        roman = m.group(1)
        rest  = t[m.end():].strip()
        return f'<div class="mh-l1"><span class="mh-label">{roman}.</span> {html_escape(rest)}</div>\n'

    # Numbered point: "1.xxx" or "(1)xxx" or "（1）xxx"
    m = re.match(r"^(\d{1,2})\.\s*(.+)", t, re.DOTALL)
    if m:
        num, rest = m.group(1), m.group(2).strip()
        return f'<p>{num}. {html_escape(rest)}</p>\n'

    m = re.match(r"^[（(](\d{1,2})[）)]\s*(.+)", t, re.DOTALL)
    if m:
        num, rest = m.group(1), m.group(2).strip()
        return f'<p>（{num}）{html_escape(rest)}</p>\n'

    # Bracket numbered: "[1.]" "[2.]"
    m = re.match(r"^\[(\d{1,2})\.\]\s*(.+)", t, re.DOTALL)
    if m:
        num, rest = m.group(1), m.group(2).strip()
        return f'<p>[{num}.] {html_escape(rest)}</p>\n'

    return f'<p>{html_escape(t)}</p>\n'


def paras_to_mh_units(paras, chapter_num):
    """Convert paragraph list into a list of mh-unit structures.

    Each unit = {'verse_range': str, 'overview': str, 'body': [para_text], 'footnotes': [(num, text)]}
    The function also returns the chapter overview text.
    """
    units = []
    chapter_overview = ""
    footnotes_all = []

    # Split into segments by date_label markers
    segments = []   # list of (label, [paras])
    current_label = ""
    current_paras = []
    intro_paras = []
    in_intro = True

    # Skip initial orphan paragraphs (continuations from previous chapter)
    def _is_chapter_start(p):
        t2 = p["text"].strip()
        kind2 = classify(p)
        # Chapter heading embedded in paragraph text (e.g. "第2 章...")
        if re.match(r'^第\s*\d+\s*章', t2):
            return True
        return kind2 in ("overview", "scripture", "date_label") or OVERVIEW_RE.match(t2)

    first_real = next((i for i, p in enumerate(paras) if _is_chapter_start(p)), None)
    if first_real is not None and first_real > 0:
        paras = paras[first_real:]
        # Strip embedded chapter heading prefix (e.g. "第2 章...") from first paragraph
        if paras:
            stripped = re.sub(r'^第\s*\d+\s*章\s*', '', paras[0]["text"].strip())
            if stripped != paras[0]["text"].strip():
                paras[0] = dict(paras[0], text=stripped)

    for p in paras:
        kind = classify(p)
        t = p["text"].strip()

        if kind == "footnote":
            # parse footnote
            m = FOOTNOTE_RE.match(t)
            if m:
                num = m.group(1)
                body = t[m.start(2):].strip()
                footnotes_all.append((num, body))
            else:
                footnotes_all.append(("?", t))
            continue

        if kind == "overview" and in_intro:
            chapter_overview = t
            continue

        if kind == "date_label":
            in_intro = False
            if current_paras or current_label:
                segments.append((current_label, current_paras))
            elif intro_paras:
                # flush intro as first segment before date label
                segments.append(("", [{"text": t2, "fonts": set()} for t2 in intro_paras]))
                intro_paras = []
            current_label = t
            current_paras = []
            continue

        if in_intro and kind == "body":
            intro_paras.append(t)
            continue

        current_paras.append(p)

    if current_paras or current_label:
        segments.append((current_label, current_paras))

    # If there were intro_paras never flushed (no date label or before first one), prepend them
    if intro_paras and (not segments or segments[0][0] != ""):
        segments.insert(0, ("", [{"text": t2, "fonts": set()} for t2 in intro_paras]))

    # Fallback: if no segments, empty result
    if not segments:
        return [], chapter_overview, footnotes_all

    for label, seg_paras in segments:
        # Find scripture verse range: prefer from label (John-style), then from scripture text
        verse_range = ""
        if JOHN_LABEL_RE.match(label):
            verse_range = label_to_verse_range(label)
        if not verse_range:
            for p in seg_paras:
                if is_scripture(p):
                    verse_range = extract_verse_range(p["text"])
                    break

        # Collect body paras (non-scripture)
        body_paras = [p["text"].strip() for p in seg_paras if not is_scripture(p) and p["text"].strip()]

        units.append({
            "label": label,
            "verse_range": verse_range,
            "body": body_paras,
        })

    # Renumber footnotes sequentially (PDF per-page numbering → chapter-sequential)
    for i, (_, text) in enumerate(footnotes_all):
        footnotes_all[i] = (str(i + 1), text)

    return units, chapter_overview, footnotes_all


# ── File generation ────────────────────────────────────────────────────────────

def render_unit(unit):
    lines = []
    label = unit.get("label", "")
    vr = unit.get("verse_range") or label
    # Render date-label heading outside the unit box
    if label and unit.get("verse_range"):
        lines.append(f'<div class="mh-date-heading">{html_escape(label)}</div>\n')
    lines.append('<div class="mh-unit">')
    if vr:
        lines.append(f'<div class="mh-verse">{html_escape(vr)}</div>')
    lines.append('<div class="mh-unit-body">')

    # Check if first body para is roman-section or not
    body = unit["body"]
    # Group by roman sections
    current_section = None
    section_paras = []

    def flush_section(lines, current_section, section_paras):
        if current_section is not None:
            lines.append(f'<div class="mh-l1"><span class="mh-label">{current_section}.</span>')
            for pt in section_paras:
                lines.append(f"<p>{html_escape(pt)}</p>")
            lines.append("</div>")
        else:
            for pt in section_paras:
                lines.append(render_body_para(pt).rstrip())

    for pt in body:
        m = ROMAN_RE.match(pt.strip())
        if m:
            flush_section(lines, current_section, section_paras)
            current_section = m.group(1)
            rest = pt.strip()[m.end():].strip()
            section_paras = [rest] if rest else []
        else:
            section_paras.append(pt)

    flush_section(lines, current_section, section_paras)

    lines.append("</div>")  # mh-unit-body
    lines.append("</div>")  # mh-unit
    return "\n".join(lines) + "\n"


def make_chapter_md(book_id, book_name, chapter_num, total_chapters, header_img,
                    units, chapter_overview, footnotes, date_str):
    cn = num_to_chinese(chapter_num)
    parts = []
    parts.append(f"""---
layout: mhenry-chapter
book_id: {book_id}
book_name: {book_name}
chapter: {chapter_num}
total_chapters: {total_chapters}
header-img: {header_img}
date: {date_str}
---

## 第{cn}章

""")
    # Build overview text: from chapter_overview field + any leading no-range units
    overview_lines = []
    if chapter_overview:
        overview_lines.append(html_escape(chapter_overview))

    # Absorb leading units with no verse_range as overview content
    remaining_units = list(units)
    while remaining_units and not remaining_units[0].get("verse_range"):
        u = remaining_units.pop(0)
        for t in u.get("body", []):
            if t.strip():
                overview_lines.append(html_escape(t.strip()))

    if overview_lines:
        parts.append(f'<div class="mh-overview">\n{" ".join(overview_lines)}\n</div>\n\n')

    for unit in remaining_units:
        parts.append(render_unit(unit))
        parts.append("\n")

    if footnotes:
        parts.append('<aside class="mhenry-footnotes">\n')
        for num, text in footnotes:
            parts.append(f"<p><sup>{num}</sup> {html_escape(text)}</p>\n")
        parts.append("</aside>\n")

    return "".join(parts)


def make_preface_md(book_id, book_name, header_img, paras, footnotes, date_str):
    body_paras = []
    fn_list = []
    for p in paras:
        t = p["text"].strip()
        kind = classify(p)
        if kind == "footnote":
            m = FOOTNOTE_RE.match(t)
            if m:
                fn_list.append((m.group(1), t[m.start(2):].strip()))
            continue
        if kind in ("body", "overview"):
            body_paras.append(t)

    fn_list.extend(footnotes)

    content = f"""---
layout: mhenry-preface
book_id: {book_id}
book_name: {book_name}
header-img: {header_img}
date: {date_str}
---

"""
    for p in body_paras:
        content += f"<p>{html_escape(p)}</p>\n\n"

    if fn_list:
        content += '<aside class="mhenry-footnotes">\n'
        for num, text in fn_list:
            content += f"<p><sup>{num}</sup> {html_escape(text)}</p>\n"
        content += "</aside>\n"

    return content


# ── Plain-text output (for format_mhenry2.py pipeline) ────────────────────────

_CN_UNITS = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
_CN_TENS  = ['', '十', '二十', '三十', '四十', '五十', '六十', '七十', '八十', '九十']

def num_to_chinese(n):
    if n <= 9:
        return _CN_UNITS[n]
    elif n < 20:
        return '十' + (_CN_UNITS[n % 10] if n % 10 else '')
    else:
        return _CN_TENS[n // 10] + (_CN_UNITS[n % 10] if n % 10 else '')


_BIBLE_BOOK_MAP = {
    'genesis': 'gn', 'exodus': 'ex', 'leviticus': 'lv', 'numbers': 'nm',
    'deuteronomy': 'dt', 'joshua': 'js', 'judges': 'jud', 'ruth': 'rt',
    '1samuel': '1sm', '2samuel': '2sm', '1kings': '1kgs', '2kings': '2kgs',
    '1chronicles': '1ch', '2chronicles': '2ch', 'ezra': 'ezr', 'nehemiah': 'ne',
    'esther': 'et', 'job': 'job', 'psalms': 'ps', 'proverbs': 'prv',
    'ecclesiastes': 'ec', 'songofsolomon': 'so', 'isaiah': 'is', 'jeremiah': 'jr',
    'lamentations': 'lm', 'ezekiel': 'ez', 'daniel': 'dn', 'hosea': 'ho',
    'joel': 'jl', 'amos': 'am', 'obadiah': 'ob', 'jonah': 'jn',
    'micah': 'mi', 'nahum': 'na', 'habakkuk': 'hk', 'zephaniah': 'zp',
    'haggai': 'hg', 'zechariah': 'zc', 'malachi': 'ml',
    'matthew': 'mt', 'mark': 'mk', 'luke': 'lk', 'john': 'jo',
    'acts': 'act', 'romans': 'rm', '1corinthians': '1co', '2corinthians': '2co',
    'galatians': 'gl', 'ephesians': 'eph', 'philippians': 'ph', 'colossians': 'cl',
    '1thessalonians': '1ts', '2thessalonians': '2ts', '1timothy': '1tm', '2timothy': '2tm',
    'titus': 'tt', 'philemon': 'phm', 'hebrews': 'hb', 'james': 'jm',
    '1peter': '1pe', '2peter': '2pe', '1john': '1jo', '2john': '2jo',
    '3john': '3jo', 'jude': 'jd', 'revelation': 're',
}

_bible_cache: dict = {}
try:
    import opencc as _opencc
    _t2s_converter = _opencc.OpenCC('t2s')
except ImportError:
    _t2s_converter = None


def _load_bible_verses_plain(book_id: str, chapter_num: int, v_start: int, v_end: int) -> str:
    """Return 'N verse_text ...' plain text for verses v_start..v_end (inclusive) from Bible JSON.
    Returns empty string on failure. Converts traditional→simplified and removes inter-char spaces."""
    global _bible_cache
    if not _bible_cache:
        bible_path = Path(__file__).parent / 'zh_cuv.json'
        if not bible_path.exists():
            return ''
        with open(bible_path, encoding='utf-8-sig') as f:
            raw = json.load(f)
        for book in raw:
            _bible_cache[book['abbrev']] = book['chapters']
    abbrev = _BIBLE_BOOK_MAP.get(book_id, '')
    chapters = _bible_cache.get(abbrev)
    if not chapters or chapter_num < 1 or chapter_num > len(chapters):
        return ''
    verses = chapters[chapter_num - 1]
    parts = []
    for vi in range(v_start - 1, min(v_end, len(verses))):
        v_text = verses[vi].replace(' ', '').replace('\u3000', '')
        if _t2s_converter:
            v_text = _t2s_converter.convert(v_text)
        parts.append(f"{vi + 1} {v_text}")
    return ' '.join(parts)


def make_chapter_md_plain(book_id, book_name, chapter_num, total_chapters, header_img,
                           paras, date_str):
    """Output plain-text chapter .md for processing by format_mhenry2.py.

    All paragraphs are output as-is (no HTML). format_mhenry2.py will:
      - Strip date labels (主前/主后 pattern)
      - Match scripture against Bible JSON → wrap in mh-verse
      - Detect roman numerals → mh-l1
      - Produce Genesis-style output
    """
    cn = num_to_chinese(chapter_num)
    fm = f"""---
layout: mhenry-chapter
book_id: {book_id}
book_name: {book_name}
chapter: {chapter_num}
total_chapters: {total_chapters}
header-img: {header_img}
date: {date_str}
---

第{cn}章

"""
    body_parts = []
    # Skip initial "orphan" paragraphs that are continuations from the previous chapter.
    # Strategy A: if a real chapter marker appears within the first 3 paragraphs, skip
    # all paragraphs before it (handles Zechariah-style "本章..." overviews).
    # Strategy B: otherwise, use a forward scan and skip only paragraphs that look
    # obviously orphaned (start mid-list/mid-sentence), stopping at the first normal para.
    OBVIOUS_ORPHAN_RE = re.compile(r'^\d+[.、]|^[（(]\d|^，|^；|^就[说叫是有把]')

    def _is_chapter_start(p):
        t = p["text"].strip()
        kind = classify(p)
        return (kind in ("overview", "scripture", "date_label")
                or OVERVIEW_RE.match(t))

    first_real = next((i for i, p in enumerate(paras) if _is_chapter_start(p)), None)
    if first_real == 1:
        # Strategy A: exactly one orphan before a known chapter-start marker → skip it
        effective_paras = paras[1:]
    else:
        # Strategy B: skip only obviously-orphaned leading paragraphs
        skip = 0
        for p in paras:
            if OBVIOUS_ORPHAN_RE.match(p["text"].strip()):
                skip += 1
            else:
                break
        effective_paras = paras[skip:]

    # Pre-process: split hybrid paragraphs where a section date label is followed
    # directly by verse text (e.g. "神谴责祭司（主前400年）6「藐视我名...").
    # Strip the date label prefix and keep only the verse text portion.
    HYBRID_DATE_PREFIX_RE = re.compile(r'^(.{4,50}[（(]主[前后]\d+\s*年[）)])\s*(\d+)')
    split_paras = []
    for p in effective_paras:
        t = p["text"].strip()
        mm = HYBRID_DATE_PREFIX_RE.match(t)
        if mm:
            rest = t[mm.start(2):]
            split_paras.append(dict(p, text=rest))
        else:
            split_paras.append(p)
    effective_paras = split_paras

    # Detect the first verse number that actually appears in the PDF content.
    # A paragraph "starts with a verse" if it begins with digit + space/bracket + CJK.
    VERSE_PARA_START_RE = re.compile(r'^(\d+)[\s「『][\u4e00-\u9fff]')
    first_verse_in_content = None
    first_verse_idx = None
    for idx, p in enumerate(effective_paras):
        mm = VERSE_PARA_START_RE.match(p["text"].strip())
        if mm:
            first_verse_in_content = int(mm.group(1))
            first_verse_idx = idx
            break

    # If the first verse in the PDF is greater than 1, inject Bible verse text for
    # vv 1..(first_verse-1) after the first paragraph (overview summary), so that
    # format_mhenry2.py can create a proper mh-unit for those verses.
    if first_verse_in_content and first_verse_in_content > 1 and first_verse_idx and first_verse_idx >= 1:
        bible_text = _load_bible_verses_plain(book_id, chapter_num, 1, first_verse_in_content - 1)
        if bible_text:
            # Insert after the first paragraph (the introductory overview summary)
            bible_para = {"text": bible_text, "fonts": set()}
            effective_paras = [effective_paras[0], bible_para] + effective_paras[1:]

    # Regex to detect inline footnotes embedded at the end of a paragraph (cross-page PDF artifact).
    # Example: "...对祭1皇帝哈德良：117-138 作罗马帝国的皇帝。" where the footnote definition
    # appears inside the body text because it was on the bottom of a PDF page between two words.
    # Also handles chained footnotes: "...事上1多马...。2钦定本...。3钦定本...。"
    # Lookbehind includes CJK chars and "。" to catch both first and chained footnotes.
    # The $ anchor ensures only matches at end of para (prevents false matches mid-para).
    INLINE_FN_RE = re.compile(r'(?<=[\u4e00-\u9fff\u3002])(\d{1,2})([\u4e00-\u9fff][^。\n]{3,120}[。])\s*$')
    # Sentence-ending characters; para that doesn't end with these may be word-split
    SENTENCE_END_RE = re.compile(r'[。！？」』）\]]\s*$')

    footnotes = []
    pending_text = None  # holds text from a para that ends abruptly (word-split across PDF pages)
    for para in effective_paras:
        t = para["text"].strip()
        if not t:
            continue
        kind = classify(para)
        if kind == "footnote":
            # Parse footnote block — may contain multiple chained footnotes
            # e.g. "1原文...名词。2钦定本...遍地。" → two footnotes
            fn_text = t
            while fn_text:
                fn_m = FOOTNOTE_RE.match(fn_text)
                if not fn_m:
                    break
                rest = fn_text[fn_m.start(2):]
                end_m = re.search(r'。(?=\d)', rest)
                if end_m:
                    footnotes.append((fn_m.group(1), rest[:end_m.start()+1].strip()))
                    fn_text = rest[end_m.start()+1:].strip()
                else:
                    footnotes.append((fn_m.group(1), rest.strip()))
                    fn_text = ''
        elif kind == "date_label":
            # Skip verse labels (John) and Zechariah date labels;
            # format_mhenry2.py handles structure via Bible JSON matching
            continue
        else:
            # Extract inline/chained footnotes from the end of the para (cross-page PDF artifact).
            # Loop to handle multiple chained footnotes (e.g., "1多马...。2钦定本...。3钦定本...。")
            # Each footnote must contain '：' to confirm it's a footnote definition, not body text.
            changed = True
            while changed:
                changed = False
                fn_match = INLINE_FN_RE.search(t)
                if fn_match and fn_match.start() > 5 and '：' in fn_match.group(2):
                    footnotes.append((fn_match.group(1), fn_match.group(2).strip()))
                    t = (t[:fn_match.start()] + t[fn_match.end():]).strip()
                    changed = True

            # Merge with pending text from a word-split in previous para
            if pending_text is not None:
                t = pending_text + t
                pending_text = None

            # If this para ends abruptly (no sentence ending, last char is CJK),
            # it may be a word-split — hold it and merge with the next para
            if t and not SENTENCE_END_RE.search(t) and re.search(r'[\u4e00-\u9fff]$', t):
                pending_text = t
            else:
                body_parts.append(t)

    if pending_text is not None:
        body_parts.append(pending_text)

    content = fm + "\n\n".join(body_parts)
    if footnotes:
        content += "\n\n"
        for num, text in footnotes:
            content += f"\n{num}\n{text}\n"
    return content + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_section_arg(arg):
    """Parse 'chap_or_preface:start[:end]' -> (label, start, end)"""
    parts = arg.split(":")
    label = parts[0]   # chapter number or 'preface'/'2' for preface
    start = int(parts[1])
    end   = int(parts[2]) if len(parts) > 2 else start
    return label, start, end


def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    # Optional --plain flag: output raw text instead of HTML (for format_mhenry2.py pipeline)
    plain_mode = "--plain" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--plain"]

    pdf_path   = Path(argv[0]).expanduser()
    book_id    = argv[1]
    book_name  = argv[2]
    header_img = argv[3]
    section_args = argv[4:]

    if not pdf_path.exists():
        sys.exit(f"PDF not found: {pdf_path}")

    pdf = fitz.open(str(pdf_path))
    total_pages = len(pdf)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    out_dir = Path(OUT_BASE) / book_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse section args: first one is preface if label is 'preface' or non-digit
    sections = [parse_section_arg(a) for a in section_args]

    # Separate preface and chapters
    preface_section = None
    chapter_sections = []
    for label, start, end in sections:
        if label.lower() == "preface" or not label.isdigit():
            preface_section = (start, end)
        else:
            chapter_sections.append((int(label), start, end))

    total_chapters = max(ch for ch, _, _ in chapter_sections) if chapter_sections else 1

    print(f"Processing: {book_name} ({book_id})")
    print(f"PDF: {pdf_path.name} ({total_pages} pages)")
    print(f"Date: {date_str}")

    # ── Preface ──
    if preface_section:
        start, end = preface_section
        print(f"\nPreface: pages {start}-{end}")
        paras = extract_pages(pdf, start, end)
        # Filter out header/chapter indicator
        filtered = [p for p in paras if not HEADER_RE.match(p["text"].strip())]
        fn_extra = []
        md = make_preface_md(book_id, book_name, header_img, filtered, fn_extra, date_str)
        out_path = out_dir / "preface.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"  → {out_path}")

    # ── Chapters ──
    for ch_num, start, end in chapter_sections:
        print(f"\nChapter {ch_num}: pages {start}-{end}")
        # Check if pages have enough text
        sample_page = pdf[start - 1]
        use_ocr = not is_text_page(sample_page, min_chars=50)
        if use_ocr:
            print(f"  Text-layer poor, using OCR...")
        paras = extract_pages(pdf, start, end, use_ocr=use_ocr)
        print(f"  {len(paras)} paragraphs extracted")

        if plain_mode:
            md = make_chapter_md_plain(
                book_id, book_name, ch_num, total_chapters, header_img,
                paras, date_str
            )
            print(f"  plain-text mode")
        else:
            units, ch_overview, footnotes = paras_to_mh_units(paras, ch_num)
            print(f"  {len(units)} units, {len(footnotes)} footnotes")
            md = make_chapter_md(
                book_id, book_name, ch_num, total_chapters, header_img,
                units, ch_overview, footnotes, date_str
            )
        out_path = out_dir / f"{ch_num}.md"
        out_path.write_text(md, encoding="utf-8")
        print(f"  → {out_path}")

    print(f"\nDone. Files written to {out_dir}/")


if __name__ == "__main__":
    main()
