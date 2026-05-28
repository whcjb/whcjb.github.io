#!/usr/bin/env python3
"""
Extract Calvin's Commentary on the Harmony of the Evangelists (Vol. 2)
PDF: /Users/yanpeifa/Documents/论文/calvin_matai_make.pdf
CCEL format with parallel gospel verse columns (2-column or 3-column per section).
"""
import fitz
import re
import os

PDF_PATH = "/Users/yanpeifa/Documents/论文/calvin_matai_make2.pdf"
OUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/matthew/matthew_raw.txt"
SKIP_PAGES = 7        # pages 1-7: title, about, TOC
HEADER_Y_MAX = 55     # running page header zone
FOOTNOTE_SIZE_MAX = 7.5   # footnotes ~6.3pt (French) and ~6.6pt (English cont.)


_LINE_BREAK = {"__line_break__": True}


def get_block_text(block):
    lines = []
    for line in block.get("lines", []):
        lines.append("".join(s["text"] for s in line.get("spans", [])))
    return "\n".join(lines)


def spans_to_md(block):
    """Convert block lines to markdown preserving bold/italic spans.
    Uses _LINE_BREAK sentinels to prevent words merging across lines."""
    all_spans = []
    lines = block.get("lines", [])
    for li, line in enumerate(lines):
        all_spans.extend(line.get("spans", []))
        if li < len(lines) - 1:
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
        is_superscript = bool(flags & 1)
        is_bold = bool(flags & 16)
        is_italic = bool(flags & 2)

        stripped = t.strip()
        if not stripped:
            if t and parts and not parts[-1].endswith(' '):
                parts.append(' ')
            i += 1
            continue

        # Inline footnote reference: superscript + small size + digit-only content
        if is_superscript and stripped.isdigit() and span.get("size", 99) < FOOTNOTE_SIZE_MAX + 2:
            parts.append(f"<sup>{stripped}</sup>")
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


def get_first_span(block):
    lines = block.get("lines", [])
    if not lines:
        return None
    spans = lines[0].get("spans", [])
    return spans[0] if spans else None


def get_first_nonempty_span(block):
    """Return the first span with non-whitespace text (skips leading NBSP/space spans)."""
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            if span.get("text", "").strip():
                return span
    return None


def is_page_header(block):
    if block["bbox"][1] > HEADER_Y_MAX:
        return False
    text = get_block_text(block).strip()
    return "John Calvin" in text or bool(re.match(r'^\d+$', text))


def is_page_number(block):
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text):
        return False
    span = get_first_span(block)
    return span is not None and span.get("size", 0) <= 10


def is_footnote_block(block):
    span = get_first_span(block)
    return span is not None and span.get("size", 0) < FOOTNOTE_SIZE_MAX


def is_section_header(block):
    """Primary section header: large text (size>=18), centered (x0>100).
    Non-bold serifed (flags=4) for most section headers.
    Contains scripture book references like MATTHEW/MARK/LUKE."""
    span = get_first_span(block)
    if not span:
        return False
    if span.get("size", 0) < 18:
        return False
    if block["bbox"][0] < 100:
        return False
    text = get_block_text(block).strip().upper()
    return bool(re.search(r'(MATTHEW|MARK|LUKE|JOHN|HARMONY)', text))


def is_col_label_block(block):
    """Column label sub-header: bold+serifed (flags=20), size 14-17.
    Contains book:chapter references like 'Luke 7:18-23'.
    x0 threshold lowered to 50 to catch left-aligned multi-line col labels."""
    span = get_first_span(block)
    if not span:
        return False
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    if not (14 <= size <= 17):
        return False
    if not (flags & 16):  # must be bold
        return False
    if block["bbox"][0] < 50:
        return False
    text = get_block_text(block).strip()
    return bool(re.search(r'(Matthew|Mark|Luke|John)\s+\d+:\d+', text))


def extract_col_info(block):
    """Extract column label positions: list of (label, x0) sorted left→right.
    Each LINE of the col label block is one column's label.
    Used to determine split thresholds for verse table columns."""
    cols = []
    for line in block.get("lines", []):
        lx0 = line["bbox"][0]
        text = "".join(s["text"] for s in line.get("spans", []))
        text = text.strip()
        if text:
            cols.append((text, lx0))
    return sorted(cols, key=lambda c: c[1])


def is_verse_block(block):
    """Gospel verse text: bold (flags & 16), size ~12.
    First span starts with 'N.' or just 'N' (period may be in next span)."""
    span = get_first_span(block)
    if not span:
        return False
    flags = span.get("flags", 0)
    size = span.get("size", 0)
    if not (flags & 16):  # bold
        return False
    if size < 10 or size > 14:
        return False
    t = span["text"].strip()
    # Accept digit-only span (period in next span) as well as digit+period/NBSP
    return bool(re.match(r'^\d+([.\xa0]|$)', t))


def is_index_start(block):
    """Detect start of appendix/index sections."""
    text = get_block_text(block).strip()
    return bool(re.match(r'^Indexes?$', text, re.IGNORECASE)) or \
           bool(re.match(r'^Index of ', text, re.IGNORECASE)) or \
           text.startswith('•')


def is_decoration(block):
    """Skip standalone decoration words like '\xa0COMMENTARY'."""
    text = get_block_text(block).strip().lstrip('\xa0').strip()
    return text in ('COMMENTARY', 'ON A', 'VOLUME SECOND')


def normalize_header(text):
    return re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()


def compute_col_splits(col_info):
    """Compute split x-thresholds from column label positions.
    Returns list of split points; len = len(col_info) - 1.
    E.g. 2 cols → [split1]; 3 cols → [split1, split2]."""
    if len(col_info) < 2:
        return [290]  # fallback for unlabeled 2-col sections
    xs = [x for _, x in col_info]
    return [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]


def assign_col(line_x0, splits):
    """Return 0-based column index for a line given split thresholds."""
    for i, s in enumerate(splits):
        if line_x0 < s:
            return i
    return len(splits)


def build_verse_table(section_header, verse_blocks, col_info):
    """Build HTML table with parallel gospel columns.
    Uses LINE-level x0 and dynamic split thresholds derived from col_info."""

    splits = compute_col_splits(col_info)
    n_cols = len(splits) + 1

    # Collect lines per column
    col_lines = [[] for _ in range(n_cols)]

    for block in verse_blocks:
        for line in block.get("lines", []):
            line_x0 = line["bbox"][0]
            line_text = "".join(s["text"] for s in line.get("spans", []))
            line_text = re.sub(r'\s+', ' ', line_text.replace('\xa0', ' ')).strip()
            if not line_text:
                continue
            ci = assign_col(line_x0, splits)
            is_verse_start = bool(re.match(r'^\d+\.?\s', line_text))
            col_lines[ci].append((is_verse_start, line_text))

    def lines_to_rows(lines):
        rows = []
        current = []
        for is_start, text in lines:
            if current and is_start:
                rows.append(' '.join(current))
                current = [text]
            else:
                current.append(text)
        if current:
            rows.append(' '.join(current))
        return rows

    col_rows = [lines_to_rows(lines) for lines in col_lines]

    if not any(col_rows):
        return ''

    max_rows = max(len(r) for r in col_rows)
    for r in col_rows:
        while len(r) < max_rows:
            r.append('')

    # Column headers from col_info (show only book/chapter, not verse range)
    if col_info:
        col_labels = [c[0] for c in col_info]
    else:
        col_labels = [''] * n_cols

    html = ['<table class="calvin-scripture">']
    # Span header across all columns
    html.append(f'<thead><tr><th colspan="{n_cols}" style="text-align:center">{section_header}</th></tr></thead>')
    if any(col_labels):
        header_cells = ''.join(f'<th>{lbl}</th>' for lbl in col_labels)
        html.append(f'<thead><tr>{header_cells}</tr></thead>')
    html.append('<tbody>')

    for row_idx in range(max_rows):
        cells = [col_rows[ci][row_idx] for ci in range(n_cols)]
        non_empty = sum(1 for c in cells if c)
        if non_empty == 0:
            continue
        if non_empty == 1 and n_cols > 1:
            # Single-gospel row: use colspan
            for ci, cell in enumerate(cells):
                if cell:
                    html.append(f'<tr><td colspan="{n_cols}">{cell}</td></tr>')
                    break
        else:
            row = ''.join(f'<td>{c}</td>' for c in cells)
            html.append(f'<tr>{row}</tr>')

    html.append('</tbody></table>')
    return '\n'.join(html)


def process_pdf():
    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"Total pages: {total}, skipping first {SKIP_PAGES}")

    output_blocks = []
    pending_continuation = None

    in_verse_section = False
    current_section_header = None
    current_col_info = []
    verse_buf = []

    def flush_verse_buf():
        nonlocal verse_buf
        if verse_buf and current_section_header:
            table = build_verse_table(current_section_header, verse_buf, current_col_info)
            if table:
                output_blocks.append(table)
        verse_buf = []

    def handle_commentary(block):
        nonlocal pending_continuation
        rich = spans_to_md(block)
        rich = re.sub(r'-\s+([a-z])', r'\1', rich)  # merge hyphenated words
        if not rich:
            return
        if rich.endswith('-'):
            pending_continuation = (pending_continuation or '') + rich[:-1]
        else:
            if pending_continuation:
                rich = pending_continuation + rich
                pending_continuation = None
            output_blocks.append(rich)

    for page_idx in range(SKIP_PAGES, total):
        page = doc[page_idx]
        blocks = sorted(
            page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"],
            key=lambda b: b["bbox"][1])

        for block in blocks:
            if block["type"] != 0:
                continue
            if is_page_header(block):
                continue
            if is_page_number(block):
                continue
            if is_footnote_block(block):
                continue
            if is_decoration(block):
                continue

            text = get_block_text(block).strip()
            if not text:
                continue

            if is_index_start(block):
                print(f"Stopping at index on page {page_idx + 1}")
                flush_verse_buf()
                if pending_continuation:
                    output_blocks.append(pending_continuation)
                doc.close()
                write_output(output_blocks)
                return

            if is_section_header(block):
                flush_verse_buf()
                current_section_header = normalize_header(text)
                current_col_info = []
                output_blocks.append(f"\n## {current_section_header}\n")
                in_verse_section = True

            elif is_col_label_block(block):
                current_col_info = extract_col_info(block)

            elif in_verse_section and is_verse_block(block):
                verse_buf.append(block)

            elif in_verse_section:
                # Non-verse-number block: verse continuation (non-bold first real span)
                # or commentary start (bold "Matthew N:N." marker).
                # Must use get_first_nonempty_span to skip leading NBSP spans.
                first_span = get_first_nonempty_span(block)
                if verse_buf and first_span and not bool(first_span.get("flags", 0) & 16):
                    verse_buf.append(block)
                else:
                    flush_verse_buf()
                    in_verse_section = False
                    handle_commentary(block)

            else:
                handle_commentary(block)

    flush_verse_buf()
    if pending_continuation:
        output_blocks.append(pending_continuation)
    doc.close()
    write_output(output_blocks)


def write_output(blocks):
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        for block in blocks:
            f.write(block + '\n\n')
    print(f"Written: {OUT_PATH}")
    print(f"Total blocks: {len(blocks)}")
    tables = sum(1 for b in blocks if '<table class="calvin-scripture">' in b)
    print(f"Tables: {tables}")


if __name__ == "__main__":
    process_pdf()
