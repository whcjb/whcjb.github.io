#!/usr/bin/env python3
"""
Extract structured text from calvin_filibi.pdf using PyMuPDF.

Font size thresholds (from analysis):
  28/24/22/20/18: Title page elements (H1)
  24 non-bold:    Section headings like TRANSLATOR'S PREFACE, CHAPTER N (H1)
  16 bold:        Scripture passage headings e.g. PHILIPPIANS 1:7-11 (H2)
  16 non-bold:    Sub-section headings (H2)
  13/12:          Body text at size 12 (BODY); bold number markers in verses
  11:             Verse poetry (VERSE)
  10:             Small caps PAUL, A.D. etc — treated as BODY
  9:              Small caps inline — treated as BODY
  8:              Inline footnote markers AND footnote content markers (FOOTNOTE)
  7:              Rare, treated as FOOTNOTE
"""

import fitz
import re
from collections import defaultdict

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_filibi.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/phil/calvin_filibi_structured.txt"


def classify_span(size: float, font: str, is_bold: bool) -> str:
    """Return a rough classification for a span based on font size."""
    if size >= 22:
        return "H1"
    elif size >= 20:
        return "H1"
    elif size >= 18:
        return "H1"
    elif size == 16 or size > 14:
        return "H2"
    elif size <= 8:
        return "FOOTNOTE_MARKER"
    else:
        return "BODY"


def get_dominant_classification(line_spans):
    """Given spans in a line, determine the dominant non-marker classification."""
    sizes = []
    for span in line_spans:
        text = span["text"].strip()
        if not text:
            continue
        sizes.append(span["size"])
    if not sizes:
        return "BODY", 12.0
    # Use the max size (heading wins)
    max_size = max(sizes)
    if max_size >= 22:
        return "H1", max_size
    elif max_size >= 16:
        return "H2", max_size
    elif max_size == 11:
        return "VERSE", max_size
    else:
        return "BODY", max_size


def reconstruct_page(page, page_num: int) -> list[str]:
    """
    Reconstruct the text of a page as a list of tagged lines.
    Returns list of strings like "[H1] heading text" or "[BODY] body text".
    """
    page_height = page.rect.height
    blocks = page.get_text("dict")["blocks"]

    # Sort blocks by vertical position
    text_blocks = [b for b in blocks if b["type"] == 0]
    text_blocks.sort(key=lambda b: b["bbox"][1])

    output_lines = []
    prev_block_y1 = None

    for block in text_blocks:
        block_y0 = block["bbox"][1]
        block_y1 = block["bbox"][3]
        is_bottom_area = block_y0 > 0.78 * page_height

        # Add blank line between blocks (paragraph break) if there is a gap
        if prev_block_y1 is not None:
            gap = block_y0 - prev_block_y1
            if gap > 8:  # significant gap = paragraph break
                output_lines.append("")

        prev_block_y1 = block_y1

        # Process each line in the block
        block_lines_output = []
        for line in block["lines"]:
            spans = line["spans"]
            if not spans:
                continue

            # Collect non-empty spans
            non_empty_spans = [s for s in spans if s["text"].strip()]
            if not non_empty_spans:
                continue

            # Determine dominant class for this line
            line_class, max_size = get_dominant_classification(non_empty_spans)

            # Build full line text, preserving inline footnote markers
            line_text_parts = []
            for span in spans:
                text = span["text"]
                # Include all text including spaces
                if text:
                    line_text_parts.append(text)

            full_line_text = "".join(line_text_parts)

            # Skip lines that are purely whitespace
            if not full_line_text.strip():
                continue

            # Determine final classification for this line
            # Check if this block is in the footnote section (pages 112+)
            # and the line starts with a small-font footnote marker
            if non_empty_spans[0]["size"] <= 8 and non_empty_spans[0]["text"].strip():
                # Could be footnote marker at start of line
                first_text = non_empty_spans[0]["text"].strip()
                # Footnote marker patterns: f1, ft1, Ft1, F1, etc.
                if re.match(r'^[Ff]t?\d+$|^<\d+>$', first_text):
                    line_class = "FOOTNOTE"

            # Override for specific patterns
            stripped = full_line_text.strip()

            # Check if this is a scripture verse block (bold scripture reference like "PHILIPPIANS 1:7-11")
            if max_size >= 16 and any(kw in stripped for kw in ['PHILIPPIANS', 'COLOSSIANS', 'THESSALONIANS']):
                # Check if it has a verse reference (digits with colon)
                if re.search(r'\d+:\d+', stripped) or re.search(r'\d+:\d+', stripped):
                    line_class = "VERSE"

            block_lines_output.append((line_class, full_line_text))

        # Now merge consecutive lines in this block into paragraphs
        # Lines of same class with no gap between them belong together
        if not block_lines_output:
            continue

        # Group consecutive same-class lines
        current_class = block_lines_output[0][0]
        current_texts = [block_lines_output[0][1]]

        for i in range(1, len(block_lines_output)):
            cls, txt = block_lines_output[i]
            if cls == current_class:
                # Merge: join with space if previous doesn't end with hyphen
                prev = current_texts[-1]
                if prev.rstrip().endswith('-'):
                    # Hyphenated word - join without space
                    current_texts[-1] = prev.rstrip()[:-1] + txt.lstrip()
                else:
                    current_texts.append(txt)
            else:
                # Flush current group
                merged = " ".join(t.strip() for t in current_texts if t.strip())
                if merged.strip():
                    output_lines.append(f"[{current_class}] {merged}")
                current_class = cls
                current_texts = [txt]

        # Flush last group
        merged = " ".join(t.strip() for t in current_texts if t.strip())
        if merged.strip():
            output_lines.append(f"[{current_class}] {merged}")

    return output_lines


def main():
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"Processing {total_pages} pages...")

    all_output = []

    for page_num in range(total_pages):
        page = doc[page_num]
        all_output.append(f"\n--- PAGE {page_num + 1} ---\n")

        page_lines = reconstruct_page(page, page_num)
        all_output.extend(page_lines)

    # Write output
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(all_output))
        f.write("\n")

    print(f"Done! Written to: {OUT_PATH}")
    print(f"Total lines: {len(all_output)}")


if __name__ == "__main__":
    main()
