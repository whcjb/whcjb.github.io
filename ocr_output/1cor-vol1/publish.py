#!/usr/bin/env python3
"""
Split calvin_1cor-vol1.md into per-section Jekyll files for calvin/1corinthians-en/.
"""
import re
import os

BOOK_ID = '1corinthians-en'
BOOK_NAME = 'Calvin on 1 Corinthians'
DATE = '2026-05-26 12:45'
OUT_DIR = os.path.join(os.path.dirname(__file__), '../../calvin/1corinthians-en')
MD_PATH = os.path.join(os.path.dirname(__file__), 'calvin_1cor-vol1.md')

# ── Load source ───────────────────────────────────────────────────────────────
with open(MD_PATH, encoding='utf-8') as f:
    src = f.read()

# Separate body text from footnote definitions block
fn_sep = '\n---\n'
sep_idx = src.rfind(fn_sep)
body_text = src[:sep_idx] if sep_idx != -1 else src
fn_block = src[sep_idx + len(fn_sep):] if sep_idx != -1 else ''

# Parse all footnote definitions: { '35': 'definition text...' }
fn_defs = {}
for m in re.finditer(r'^\[?\^?(\d+)\]?:\s+(.+)', fn_block, re.MULTILINE):
    # Handle both [^N]: and bare [^N]: formats
    pass
for m in re.finditer(r'^\[\^(\d+)\]:\s*(.*(?:\n(?!\[\^).+)*)', fn_block, re.MULTILINE):
    fn_defs[m.group(1)] = m.group(2).strip()

# ── Split body into sections ───────────────────────────────────────────────────
# Sections are determined by H1 (# HEADING) boundaries.
# Everything before the first # CHAPTER N is "introduction".
# We split at '# CHAPTER N' lines.

lines = body_text.split('\n')

sections = []   # list of (label, lines_list)
# label: 'introduction' or '1'..'14'

current_label = 'introduction'
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

# ── Helper: extract footnote refs used in text ────────────────────────────────
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
# sections: [('introduction', ...), ('1', ...), ..., ('14', ...)]
TOTAL_CHAPTERS = 14

section_labels = []
for label, _ in sections:
    if label == 'introduction':
        section_labels.append(('preface', 'Translator\'s Preface'))
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

    if label == 'introduction':
        filename = 'preface.md'
        title = "Translator's Preface"
    else:
        filename = f'{label}.md'
        title = f'Chapter {label}'

    # Build front matter
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

    # Build content (strip leading blank lines, remove PAGE comments)
    content_lines = sec_lines
    # Remove <!-- PAGE N --> comments (optional: keep for debugging → remove for clean output)
    content_lines = [l for l in content_lines if not re.match(r'^<!-- PAGE \d+ -->$', l)]
    content = '\n'.join(content_lines).strip()

    # Append footnote defs used in this section
    refs = extract_refs(content)
    fn_section = build_fn_section(refs)

    # Write file
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
book_name: "Calvin's Commentary on 1 Corinthians, Vol. 1 (English)"
chapters: {TOTAL_CHAPTERS}
---
''')
print(f'Written index.html')

print(f'\nAll files written to {OUT_DIR}')
