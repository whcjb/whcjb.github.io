#!/usr/bin/env python3
"""
Find mhenry units where body ends mid-sentence (no proper ending punctuation)
AND next unit body clearly continues mid-sentence.
"""
import os
import re
import sys

mhenry_dir = "mhenry"
issues = []

SENTENCE_ENDERS = set(['。', '！', '？', '」', '』', '）', '\u201d', '\u2019', '…', '；', '"', "'"])

# Patterns that indicate the next unit body starts a NEW topic (not continuation)
NEW_TOPIC_STARTS = [
    r'^这里说的是',
    r'^请注意看',
    r'^注意：',
    r'^\d+[节章]',   # verse reference
    r'^[IVX]+[\.、]',  # Roman numeral
    r'^[一二三四五六七八九十]+[、．]',  # Chinese numeral
    r'^第[一二三四五六七八九十\d]+[节章]',  # 第X节
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

def get_body_last_text(body_html):
    """Get the last non-empty text from body, ignoring HTML tags"""
    text = re.sub(r'<[^>]+>', '', body_html)
    text = text.strip()
    if not text:
        return ''
    return text

def ends_mid_sentence(text):
    """Check if text ends mid-sentence (no proper ending punctuation)"""
    if not text:
        return False
    last = text.rstrip()
    if not last:
        return False
    return last[-1] not in SENTENCE_ENDERS

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

        # Find all mh-unit positions in the file
        # Each unit: <div class="mh-unit">...</div>\n</div>
        unit_pattern = re.compile(
            r'(<div class="mh-unit">\s*<div class="mh-verse">(.*?)</div>\s*<div class="mh-unit-body">(.*?)</div>\s*</div>)',
            re.DOTALL
        )
        matches = list(unit_pattern.finditer(content))

        for i in range(len(matches) - 1):
            full_match_i = matches[i].group(1)
            verse_html_i = matches[i].group(2)
            body_html_i = matches[i].group(3)

            full_match_next = matches[i+1].group(1)
            verse_html_next = matches[i+1].group(2)
            body_html_next = matches[i+1].group(3)

            body_text_i = get_body_last_text(body_html_i)
            body_text_next = get_body_last_text(body_html_next)

            if not body_text_i or not body_text_next:
                continue

            if not ends_mid_sentence(body_text_i):
                continue

            if is_new_topic(body_text_next):
                continue

            # Additional check: last word of body_i should look like a fragment
            # Specifically, look for lines ending with （第, 节）, mid-parenthesis, etc.
            last_lines = [l for l in body_text_i.split('\n') if l.strip()]
            last_line = last_lines[-1].strip() if last_lines else ''

            first_lines = [l for l in body_text_next.split('\n') if l.strip()]
            first_line = first_lines[0].strip() if first_lines else ''

            verse_i_text = re.sub(r'<[^>]+>', '', verse_html_i).strip()[:80]
            verse_next_text = re.sub(r'<[^>]+>', '', verse_html_next).strip()[:80]

            # Strong indicators of truncation
            strong_truncation = (
                last_line.endswith('（第') or
                re.search(r'（第\d*$', last_line) or
                re.search(r'节）$', last_line) and first_line[0:1] in ['，', '；', '）', '、'] or
                (len(last_line) > 0 and last_line[-1] in ['（', '【', '，', '、', '的', '了', '是', '在', '和'])
            )

            issues.append({
                'file': fpath,
                'unit_i': i,
                'last_line': last_line[-100:],
                'first_line': first_line[:100],
                'verse_i': verse_i_text,
                'verse_next': verse_next_text,
                'strong': strong_truncation,
                'match_i': matches[i],
                'match_next': matches[i+1],
            })

strong_issues = [x for x in issues if x['strong']]
weak_issues = [x for x in issues if not x['strong']]

print(f"Strong truncation issues: {len(strong_issues)}")
print(f"Weak/unclear issues: {len(weak_issues)}")
print(f"Total: {len(issues)}")
print()
print("=== STRONG TRUNCATION ISSUES ===")
for iss in strong_issues:
    print()
    print("=" * 60)
    print(f"File: {iss['file']}")
    print(f"Unit {iss['unit_i']} verse: {iss['verse_i']}")
    print(f"Unit {iss['unit_i']} body ends: ...{iss['last_line']}")
    print(f"Unit {iss['unit_i']+1} verse: {iss['verse_next']}")
    print(f"Unit {iss['unit_i']+1} body starts: {iss['first_line']}...")
