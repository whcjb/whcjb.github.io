"""
Calvin on 1 Corinthians (Vol. 1) — PDF 提取脚本
格式：每页脚注在页底，双列 scripture 表，单列 commentary
"""
import fitz, re, os

PDF_PATH   = "/Users/yanpeifa/Documents/论文/calvin_gelinduo1.pdf"
OUTPUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/ocr_output/1cor-vol1/calvin_1cor-vol1.md"

doc = fitz.open(PDF_PATH)

TABLE_SPLIT_X = 305   # x < 305 = English (left), x >= 305 = Latin (right)

# ── Span helpers ──────────────────────────────────────────────────────────────
def span_text(span):
    return span['text']

def is_bold(span):
    return bool(span['flags'] & 16)   # bit 4 = bold

def is_italic(span):
    return bool(span['flags'] & 2)    # bit 1 = italic

def is_superscript(span):
    return bool(span['flags'] & 1)    # bit 0 = superscript

def is_right_col(span):
    return span['bbox'][0] >= TABLE_SPLIT_X

def is_footnote_ref(span):
    """Inline footnote reference: small digit in body text.
    Body refs are size ~6.6 (vs definition labels size ~6.3).
    Some refs lack the superscript flag (e.g., in Latin column), so use size
    range rather than flag: 6.4–7.5pt digit = footnote ref."""
    t = span['text'].strip()
    if not t.isdigit():
        return False
    return (is_superscript(span) and span['size'] < 8) or (6.4 <= span['size'] <= 7.5)

def is_footnote_def_block(block):
    """Footnote definition block: all spans ≤ 9.5pt AND at least one span is a
    small non-superscript digit (footnote label).  The label need not be first —
    some blocks begin with cross-page continuation text (9pt) before the next label."""
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans:
        return False
    # ALL spans must be small text (no 12pt body text)
    if not all(s['size'] <= 9.5 for s in spans):
        return False
    # Must contain at least one footnote label
    return any(s['size'] < 7 and s['text'].strip().isdigit() and not is_superscript(s)
               for s in spans)

def is_running_header(block):
    return block['bbox'][1] < 58

def is_page_number(block):
    if block['bbox'][1] < 725:
        return False
    text = ''.join(s['text'] for l in block['lines'] for s in l['spans']).strip()
    return bool(re.match(r'^\d+$', text))

def split_block_by_size(block):
    """Split a block into virtual sub-blocks where font size changes significantly
    (e.g., a chapter heading merged with body intro text by PyMuPDF).
    Returns a list of block-like dicts with the same keys as a real block.

    Special case: ascending-size decorative title blocks (small → medium → H1) are
    collapsed to emit only the H1-size lines, discarding decorative smaller lines.
    """
    # Detect ascending-size title block: starts with body (<14pt) but contains H1 (≥24pt)
    lines_with_spans = [(line, next((s for s in line['spans'] if s['text'].strip()), None))
                        for line in block['lines']]
    sizes = [fs['size'] for _, fs in lines_with_spans if fs is not None]
    if sizes and sizes[0] < 14 and max(sizes) >= 24:
        # Keep only H1-size lines
        h1_lines = [line for line, fs in lines_with_spans
                    if fs is not None and fs['size'] >= 24]
        if h1_lines:
            return [_make_sub_block(block, h1_lines)]

    groups = []
    current_lines = []
    current_size = None

    for line in block['lines']:
        first_span = next((s for s in line['spans'] if s['text'].strip()), None)
        if first_span is None:
            current_lines.append(line)
            continue
        sz = first_span['size']
        # Start a new group when size changes by > 2pt
        if current_size is not None and abs(sz - current_size) > 2:
            if current_lines:
                groups.append(_make_sub_block(block, current_lines))
            current_lines = [line]
        else:
            current_lines.append(line)
        current_size = sz

    if current_lines:
        groups.append(_make_sub_block(block, current_lines))

    return groups if groups else [block]

def _make_sub_block(orig_block, lines):
    if not lines:
        return orig_block
    y0 = lines[0]['bbox'][1] if lines[0]['bbox'] else orig_block['bbox'][1]
    y1 = lines[-1]['bbox'][3] if lines[-1]['bbox'] else orig_block['bbox'][3]
    return {
        'type': 0,
        'bbox': [orig_block['bbox'][0], y0, orig_block['bbox'][2], y1],
        'lines': lines,
    }

def is_table_header(block):
    """'1 Corinthians N:M-K' type header, size ~16.8."""
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    first = block['lines'][0]['spans'][0]
    return abs(first['size'] - 16.8) < 0.6

def is_h1(block):
    """Chapter heading (size ≥ 24)."""
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return block['lines'][0]['spans'][0]['size'] >= 24

def is_h2(block):
    """Section header size 14–23."""
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    s = block['lines'][0]['spans'][0]['size']
    return 14 <= s < 24

def block_has_right_col(block):
    """A block has right-column content if any LINE starts at x >= TABLE_SPLIT_X.
    Checking line-starts (not any span) prevents false positives from
    word-wrapped commentary text whose continuation spans land past TABLE_SPLIT_X."""
    for line in block['lines']:
        first_spans = [s for s in line['spans'] if s['text'].strip()]
        if first_spans and first_spans[0]['bbox'][0] >= TABLE_SPLIT_X:
            return True
    return False

def block_is_full_width(block):
    """Block is commentary (all lines start in left column)."""
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans: return False
    return not block_has_right_col(block) and block['bbox'][2] > 400

# ── Footnote definition collector ─────────────────────────────────────────────
def collect_footnote_defs(blocks):
    """
    Returns dict: {footnote_number_str → definition_text}
    A single block may contain multiple footnote definitions (102, 103, 104…),
    each starting with a small non-superscript digit label.
    """
    defs = {}
    for b in blocks:
        if not is_footnote_def_block(b):
            continue
        current_num = None
        current_parts = []

        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                if not t:
                    continue
                # A new footnote label: small non-superscript digit
                if t.isdigit() and span['size'] < 7 and not is_superscript(span):
                    # Save previous entry
                    if current_num is not None:
                        defs[current_num] = ' '.join(current_parts).strip()
                    current_num = t
                    current_parts = []
                else:
                    current_parts.append(t)

        # Save last entry
        if current_num is not None:
            defs[current_num] = ' '.join(current_parts).strip()

    return defs

# ── Format inline body text ──────────────────────────────────────────────────
def format_span(span):
    """Convert a body span to Markdown inline text."""
    t = span['text']
    if not t.strip():
        return t
    if is_footnote_ref(span):
        return f'[^{t.strip()}]'
    if is_bold(span) and is_italic(span):
        return f'***{t}***'
    if is_bold(span):
        return f'**{t}**'
    if is_italic(span):
        return f'*{t}*'
    return t

def spans_to_text(spans):
    """Reconstruct text from a list of spans with inline formatting.
    Adds a space between adjacent spans that share no whitespace boundary,
    which handles line-break span transitions in PDF extraction."""
    parts = []
    prev_y = None
    for span in spans:
        part = format_span(span)
        if not part:
            continue
        cur_y = round(span['bbox'][1])
        # Add space if neither previous part ends with space/punct
        # nor this part starts with space/punct
        if parts:
            prev = parts[-1]
            needs_space = (prev and not prev[-1].isspace()
                           and not part[0].isspace()
                           and part[0] not in '.,;:!?)\'"*_-')
            if needs_space:
                parts.append(' ')
        parts.append(part)
        prev_y = cur_y
    result = ''.join(parts)
    # Fix italic markers: move trailing space outside: '*text *' → '*text* '
    result = re.sub(r'\*([^*]+?) \*', r'*\1* ', result)
    # Collapse multiple spaces (including those created by italic fix)
    result = re.sub(r' {2,}', ' ', result)
    return result.strip()

# ── Scripture table builder ──────────────────────────────────────────────────
def build_table(header_text, rows):
    """
    rows: list of (english_text, latin_text)
    """
    hdr = header_text.strip().upper()
    lines = ['', f'<table class="calvin-scripture">',
             f'<thead><tr><th colspan="2" style="text-align:center">{hdr}</th></tr></thead>',
             '<tbody>']
    for en, la in rows:
        en_esc = en.replace('|', '&#124;')
        la_esc = la.replace('|', '&#124;')
        lines.append(f'<tr><td>{en_esc}</td><td>{la_esc}</td></tr>')
    lines.append('</tbody>')
    lines.append('</table>')
    lines.append('')
    return '\n'.join(lines)

def extract_scripture_section(header_block, verse_blocks):
    """
    header_block: the 'N Corinthians X:Y-Z' block
    verse_blocks: list of blocks containing verse spans
    Returns: HTML table string
    """
    header_text = ' '.join(
        s['text'] for l in header_block['lines'] for s in l['spans']
    ).strip()

    # Collect all spans from verse blocks, sorted by y then x
    all_spans = []
    for b in verse_blocks:
        for line in b['lines']:
            for span in line['spans']:
                if span['text'].strip():
                    all_spans.append(span)
    all_spans.sort(key=lambda s: (s['bbox'][1], s['bbox'][0]))

    # Split into left (English) and right (Latin) columns
    left_spans  = [s for s in all_spans if not is_right_col(s)]
    right_spans = [s for s in all_spans if is_right_col(s)]

    def parse_verses(spans):
        """Returns list of (verse_num_str, text_str)"""
        verses = []
        current_num = None
        current_parts = []
        for span in spans:
            t = span['text'].strip()
            # Bold digit(s) followed by '.' = verse number
            if is_bold(span) and re.match(r'^\d+\.$', t):
                if current_num is not None:
                    verses.append((current_num, spans_to_text(current_parts)))
                current_num = t
                current_parts = []
            else:
                current_parts.append(span)
        if current_num is not None:
            verses.append((current_num, spans_to_text(current_parts)))
        return verses

    en_verses = parse_verses(left_spans)
    la_verses = parse_verses(right_spans)

    # Zip by verse number (match on first element)
    en_dict = {v[0]: v[1] for v in en_verses}
    la_dict = {v[0]: v[1] for v in la_verses}
    all_nums = sorted(set(list(en_dict.keys()) + list(la_dict.keys())),
                      key=lambda x: int(x.rstrip('.')))
    rows = []
    for num in all_nums:
        en_text = f'{num} {en_dict.get(num, "")}'.strip()
        la_text = f'{num} {la_dict.get(num, "")}'.strip()
        rows.append((en_text, la_text))

    return build_table(header_text, rows)

# ── Process a single page ─────────────────────────────────────────────────────
def process_page(page, page_num):
    """Returns (body_items, footnote_defs) where each is a list/dict."""
    blocks = page.get_text('dict')['blocks']

    body_blocks = []
    fn_def_blocks = []

    for b in blocks:
        if b['type'] != 0:
            continue
        if is_running_header(b):
            continue
        if is_page_number(b):
            continue
        if is_footnote_def_block(b):
            fn_def_blocks.append(b)
        else:
            # Split blocks where heading and body text are merged
            body_blocks.extend(split_block_by_size(b))

    footnote_defs = collect_footnote_defs(fn_def_blocks)

    # Sort body blocks by y
    body_blocks.sort(key=lambda b: b['bbox'][1])

    # Group body blocks into items
    items = []
    page_h1_count = 0  # track H1s emitted per page; second H1 from ascending block = decoration
    i = 0
    while i < len(body_blocks):
        b = body_blocks[i]
        if is_h1(b):
            if page_h1_count > 0:
                # Second H1 on same page: it came from an ascending-size decorative subtitle block
                # (e.g., "ON THE / FIRST EPISTLE TO THE / CORINTHIANS" after "THE ARGUMENT").
                # Skip it entirely.
                i += 1
                continue
            text = ' '.join(s['text'] for l in b['lines'] for s in l['spans']).strip()
            items.append({'type': 'H1', 'text': text})
            page_h1_count += 1
            i += 1
        elif is_table_header(b):  # must be before is_h2: size 16.8 overlaps h2 range
            # Collect following verse blocks (have right-col content)
            header_block = b
            verse_blocks = []
            j = i + 1
            while j < len(body_blocks):
                nb = body_blocks[j]
                if is_table_header(nb) or is_h1(nb) or is_h2(nb):
                    break
                if block_has_right_col(nb):
                    verse_blocks.append(nb)
                    j += 1
                elif block_is_full_width(nb):
                    break
                else:
                    verse_blocks.append(nb)
                    j += 1
            table_html = extract_scripture_section(header_block, verse_blocks)
            items.append({'type': 'TABLE', 'html': table_html})
            i = j
        elif is_h2(b):
            # Split block: heading-size lines → H2, remaining 12pt lines → BODY
            h2_lines, body_lines = [], []
            for line in b['lines']:
                first_span = next((s for s in line['spans'] if s['text'].strip()), None)
                if first_span and first_span['size'] >= 14:
                    h2_lines.append(line)
                else:
                    body_lines.append(line)
            h2_text = ' '.join(s['text'] for l in h2_lines for s in l['spans']).strip()
            if h2_text:
                items.append({'type': 'H2', 'text': h2_text})
            if body_lines:
                body_spans = [s for l in body_lines for s in l['spans']]
                body_text = spans_to_text(body_spans)
                if body_text:
                    items.append({'type': 'BODY', 'text': body_text})
            i += 1
        else:
            # Body paragraph
            all_spans = [s for l in b['lines'] for s in l['spans']]
            text = spans_to_text(all_spans)
            if text:
                items.append({'type': 'BODY', 'text': text})
            i += 1

    return items, footnote_defs

# ── Main extraction ───────────────────────────────────────────────────────────
all_items = []
all_fn_defs = {}  # num_str → text (accumulated across pages)

for page_num in range(len(doc)):
    # Skip meta/title pages
    SKIP_PAGES = set(range(6)) | {6, 19}  # 0-5: cover/TOC, 6: main title, 19: alt title
    if page_num in SKIP_PAGES:
        continue
    # Stop after chapter 14 ends (page 301)
    if page_num >= 301:
        break

    page = doc[page_num]
    items, fn_defs = process_page(page, page_num)

    all_items.append({'type': 'PAGE', 'num': page_num + 1})
    all_items.extend(items)
    all_fn_defs.update(fn_defs)

# ── Render to Markdown ────────────────────────────────────────────────────────
md_lines = []

for item in all_items:
    t = item['type']
    if t == 'PAGE':
        md_lines.append(f'\n<!-- PAGE {item["num"]} -->\n')
    elif t == 'H1':
        md_lines.append(f'\n# {item["text"]}\n')
    elif t == 'H2':
        md_lines.append(f'\n## {item["text"]}\n')
    elif t == 'TABLE':
        md_lines.append(item['html'])
    elif t == 'BODY':
        text = item['text']
        # Escape line-leading N. patterns
        text = re.sub(r'^(\d+)\. ', lambda m: f'{m.group(1)}\\. ', text)
        # Escape bare | (not inside HTML)
        if '<table' not in text and '<tr' not in text:
            text = text.replace('|', '\\|')
        md_lines.append(f'\n{text}\n')

# Append footnote definitions
if all_fn_defs:
    md_lines.append('\n---\n')
    # Sort by number
    for num in sorted(all_fn_defs.keys(), key=lambda x: int(x)):
        fn_text = all_fn_defs[num]
        fn_text = fn_text.replace('|', '\\|')
        md_lines.append(f'\n[^{num}]: {fn_text}\n')

# Write output
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(''.join(md_lines))

print(f"Done. Written to {OUTPUT_PATH}")
print(f"Total pages processed: {sum(1 for i in all_items if i['type']=='PAGE')}")
print(f"Tables: {sum(1 for i in all_items if i['type']=='TABLE')}")
print(f"Body paragraphs: {sum(1 for i in all_items if i['type']=='BODY')}")
print(f"H1 headers: {sum(1 for i in all_items if i['type']=='H1')}")
print(f"Footnote definitions: {len(all_fn_defs)}")
