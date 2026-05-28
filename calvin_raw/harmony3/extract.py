#!/usr/bin/env python3
"""
Extract Calvin's Commentary on the Harmony of the Evangelists (Vol. 3) from CCEL PDF.
Covers Matthew 21:10 – 28, Mark 16, Luke 24 (Passion through Resurrection).
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_matai_make3.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/harmony3/harmony3_raw.txt"
SKIP_PAGES = 8        # skip title, TOC, CCEL notice pages
HEADER_Y_MAX = 62     # running page header zone
FOOTNOTE_SIZE_MAX = 9.5
PAGE_NUM_X_MIN = 450  # page numbers at far right


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
    """Stop at index pages."""
    text = get_block_text(block).strip()
    return bool(re.match(r'^(Indexes?$|Index of (Scripture|Greek|Hebrew|Latin|French))', text, re.I))


def is_section_header(block):
    """ALL CAPS section header starting with a gospel book name.
    Only check first span for all-caps (second span may be mixed-case or blue)."""
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
    In Vol. 3, these are always column-order labels for parallel verse tables.
    Blue BOLD blocks (flags&16) are body text with inline scripture citations."""
    span = get_first_span(block)
    if not span:
        return False
    if span.get("color", 0) != 255:
        return False
    if span.get("flags", 0) & 16:  # bold → body text
        return False
    return True


def normalize_section_text(text):
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    text = re.sub(r':\s+(\d)', r':\1', text)
    return text


_LINE_BREAK = {"__line_break__": True}


def spans_to_md(lines):
    """Convert block lines to markdown, preserving bold/italic.
    Uses _LINE_BREAK sentinels between lines to prevent word merging."""
    all_spans = []
    for line_idx, line in enumerate(lines):
        all_spans.extend(line.get("spans", []))
        if line_idx < len(lines) - 1:
            all_spans.append(_LINE_BREAK)

    parts = []
    i = 0
    while i < len(all_spans):
        span = all_spans[i]

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
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
            if (j < len(all_spans)
                    and all_spans[j] is not _LINE_BREAK
                    and all_spans[j]["text"].strip() in ('.', '.\xa0', '')
                    and not (all_spans[j]["flags"] & 16)):
                j += 1
            while j < len(all_spans) and all_spans[j] is _LINE_BREAK:
                j += 1
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


def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, processing pages {SKIP_PAGES + 1}–{total}")

    output_blocks = []
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
                if not re.match(r'^(MATTHEW|MARK|LUKE|JOHN)\b', label):
                    continue  # skip non-scripture blue labels
                x0 = block["bbox"][0]
                if x0 > 118:
                    if label != last_section_upper:
                        output_blocks.append(f"\n## {label}\n")
                        last_section_upper = label
                else:
                    # subtitle-position: only use for very first section
                    if last_section_upper is None:
                        output_blocks.append(f"\n## {label}\n")
                        last_section_upper = label
                continue

            # Body block
            md = spans_to_md(block.get("lines", []))
            md = fix_hyphenation(md)
            if md:
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
