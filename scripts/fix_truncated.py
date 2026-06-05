#!/usr/bin/env python3
"""
Fix mhenry units where body ends mid-sentence and next unit body continues it.
For each such consecutive pair, merge them: combine verse sections and body content.
"""
import os
import re
import sys

mhenry_dir = "mhenry"

SENTENCE_ENDERS = set(['。', '！', '？', '」', '』', '）', '\u201d', '\u2019', '\u2026', '；', '"', "'"])

NEW_TOPIC_STARTS = [
    r'^这里说的是',
    r'^请注意看',
    r'^注意：',
    r'^\d+[节章]',
    r'^[IVX]+[\.、]',
    r'^[一二三四五六七八九十]+[、．]',
    r'^第[一二三四五六七八九十\d]+[节章]',
    r'^在这一段',
    r'^这段经文',
    r'^本节',
    r'^本章',
    r'^这章',
    r'^这节',
]

def is_new_topic(text):
    text = text.lstrip()
    for pat in NEW_TOPIC_STARTS:
        if re.match(pat, text):
            return True
    return False

def get_plain_text(html):
    return re.sub(r'<[^>]+>', '', html).strip()

def ends_mid_sentence(text):
    if not text:
        return False
    last = text.rstrip()
    if not last:
        return False
    return last[-1] not in SENTENCE_ENDERS

def is_strong_truncation(last_line):
    return (
        last_line.endswith('（第') or
        bool(re.search(r'（第\d*$', last_line)) or
        (len(last_line) > 0 and last_line[-1] in ['（', '【', '，', '、', '的', '了', '是', '在', '和'])
    )

fixed_files = 0
total_merges = 0

for book in sorted(os.listdir(mhenry_dir)):
    book_path = os.path.join(mhenry_dir, book)
    if not os.path.isdir(book_path):
        continue
    for fname in sorted(os.listdir(book_path)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(book_path, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Find all mh-unit positions - we need to process in reverse to preserve positions
        unit_pattern = re.compile(
            r'(<div class="mh-unit">\s*<div class="mh-verse">(.*?)</div>\s*<div class="mh-unit-body">(.*?)</div>\s*</div>)',
            re.DOTALL
        )

        # Iteratively find and fix merges (process pairs from end to start)
        changed = True
        file_merges = 0
        while changed:
            changed = False
            matches = list(unit_pattern.finditer(content))

            for i in range(len(matches) - 1):
                full_i = matches[i].group(1)
                verse_html_i = matches[i].group(2)
                body_html_i = matches[i].group(3)

                full_next = matches[i+1].group(1)
                verse_html_next = matches[i+1].group(2)
                body_html_next = matches[i+1].group(3)

                body_text_i = get_plain_text(body_html_i)
                body_text_next = get_plain_text(body_html_next)

                if not body_text_i or not body_text_next:
                    continue
                if not ends_mid_sentence(body_text_i):
                    continue
                if is_new_topic(body_text_next):
                    continue

                last_lines = [l for l in body_text_i.split('\n') if l.strip()]
                last_line = last_lines[-1].strip() if last_lines else ''

                if not is_strong_truncation(last_line):
                    continue

                # Perform the merge
                # 1. Combine verse sections: verse_i + newline + verse_next
                # But if verse_next starts with the same verse as verse_i ends with, deduplicate
                verse_i_text = get_plain_text(verse_html_i).strip()
                verse_next_text = get_plain_text(verse_html_next).strip()

                # Check if verse_next is a subset/repeat of the end of verse_i
                # Often the pattern is: verse_i ends with "5都因..." and verse_next starts with "5都因..."
                # We need to handle deduplication
                # Simple approach: if verse_next starts with text already in verse_i, skip duplicate

                # Build combined verse HTML
                # verse_html_i may contain the verse_next content partially (for the truncated verse)
                # We keep verse_html_i as-is and append verse_next_text if not already included
                verse_i_clean = verse_html_i.strip()
                verse_next_clean = verse_html_next.strip()

                # Check overlap: does verse_i end with the beginning of verse_next?
                # Look at the first ~30 chars of verse_next
                verse_next_start = verse_next_text[:40].strip()
                if verse_next_start and verse_next_start in verse_i_text:
                    # Already covered, don't add verse_next
                    combined_verse = verse_i_clean
                else:
                    # Append verse_next (possibly with deduplication of the trailing/leading part)
                    # Find the overlap between end of verse_i and start of verse_next
                    # Try overlap of decreasing length
                    overlap_found = 0
                    for overlap_len in range(min(len(verse_i_text), len(verse_next_text), 60), 4, -1):
                        if verse_i_text[-overlap_len:] == verse_next_text[:overlap_len]:
                            overlap_found = overlap_len
                            break

                    if overlap_found > 0:
                        # Merge with overlap removal
                        combined_verse = verse_i_clean + '\n' + verse_next_clean[overlap_found:].strip()
                    else:
                        combined_verse = verse_i_clean + '\n' + verse_next_clean

                # 2. Combine body content
                # body_i ends mid-sentence, body_next continues it
                # We need to concatenate them, removing the artificial break

                # The body sections may contain inner div tags for mh-l1 blocks
                # Strip trailing whitespace/newlines from body_i and leading from body_next
                body_i_stripped = body_html_i.rstrip()
                body_next_stripped = body_html_next.lstrip()

                # Remove trailing newlines from body_i
                body_i_joined = body_i_stripped
                # Remove any leading newlines from body_next
                body_next_joined = body_next_stripped

                combined_body = body_i_joined + body_next_joined

                # 3. Build the merged unit
                merged_unit = (
                    '<div class="mh-unit">\n'
                    '<div class="mh-verse">\n'
                    + combined_verse + '\n'
                    '</div>\n'
                    '<div class="mh-unit-body">'
                    + combined_body +
                    '</div>\n'
                    '</div>'
                )

                # Find the span in content that covers both units
                start_pos = matches[i].start()
                end_pos = matches[i+1].end()

                content = content[:start_pos] + merged_unit + content[end_pos:]
                file_merges += 1
                total_merges += 1
                changed = True
                break  # restart the search after modification

        if content != original_content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed {fpath} ({file_merges} merges)")
            fixed_files += 1

print(f"\nTotal: fixed {total_merges} truncations in {fixed_files} files")
