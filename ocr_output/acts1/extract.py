#!/usr/bin/env python3
"""
Extract Calvin's Commentary on Acts Vol 1 (Acts 1-13)
PDF: /Users/yanpeifa/Documents/论文/calvin_acts1.pdf
Format: CCEL (English only, no Latin column)
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_acts1.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/acts1/acts1_raw.txt"
SKIP_PAGES = 6  # first 6 pages are title/TOC

# Thresholds
HEADER_Y_MAX = 55       # page running header
FOOTER_Y_MIN = 705      # footnote area
PAGE_W = 612            # standard letter width
CENTER_X = PAGE_W / 2

def get_block_text(block):
    """Get all text from a block, preserving span structure."""
    lines = []
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        line_text = ""
        for span in spans:
            line_text += span["text"]
        lines.append(line_text)
    return "\n".join(lines)

def get_first_span(block):
    """Get first span of first line."""
    lines = block.get("lines", [])
    if not lines:
        return None
    spans = lines[0].get("spans", [])
    if not spans:
        return None
    return spans[0]

def is_scripture_header(block):
    """Scripture section header: centered, large, bold-italic."""
    span = get_first_span(block)
    if not span:
        return False
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    x = block["bbox"][0]
    # centered block: x around 200-350
    if size >= 14 and flags & 20 and x > 180 and x < 360:
        text = get_block_text(block).strip()
        # Must look like "Acts N:M" or "Acts N:M-P" or "Acts N:M, P"
        if re.match(r'^Acts\s+\d+:\d+', text):
            return True
    return False

def is_page_header(block):
    """Running page header: 'John Calvin' or 'Comm on Acts' near top."""
    y0 = block["bbox"][1]
    if y0 > HEADER_Y_MAX:
        return False
    text = get_block_text(block).strip()
    if "John Calvin" in text or "Comm on Acts" in text or "Commentary on Acts" in text:
        return True
    # Also skip page numbers at top
    if re.match(r'^\d+$', text):
        return True
    return False

def is_page_number(block):
    """Page number block: centered at bottom or single number."""
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text):
        return False
    span = get_first_span(block)
    if span and span.get("size", 0) <= 10:
        return True
    return False

def is_footnote_block(block):
    """Footnote block: near bottom of page, first span very small."""
    y0 = block["bbox"][1]
    if y0 < FOOTER_Y_MIN:
        return False
    span = get_first_span(block)
    if span and span.get("size", 0) < 8:
        return True
    # Also a rule line (no text)
    text = get_block_text(block).strip()
    if not text:
        return True
    return False

def is_verse_block(block):
    """
    Verse text block: x≈74, first span is bold+italic 'N.' at x≈90.
    flags=20 means bold+italic (4+16=20).
    """
    x0 = block["bbox"][0]
    if x0 < 65 or x0 > 85:
        return False
    # Check first span: bold+italic digit
    lines = block.get("lines", [])
    if not lines:
        return False
    first_spans = lines[0].get("spans", [])
    if not first_spans:
        return False
    fs = first_spans[0]
    flags = fs.get("flags", 0)
    text = fs["text"].strip()
    # bold (4) or bold+italic (20) with digit number
    if (flags & 4) and re.match(r'^\d+\.$', text):
        return True
    return False

def extract_block_rich(block):
    """
    Extract block text, preserving bold for verse numbers.
    Returns plain text with **N.** for bold verse numbers.
    """
    parts = []
    for line in block.get("lines", []):
        line_parts = []
        for span in line.get("spans", []):
            text = span["text"]
            flags = span.get("flags", 0)
            t = text.strip()
            # Bold+italic verse number
            if (flags & 4) and re.match(r'^\d+\.$', t):
                line_parts.append(f"**{t}**")
            else:
                line_parts.append(text)
        parts.append("".join(line_parts))
    return " ".join(parts).strip()

def is_index_start(text):
    """Detect start of index section at end of book."""
    t = text.strip().upper()
    return t in ("INDEX", "INDEX OF SCRIPTURE REFERENCES", "SUBJECT INDEX", "INDEX OF SUBJECTS")

def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, skipping first {SKIP_PAGES}")

    output_blocks = []
    pending_continuation = None  # text that may continue on next page

    for page_idx in range(SKIP_PAGES, total):
        page = doc[page_idx]
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks = sorted(page_dict["blocks"], key=lambda b: b["bbox"][1])

        page_blocks = []
        for block in blocks:
            if block["type"] != 0:  # only text blocks
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
                # flush pending
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
                # Clean up scripture header text
                clean = text.replace("\n", " ").strip()
                output_blocks.append(f"\n## {clean}\n")
            elif is_verse_block(block):
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                    pending_continuation = None
                rich = extract_block_rich(block)
                output_blocks.append(rich)
            else:
                # Commentary paragraph block
                rich = extract_block_rich(block)
                # Check if this ends with a hyphen (word wrapped across page)
                if rich.endswith("-"):
                    # Will try to merge with next block
                    pending_continuation = rich[:-1]  # remove hyphen
                else:
                    if pending_continuation:
                        # Merge: this is a continuation
                        merged = pending_continuation + rich
                        output_blocks.append(merged)
                        pending_continuation = None
                    else:
                        output_blocks.append(rich)

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
