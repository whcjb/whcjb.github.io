#!/usr/bin/env python3
"""
Publish Calvin's Commentary on John (English, Pringle translation) from
the unified raw MD to /calvin/john-en/.

Pipeline:
 1. Normalize back-section `FT### text` lines into `[^fN]: text` format
    (ages_phil emitted them as plain BODY lines).
 2. Split into sections: preface (lines 1-177) + chapters 1-21.
 3. For each section, collect referenced `[^fN]` from the body and append
    the matching definitions (collected from anywhere in the file) at the
    end, so Kramdown can render the footnotes block inline.
 4. Write to calvin/john-en/{preface,1..21}.md with calvin-en layout.
 5. Write index.html (calvin-en-book layout).
"""

from __future__ import annotations
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "calvin_raw" / "john" / "calvin_john.md"
OUT_DIR = ROOT / "calvin" / "john-en"

BOOK_ID = "john-en"
BOOK_NAME = "Calvin on John"


def get_date() -> str:
    return subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip()


def normalize_back_footnotes(lines: list[str]) -> list[str]:
    """Convert raw `FT### text` lines (Ages back-section) to `[^fN]: text`.
    Handles letter-suffix variants (FT29A, FT36A, ...) and same-line concatenation
    of multiple footnotes (`FT339"..."FT340"..."FT341"..."`).
    Also matches lowercase `ft###` since extractor sometimes emits that form.
    """
    out = []
    for line in lines:
        # Pre-strip leading <span ...>FTN</span> wrappers so split below is clean.
        # Allow whitespace inside the wrap (e.g., `<span ...>FT306 </span>`).
        line = re.sub(
            r'<span[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\s*</span>',
            r'\1', line)
        # Also strip stray </span> tags that snuck in (e.g., before ft due to
        # split-before-strip).
        # Try same-line concatenated footnotes first: split on ftNNN boundaries.
        parts = re.split(r'(?=\b[Ff][Tt]\d+[A-Za-z]?\b)', line)
        normalized = []
        any_match = False
        for part in parts:
            part = part.rstrip('\n')
            m = re.match(r'^[Ff][Tt](\d+[A-Za-z]?)\s*(.*)$', part)
            if m:
                label = m.group(1).lower()
                body_part = m.group(2).strip()
                # Strip stray leading </span> or other HTML close tags
                body_part = re.sub(r'^(?:</span>|</sty>|\s)+', '', body_part)
                if body_part:
                    normalized.append(f'[^f{label}]: {body_part}')
                    any_match = True
        if any_match:
            for nl in normalized:
                out.append(nl + '\n')
            out.append('\n')
        else:
            out.append(line)
    return out


def find_chapter_starts(lines: list[str]) -> dict[str, int]:
    """Return {key: line_index (0-based)} for preface + chapters 1..21."""
    starts: dict[str, int] = {}
    for i, line in enumerate(lines):
        m = re.match(r'^# CHAPTER (\d+)\s*$', line)
        if m:
            ch = m.group(1)
            if ch not in starts:
                starts[ch] = i
    # Preface starts at the very first emitted content (line 0) so the AGES
    # title page + Pringle translator-attribution page are included.
    starts['preface'] = 0
    return starts


def find_footnotes_section_start(lines: list[str]) -> int:
    """Return line index of `# FOOTNOTES` heading (back-section)."""
    for i, line in enumerate(lines):
        if line.strip() == '# FOOTNOTES':
            return i
    return len(lines)


FN_DEF_RE = re.compile(r'^\[\^(f\d+)\]:\s*(.*)$', re.DOTALL)
FN_REF_RE = re.compile(r'\[\^(f\d+)\](?!:)')


def collect_all_definitions(lines: list[str]) -> dict[str, list[str]]:
    """Walk the file; for each `[^fN]:` line, accumulate the definition until
    the next definition / heading / blank-after-blank. Returns {label: [lines...]}.
    """
    defs: dict[str, list[str]] = {}
    cur_label = None
    cur_lines: list[str] = []
    for line in lines:
        m = FN_DEF_RE.match(line)
        if m:
            if cur_label:
                defs[cur_label] = cur_lines
            cur_label = m.group(1)
            cur_lines = [line.rstrip('\n')]
        elif cur_label is not None:
            stripped = line.rstrip()
            if (stripped.startswith('#')
                    or stripped.startswith('<!-- PAGE')
                    or stripped.startswith('[^')
                    or stripped.startswith('## ')):
                defs[cur_label] = cur_lines
                cur_label = None
                cur_lines = []
            else:
                # Continuation line — collect until terminator
                cur_lines.append(stripped)
        # otherwise: outside any definition, ignore
    if cur_label:
        defs[cur_label] = cur_lines
    return defs


def render_section(body_lines: list[str], all_defs: dict[str, list[str]]) -> str:
    """Stitch body + referenced footnote definitions for publishing."""
    body_text = ''.join(body_lines)
    # Find all refs in body (excluding ref-like patterns inside other contexts)
    refs_in_order: list[str] = []
    seen = set()
    for m in FN_REF_RE.finditer(body_text):
        label = m.group(1)
        if label not in seen:
            seen.add(label)
            refs_in_order.append(label)

    # Also strip any `[^fN]:` definitions that happen to be inside this slice
    # (they'll be reintroduced cleanly from all_defs to avoid duplication / wrong-place)
    stripped_lines = []
    skip_def = False
    for line in body_lines:
        if FN_DEF_RE.match(line):
            skip_def = True
            continue
        if skip_def:
            stripped = line.rstrip()
            if (not stripped
                    or stripped.startswith('#')
                    or stripped.startswith('<!--')
                    or stripped.startswith('[^')):
                skip_def = False
            else:
                continue  # skip continuation
        if not skip_def:
            stripped_lines.append(line)

    body_clean = ''.join(stripped_lines).rstrip()

    if not refs_in_order:
        return body_clean + '\n'

    # Append definitions at the end, in body-ref-order
    def_block_lines = []
    for label in refs_in_order:
        if label in all_defs:
            def_block_lines.extend(all_defs[label])
            def_block_lines.append('')  # blank line between defs
    if not def_block_lines:
        return body_clean + '\n'

    return body_clean + '\n\n' + '\n'.join(def_block_lines) + '\n'


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATE = get_date()

    with SRC.open(encoding='utf-8') as f:
        lines = f.readlines()

    # Step 1: normalize back FT### → [^fN]:
    lines = normalize_back_footnotes(lines)

    # Step 2: collect global footnote definitions (after FT normalization)
    all_defs = collect_all_definitions(lines)
    print(f'collected {len(all_defs)} unique footnote definitions')

    # Step 3: find chapter starts
    starts = find_chapter_starts(lines)
    fn_section_start = find_footnotes_section_start(lines)
    print(f'preface starts at line {starts["preface"] + 1}')
    print(f'FOOTNOTES section at line {fn_section_start + 1}')

    # Step 4: build chapter list and nav
    chapter_keys = sorted([k for k in starts if k != 'preface'], key=int)
    all_keys = ['preface'] + chapter_keys

    labels = {'preface': 'Preface'}
    labels.update({k: f'Chapter {k}' for k in chapter_keys})

    nav = {}
    for idx, key in enumerate(all_keys):
        prev_k = all_keys[idx-1] if idx > 0 else ''
        next_k = all_keys[idx+1] if idx < len(all_keys)-1 else ''
        nav[key] = (prev_k, labels.get(prev_k, ''), next_k, labels.get(next_k, ''))

    # Step 5: compute section boundaries
    section_bounds = {}
    for idx, key in enumerate(all_keys):
        start = starts[key]
        if idx + 1 < len(all_keys):
            end = starts[all_keys[idx + 1]]
        else:
            # Last chapter: ends at the FOOTNOTES heading (exclusive)
            end = fn_section_start
        section_bounds[key] = (start, end)

    # Step 6: write each section
    for key in all_keys:
        start, end = section_bounds[key]
        section_lines = lines[start:end]
        body_md = render_section(section_lines, all_defs)
        prev_s, prev_l, next_s, next_l = nav[key]

        fm = '---\n'
        fm += 'layout: calvin-en\n'
        fm += f'book_id: {BOOK_ID}\n'
        fm += f'book_name: "{BOOK_NAME}"\n'
        fm += f'title: "{labels[key]}"\n'
        fm += f'date: {DATE}\n'
        if prev_s:
            fm += f'prev_section: {prev_s}\nprev_label: "{prev_l}"\n'
        if next_s:
            fm += f'next_section: {next_s}\nnext_label: "{next_l}"\n'
        fm += '---\n\n'

        out_path = OUT_DIR / f'{key}.md'
        out_path.write_text(fm + body_md, encoding='utf-8')
        print(f'  → {key}.md ({len(body_md):,} chars)')

    # Step 7: index.html
    index_path = OUT_DIR / 'index.html'
    index_path.write_text(
        f'---\nlayout: calvin-en-book\nbook_id: {BOOK_ID}\n'
        f'book_name: "{BOOK_NAME}"\nchapters: {len(chapter_keys)}\n---\n',
        encoding='utf-8',
    )
    print(f'  → index.html')


if __name__ == '__main__':
    main()
