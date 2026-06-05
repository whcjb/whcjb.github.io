#!/usr/bin/env python3
"""
extract_prince_v3.py — faithful re-extraction of 正直生活要道
Preserves: sub-headings, numbered lists (N. and （N）), footnotes, translator notes.
"""
import re, os

PDF_TXT = "/tmp/prince.txt"
OUT_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/reading/murray/principles"

# Page ranges (0-indexed into pages[] split by \x0c)
SECTIONS = [
    ("foreword", "序（巴刻）",                                             3,   5),
    ("preface",  "前言",                                                    5,   9),
    ("1",        "第一章　问题导入",                                         9,  22),
    ("2",        "第二章　创造的条例",                                      22,  36),
    ("3",        "第三章　婚姻条例与生养众多",                              36,  63),
    ("4",        "第四章　劳动的条例",                                      63,  81),
    ("5",        "第五章　生命的神圣",                                      81,  93),
    ("6",        "第六章　真理的神圣",                                      93, 113),
    ("7",        "第七章　主的教训",                                       113, 137),
    ("8",        "第八章　律法与恩典",                                     137, 153),
    ("9",        "第九章　圣经伦理动力",                                   153, 173),
    ("10",       "第十章　敬畏神",                                         173, 184),
    ("11",       "附录一　神的儿子和人的女子（创世记6：1-4）",             184, 190),
    ("12",       "附录二　对利未记18章16、18节的附加解释",                 190, 196),
    ("13",       "附录三　对哥林多前书5章1节的附加解释",                   196, 198),
    ("14",       "附录四　美国长老制教会与奴隶制度",                       198, 202),
    ("15",       "附录五　反律主义",                                       202, None),
]

FRONT_MATTER = """\
---
layout: reading-chapter
author_id: murray
author_name: 约翰·慕理
book_id: principles
book_title: 正直生活要道
section: "{section}"
section_title: "{section_title}"
header-img: img/post-bg-2015.jpg
date: 2026-04-29
---
"""

OCR_FIXES = [
    ('⼀一','一'),('⼗〸十','十'),('⼆二','二'),('⼠士','士'),('⽤用','用'),
    ('⽣生','生'),('⾔言','言'),('⾏行','行'),('⼈人','人'),('⽩白','白'),
    ('⾳音','音'),('⾥里','里'),('⾃自','自'),('⼤大','大'),('⼩小','小'),
    ('⼒力','力'),('⽂文','文'),('⽅方','方'),('⾒见','见'),('⾯面','面'),
    ('⾝身','身'),('⾼高','高'),('⽐比','比'),('⻅见','见'),('⼦子','子'),
    ('⼼心','心'),('⼝口','口'),('⼿手','手'),('⽬目','目'),('⼥女','女'),
    ('⽗父','父'),('⺟母','母'),('⻝食','食'),('⾜足','足'),
]

def fix_ocr(text):
    for old, new in OCR_FIXES:
        text = text.replace(old, new)
    return text

def has_ocr(text):
    return any(old in text for old, _ in OCR_FIXES)

# ── Page splitting ──────────────────────────────────────────────────

def split_page(page_text):
    """Return (body_lines, footnote_raw_lines) for one PDF page."""
    lines = page_text.split('\n')
    # Separator: a line made only of \t \xa0 space characters, after body content exists
    sep_idx = len(lines)
    had_content = False
    for i, line in enumerate(lines):
        clean = line.replace('\t','').replace('\xa0','').replace(' ','')
        if clean:
            had_content = True
        if had_content and i > 2 and '\t' in line and not clean:
            sep_idx = i
            break

    body_lines = lines[:sep_idx]

    # Footnote area: after separator, skip spacer lines then read footnotes
    footnote_raw = []
    spacer_done = False
    for line in lines[sep_idx:]:
        if not spacer_done:
            if re.match(r'^[\t\xa0 ]*$', line):
                continue
            spacer_done = True
        # Skip page number lines — they have surrounding spaces/tabs around the number.
        # Bare footnote-number lines like '1' or '2' must NOT be skipped.
        if re.match(r'^[\s\xa0]+\d{1,3}[\s\xa0\t]*$', line):   # leading spaces → page num
            continue
        if re.match(r'^[\s\xa0]*\d{1,3}[\s\xa0\t]+$', line):   # trailing spaces → page num
            continue
        if not spacer_done:
            continue
        footnote_raw.append(line)

    return body_lines, footnote_raw

def parse_footnotes(footnote_raw):
    """Return list of (num_str, text_str) tuples."""
    if not footnote_raw:
        return []
    footnotes = []
    current_num = None
    current_parts = []

    for line in footnote_raw:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^\d{1,2}$', stripped):
            if current_num is not None and current_parts:
                footnotes.append((current_num, fix_ocr(''.join(current_parts))))
            current_num = stripped
            current_parts = []
        else:
            current_parts.append(stripped)

    if current_num is not None and current_parts:
        footnotes.append((current_num, fix_ocr(''.join(current_parts))))

    return footnotes

# ── Line classification helpers ─────────────────────────────────────

def leading_sp(line):
    return len(line) - len(line.lstrip(' '))

def is_chapter_heading_line(line):
    """
    Chapter title artifact lines that should always be filtered:
    - Lines with >40 leading spaces (right-aligned chapter titles in PDF layout)
    - Lines with 14-25 leading spaces that are EXACT chapter/appendix markers
    Short sub-title lines like '创造的条例' are NOT filtered here; they are
    handled in parse_body via content_seen logic (skipped if before first paragraph,
    treated as section sub-headings if after first paragraph).
    """
    s = line.strip()
    if not s:
        return False
    lead = leading_sp(line)
    if lead > 40:
        # List item continuation lines have very high indent (96+) and long content.
        # Chapter headings are short (≤20 chars) or exact chapter/appendix markers.
        # Keep long content lines — they are wide-column list continuations.
        if len(s) > 20:
            return False   # long line → list continuation, keep it
        return True        # short line → chapter heading artifact, filter
    if 14 <= lead <= 25:
        if re.match(r'^(第[一二三四五六七八九十百]+章|附录[一二三四五六]|序|前言)\s*$', s):
            return True
    return False

def try_list_item(line):
    """
    Try to parse a numbered list item from line.
    Returns (num_str, content_str, style) or None.
    style = 'dot' for N. form, 'cn' for （N） form.
    """
    # Wide layout: >=30 leading spaces + N. + >=5 spaces + content
    m = re.match(r'^( {15,}?)(\d{1,2})\.\s{5,}(.+)', line)
    if m:
        return (m.group(2), m.group(3).strip(), 'dot')

    # Regular N. : 4-12 leading
    m = re.match(r'^ {4,12}(\d{1,2})[.．]\s+(.+)', line)
    if m:
        return (m.group(1), m.group(2).strip(), 'dot')

    # （N） Chinese parens
    m = re.match(r'^ {3,12}（(\d{1,2})）\s*(.+)', line)
    if m:
        return (m.group(1), m.group(2).strip(), 'cn')

    # (N) ASCII parens
    m = re.match(r'^ {3,12}\((\d{1,2})\)\s+(.+)', line)
    if m:
        return (m.group(1), m.group(2).strip(), 'dot')

    return None

def is_list_continuation_line(line):
    """Indented continuation of a list item."""
    s = line.strip()
    if not s:
        return False
    lead = leading_sp(line)
    # Very wide (two-column layout continuation)
    if lead >= 60:
        return True
    # Regular continuation indent (10-16 spaces)
    if 9 <= lead <= 16:
        return True
    return False

def is_subheading_line(s, lead):
    """Section sub-heading within a chapter body (single-line block, 14-25 spaces)."""
    if not s or len(s) > 16:
        return False
    if 14 <= lead <= 25:
        # No digits, no brackets — pure Chinese heading text
        if not re.search(r'[\d（）()\[\]]', s):
            if not re.match(r'^(第[一二三四五六七八九十百]+章|附录[一二三四五六])$', s):
                return True
    return False

# ── Block object ────────────────────────────────────────────────────

class Block:
    def __init__(self, kind, content, number=None, style=None):
        self.kind = kind      # 'para' | 'subheading' | 'list_item'
        self.content = content
        self.number = number  # for list_item
        self.style = style    # 'dot' or 'cn'

# ── Body parsing ────────────────────────────────────────────────────

def parse_body(all_body_lines):
    """Parse combined body lines from all pages of a section into Blocks."""

    # Step 1: filter noise lines
    filtered = []
    for line in all_body_lines:
        if is_chapter_heading_line(line):
            filtered.append('')
            continue
        # Skip lines that are only tabs / non-breaking spaces
        if re.match(r'^[\t\xa0 ]*$', line) and '\t' in line:
            continue
        # Skip page number lines
        if re.match(r'^[\s\xa0]*\d{1,3}[\s\xa0\t]*$', line.rstrip()):
            continue
        filtered.append(line)

    # Step 2: group into raw blocks by blank lines
    raw_blocks = []
    cur = []
    for line in filtered:
        if line.strip() == '':
            if cur:
                raw_blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        raw_blocks.append(cur)

    # Step 3: classify each block
    blocks = []
    content_seen = False   # True once a proper paragraph has been emitted

    for bi, block in enumerate(raw_blocks):
        if not block:
            continue
        first = block[0]
        first_s = first.strip()
        first_lead = leading_sp(first)
        # Short single-line block with 14-25 leading spaces, no punctuation:
        #   • Before any real paragraph → chapter title/subtitle → skip
        #   • After real paragraph → section sub-heading → keep as <h3>
        if (len(block) == 1 and is_subheading_line(first_s, first_lead)):
            if not content_seen:
                continue  # chapter subtitle at section start
            blocks.append(Block('subheading', first_s))
            continue

        # Try list item on first line
        li = try_list_item(first)
        if li:
            num, content, style = li
            # Collect continuation lines from rest of block
            cont = [content]
            for line in block[1:]:
                s = line.strip()
                if not s:
                    break
                if is_list_continuation_line(line):
                    cont.append(s)
                else:
                    # Not a continuation — break and handle below (rare)
                    cont.append(s)
            blocks.append(Block('list_item', ''.join(cont), number=num, style=style))
            content_seen = True
            continue

        # Cross-page list item continuation:
        # If previous block is a list_item AND this block's first line is at
        # continuation indent (9-16 spaces, same as list continuation), it is
        # the next sub-paragraph of that list item, split by a page boundary.
        if (blocks and blocks[-1].kind == 'list_item'
                and 9 <= first_lead <= 16
                and not try_list_item(first)):
            parts = [l.strip() for l in block if l.strip()]
            blocks[-1].content += ''.join(parts)
            content_seen = True
            continue

        # Regular paragraph: join all lines
        parts = [l.strip() for l in block if l.strip()]
        if parts:
            blocks.append(Block('para', ''.join(parts)))
            content_seen = True

    return blocks

# ── Cross-page paragraph merging ────────────────────────────────────

ENDS_SENTENCE = re.compile(r'[。！？…」』）】"]\s*$')

def merge_broken_paras(blocks):
    """Merge adjacent blocks when the first ended mid-sentence (page break artifact).
    Handles para+para and list_item+para when the first block has no sentence terminator.
    """
    out = []
    for b in blocks:
        if out and b.kind == 'para' and not ENDS_SENTENCE.search(out[-1].content):
            if out[-1].kind in ('para', 'list_item'):
                out[-1].content += b.content
                continue
        out.append(b)
    return out

# ── Text cleaning ───────────────────────────────────────────────────

def clean(text):
    text = fix_ocr(text)
    # Remove superscript footnote markers after letters before Chinese punctuation
    text = re.sub(r'([^\W\d_])(\d{1,2})([，。；、？！」』）】])', r'\1\3', text, flags=re.UNICODE)
    # Footnote marker between sentences: 。N space → 。
    text = re.sub(r'([。！？])(\d{1,2})(?=\s)', r'\1', text)
    return text.strip()

# ── HTML rendering ──────────────────────────────────────────────────

def render(blocks, footnotes):
    parts = []

    for b in blocks:
        text = clean(b.content)
        if not text:
            continue

        if b.kind == 'subheading':
            parts.append(f'<h3 class="reading-subheading">{text}</h3>')

        elif b.kind == 'list_item':
            if b.style == 'cn':
                num_html = f'（{b.number}）'
            else:
                num_html = f'{b.number}.'
            parts.append(
                f'<div class="reading-list-item">'
                f'<span class="list-num">{num_html}</span>'
                f'<p>{text}</p>'
                f'</div>'
            )

        else:
            parts.append(f'<p>{text}</p>')

    if footnotes:
        fn_items = [f'<p><sup>{n}</sup> {fix_ocr(t)}</p>' for n, t in footnotes]
        parts.append('<aside class="reading-footnotes">\n' + '\n'.join(fn_items) + '\n</aside>')

    return '\n\n'.join(parts)

# ── Main ────────────────────────────────────────────────────────────

def process_section(pages):
    all_body = []
    all_footnotes = []
    for page in pages:
        body_lines, fn_raw = split_page(page)
        all_body.extend(body_lines)
        all_body.append('')  # page boundary as blank
        all_footnotes.extend(parse_footnotes(fn_raw))

    blocks = parse_body(all_body)
    blocks = merge_broken_paras(blocks)
    return render(blocks, all_footnotes)

def main():
    with open(PDF_TXT, 'r', encoding='utf-8') as f:
        text = f.read()
    pages = text.split('\x0c')
    print(f'Loaded {len(pages)} pages')

    for sec_id, sec_title, start, end in SECTIONS:
        sec_pages = pages[start:end]
        html = process_section(sec_pages)
        n_para = html.count('<p>')
        n_fn = html.count('<sup>')
        n_list = html.count('list-item')
        n_h3 = html.count('<h3')
        print(f'  [{sec_id:8}] paras={n_para:3} lists={n_list:3} h3={n_h3} footnotes={n_fn}')

        path = os.path.join(OUT_DIR, f'{sec_id}.md')
        fm = FRONT_MATTER.format(section=sec_id, section_title=sec_title)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fm + '\n' + html + '\n')

    print('Done.')

if __name__ == '__main__':
    main()
