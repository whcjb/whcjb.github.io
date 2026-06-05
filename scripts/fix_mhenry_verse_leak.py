#!/usr/bin/env python3
"""
Scan and fix "commentary leaked into mh-verse" issues in all mhenry chapter files.

The structure we're looking for:
<div class="mh-unit">
<div class="mh-verse">
[bible verses][LEAKED COMMENTARY]
</div>
<div class="mh-unit-body">
[empty or just whitespace/label divs before any content]
</div>
</div>

We ONLY operate within proper mh-unit > mh-verse structures.
"""

import os
import re
import sys

MHENRY_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/mhenry"

# Chinese narrative openers that signal start of commentary
# These must be at the START of the leaked text
COMMENTARY_STARTERS = [
    # Demonstratives
    '这里', '这章', '这段', '这一段', '这节', '这些', '这条', '这场',
    '这首', '这事', '这两', '这三', '这四', '这五', '这六',
    '这是', '这几节', '这个段落', '这部分', '这几章',
    # Other common commentary openers
    '在这', '关于', '本章', '本节', '本段',
    '约伯', '比勒达', '以利法', '以利户', '琐法',
    '使徒', '写信人', '作者在',
    # Causal/logical connectors (rare in Bible text as verse starters after closing quote)
    '此时', '因此', '因为', '所以',
    # Meta-commentary
    '注意', '请注意', '我们', '值得注意',
    '大意是', '意思是',
    '从这里', '从上文', '前面', '下面',
    # Proper names as subjects (commentary typically starts with subject)
    '撒母耳', '扫罗', '大卫', '约书亚', '士师', '所罗门',
    '彼得', '约翰', '雅各', '以利亚', '以利沙', '但以理',
    '以赛亚', '耶利米', '以西结',
    '摩西', '亚伦', '先知', '作者', '保罗',
    '神在', '主在', '耶和华在',
    '神呼', '神告', '神命', '神向', '神对', '神的祭司',
    '主耶', '基督', '救主',
    '大祭司', '祭司',
]


def fix_curly_quotes_in_tags(content):
    """Fix curly quotes inside HTML tags."""
    result = []
    in_tag = False
    for c in content:
        if c == '<':
            in_tag = True
        elif c == '>':
            in_tag = False
        if in_tag and c in '\u201c\u201d':
            result.append('"')
        elif in_tag and c in '\u2018\u2019':
            result.append("'")
        else:
            result.append(c)
    return ''.join(result)


def find_commentary_split_point(verse_text):
    """
    Find the index where commentary begins in verse_text (the content between
    <div class="mh-verse"> and </div>).

    Returns (verse_end_idx, commentary_text) or (None, None) if no clear leak.

    verse_end_idx: position in verse_text where the Bible verse ends
                   (everything from 0 to verse_end_idx is the clean verse)
    commentary_text: the leaked commentary (already stripped)
    """
    # We look for patterns where a closing quote is followed by commentary text.
    # The pattern is:
    #   [verse-number][verse-text]。"[SPACE][commentary-starter]
    #   or [verse-number][verse-text]。'[SPACE][commentary-starter]
    #
    # We must be conservative: only match if:
    # 1. The split point is after a closing quote character (。" or 。' or just " or ')
    # 2. What follows starts with a known commentary opener
    # 3. The "before" part starts with a verse number (Chinese digit or Arabic digit)

    stripped = verse_text.strip()
    if not stripped:
        return None, None

    # Must start with a verse number
    if not re.match(r'^\d', stripped):
        return None, None

    # Patterns to try:
    # 1. Quote-period-quote sequences like 。" or 。'
    # 2. Just a closing quote followed by whitespace then commentary

    best_split = None
    best_commentary = None
    best_verse_end = None

    closing_seqs = [
        '。\u201d',  # 。"
        '。\u2019',  # 。'
        '。"',
        "。'",
    ]

    for seq in closing_seqs:
        pos = 0
        while True:
            idx = stripped.find(seq, pos)
            if idx == -1:
                break

            split_pos = idx + len(seq)

            # What comes after?
            after = stripped[split_pos:]
            after_stripped = after.lstrip(' \t\n')

            if after_stripped:
                matched_starter = None
                for starter in COMMENTARY_STARTERS:
                    if after_stripped.startswith(starter):
                        matched_starter = starter
                        break

                if matched_starter is not None:
                    # Found a potential split!
                    # Make sure what comes before is actually a Bible verse
                    before = stripped[:split_pos]
                    # Sanity check: before should contain verse numbers
                    if re.search(r'\d', before[:50]):
                        # CRITICAL CHECK: if the "commentary" text contains embedded
                        # verse numbers (like " 17他们", " 33主对"), it's more Bible verse
                        # not commentary. Bible verse numbers appear as: space+digits+Chinese
                        # Commentary may have references like (3：1) but not standalone
                        # verse numbers at start of sentences.
                        first_150 = after_stripped[:150]
                        # Pattern: space + 1-3 digits + Chinese/quote character (verse number in flow)
                        # This catches " 7 "在收割", "17他们再三", " 33主对" patterns
                        # But NOT numbers in parentheses like (第16节) or chapter refs
                        if re.search(r'[ 　]\d{1,3}[ 　]?[\u4e00-\u9fff\u201c\u2018"\'（(]', first_150[:100]):
                            # Has embedded verse number -> still Bible verse text
                            pos = idx + 1
                            continue
                        # Extra check: if commentary starter is a proper name followed by
                        # verb+speech pattern (like "撒母耳说：" or "大卫对...说"), it's
                        # still Bible verse text (narrative continuation)
                        if re.search(r'^[\u4e00-\u9fff]{2,6}[对说领问答呼告请]', after_stripped[:20]):
                            pos = idx + 1
                            continue

                        # Calculate the position in verse_text (not stripped)
                        leading_ws = len(verse_text) - len(verse_text.lstrip())
                        abs_split = leading_ws + split_pos
                        commentary = after_stripped

                        # Take the FIRST (leftmost) valid split point
                        if best_split is None or abs_split < best_split:
                            best_split = abs_split
                            best_commentary = commentary
                            best_verse_end = abs_split

            pos = idx + 1

    # Also check: just a closing quote (") at a natural verse-boundary followed by commentary
    # without requiring 。 before it
    for quote_char in ['\u201d', '\u2019']:
        pos = 0
        while True:
            idx = stripped.find(quote_char, pos)
            if idx == -1:
                break

            split_pos = idx + 1
            after = stripped[split_pos:]
            after_stripped = after.lstrip(' \t\n')

            if after_stripped:
                matched_starter = None
                for starter in COMMENTARY_STARTERS:
                    if after_stripped.startswith(starter):
                        matched_starter = starter
                        break

                if matched_starter is not None:
                    before = stripped[:split_pos]
                    # More careful check: before should end with a complete verse
                    # (ends with 。" or similar, not in the middle of a sentence)
                    # The character before the quote should be a period or a digit or )
                    if idx > 0 and re.search(r'\d', before[:50]):
                        char_before = stripped[idx-1] if idx > 0 else ''
                        # Accept if the character before the closing quote is
                        # period, digit, Chinese punctuation indicating end of sentence
                        if char_before in '。！？）」』':
                            # CRITICAL CHECK: if commentary starts with verse numbers
                            first_150 = after_stripped[:150]
                            if re.search(r'[ 　]\d{1,3}[ 　]?[\u4e00-\u9fff\u201c\u2018"\'（(]', first_150[:100]):
                                pos = idx + 1
                                continue  # Has embedded verse numbers -> still Bible text
                            # Extra check: narrative continuation (proper name + speech verb)
                            if re.search(r'^[\u4e00-\u9fff]{2,6}[对说领问答呼告请]', after_stripped[:20]):
                                pos = idx + 1
                                continue
                            leading_ws = len(verse_text) - len(verse_text.lstrip())
                            abs_split = leading_ws + split_pos
                            commentary = after_stripped
                            if best_split is None or abs_split < best_split:
                                best_split = abs_split
                                best_commentary = commentary
                                best_verse_end = abs_split

            pos = idx + 1

    return best_verse_end, best_commentary


def is_body_empty_before_content(body_text):
    """
    Check if the mh-unit-body text (between <div class="mh-unit-body"> and the
    first structural child) has no actual text content.

    Returns True if empty (no text before first <div child).
    """
    stripped = body_text.lstrip('\n \t')
    if not stripped:
        return True
    # Starts immediately with a div -> empty
    if stripped.startswith('<div'):
        return True
    return False


def find_mh_units(content):
    """
    Find all mh-unit blocks in the content.
    Returns list of (unit_start, unit_end, verse_content_start, verse_content_end,
                     body_tag_end, body_text_snippet)
    where verse_content is between the mh-verse tags,
    and body_tag_end is the position right after <div class="mh-unit-body">

    Only returns units that are PROPERLY structured:
    <div class="mh-unit">
    <div class="mh-verse">...</div>
    <div class="mh-unit-body">...
    """
    results = []

    # Find mh-unit openings
    unit_pattern = re.compile(r'<div class="mh-unit">')
    verse_open = '<div class="mh-verse">'
    verse_close = '</div>'
    body_open = '<div class="mh-unit-body">'

    for um in unit_pattern.finditer(content):
        unit_start = um.start()
        unit_content_start = um.end()

        # The next thing should be whitespace + mh-verse
        rest = content[unit_content_start:]
        verse_idx = rest.find(verse_open)
        if verse_idx == -1:
            continue
        # Make sure there's no other mh-unit before the verse
        next_unit = rest.find('<div class="mh-unit">')
        if next_unit != -1 and next_unit < verse_idx:
            continue

        abs_verse_open = unit_content_start + verse_idx
        abs_verse_content_start = abs_verse_open + len(verse_open)

        # Find the closing </div> for this verse
        verse_end = content.find(verse_close, abs_verse_content_start)
        if verse_end == -1:
            continue

        verse_content = content[abs_verse_content_start:verse_end]

        # After the verse close, find mh-unit-body
        after_verse = content[verse_end + len(verse_close):]
        body_idx = after_verse.find(body_open)
        if body_idx == -1:
            continue

        # Make sure there's no mh-unit in between
        next_unit_between = after_verse.find('<div class="mh-unit">')
        if next_unit_between != -1 and next_unit_between < body_idx:
            continue

        abs_body_tag_end = verse_end + len(verse_close) + body_idx + len(body_open)

        # Get a snippet of body content to check if empty
        body_snippet = content[abs_body_tag_end:abs_body_tag_end + 500]

        results.append({
            'unit_start': unit_start,
            'verse_open': abs_verse_open,
            'verse_content_start': abs_verse_content_start,
            'verse_content_end': verse_end,
            'verse_content': verse_content,
            'body_tag_end': abs_body_tag_end,
            'body_snippet': body_snippet,
        })

    return results


def process_file(filepath):
    """Process a single file, return list of fix descriptions."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    fixes = []
    modifications = []  # list of (old_str, new_str) to apply

    units = find_mh_units(content)

    for unit in units:
        verse_content = unit['verse_content']
        body_snippet = unit['body_snippet']

        # Check if body is empty
        if not is_body_empty_before_content(body_snippet):
            continue

        # Try to find a commentary split point
        split_idx, commentary = find_commentary_split_point(verse_content)
        if split_idx is None:
            continue

        # Double-check that commentary is meaningful (at least a few Chinese chars)
        if len(commentary) < 5:
            continue

        # Build the fix
        clean_verse = verse_content[:split_idx].rstrip()

        # The old verse block content
        old_verse_content = verse_content
        new_verse_content = '\n' + clean_verse + '\n'

        # The old body start (what comes right after <div class="mh-unit-body">)
        # We insert commentary at the start
        abs_body_tag_end = unit['body_tag_end']

        old_body_after = content[abs_body_tag_end:abs_body_tag_end + 3]  # just a check

        # Record the modification
        modifications.append({
            'verse_content_start': unit['verse_content_start'],
            'verse_content_end': unit['verse_content_end'],
            'old_verse_content': old_verse_content,
            'new_verse_content': new_verse_content,
            'body_tag_end': abs_body_tag_end,
            'commentary': commentary,
        })

        # For reporting
        verse_text_stripped = verse_content.strip()
        first_verse_num = re.match(r'(\d+)', verse_text_stripped)
        first_num = first_verse_num.group(1) if first_verse_num else '?'
        fixes.append(f"  Verse ~{first_num}: moved leaked commentary ({commentary[:70]}...)")

    if not modifications:
        return []

    # Apply modifications from last to first to preserve positions
    modifications.sort(key=lambda m: m['verse_content_start'], reverse=True)

    new_content = content
    for mod in modifications:
        vc_start = mod['verse_content_start']
        vc_end = mod['verse_content_end']
        body_end = mod['body_tag_end']
        commentary = mod['commentary']
        new_vc = mod['new_verse_content']

        # After applying the verse change, the body_tag_end shifts
        # We need to apply both changes atomically or adjust positions

        # Since we sort in reverse, and we haven't applied any modifications yet
        # for this iteration, positions are still valid in new_content

        # Step 1: Replace verse content
        old_verse = new_content[vc_start:vc_end]
        if old_verse != mod['old_verse_content']:
            # Position was shifted by a previous modification - skip
            continue

        new_content = new_content[:vc_start] + new_vc + new_content[vc_end:]

        # Step 2: The body_tag_end position shifted by the difference in verse content length
        shift = len(new_vc) - len(old_verse)
        new_body_end = body_end + shift

        # Insert commentary after body tag
        after_body = new_content[new_body_end:]
        after_body_stripped = after_body.lstrip('\n ')

        new_content = (new_content[:new_body_end] +
                      '\n\n' + commentary + '\n\n' +
                      after_body_stripped)

    if new_content != content:
        # Apply curly quote fix in tags
        fixed_content = fix_curly_quotes_in_tags(new_content)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        return fixes

    return []


def main():
    total_files = 0
    fixed_files = 0
    total_fixes = 0
    errors = []

    for root, dirs, files in os.walk(MHENRY_DIR):
        dirs.sort()
        for filename in sorted(files):
            if not filename.endswith('.md'):
                continue
            filepath = os.path.join(root, filename)
            total_files += 1

            try:
                fixes = process_file(filepath)
                if fixes:
                    rel_path = os.path.relpath(filepath, MHENRY_DIR)
                    print(f"FIXED: {rel_path}")
                    for fix in fixes:
                        print(fix)
                    fixed_files += 1
                    total_fixes += len(fixes)
            except Exception as e:
                import traceback
                rel_path = os.path.relpath(filepath, MHENRY_DIR)
                errors.append(f"ERROR: {rel_path}: {e}")
                print(f"ERROR: {rel_path}: {e}", file=sys.stderr)

    print(f"\nSummary: scanned {total_files} files, fixed {fixed_files} files ({total_fixes} total fixes)")
    if errors:
        print(f"Errors: {len(errors)}")


if __name__ == '__main__':
    main()
