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
OVERVIEW_RE   = re.compile(r"^本章[说讲论介绍]|^本章包含|^这一章")
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
    vr = unit.get("verse_range") or unit.get("label", "")
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
    parts = []
    parts.append(f"""---
layout: mhenry
book_id: {book_id}
book_name: {book_name}
chapter: {chapter_num}
total_chapters: {total_chapters}
header-img: {header_img}
date: {date_str}
---
""")
    if chapter_overview:
        overview_text = html_escape(chapter_overview)
        parts.append(f'<div class="mh-overview">\n{overview_text}\n</div>\n\n')

    for unit in units:
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

    pdf_path   = Path(sys.argv[1]).expanduser()
    book_id    = sys.argv[2]
    book_name  = sys.argv[3]
    header_img = sys.argv[4]
    section_args = sys.argv[5:]

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
