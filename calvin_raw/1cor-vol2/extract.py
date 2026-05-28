"""
Calvin on Corinthians Vol. 2 (1 Cor 15-16 + 2 Cor 1-13) — PDF 提取脚本
格式：每页脚注在页底，双列 scripture 表，单列 commentary
源文件：/Users/yanpeifa/Documents/论文/calvin_gelinduo2.pdf
输出：calvin_raw/1cor-vol2/calvin_corinth-vol2.md（含 1 Cor 15-16 和 2 Cor 1-13 全部内容）
"""
import fitz, re, os

PDF_PATH    = "/Users/yanpeifa/Documents/论文/calvin_gelinduo2.pdf"
OUTPUT_PATH = "/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/1cor-vol2/calvin_corinth-vol2.md"

doc = fitz.open(PDF_PATH)

TABLE_SPLIT_X = 305

# ── Ages Digital Library Greek converter ──────────────────────────────────────
# Ages uses a private encoding for Greek. PyMuPDF gives ASCII transliteration.
# Mapping: consonants direct; j=smooth breathing; >=acute; <=grave; ~=circumflex;
# |=iota subscript; v=terminal sigma; diacritics belong to the preceding vowel.
def convert_ages_greek(text):
    """Convert Ages Digital Library ASCII Greek transliteration to Unicode."""
    VOWELS = set('aehiouAEHIOU')
    CONSMAP = {'b': 'β', 'g': 'γ', 'd': 'δ', 'z': 'ζ', 'q': 'θ', 'k': 'κ',
               'l': 'λ', 'm': 'μ', 'n': 'ν', 'x': 'ξ', 'p': 'π', 'r': 'ρ',
               's': 'σ', 'v': 'ς', 't': 'τ', 'f': 'φ', 'c': 'χ', 'y': 'ψ',
               'B': 'Β', 'G': 'Γ', 'D': 'Δ', 'Z': 'Ζ', 'Q': 'Θ', 'K': 'Κ',
               'L': 'Λ', 'M': 'Μ', 'N': 'Ν', 'X': 'Ξ', 'P': 'Π', 'R': 'Ρ',
               'S': 'Σ', 'T': 'Τ', 'F': 'Φ', 'C': 'Χ', 'Y': 'Ψ'}
    VMAP = {
        'a': 'α', 'e': 'ε', 'h': 'η', 'i': 'ι', 'o': 'ο', 'u': 'υ', 'w': 'ω',
        'A': 'Α', 'E': 'Ε', 'H': 'Η', 'I': 'Ι', 'O': 'Ο', 'U': 'Υ', 'W': 'Ω',
    }
    # Detect Greek words: sequences of ASCII letters mixed with ><~|j
    import unicodedata
    def is_greek_word(token):
        return bool(re.search(r'[a-zA-Z][><~|j]|[j][aehiouAEHIOUw]|[aehiouAEHIOUwbgdzkqlmnxprsfcyvtBGDZKQLMNXPRSFCYVT]{3,}', token))

    # Simpler heuristic: look for tokens containing Ages diacritics mixed with letters
    def convert_token(token):
        # Only convert if the token looks like Ages Greek
        if not re.search(r'[><~|j]', token):
            return token
        result = []
        i = 0
        chars = list(token)
        while i < len(chars):
            c = chars[i]
            if c == 'j':  # smooth breathing — attach to next vowel
                i += 1
                continue
            if c in VMAP:
                base = VMAP[c]
                # Collect following diacritics
                diacritics = []
                j = i + 1
                while j < len(chars) and chars[j] in '><~|j':
                    diacritics.append(chars[j])
                    j += 1
                i = j
                # Apply combining diacritics via unicodedata (simplified: just map common combos)
                combined = base
                for d in diacritics:
                    if d == '>':
                        combined += '\u0301'  # acute
                    elif d == '<':
                        combined += '\u0300'  # grave
                    elif d == '~':
                        combined += '\u0342'  # circumflex
                    elif d == '|':
                        combined += '\u0345'  # iota subscript
                combined = unicodedata.normalize('NFC', combined)
                result.append(combined)
            elif c in CONSMAP:
                result.append(CONSMAP[c])
                i += 1
            elif c in '><~|':
                # Stray diacritic — skip
                i += 1
            else:
                result.append(c)
                i += 1
        return ''.join(result)

    # Apply conversion only to potential Greek tokens (between HTML tags is safe to skip)
    # Split on HTML tags first to avoid corrupting them
    parts = re.split(r'(<[a-zA-Z/!][^>]*>)', text)
    out = []
    for part in parts:
        if part.startswith('<'):
            out.append(part)
        else:
            # Convert runs of letters+diacritics that look like Ages Greek
            out.append(re.sub(r'[a-zA-Z][a-zA-Z><~|j]*(?:[><~|j][a-zA-Z]*)*',
                               lambda m: convert_token(m.group()) if re.search(r'[><~|j]', m.group()) else m.group(),
                               part))
    return ''.join(out)   # x < 305 = English (left), x >= 305 = Latin (right)

# ── Span helpers ──────────────────────────────────────────────────────────────
def is_bold(span):
    return bool(span['flags'] & 16)

def is_italic(span):
    return bool(span['flags'] & 2)

def is_superscript(span):
    return bool(span['flags'] & 1)

def is_right_col(span):
    return span['bbox'][0] >= TABLE_SPLIT_X

def is_footnote_ref(span):
    """Inline footnote reference: small digit in body text.
    Body refs are size ~6.6 (vs definition labels size ~6.3).
    Some refs lack the superscript flag, so use size range: 6.4–7.5pt digit."""
    t = span['text'].strip()
    if not t.isdigit():
        return False
    return (is_superscript(span) and span['size'] < 8) or (6.4 <= span['size'] <= 7.5)

def is_footnote_def_block(block):
    """Footnote definition block: all spans ≤ 9.5pt AND at least one small non-superscript digit."""
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans:
        return False
    if not all(s['size'] <= 9.5 for s in spans):
        return False
    return any(s['size'] < 7 and s['text'].strip().isdigit() and not is_superscript(s)
               for s in spans)

def is_running_header(block):
    return block['bbox'][1] < 58

def is_page_number(block):
    if block['bbox'][1] < 725:
        return False
    text = ''.join(s['text'] for l in block['lines'] for s in l['spans']).strip()
    return bool(re.match(r'^\d+$', text))

def _make_sub_block(orig_block, lines):
    if not lines:
        return orig_block
    y0 = lines[0]['bbox'][1]
    y1 = lines[-1]['bbox'][3]
    return {'type': 0, 'bbox': [orig_block['bbox'][0], y0, orig_block['bbox'][2], y1], 'lines': lines}

def split_block_by_size(block):
    """Split a block where font size changes >2pt between lines.
    Ascending-size decorative title blocks (start <14pt, contain ≥24pt) are
    collapsed to only the H1-size lines."""
    lines_with_spans = [(line, next((s for s in line['spans'] if s['text'].strip()), None))
                        for line in block['lines']]
    sizes = [fs['size'] for _, fs in lines_with_spans if fs is not None]
    if sizes and sizes[0] < 14 and max(sizes) >= 24:
        h1_lines = [line for line, fs in lines_with_spans if fs is not None and fs['size'] >= 24]
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

def block_has_right_col(block):
    for line in block['lines']:
        first_spans = [s for s in line['spans'] if s['text'].strip()]
        if first_spans and first_spans[0]['bbox'][0] >= TABLE_SPLIT_X:
            return True
    return False

def block_is_full_width(block):
    spans = [s for l in block['lines'] for s in l['spans'] if s['text'].strip()]
    if not spans: return False
    return not block_has_right_col(block) and block['bbox'][2] > 400

def split_block_by_verse_number(block):
    if block_has_right_col(block):
        return [block]
    if not block_is_full_width(block):
        return [block]
    groups = []
    current_lines = []
    for i, line in enumerate(block['lines']):
        first_spans = [s for s in line['spans'] if s['text'].strip()]
        if i > 0 and first_spans:
            s = first_spans[0]
            if (bool(s['flags'] & 16) and not bool(s['flags'] & 2)
                    and re.match(r'^\d+\.$', s['text'].strip())):
                if current_lines:
                    groups.append(_make_sub_block(block, current_lines))
                current_lines = [line]
                continue
        current_lines.append(line)
    if current_lines:
        groups.append(_make_sub_block(block, current_lines))
    return groups if len(groups) > 1 else [block]

def split_block_by_paragraph_indent(block):
    if block_has_right_col(block):
        return [block]
    if not block_is_full_width(block):
        return [block]

    block_x0 = block['bbox'][0]
    INDENT_LOW, INDENT_HIGH = 10, 60
    BODY_SIZE_MIN = 11.0

    groups = []
    current_lines = []
    first_nonempty_seen = False
    prev_was_deep = False

    for line in block['lines']:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            current_lines.append(line)
            continue
        x0 = spans[0]['bbox'][0]
        size = spans[0]['size']
        indent = x0 - block_x0
        is_deep = indent > INDENT_HIGH and size >= BODY_SIZE_MIN
        first_char = spans[0]['text'].lstrip()[:1]
        is_para_start = (
            first_nonempty_seen
            and size >= BODY_SIZE_MIN
            and (
                (INDENT_LOW <= indent <= INDENT_HIGH)
                or (is_deep and not prev_was_deep and not first_char.islower())
            )
        )
        if is_para_start and current_lines:
            groups.append(_make_sub_block(block, current_lines))
            current_lines = []
        current_lines.append(line)
        first_nonempty_seen = True
        prev_was_deep = is_deep
    if current_lines:
        groups.append(_make_sub_block(block, current_lines))
    return groups if len(groups) > 1 else [block]

def is_table_header(block):
    """'N Corinthians X:Y-Z' type header, size ~16.8."""
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    first = block['lines'][0]['spans'][0]
    return abs(first['size'] - 16.8) < 0.6

def is_h1(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    return block['lines'][0]['spans'][0]['size'] >= 24

def is_h2(block):
    if not block['lines'] or not block['lines'][0]['spans']:
        return False
    s = block['lines'][0]['spans'][0]['size']
    return 14 <= s < 24

# ── Footnote definition collector ─────────────────────────────────────────────
def collect_footnote_defs(blocks):
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
                if t.isdigit() and span['size'] < 7 and not is_superscript(span):
                    if current_num is not None:
                        defs[current_num] = ' '.join(current_parts).strip()
                    current_num = t
                    current_parts = []
                else:
                    current_parts.append(t)
        if current_num is not None:
            defs[current_num] = ' '.join(current_parts).strip()
    return defs

# ── Format inline body text ──────────────────────────────────────────────────
def format_span(span):
    t = span['text']
    if not t.strip():
        return t
    if is_footnote_ref(span):
        return f'[^{t.strip()}]'
    if is_bold(span) and is_italic(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}***{t.strip()}***{tail}'
    if is_bold(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}**{t.strip()}**{tail}'
    if is_italic(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}*{t.strip()}*{tail}'
    return t

def spans_to_text(spans):
    parts = []
    for span in spans:
        part = format_span(span)
        if not part:
            continue
        if parts:
            prev = parts[-1]
            needs_space = (prev and not prev[-1].isspace()
                           and not part[0].isspace()
                           and part[0] not in '.,;:!?)\'"_-')
            if needs_space:
                parts.append(' ')
        parts.append(part)
    result = ''.join(parts)
    result = re.sub(r' {2,}', ' ', result)
    return result.strip()

# ── Scripture table builder ──────────────────────────────────────────────────
def _fnref_to_html(text):
    text = re.sub(r'\[\^(\d+)\]',
                  lambda m: f'<sup><a href="#fn:{m.group(1)}" id="fnref:{m.group(1)}">{m.group(1)}</a></sup>',
                  text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<em><strong>\1</strong></em>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text

def build_table(header_text, rows):
    hdr = header_text.strip().upper()
    lines = ['', '<table class="calvin-scripture">',
             f'<thead><tr><th colspan="2" style="text-align:center">{hdr}</th></tr></thead>',
             '<tbody>']
    for en, la in rows:
        en_esc = _fnref_to_html(en.replace('|', '&#124;'))
        la_esc = _fnref_to_html(la.replace('|', '&#124;'))
        lines.append(f'<tr><td>{en_esc}</td><td>{la_esc}</td></tr>')
    lines.append('</tbody>')
    lines.append('</table>')
    lines.append('')
    return '\n'.join(lines)

def extract_scripture_section(header_block, verse_blocks):
    header_text = ' '.join(
        s['text'] for l in header_block['lines'] for s in l['spans']
    ).strip()

    all_spans = []
    for b in verse_blocks:
        for line in b['lines']:
            for span in line['spans']:
                if span['text'].strip():
                    all_spans.append(span)
    all_spans.sort(key=lambda s: (s['bbox'][1], s['bbox'][0]))

    left_spans  = [s for s in all_spans if not is_right_col(s)]
    right_spans = [s for s in all_spans if is_right_col(s)]

    def parse_verses(spans):
        """Parse verse spans into (verse_num, text) pairs.
        Handles two span formats used in Ages Digital Library PDFs:
          Format A (1 Cor style):  bold span '1.' → verse number with period
          Format B (2 Cor style):  bold span '1'  → verse number without period,
                                   followed by span '. text...'
        """
        verses = []
        current_num = None
        current_parts = []
        for span in spans:
            t = span['text'].strip()
            # Match "1." (format A) or "1" (format B) — period is optional
            if is_bold(span) and re.match(r'^\d+\.?$', t):
                if current_num is not None:
                    verses.append((current_num, spans_to_text(current_parts)))
                current_num = t.rstrip('.')  # normalize: "1." → "1"
                current_parts = []
            else:
                current_parts.append(span)
        if current_num is not None:
            verses.append((current_num, spans_to_text(current_parts)))
        return verses

    en_verses = parse_verses(left_spans)
    la_verses  = parse_verses(right_spans)

    en_dict = {v[0]: v[1] for v in en_verses}
    la_dict = {v[0]: v[1] for v in la_verses}
    all_nums = sorted(set(list(en_dict.keys()) + list(la_dict.keys())),
                      key=lambda x: int(x))
    rows = []
    for num in all_nums:
        # Strip leading '. ' from verse text (format B: '. Paul...' → 'Paul...')
        en_raw = en_dict.get(num, '')
        la_raw = la_dict.get(num, '')
        if en_raw.startswith('. '):
            en_raw = en_raw[2:]
        if la_raw.startswith('. '):
            la_raw = la_raw[2:]
        en_text = f'{num}. {en_raw}'.strip() if en_raw else f'{num}.'
        la_text = f'{num}. {la_raw}'.strip() if la_raw else f'{num}.'
        rows.append((en_text, la_text))

    return build_table(header_text, rows)

# ── Process a single page ─────────────────────────────────────────────────────
def process_page(page, page_num, pending_header=None):
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
            for sub in split_block_by_size(b):
                for sub2 in split_block_by_verse_number(sub):
                    body_blocks.extend(split_block_by_paragraph_indent(sub2))

    footnote_defs = collect_footnote_defs(fn_def_blocks)
    body_blocks.sort(key=lambda b: b['bbox'][1])

    pending_header_out = None
    if pending_header is not None:
        if isinstance(pending_header, dict) and 'header' in pending_header:
            carry_header = pending_header['header']
            prev_verses  = pending_header['verses']
        else:
            carry_header = pending_header
            prev_verses  = []

        new_verses = []
        for b in body_blocks:
            if is_table_header(b) or is_h1(b) or is_h2(b):
                break
            if block_is_full_width(b):
                break
            new_verses.append(b)

        all_carry_verses = prev_verses + new_verses
        table_html = extract_scripture_section(carry_header, all_carry_verses)
        body_blocks = body_blocks[len(new_verses):]
        carried_table = {'type': 'TABLE', 'html': table_html}
    else:
        carried_table = None

    items = []
    if carried_table is not None:
        items.append(carried_table)

    page_h1_count = 0
    i = 0
    while i < len(body_blocks):
        b = body_blocks[i]
        if is_h1(b):
            if page_h1_count > 0:
                i += 1
                continue
            text = ' '.join(s['text'] for l in b['lines'] for s in l['spans']).strip()
            items.append({'type': 'H1', 'text': text})
            page_h1_count += 1
            i += 1
        elif is_table_header(b):
            header_block = b
            verse_blocks = []
            j = i + 1
            hit_commentary = False
            while j < len(body_blocks):
                nb = body_blocks[j]
                if is_table_header(nb) or is_h1(nb) or is_h2(nb):
                    hit_commentary = True
                    break
                if block_has_right_col(nb):
                    verse_blocks.append(nb)
                    j += 1
                elif block_is_full_width(nb):
                    hit_commentary = True
                    break
                else:
                    verse_blocks.append(nb)
                    j += 1
            if not hit_commentary and verse_blocks:
                pending_header_out = {'header': header_block, 'verses': verse_blocks}
            elif not hit_commentary and not verse_blocks:
                pending_header_out = header_block
            else:
                if verse_blocks:
                    table_html = extract_scripture_section(header_block, verse_blocks)
                    items.append({'type': 'TABLE', 'html': table_html})
            i = j
        elif is_h2(b):
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
                    first_indent = 0
                    for line in body_lines:
                        ls = [s for s in line['spans'] if s['text'].strip()]
                        if ls:
                            first_indent = round(ls[0]['bbox'][0] - b['bbox'][0])
                            break
                    items.append({'type': 'BODY', 'text': body_text, 'indent': first_indent})
            i += 1
        else:
            all_spans = [s for l in b['lines'] for s in l['spans']]
            text = spans_to_text(all_spans)
            if text:
                first_indent = 0
                for line in b['lines']:
                    ls = [s for s in line['spans'] if s['text'].strip()]
                    if ls:
                        first_indent = round(ls[0]['bbox'][0] - b['bbox'][0])
                        break
                items.append({'type': 'BODY', 'text': text, 'indent': first_indent})
            i += 1

    return items, footnote_defs, pending_header_out

# ── Main extraction ───────────────────────────────────────────────────────────
all_items = []
all_fn_defs = {}

# Skip pages 0-5 (title, about, TOC pages)
SKIP_PAGES = set(range(6))

pending_header = None
for page_num in range(len(doc)):
    if page_num in SKIP_PAGES:
        continue

    page = doc[page_num]
    items, fn_defs, pending_header = process_page(page, page_num, pending_header)

    all_items.append({'type': 'PAGE', 'num': page_num + 1})
    all_items.extend(items)
    all_fn_defs.update(fn_defs)

# ── Stage 1.5: merge paragraph fragments split across page/block boundaries ───
PARA_INDENT_LOW = 10

def is_sentence_end(text):
    stripped = text.rstrip().rstrip('"\'')
    return not stripped or stripped[-1] in '.!?…'

idx = 0
while idx < len(all_items):
    if all_items[idx]['type'] == 'BODY':
        j = idx + 1
        while j < len(all_items) and all_items[j]['type'] == 'PAGE':
            j += 1
        if j < len(all_items) and all_items[j]['type'] == 'BODY':
            cur = all_items[idx]['text']
            nxt = all_items[j]['text']
            nxt_indent = all_items[j].get('indent', 0)
            cur_has_open_paren = bool(re.search(r'\([^)]*$', cur.rstrip()))
            if (nxt_indent < PARA_INDENT_LOW and not is_sentence_end(cur)) \
                    or (cur_has_open_paren and not is_sentence_end(cur)):
                all_items[idx]['text'] = cur.rstrip() + ' ' + nxt.lstrip()
                all_items[idx]['indent'] = min(
                    all_items[idx].get('indent', 0),
                    all_items[j].get('indent', 0))
                del all_items[j]
                continue
    idx += 1

# ── Stage 1.6: move leading footnote refs from paragraph start to previous end ─
idx = 0
while idx < len(all_items):
    if all_items[idx]['type'] == 'BODY':
        text = all_items[idx]['text']
        m_prefix = re.match(r'^(\[\^\d+\])\s+', text)
        m_solo   = re.match(r'^(\[\^\d+\])$', text.strip())
        if m_prefix or m_solo:
            fn_ref = (m_prefix or m_solo).group(1)
            rest   = text[m_prefix.end():] if m_prefix else ''
            prev_idx = idx - 1
            while prev_idx >= 0 and all_items[prev_idx]['type'] == 'PAGE':
                prev_idx -= 1
            if prev_idx >= 0 and all_items[prev_idx]['type'] == 'BODY':
                all_items[prev_idx]['text'] = all_items[prev_idx]['text'].rstrip() + fn_ref
                if rest:
                    all_items[idx]['text'] = rest
                else:
                    del all_items[idx]
                    continue
    idx += 1

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
        text = convert_ages_greek(text)
        text = re.sub(r'^(\d+)\. ', lambda m: f'{m.group(1)}\\. ', text)
        if '<table' not in text and '<tr' not in text:
            text = text.replace('|', '\\|')
        md_lines.append(f'\n{text}\n')
        if item.get('indent', 0) > 20:
            md_lines.append('{: style="text-align: center"}\n')

# Append footnote definitions
if all_fn_defs:
    md_lines.append('\n---\n')
    for num in sorted(all_fn_defs.keys(), key=lambda x: int(x)):
        fn_text = all_fn_defs[num]
        fn_text = convert_ages_greek(fn_text)
        fn_text = fn_text.replace('|', '\\|')
        md_lines.append(f'\n[^{num}]: {fn_text}\n')

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(''.join(md_lines))

print(f"Done. Written to {OUTPUT_PATH}")
print(f"Total pages processed: {sum(1 for i in all_items if i['type']=='PAGE')}")
print(f"Tables: {sum(1 for i in all_items if i['type']=='TABLE')}")
print(f"Body paragraphs: {sum(1 for i in all_items if i['type']=='BODY')}")
print(f"H1 headers: {sum(1 for i in all_items if i['type']=='H1')}")
print(f"Footnote definitions: {len(all_fn_defs)}")
