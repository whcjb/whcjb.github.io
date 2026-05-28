#!/usr/bin/env python3
"""
Split calvin_corinth-vol2.md (2 Cor portion) into per-section Jekyll files
for calvin/2corinthians-en/ (preface + chapters 1-13).
"""
import re
import os

BOOK_ID = '2corinthians-en'
BOOK_NAME = 'Calvin on 2 Corinthians'
DATE = '2026-05-26 20:43'
OUT_DIR = os.path.join(os.path.dirname(__file__), '../../calvin/2corinthians-en')
MD_PATH = os.path.join(os.path.dirname(__file__), 'calvin_corinth-vol2.md')

# ── Load source ───────────────────────────────────────────────────────────────
with open(MD_PATH, encoding='utf-8') as f:
    src = f.read()

# Separate body text from footnote definitions block
fn_sep = '\n---\n'
sep_idx = src.rfind(fn_sep)
body_text = src[:sep_idx] if sep_idx != -1 else src
fn_block = src[sep_idx + len(fn_sep):] if sep_idx != -1 else ''

# Restrict to 2 Cor content only:
# Start at "# COMMENTARIES" (2 Cor title page), stop before index sections
cor2_start = body_text.find('\n# COMMENTARIES\n')
index_start = body_text.find('\n## Index of Scripture References\n')
if cor2_start != -1:
    body_text = body_text[cor2_start + 1:]   # strip leading newline
if index_start != -1:
    # Recalculate after slicing
    idx2 = body_text.find('\n## Index of Scripture References\n')
    if idx2 != -1:
        body_text = body_text[:idx2]

# Parse all footnote definitions: { 'N': 'text' }
fn_defs = {}
for m in re.finditer(r'^\[\^(\d+)\]:\s*(.*(?:\n(?!\[\^).+)*)', fn_block, re.MULTILINE):
    fn_defs[m.group(1)] = m.group(2).strip()

# ── Split body into sections by # CHAPTER N ──────────────────────────────────
# Everything before the first # CHAPTER N is "preface" (title page + translator's
# preface + author's dedicatory + the argument)
lines = body_text.split('\n')

sections = []   # list of (label, lines_list)
current_label = 'preface'
current_lines = []

for line in lines:
    m = re.match(r'^# CHAPTER (\d+)\s*$', line)
    if m:
        sections.append((current_label, current_lines))
        current_label = m.group(1)
        current_lines = [line]
    else:
        current_lines.append(line)

if current_lines:
    sections.append((current_label, current_lines))

TOTAL_CHAPTERS = 13

# ── Helper: footnote refs and section builder ─────────────────────────────────
def extract_refs(text):
    return set(re.findall(r'\[\^(\d+)\]', text))

def build_fn_section(refs):
    if not refs:
        return ''
    parts = ['\n\n---\n']
    for num in sorted(refs, key=lambda x: int(x)):
        if num in fn_defs:
            txt = fn_defs[num].replace('|', '\\|')
            parts.append(f'\n[^{num}]: {txt}\n')
    return ''.join(parts)

# ── Build nav labels ──────────────────────────────────────────────────────────
section_labels = []
for label, _ in sections:
    if label == 'preface':
        section_labels.append(('preface', "Translator's Preface & The Argument"))
    else:
        section_labels.append((label, f'Chapter {label}'))

def prev_next(idx):
    prev_section = prev_label = next_section = next_label = None
    if idx > 0:
        prev_section, prev_label = section_labels[idx - 1]
    if idx < len(section_labels) - 1:
        next_section, next_label = section_labels[idx + 1]
    return prev_section, prev_label, next_section, next_label

# ── Write section files ───────────────────────────────────────────────────────
os.makedirs(OUT_DIR, exist_ok=True)

for idx, (label, sec_lines) in enumerate(sections):
    prev_section, prev_label, next_section, next_label = prev_next(idx)

    if label == 'preface':
        filename = 'preface.md'
        title = "Translator's Preface & The Argument"
    else:
        filename = f'{label}.md'
        title = f'Chapter {label}'

    fm_lines = ['---']
    fm_lines.append(f'layout: calvin-en')
    fm_lines.append(f'book_id: {BOOK_ID}')
    fm_lines.append(f'book_name: "{BOOK_NAME}"')
    fm_lines.append(f'title: "{title}"')
    fm_lines.append(f'date: {DATE}')
    if prev_section:
        fm_lines.append(f'prev_section: {prev_section}')
        fm_lines.append(f'prev_label: "{prev_label}"')
    if next_section:
        fm_lines.append(f'next_section: {next_section}')
        fm_lines.append(f'next_label: "{next_label}"')
    fm_lines.append('---')
    front_matter = '\n'.join(fm_lines) + '\n\n'

    content_lines = [l for l in sec_lines if not re.match(r'^<!-- PAGE \d+ -->$', l)]
    content = '\n'.join(content_lines).strip()

    refs = extract_refs(content)
    fn_section = build_fn_section(refs)

    out_path = os.path.join(OUT_DIR, filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(front_matter + content + fn_section + '\n')

    print(f'Written {filename}: {len(content_lines)} lines, {len(refs)} footnote refs')

# ── Write index.html ──────────────────────────────────────────────────────────
index_path = os.path.join(OUT_DIR, 'index.html')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(f'''---
layout: calvin-en-book
book_id: {BOOK_ID}
book_name: "Calvin's Commentary on 2 Corinthians (English)"
chapters: {TOTAL_CHAPTERS}
---
''')
print(f'Written index.html')

print(f'\nAll files written to {OUT_DIR}')
