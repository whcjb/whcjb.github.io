#!/usr/bin/env python3
"""
Extract Calvin's Commentary on Acts Vol 2 (Acts 14-28)
PDF: /Users/yanpeifa/Documents/论文/calvin_acts2.pdf
Format: CCEL (English only, no Latin column)
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_acts2.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/acts2/acts2_raw.txt"
SKIP_PAGES = 6  # first 6 pages are title/TOC

HEADER_Y_MAX = 55
FOOTER_Y_MIN = 705
PAGE_W = 612

def get_block_text(block):
    lines = []
    for line in block.get("lines", []):
        line_text = "".join(span["text"] for span in line.get("spans", []))
        lines.append(line_text)
    return "\n".join(lines)

def get_first_span(block):
    lines = block.get("lines", [])
    if not lines:
        return None
    spans = lines[0].get("spans", [])
    return spans[0] if spans else None

def is_scripture_header(block):
    span = get_first_span(block)
    if not span:
        return False
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    x = block["bbox"][0]
    if size >= 14 and flags & 20 and x > 180 and x < 360:
        text = get_block_text(block).strip()
        if re.match(r'^Acts\s+\d+:\d+', text):
            return True
    return False

def is_page_header(block):
    y0 = block["bbox"][1]
    if y0 > HEADER_Y_MAX:
        return False
    text = get_block_text(block).strip()
    if "John Calvin" in text or "Comm on Acts" in text or "Commentary on Acts" in text:
        return True
    if re.match(r'^\d+$', text):
        return True
    return False

def is_page_number(block):
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text):
        return False
    span = get_first_span(block)
    return span and span.get("size", 0) <= 10

def is_footnote_block(block):
    y0 = block["bbox"][1]
    if y0 < FOOTER_Y_MIN:
        return False
    span = get_first_span(block)
    if span and span.get("size", 0) < 8:
        return True
    text = get_block_text(block).strip()
    return not text

def is_verse_block(block):
    x0 = block["bbox"][0]
    if x0 < 65 or x0 > 85:
        return False
    lines = block.get("lines", [])
    if not lines:
        return False
    first_spans = lines[0].get("spans", [])
    if not first_spans:
        return False
    fs = first_spans[0]
    flags = fs.get("flags", 0)
    text = fs["text"].strip()
    return (flags & 4) and re.match(r'^\d+\.$', text)

def extract_block_rich(block):
    parts = []
    for line in block.get("lines", []):
        line_parts = []
        for span in line.get("spans", []):
            text = span["text"]
            flags = span.get("flags", 0)
            t = text.strip()
            if (flags & 4) and re.match(r'^\d+\.$', t):
                line_parts.append(f"**{t}**")
            else:
                line_parts.append(text)
        parts.append("".join(line_parts))
    return " ".join(parts).strip()

def split_rich_by_verse(rich):
    """Split rich text at **N.** markers that appear mid-text."""
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

def is_index_start(text):
    t = text.strip().upper()
    return t in ("INDEX", "INDEX OF SCRIPTURE REFERENCES", "SUBJECT INDEX", "INDEX OF SUBJECTS")

def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, skipping first {SKIP_PAGES}")

    output_blocks = []
    pending_continuation = None

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

            text = get_block_text(block).strip()
            if not text:
                continue

            if is_index_start(text):
                print(f"Stopping at index page {page_idx + 1}")
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                doc.close()
                write_output(output_blocks)
                return

            if is_scripture_header(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                clean = text.replace("\n", " ").strip()
                output_blocks.append(f"\n## {clean}\n")
            elif is_verse_block(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                rich = extract_block_rich(block)
                output_blocks.append(rich)
            else:
                rich = extract_block_rich(block)
                if rich.endswith("-"):
                    pending_continuation = (pending_continuation or "") + rich[:-1]
                else:
                    if pending_continuation:
                        rich = pending_continuation + rich
                        pending_continuation = None
                    for sub in split_rich_by_verse(rich):
                        output_blocks.append(sub)

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
