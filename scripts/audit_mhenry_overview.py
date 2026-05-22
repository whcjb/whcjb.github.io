#!/usr/bin/env python3
"""Audit Matthew Henry commentary chapter files for mh-overview section quality."""

import os
import re
import sys
from pathlib import Path

MHENRY_DIR = Path("/Users/yanpeifa/Documents/whcjb.github.io/mhenry")

def extract_overview(content):
    """Extract text content from mh-overview div."""
    # Match <div class="mh-overview">...</div> (potentially multiline)
    pattern = re.compile(r'<div\s+class="mh-overview">(.*?)</div>', re.DOTALL)
    match = pattern.search(content)
    if match is None:
        return None
    inner = match.group(1)
    # Strip HTML tags to get plain text
    text = re.sub(r'<[^>]+>', '', inner).strip()
    return text

def check_unit_body_starts_with_benz(content):
    """Check if first mh-unit-body starts with text mentioning 本章."""
    pattern = re.compile(r'<div\s+class="mh-unit-body">(.*?)</div>', re.DOTALL)
    match = pattern.search(content)
    if match is None:
        return None
    inner = match.group(1)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', '', inner).strip()
    # Check if it starts with or contains 本章 near the beginning
    if '本章' in text[:300]:
        return text[:300]
    return None

def categorize(text):
    if text is None:
        return 'MISSING'
    length = len(text)
    if length < 50:
        return 'EMPTY'
    elif length < 200:
        return 'SHORT'
    else:
        return 'OK'

def main():
    results = {
        'MISSING': [],
        'EMPTY': [],
        'SHORT': [],
        'OK': [],
    }
    unit_body_issues = []

    books = sorted(os.listdir(MHENRY_DIR))

    for book in books:
        book_path = MHENRY_DIR / book
        if not book_path.is_dir():
            continue

        chapter_files = []
        for f in book_path.iterdir():
            if f.suffix == '.md' and f.stem != 'preface' and f.stem.isdigit():
                chapter_files.append(f)

        chapter_files.sort(key=lambda x: int(x.stem))

        for chap_file in chapter_files:
            content = chap_file.read_text(encoding='utf-8')
            overview_text = extract_overview(content)
            category = categorize(overview_text)

            entry = {
                'book': book,
                'chapter': int(chap_file.stem),
                'text': overview_text,
                'file': str(chap_file),
            }
            results[category].append(entry)

            # Check unit body for 本章
            unit_body_issue = check_unit_body_starts_with_benz(content)
            if unit_body_issue:
                unit_body_issues.append({
                    'book': book,
                    'chapter': int(chap_file.stem),
                    'snippet': unit_body_issue,
                })

    # Print report
    total = sum(len(v) for v in results.values())
    print(f"=== Matthew Henry Overview Audit ===")
    print(f"Total chapter files scanned: {total}")
    print(f"  OK:      {len(results['OK'])}")
    print(f"  SHORT:   {len(results['SHORT'])}")
    print(f"  EMPTY:   {len(results['EMPTY'])}")
    print(f"  MISSING: {len(results['MISSING'])}")
    print()

    if results['MISSING']:
        print("=== MISSING (no mh-overview div) ===")
        for e in results['MISSING']:
            print(f"  {e['book']} ch{e['chapter']}")
        print()

    if results['EMPTY']:
        print("=== EMPTY (< 50 chars) ===")
        for e in results['EMPTY']:
            snippet = repr(e['text']) if e['text'] is not None else 'None'
            print(f"  {e['book']} ch{e['chapter']}: {snippet}")
        print()

    if results['SHORT']:
        print("=== SHORT (50–199 chars) ===")
        for e in results['SHORT']:
            print(f"  {e['book']} ch{e['chapter']} [{len(e['text'])} chars]: {e['text']!r}")
        print()

    if unit_body_issues:
        print("=== Unit Body starts with '本章' (possible misplaced overview content) ===")
        for e in unit_body_issues:
            print(f"  {e['book']} ch{e['chapter']}: {e['snippet']!r}")
        print()
    else:
        print("=== No unit body issues found (no 本章 in first 300 chars of first unit body) ===")

if __name__ == '__main__':
    main()
