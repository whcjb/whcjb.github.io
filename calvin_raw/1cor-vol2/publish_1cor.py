#!/usr/bin/env python3
"""
Split calvin_corinth-vol2.md (1 Cor portion) into per-section Jekyll files
for calvin/1corinthians-vol2-en/ (chapters 15-16).
"""
import re
import os

BOOK_ID = '1corinthians-vol2-en'
BOOK_NAME = 'Calvin on 1 Corinthians, Vol. 2'
DATE = '2026-05-26 20:43'
OUT_DIR = os.path.join(os.path.dirname(__file__), '../../calvin/1corinthians-vol2-en')
MD_PATH = os.path.join(os.path.dirname(__file__), 'calvin_corinth-vol2.md')

# ── Load source ───────────────────────────────────────────────────────────────
with open(MD_PATH, encoding='utf-8') as f:
    src = f.read()

# Separate body text from footnote definitions block
fn_sep = '\n---\n'
sep_idx = src.rfind(fn_sep)
body_text = src[:sep_idx] if sep_idx != -1 else src
fn_block = src[sep_idx + len(fn_sep):] if sep_idx != -1 else ''

# Restrict to 1 Cor content only (stop before 2 Cor section at "# COMMENTARIES")
# The 2 Cor section starts at the line containing "# COMMENTARIES" on the second volume
cor2_idx = body_text.find('\n# COMMENTARIES\n')
if cor2_idx != -1:
    body_text = body_text[:cor2_idx]

# Parse all footnote definitions: { 'N': 'text' }
fn_defs = {}
for m in re.finditer(r'^\[\^(\d+)\]:\s*(.*(?:\n(?!\[\^).+)*)', fn_block, re.MULTILINE):
    fn_defs[m.group(1)] = m.group(2).strip()

# ── Split body into sections by # CHAPTER N ──────────────────────────────────
lines = body_text.split('\n')

sections = []   # list of (label, lines_list)
current_label = None
current_lines = []

for line in lines:
    m = re.match(r'^# CHAPTER (\d+)\s*$', line)
    if m:
        if current_label is not None:
            sections.append((current_label, current_lines))
        current_label = m.group(1)
        current_lines = [line]
    else:
        if current_label is not None:
            current_lines.append(line)

if current_label is not None and current_lines:
    sections.append((current_label, current_lines))

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
section_labels = [(label, f'Chapter {label}') for label, _ in sections]

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

# ── Write index.html (custom, since chapters are 15-16 not 1..N) ─────────────
index_path = os.path.join(OUT_DIR, 'index.html')
chapter_links = '\n'.join(
    f'        <a href="{{{{ site.baseurl }}}}/calvin/{BOOK_ID}/{label}/" class="list-group-item">Chapter {label}</a>'
    for label, _ in sections
)
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(f'''---
layout: default
book_id: {BOOK_ID}
book_name: "{BOOK_NAME}"
---

<div class="container">
  <div class="row">
    <div class="col-lg-8 col-lg-offset-2 col-md-10 col-md-offset-1">

      <div style="margin: 32px 0 24px;">
        <a href="{{{{ site.baseurl }}}}/calvin/">&larr; 返回书卷列表</a>
      </div>

      <h2 style="border-bottom: 2px solid #0085a1; padding-bottom:8px; margin-bottom:24px;">
        {BOOK_NAME}
      </h2>

      <div class="list-group" style="max-width:360px;">
{chapter_links}
      </div>

    </div>
  </div>
</div>
''')
print(f'Written index.html')

print(f'\nAll files written to {OUT_DIR}')
