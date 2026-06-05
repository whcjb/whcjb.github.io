#!/usr/bin/env python3
"""extract_quest.py — 寻求更大的事 from OCR"""
import re, os, glob
from datetime import datetime

OCR_DIR   = "/tmp/paul_ocr"
OUT_DIR   = "/Users/yanpeifa/Documents/whcjb.github.io/reading/tripp/quest"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

FRONT_MATTER = """\
---
layout: reading-chapter
author_id: tripp
author_name: 保罗·区普
book_id: quest
book_title: 寻求更大的事
section: "{section}"
section_title: "{section_title}"
header-img: img/post-bg-2015.jpg
date: {timestamp}
---
"""

SECTIONS = [
    ("preface",  "自序　先求他的国",         8,  10),
    ("foreword", "前言　关于这段旅途",       10,  12),
    ("1",  "第1章　寻求更大的事",           18,  32),
    ("2",  "第2章　是多是少？",             32,  44),
    ("3",  "第3章　天大的灾难",             44,  56),
    ("4",  "第4章　欢迎来到我的小王国",     56,  68),
    ("5",  "第5章　发现你的文明",           68,  82),
    ("6",  "第6章　伪装的国度",             82,  94),
    ("7",  "第7章　缩减的动力",             94, 108),
    ("8",  "第8章　万事的中心",            108, 122),
    ("9",  "第9章　迎接你的死亡",          122, 136),
    ("10", "第10章　专注于耶稣",           136, 146),
    ("11", "第11章　叹息",                146, 158),
    ("12", "第12章　爵士乐",              158, 170),
    ("13", "第13章　赦免",                170, 180),
    ("14", "第14章　孤独",                180, 192),
    ("15", "第15章　牺牲",                192, 202),
    ("16", "第16章　忿怒",                202, 212),
    ("17", "第17章　盼望",                212, 222),
    ("18", "第18章　整合的侍奉生命",       222, None),
]

# General "word: definition" subtitle pattern (超越:, 自治:, 国度:, etc.)
# The detect form requires content after the colon; strip form removes just the prefix.
RE_SUBTITLE_DETECT = re.compile(r'^[\u4e00-\u9fff]{1,4}[：:]\s*.+')
RE_SUBTITLE_STRIP  = re.compile(r'^[\u4e00-\u9fff]{1,4}[：:]\s*')
RE_SUBTITLE = RE_SUBTITLE_DETECT   # alias used in sub_idx detection
RE_LEFT_HDR  = re.compile(r'^寻求更大的事')
RE_RIGHT_HDR = re.compile(r'A\s*Quest\s*(?:for\s*More|Questfor)', re.IGNORECASE)
RE_CHAP_HDR  = re.compile(r'^第\s*[0-9一二三四五六七八九十]+\s*章')
RE_PAGE_NUM  = re.compile(r'^\s*\d{1,3}\s*$')
# OCR noise: ≤3 real Chinese characters that don't form a real heading
RE_NOISE_SHORT = re.compile(r'^[\u4e00-\u9fff\s\d\W]{1,3}$')
ENDS_SENT    = re.compile(r'[。！？…"）]\s*$')
# Max chars for a key-quote line; longer lines are body text
KQ_MAX_LINE = 25

def is_header_line(s):
    return (RE_LEFT_HDR.match(s) or RE_RIGHT_HDR.search(s)
            or RE_CHAP_HDR.match(s) or RE_PAGE_NUM.match(s))

def is_noise_line(s):
    if not s:
        return True
    if is_header_line(s):
        return True
    # 1-3 char lines that are pure noise
    if len(s) <= 3:
        return True
    return False

def is_subheading_line(s, para_seen):
    if not para_seen or not s:
        return False
    if len(s) < 3 or len(s) > 22:
        return False
    if s[-1] in '。，；：？！…':
        return False
    if is_header_line(s):
        return False
    return True

def _collect_kq(remaining, start_i):
    """
    Collect key-quote lines from remaining[start_i:].
    Stops at ENDS_SENT match or when a line >= KQ_MAX_LINE chars (body text).
    Returns (kq_text_or_None, next_i).
    """
    kq_lines = []
    i = start_i
    while i < len(remaining):
        if len(remaining[i]) >= KQ_MAX_LINE:   # body text line — stop
            break
        kq_lines.append(remaining[i])
        if ENDS_SENT.search(remaining[i]):
            i += 1
            break
        i += 1
    if kq_lines:
        return ''.join(kq_lines), i
    return None, i


def process_block_lines(lines, para_seen, subtitle_done, key_quote_done):
    """
    Process the lines within one blank-delimited block.
    Returns list of (kind, text) tuples and updated state flags.
    """
    results = []
    # Strip header/noise lines from the block
    clean = [l.strip() for l in lines if not is_noise_line(l.strip())]
    if not clean:
        return results, para_seen, subtitle_done, key_quote_done

    # ── Chapter opening: subtitle detected ────────────────────────
    # Subtitle lines match "word: definition" (超越:, 自治:, 国度:, etc.)
    sub_idx = next((i for i,l in enumerate(clean) if RE_SUBTITLE.match(l)), None)
    if sub_idx is not None and not subtitle_done:
        subtitle_done = True
        sub_text = RE_SUBTITLE_STRIP.sub('', clean[sub_idx]).strip()
        if sub_text:
            results.append(('chapter_subtitle', sub_text))
        remaining = clean[sub_idx+1:]
        # Skip short OCR noise labels (≤5 chars: "知雹必考"→4, "塌塌个居"→4 etc.)
        i = 0
        while i < len(remaining) and len(remaining[i]) <= 5:
            i += 1
        # Collect key quote; lines ≥ KQ_MAX_LINE chars are body text
        kq_text, i = _collect_kq(remaining, i)
        if kq_text:
            results.append(('key_quote', kq_text))
            key_quote_done = True
        rest = remaining[i:]
        if rest:
            text = ''.join(rest)
            if text:
                results.append(('para', text))
                para_seen = True
        return results, para_seen, subtitle_done, key_quote_done

    # ── Single-line block ─────────────────────────────────────────
    if len(clean) == 1:
        s = clean[0]
        if is_subheading_line(s, para_seen):
            results.append(('subheading', s))
        elif not para_seen and not key_quote_done and ENDS_SENT.search(s):
            results.append(('key_quote', s))
            key_quote_done = True
        else:
            if not is_noise_line(s):
                results.append(('para', s))
                para_seen = True
        return results, para_seen, subtitle_done, key_quote_done

    # ── Multi-line block: fallback chapter-opening detection ──────
    # Fires only for chapters without a "word: definition" subtitle
    # (e.g. ch.2 "是多是少?", ch.18 "整合的侍奉生命") and before any
    # body paragraphs have been seen.
    if not subtitle_done and not key_quote_done and not para_seen:
        i = 0
        # Skip short chapter-title / noise lines (≤7 chars)
        while i < len(clean) and len(clean[i]) <= 7:
            i += 1
        if i < len(clean):
            kq_text, i = _collect_kq(clean, i)
            if kq_text:
                results.append(('key_quote', kq_text))
                key_quote_done = True
            rest = clean[i:]
            if rest:
                results.append(('para', ''.join(rest)))
                para_seen = True
            return results, para_seen, subtitle_done, key_quote_done

    # ── Multi-line block: normal processing ───────────────────────
    if len(clean) >= 2 and is_subheading_line(clean[0], para_seen):
        results.append(('subheading', clean[0]))
        text = ''.join(clean[1:])
        if text:
            results.append(('para', text))
            para_seen = True
    else:
        text = ''.join(clean)
        if text:
            results.append(('para', text))
            para_seen = True
    return results, para_seen, subtitle_done, key_quote_done


def parse_section(pages_text):
    full = '\n\n'.join(pages_text)
    full = re.sub(r'\n{3,}', '\n\n', full)

    raw_blocks = []
    for chunk in full.split('\n\n'):
        lines = [l for l in chunk.split('\n') if l.strip()]
        if lines:
            raw_blocks.append(lines)

    blocks = []
    para_seen = subtitle_done = key_quote_done = False

    for bl in raw_blocks:
        new_items, para_seen, subtitle_done, key_quote_done = process_block_lines(
            bl, para_seen, subtitle_done, key_quote_done)
        blocks.extend(new_items)

    # Merge broken paragraphs
    merged = []
    for kind, text in blocks:
        if (kind == 'para' and merged and merged[-1][0] == 'para'
                and not ENDS_SENT.search(merged[-1][1])):
            merged[-1] = ('para', merged[-1][1] + text)
        else:
            merged.append((kind, text))

    # Render
    parts = []
    for kind, text in merged:
        text = text.strip()
        if not text:
            continue
        if kind == 'chapter_subtitle':
            parts.append(f'<p class="reading-chapter-subtitle">{text}</p>')
        elif kind == 'key_quote':
            parts.append(
                '<div class="reading-key-quote">\n'
                '<div class="quote-label">超越心语</div>\n'
                f'<p>{text}</p>\n'
                '</div>'
            )
        elif kind == 'subheading':
            parts.append(f'<h3 class="reading-subheading">{text}</h3>')
        else:
            parts.append(f'<p>{text}</p>')
    return '\n\n'.join(parts)


def load_pages(start, end):
    total = len(glob.glob(os.path.join(OCR_DIR, 'page-*.txt')))
    end_idx = end if end is not None else total
    pages = []
    for i in range(start + 1, end_idx + 1):
        path = os.path.join(OCR_DIR, f'page-{i:03d}.txt')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                pages.append(f.read())
    return pages


def main():
    files = glob.glob(os.path.join(OCR_DIR, 'page-*.txt'))
    if not files:
        print(f"No OCR files in {OCR_DIR}. Run: bash /tmp/ocr_paul.sh"); return

    print(f"Found {len(files)} OCR pages")
    os.makedirs(OUT_DIR, exist_ok=True)

    for sec_id, sec_title, start, end in SECTIONS:
        pages = load_pages(start, end)
        if not pages:
            print(f"  [{sec_id:8}] NO PAGES"); continue
        html = parse_section(pages)
        n_p  = html.count('<p>')
        n_h3 = html.count('<h3')
        n_kq = html.count('reading-key-quote')
        n_st = html.count('chapter_subtitle')
        print(f"  [{sec_id:8}] paras={n_p:3} h3={n_h3:2} kq={n_kq} subtitle={n_st}  ({len(pages)} pg)")
        path = os.path.join(OUT_DIR, f'{sec_id}.md')
        fm = FRONT_MATTER.format(section=sec_id, section_title=sec_title, timestamp=TIMESTAMP)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fm + '\n' + html + '\n')

    print("Done.")

if __name__ == '__main__':
    main()
