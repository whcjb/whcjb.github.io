#!/usr/bin/env python3
import os
import re
import sys

mhenry_dir = "mhenry"
issues = []

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

        unit_pattern = re.compile(
            r'<div class="mh-unit">\s*<div class="mh-verse">(.*?)</div>\s*<div class="mh-unit-body">(.*?)</div>\s*</div>',
            re.DOTALL
        )
        matches = list(unit_pattern.finditer(content))

        for i in range(len(matches) - 1):
            body_i = matches[i].group(2)
            body_next = matches[i+1].group(2)

            body_i_stripped = re.sub(r'<[^>]+>', '', body_i).strip()
            body_next_stripped = re.sub(r'<[^>]+>', '', body_next).strip()

            if not body_i_stripped or not body_next_stripped:
                continue

            last_chars = body_i_stripped.rstrip()
            if not last_chars:
                continue
            last_char = last_chars[-1]

            sentence_enders = {'。', '！', '？', '」', '』', '）', '"', '\u2019', '\u2026', '；'}

            ends_properly = last_char in sentence_enders

            if not ends_properly:
                first_chars = body_next_stripped.lstrip()
                if not first_chars:
                    continue

                skip_patterns = [
                    r'^这里说的是',
                    r'^请注意',
                    r'^\d+',
                    r'^[IVX]+\.',
                    r'^注意：',
                    r'^[一二三四五六七八九十]+[、。]',
                ]
                skip = False
                for pat in skip_patterns:
                    if re.match(pat, first_chars):
                        skip = True
                        break

                if not skip:
                    last_lines = [l for l in body_i_stripped.split('\n') if l.strip()]
                    last_line = last_lines[-1] if last_lines else ''
                    first_lines = [l for l in body_next_stripped.split('\n') if l.strip()]
                    first_line = first_lines[0] if first_lines else ''

                    verse_i = re.sub(r'<[^>]+>', '', matches[i].group(1)).strip()[:80]
                    verse_next = re.sub(r'<[^>]+>', '', matches[i+1].group(1)).strip()[:80]

                    issues.append({
                        'file': fpath,
                        'unit_i': i,
                        'last_char': last_char,
                        'last_line': last_line[-100:],
                        'first_line': first_line[:100],
                        'verse_i': verse_i,
                        'verse_next': verse_next,
                        'match_i': matches[i],
                        'match_next': matches[i+1],
                    })

print(f"Found {len(issues)} potential issues:")
for iss in issues:
    print("")
    print("=" * 60)
    print(f"File: {iss['file']}")
    print(f"Unit {iss['unit_i']} verse: {iss['verse_i']}")
    print(f"Unit {iss['unit_i']} body ends: ...{iss['last_line']}")
    print(f"Unit {iss['unit_i']+1} verse: {iss['verse_next']}")
    print(f"Unit {iss['unit_i']+1} body starts: {iss['first_line']}...")
