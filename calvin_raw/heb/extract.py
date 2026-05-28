#!/usr/bin/env python3
"""
Extract Calvin's Commentary on Hebrews (bilingual table format).
PDF: /Users/yanpeifa/Documents/论文/calvin_xibolaishu.pdf
Scripture verses → HTML table with English | Latin columns.
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_xibolaishu.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/heb/heb_raw.txt"
SKIP_PAGES = 8

HEADER_Y_MAX = 55
LATIN_X_MIN  = 200   # lines at x>=200 are Latin column


def get_first_span(block):
    lines = block.get("lines", [])
    if not lines:
        return None
    spans = lines[0].get("spans", [])
    return spans[0] if spans else None


def get_block_text(block):
    lines = []
    for line in block.get("lines", []):
        lines.append("".join(s["text"] for s in line.get("spans", [])))
    return "\n".join(lines)


def is_page_header(block):
    if block["bbox"][1] > HEADER_Y_MAX:
        return False
    text = get_block_text(block).strip()
    if "John Calvin" in text or "Comm on Hebrews" in text or "Commentary on Hebrews" in text:
        return True
    if re.match(r'^\d+$', text):
        return True
    return False


def is_page_number(block):
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text):
        return False
    span = get_first_span(block)
    return span is not None and span.get("size", 0) <= 10


def is_footnote_block(block):
    """Footnote definition blocks: size < 10pt anywhere on page."""
    span = get_first_span(block)
    if span and span.get("size", 0) < 10:
        return True
    text = get_block_text(block).strip()
    if not text:
        return True
    return False


def is_pure_latin_block(block):
    """Block entirely in the Latin column (bx0 >= LATIN_X_MIN)."""
    return block["bbox"][0] >= LATIN_X_MIN


def is_decorative_header(block):
    """Large decorative titles to skip."""
    span = get_first_span(block)
    if not span:
        return False
    if span.get("size", 0) < 14:
        return False
    text = get_block_text(block).strip().upper()
    patterns = [
        r'^COMMENTAR', r'^CHAPTER\s+\d', r'^THE\s+ARGUMENT',
        r'^TRANSLATOR', r'^DEDICATOR', r'^TO\s+THE\s+',
        r'^EPISTLE\s+', r'^PREFACE',
    ]
    return any(re.match(p, text) for p in patterns)


def is_scripture_header(block):
    """Scripture section header: 'Hebrews N:M' or 'Hebrews Chapter N:M', bold-italic."""
    span = get_first_span(block)
    if not span:
        return False
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    x0 = block["bbox"][0]
    if size >= 14 and (flags & 20) and 80 < x0 < 300:
        text = get_block_text(block).strip()
        if re.match(r'^Hebrews\s+(Chapter\s+)?\d+:\d+', text):
            return True
    return False


def normalize_scripture_header(text):
    """Remove 'Chapter' from 'Hebrews Chapter N:M' → 'Hebrews N:M'."""
    return re.sub(r'^(Hebrews)\s+Chapter\s+', r'\1 ',
                  text.replace("\n", " ").strip())


def is_verse_block(block):
    """
    Verse text block: first English-column line starts with bold-italic digit (size>=10).
    Handles combined bilingual blocks AND English-only narrow blocks.
    """
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        if not spans:
            continue
        lx = line["bbox"][0]
        if lx >= LATIN_X_MIN:
            continue  # skip Latin lines, look for first English line
        fs = spans[0]
        flags = fs.get("flags", 0)
        size = fs.get("size", 0)
        t = fs["text"].strip()
        # Verse numbers are bold (flags&4), 12pt; footnote refs are 6.6pt
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            return True
        break  # first English line is not a verse number → not a verse block
    return False


def is_appendix_start(text):
    return re.match(r'^(APPENDIX|INDEX)', text.strip().upper()) is not None


# ── Line-level rich-text extraction ───────────────────────────────────────────

def extract_line_rich(line):
    """
    Extract rich text from a single line, wrapping bold verse numbers as **N.**.
    Handles the split case where digit ('1') and period ('. God...') are in separate spans.
    Returns: (rich_text_string)
    """
    spans = [s for s in line.get("spans", []) if s.get("text", "")]
    if not spans:
        return ""
    parts = []
    skip_dot = False
    for span in spans:
        text = span["text"]
        flags = span.get("flags", 0)
        size = span.get("size", 0)
        t = text.strip()
        if skip_dot:
            skip_dot = False
            if text.startswith('.'):
                text = text[1:]  # strip period only, keep space
            parts.append(text)
            continue
        # Bold verse number: digit+period OR digit-only (period in next span)
        # Size >= 10 to exclude footnote reference superscripts (6.6pt)
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            num = t.rstrip('.')
            parts.append(f"**{num}.**")
            if not t.endswith('.'):
                skip_dot = True
        else:
            parts.append(text)
    return "".join(parts).strip()


def extract_english_lines(block):
    """
    Extract only English-column lines (lx < LATIN_X_MIN) with rich formatting.
    Used for commentary blocks.
    """
    parts = []
    for line in block.get("lines", []):
        if line["bbox"][0] >= LATIN_X_MIN:
            continue
        text = extract_line_rich(line)
        if text:
            parts.append(text)
    return " ".join(parts).strip()


# ── Verse table building ───────────────────────────────────────────────────────

def build_verse_table(section_header, verse_blocks):
    """
    Build HTML table with English | Latin columns from a list of verse PDF blocks.
    Each row is one verse.
    """
    verses = {}   # {verse_num (int): {'en': [], 'la': []}}

    for block in verse_blocks:
        cur_en = None
        cur_la = None

        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            lx = line["bbox"][0]
            line_text = extract_line_rich(line)
            if not line_text:
                continue

            # Detect verse number at start of line
            vn_m = re.match(r'\*\*(\d+)\.\*\*', line_text)

            if lx >= LATIN_X_MIN:
                if vn_m:
                    cur_la = int(vn_m.group(1))
                if cur_la is not None:
                    verses.setdefault(cur_la, {'en': [], 'la': []})['la'].append(line_text)
            else:
                if vn_m:
                    cur_en = int(vn_m.group(1))
                if cur_en is not None:
                    verses.setdefault(cur_en, {'en': [], 'la': []})['en'].append(line_text)

    if not verses:
        return ''

    def md_to_html(text):
        text = text.replace('|', '&#124;')
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text

    html = ['<table class="calvin-scripture">']
    html.append(f'<thead><tr><th colspan="2" style="text-align:center">{section_header}</th></tr></thead>')
    html.append('<tbody>')
    for vn in sorted(verses.keys()):
        en = md_to_html(' '.join(verses[vn].get('en', [])))
        la = md_to_html(' '.join(verses[vn].get('la', [])))
        html.append(f'<tr><td>{en}</td><td>{la}</td></tr>')
    html.append('</tbody>')
    html.append('</table>')
    return '\n'.join(html)


# ── Commentary splitting ───────────────────────────────────────────────────────

def split_rich_by_verse(rich):
    """Split rich commentary text at **N.** markers that appear mid-text."""
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]


# ── Main extraction ────────────────────────────────────────────────────────────

def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, skipping first {SKIP_PAGES}")

    output_blocks = []
    pending_continuation = None

    # State machine for verse sections
    in_verse_section = False
    current_section_header = None
    verse_buf = []

    def flush_verse_buf():
        nonlocal verse_buf
        if verse_buf and current_section_header:
            table = build_verse_table(current_section_header, verse_buf)
            if table:
                output_blocks.append(table)
        verse_buf = []

    def handle_commentary(rich):
        nonlocal pending_continuation
        if rich.endswith("-"):
            pending_continuation = (pending_continuation or "") + rich[:-1]
        else:
            if pending_continuation:
                rich = pending_continuation + rich
                pending_continuation = None
            for sub in split_rich_by_verse(rich):
                output_blocks.append(sub)

    for page_idx in range(SKIP_PAGES, total):
        page = doc[page_idx]
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks = sorted(page_dict["blocks"], key=lambda b: b["bbox"][1])

        for block in blocks:
            if block["type"] != 0:
                continue
            if is_page_header(block):
                continue
            if is_page_number(block):
                continue
            if is_footnote_block(block):
                continue
            if is_decorative_header(block):
                continue

            text = get_block_text(block).strip()
            if not text:
                continue

            if is_appendix_start(text):
                print(f"Stopping at appendix/index on page {page_idx + 1}")
                flush_verse_buf()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                doc.close()
                write_output(output_blocks)
                return

            if is_scripture_header(block):
                # Flush previous verse section and start new one
                flush_verse_buf()
                current_section_header = normalize_scripture_header(text)
                # Keep ## marker for chapter grouping in publish script
                output_blocks.append(f"\n## {current_section_header}\n")
                in_verse_section = True

            elif in_verse_section and (is_pure_latin_block(block) or is_verse_block(block)):
                # Collect verse blocks (both English-only, Latin-only, and combined bilingual)
                verse_buf.append(block)

            elif in_verse_section:
                # Commentary starts → flush verse buffer, then handle commentary
                flush_verse_buf()
                in_verse_section = False
                rich = extract_english_lines(block)
                if not rich:
                    rich = get_block_text(block).replace("\n", " ").strip()
                if rich:
                    handle_commentary(rich)

            else:
                # Already in commentary section
                if is_pure_latin_block(block):
                    continue  # skip stray Latin blocks
                rich = extract_english_lines(block)
                if not rich:
                    rich = get_block_text(block).replace("\n", " ").strip()
                if rich:
                    handle_commentary(rich)

    flush_verse_buf()
    if pending_continuation:
        output_blocks.append(pending_continuation)

    doc.close()
    write_output(output_blocks)


def write_output(blocks):
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for block in blocks:
            f.write(block + "\n\n")
    print(f"Written: {OUT_PATH}")
    print(f"Total blocks: {len(blocks)}")


if __name__ == "__main__":
    process_pdf()
