#!/usr/bin/env python3
"""
Extract Calvin's Commentary on the Harmony of the Evangelists (Vol. 1)
PDF: /Users/yanpeifa/Documents/论文/calvin_matai_make1.pdf
CCEL single-column format.
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_matai_make1.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/matthew1/matthew1_raw.txt"
SKIP_PAGES = 29       # skip pages 1-29 (title, TOC, CCEL notice, prefaces, title page)
HEADER_Y_MAX = 62     # running page header zone
FOOTNOTE_SIZE_MAX = 9.5
PAGE_NUM_X_MIN = 450  # page numbers at far right
PAGE_W = 612.0        # page width
BODY_LEFT = 108.0     # normal body text left margin
BODY_RIGHT = 504.0    # normal body text right margin


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


def is_running_header(block):
    """Italic text at very top of page."""
    if block["bbox"][1] > HEADER_Y_MAX:
        return False
    span = get_first_span(block)
    return span is not None and bool(span.get("flags", 0) & 2)


def is_page_number(block):
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text):
        return False
    return block["bbox"][0] > PAGE_NUM_X_MIN


def is_footnote(block):
    span = get_first_span(block)
    return span is not None and span.get("size", 0) < FOOTNOTE_SIZE_MAX


def is_index_start(block):
    """Scripture index pages — stop processing here."""
    text = get_block_text(block).strip()
    return bool(re.match(r'^Index of (Scripture|Greek|Hebrew|Latin|French)', text, re.I))


def is_section_header(block):
    """ALL CAPS section header starting with a gospel book name.
    Check only first span for all-caps (second span may be blue/mixed-case,
    e.g. 'MATTHEW 6:14-15; Mark 11:25-26' where 'Mark...' is a blue span)."""
    span = get_first_span(block)
    if not span:
        return False
    if span.get("color", 0) != 0:  # first span must be black
        return False
    if span.get("size", 0) < 10.0:
        return False
    first_text = span["text"].strip()
    if not first_text or first_text != first_text.upper():
        return False
    return bool(re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', first_text))


def is_blue_label(block):
    """Blue NON-BOLD label (color=255, not bold).
    These are section subtitle labels to skip or use as fallback headers.
    Blue BOLD blocks are body text and are not detected here."""
    span = get_first_span(block)
    if not span:
        return False
    if span.get("color", 0) != 255:
        return False
    if span.get("flags", 0) & 16:  # bold → body text, not a label
        return False
    return True


def normalize_section_text(text):
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()


_LINE_BREAK = {"__line_break__": True}


def spans_to_md(lines):
    """Convert block lines to markdown, preserving bold/italic.
    Normalizes verse number pattern: bold-digit + period → **N.**"""
    all_spans = []
    for line_idx, line in enumerate(lines):
        all_spans.extend(line.get("spans", []))
        if line_idx < len(lines) - 1:
            all_spans.append(_LINE_BREAK)  # sentinel between lines

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]

        # Handle line-boundary sentinel: add space if needed
        if span is _LINE_BREAK:
            if parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        t = span["text"]
        flags = span.get("flags", 0)
        is_bold = bool(flags & 16)
        is_italic = bool(flags & 2)

        # Normalize verse number: bold-digits + optional non-bold-period + optional bold-NBSP
        if is_bold and re.match(r'^\d+$', t.strip()):
            num = t.strip()
            j = i + 1
            # skip any line-break sentinels
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional non-bold period
            if (j < len(all_spans)
                    and all_spans[j] is not _LINE_BREAK
                    and all_spans[j]["text"].strip() in ('.', '.\xa0', '')
                    and not (all_spans[j]["flags"] & 16)):
                j += 1
            # skip sentinels again
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            # consume optional bold NBSP/whitespace
            while (j < len(all_spans)
                   and all_spans[j] is not _LINE_BREAK
                   and not all_spans[j]["text"].strip()
                   and (all_spans[j]["flags"] & 16)):
                j += 1
            parts.append(f"**{num}.**")
            i = j
            continue

        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]

        if is_bold and is_italic:
            parts.append(f"{lead}***{stripped}***{tail}")
        elif is_bold:
            parts.append(f"{lead}**{stripped}**{tail}")
        elif is_italic:
            parts.append(f"{lead}*{stripped}*{tail}")
        else:
            parts.append(t)
        i += 1

    result = ''.join(parts)
    result = re.sub(r' {2,}', ' ', result)
    return result.strip()


def fix_hyphenation(text):
    """Merge words hyphenated at line boundaries."""
    return re.sub(r'-\s+([a-z])', r'\1', text)


def classify_lines_by_centering(lines):
    """Split block lines into groups of (is_centered, lines).

    Centered lines: narrow (< 50% body width) with center_x ≈ page center.
    Also promotes the immediately preceding quote line (ending with closing quote)
    into the centered group, since in the PDF the scripture quote and its
    reference form a single visual block even though the quote fills full width.
    """
    body_w = BODY_RIGHT - BODY_LEFT
    page_cx = PAGE_W / 2

    # Classify each non-empty line
    classified = []
    for line in lines:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            continue
        lx0 = spans[0]['bbox'][0]
        lx1 = spans[-1]['bbox'][2]
        w = lx1 - lx0
        cx = (lx0 + lx1) / 2
        text = ''.join(s['text'] for s in spans).strip()
        # Narrow AND centered → clearly a centered element (scripture reference etc.)
        is_centered = w < body_w * 0.50 and abs(cx - page_cx) < 30
        classified.append([is_centered, line, text])

    # Promote preceding quote line: if line[i] is centered and line[i-1] ends
    # with a closing quotation mark, treat line[i-1] as centered too.
    for i in range(1, len(classified)):
        if classified[i][0] and not classified[i - 1][0]:
            prev_text = classified[i - 1][2]
            if prev_text.endswith(('"', ',"', ';"', '."', '”', ',”')):
                classified[i - 1][0] = True

    # Group consecutive same-type lines
    groups = []
    for is_centered, line, _text in classified:
        if groups and groups[-1][0] == is_centered:
            groups[-1][1].append(line)
        else:
            groups.append([is_centered, [line]])
    return groups


def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, processing pages {SKIP_PAGES + 1}–{total}")

    output_blocks = []
    # Track current section to detect blue-label-only section starts
    last_section_upper = None

    for page_idx in range(SKIP_PAGES, total):
        page = doc[page_idx]
        blocks = sorted(
            page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"],
            key=lambda b: b["bbox"][1])

        for block in blocks:
            if block["type"] != 0:
                continue
            if is_running_header(block):
                continue
            if is_page_number(block):
                continue
            if is_footnote(block):
                continue

            text = get_block_text(block).strip()
            if not text:
                continue

            if is_index_start(block):
                print(f"Stopping at index on page {page_idx + 1}")
                doc.close()
                write_output(output_blocks)
                return

            if is_section_header(block):
                norm = normalize_section_text(text).upper()
                output_blocks.append(f"\n## {norm}\n")
                last_section_upper = norm
                continue

            if is_blue_label(block):
                label = normalize_section_text(text).upper()
                # Only use as section header if it's a scripture reference
                if not re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', label):
                    continue  # skip non-scripture blue labels
                x0 = block["bbox"][0]
                if x0 > 118:
                    # Header-position blue label (x0≈126): use if different section
                    if label != last_section_upper:
                        output_blocks.append(f"\n## {label}\n")
                        last_section_upper = label
                else:
                    # Subtitle-position blue label (x0≈113): only for very first section
                    if last_section_upper is None:
                        output_blocks.append(f"\n## {label}\n")
                        last_section_upper = label
                continue

            # Body block — split by centered lines
            for is_centered, grp_lines in classify_lines_by_centering(block.get("lines", [])):
                md = spans_to_md(grp_lines)
                md = fix_hyphenation(md)
                if not md:
                    continue
                if is_centered:
                    output_blocks.append(f'<p style="text-align:center">{md}</p>')
                else:
                    output_blocks.append(md)

    doc.close()
    write_output(output_blocks)


def write_output(blocks):
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(block + '\n\n')
    print(f"Written: {OUT_PATH}")
    print(f"Total blocks: {len(blocks)}")
    sections = sum(1 for b in blocks if b.startswith('\n## '))
    print(f"Sections: {sections}")


if __name__ == "__main__":
    process_pdf()
