#!/usr/bin/env python3
"""
Publish a Calvin commentary from the unified raw MD to /calvin/<book>-en/.

Generic for any Ages-format book (john, phil, heb, 1cor-vol1, etc.) that's
been extracted via `scripts/calvin_extract.py <volume>` then converted via
`scripts/structured_to_md.py`. Pipeline (all generic, zero per-book logic):

 1. Normalize back-section `FT### text` lines → `[^fN]: text` format
    (Ages extractor emits them as plain BODY lines or sty-wrapped).
 2. Split into sections: preface + chapters by `^# CHAPTER N` markers.
 3. For each section, collect referenced `[^fN]` from body and append
    matching defs at the end so kramdown renders the fn block inline.
 4. Write `calvin/<book>-en/{preface,1..N}.md` with calvin-en layout.
 5. Write `index.html` (calvin-en-book layout, `has_preface: true`).

Usage:
    python3 scripts/publish_calvin_en.py <book>

Where <book> is the calvin_raw/ subdirectory name (also used to derive
book_id = <book>-en, src = calvin_raw/<book>/calvin_<book>.md). The
book_name is read from _data/calvin_books.yml english section if present,
or can be overridden via --name.
"""

from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ────────────────────────────────────────────────────────────────────────
# Generic helpers (unchanged from publish_john_en.py)
# ────────────────────────────────────────────────────────────────────────

def get_date() -> str:
    return subprocess.check_output(["date", "+%Y-%m-%d %H:%M"]).decode().strip()


def normalize_back_footnotes(lines: list[str]) -> list[str]:
    """Convert raw `FT### text` lines (Ages back-section) to `[^fN]: text`.
    Handles letter-suffix variants (FT29A, FT36A, ...) and same-line
    concatenation of multiple footnotes (`FT339"..."FT340"..."`).
    Strips leading `<span ...>ftN</span>` wraps (extractor colors ftN red).
    """
    out = []
    for line in lines:
        # Skip lines that already start with `[^fN]:` — they're proper fn defs,
        # don't touch (otherwise body inline `ftN` mentions get split out).
        if re.match(r'^\[\^f\d+[A-Za-z]?\]:', line):
            out.append(line)
            continue
        # Pre-strip <span ...>ftN</span> wrappers (allow whitespace inside)
        line = re.sub(
            r'<span[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\s*</span>',
            r'\1', line)
        # Only consider line for FT normalization if it STARTS with ftN
        # (i.e. legitimate raw `FT### text` from Ages back-section). Lines
        # where ftN appears only inline (`some text … ftN more text`) should
        # be left alone — splitting them drops the prefix.
        if not re.match(r'^\s*[Ff][Tt]\d+[A-Za-z]?\b', line):
            out.append(line)
            continue
        parts = re.split(r'(?=\b[Ff][Tt]\d+[A-Za-z]?\b)', line)
        normalized = []
        any_match = False
        for part in parts:
            part = part.rstrip('\n')
            m = re.match(r'^[Ff][Tt](\d+[A-Za-z]?)\s*(.*)$', part)
            if m:
                label = m.group(1).lower()
                body_part = m.group(2).strip()
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
    """Return {key: line_index (0-based)} for preface + chapters 1..N.
    Accepts trailing footnote ref `[^fN]` (some PDF chapter heads have one)."""
    starts: dict[str, int] = {}
    for i, line in enumerate(lines):
        m = re.match(r'^# CHAPTER (\d+)(?:\s+\[\^f\d+[A-Za-z]?\])?\s*$', line)
        if m:
            ch = m.group(1)
            if ch not in starts:
                starts[ch] = i
    # Preface starts at the very first emitted content (line 0) so AGES
    # title page + Pringle translator-attribution page are included.
    starts['preface'] = 0
    return starts


_APPENDIX_END_RE = re.compile(r'END OF THE COMMENTARIES', re.IGNORECASE)
_FOOTNOTES_HEADING_RE = re.compile(r'^\s*(?:#\s+)?FOOTNOTES\s*$', re.IGNORECASE)


def excise_translation_appendix(lines: list[str]) -> list[str]:
    """Some Ages PDFs (Ephesians) have a bilingual re-translation appendix
    between "END OF THE COMMENTARIES..." and the legitimate FOOTNOTES section.
    Cut that segment out, KEEP the FOOTNOTES def section after it.

    Pipeline:
      [main body] ... END OF THE COMMENTARIES ... [TRANSLATION] ... FOOTNOTES heading ... [^fN]: defs
      ↓ excise
      [main body] ... [^fN]: defs
    """
    end_idx = None
    fn_idx = None
    for i, line in enumerate(lines):
        t = re.sub(r'<[^>]+>', '', line).strip()
        if end_idx is None and _APPENDIX_END_RE.search(t):
            end_idx = i
        elif end_idx is not None and _FOOTNOTES_HEADING_RE.match(t):
            fn_idx = i
            break
    if end_idx is None:
        return lines  # no appendix
    if fn_idx is None:
        # END marker but no FOOTNOTES heading after — cut everything after END
        print(f'  cutting from line {end_idx + 1} to EOF ({len(lines) - end_idx} lines)')
        return lines[:end_idx]
    # Excise [end_idx, fn_idx + 1) — drop END marker line and translation
    # appendix, but keep FOOTNOTES heading + everything after.
    print(f'  excising translation appendix lines {end_idx + 1}-{fn_idx} ({fn_idx - end_idx} lines)')
    return lines[:end_idx] + lines[fn_idx:]


def find_footnotes_section_start(lines: list[str]) -> int:
    """Return line index of `# FOOTNOTES` heading (back-section)."""
    for i, line in enumerate(lines):
        if line.strip() == '# FOOTNOTES':
            return i
    return len(lines)


FN_DEF_RE = re.compile(r'^\[\^(f\d+[A-Za-z]?)\]:\s*(.*)$', re.DOTALL)
FN_REF_RE = re.compile(r'\[\^(f\d+[A-Za-z]?)\](?!:)')


def collect_all_definitions(lines: list[str]) -> dict[str, list[str]]:
    """Walk the file; for each `[^fN]:` line accumulate until next def /
    heading / page-break. Returns {label: [lines...]}."""
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
                    or stripped.startswith('## ')
                    or stripped.startswith('<p ')
                    or stripped.startswith('<p>')):
                defs[cur_label] = cur_lines
                cur_label = None
                cur_lines = []
            else:
                cur_lines.append(stripped)
    if cur_label:
        defs[cur_label] = cur_lines
    return defs


def render_section(body_lines: list[str], all_defs: dict[str, list[str]]) -> str:
    """Stitch section body + referenced fn defs in body-ref order."""
    body_text = ''.join(body_lines)
    refs_in_order: list[str] = []
    seen = set()
    for m in FN_REF_RE.finditer(body_text):
        label = m.group(1)
        if label not in seen:
            seen.add(label)
            refs_in_order.append(label)

    # Strip any fn defs that happen to be inside this slice
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
                continue
        if not skip_def:
            stripped_lines.append(line)
    body_clean = ''.join(stripped_lines).rstrip()

    if not refs_in_order:
        return body_clean + '\n'

    def_block_lines = []
    for label in refs_in_order:
        if label in all_defs:
            def_block_lines.extend(all_defs[label])
            def_block_lines.append('')
    if not def_block_lines:
        return body_clean + '\n'
    return body_clean + '\n\n' + '\n'.join(def_block_lines) + '\n'


# ────────────────────────────────────────────────────────────────────────
# Book-name lookup from _data/calvin_books.yml
# ────────────────────────────────────────────────────────────────────────

def lookup_book_name(book_id: str) -> str | None:
    """Read _data/calvin_books.yml; find entry with id matching <book>-en;
    return its `name` value. Returns None if not found."""
    yml_path = ROOT / '_data' / 'calvin_books.yml'
    if not yml_path.exists():
        return None
    in_english = False
    cur_id = None
    for raw in yml_path.read_text(encoding='utf-8').splitlines():
        line = raw.rstrip()
        if line.startswith('english:'):
            in_english = True
            continue
        if line and not line[0].isspace():
            in_english = False
            continue
        if not in_english:
            continue
        m = re.match(r'\s*-\s*id:\s*(.+?)\s*$', line)
        if m:
            cur_id = m.group(1).strip()
            continue
        m = re.match(r'\s*name:\s*(.+?)\s*$', line)
        if m and cur_id == book_id:
            return m.group(1).strip()
    return None


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='Publish a Calvin commentary (English).')
    ap.add_argument('book', help='Book key (calvin_raw/<book>/ subdir name, e.g. john / phil / heb / 1cor-vol1)')
    ap.add_argument('--name', help='Override book_name (otherwise looked up from _data/calvin_books.yml; falls back to derived)')
    ap.add_argument('--src', help='Override source MD path (default: calvin_raw/<book>/calvin_<book>.md)')
    ap.add_argument('--out', help='Override output dir (default: calvin/<book>-en)')
    ap.add_argument('--book-id', help='Override book_id (default: <book>-en)')
    args = ap.parse_args()

    book_key = args.book
    book_id = args.book_id or f'{book_key}-en'
    src = Path(args.src) if args.src else ROOT / 'calvin_raw' / book_key / f'calvin_{book_key}.md'
    out_dir = Path(args.out) if args.out else ROOT / 'calvin' / book_id

    if not src.exists():
        sys.exit(f'ERROR: source MD not found: {src}')

    # book_name lookup: CLI > yml > derived. Convention: front-matter book_name
    # is "Calvin on <Book>" (full); _data yml `name:` is just the short book
    # name (e.g. "John") used in nav UI. Prepend "Calvin on " if yml short name.
    if args.name:
        book_name = args.name
    else:
        yml_name = lookup_book_name(book_id)
        if yml_name and not yml_name.lower().startswith('calvin'):
            book_name = f'Calvin on {yml_name}'
        else:
            book_name = yml_name or f'Calvin on {book_key.title()}'
    print(f'book_id={book_id}  book_name="{book_name}"')
    print(f'src={src}\nout={out_dir}')

    out_dir.mkdir(parents=True, exist_ok=True)
    DATE = get_date()

    lines = src.read_text(encoding='utf-8').splitlines(keepends=True)

    # Step 1: normalize FT### → [^fN]:
    lines = normalize_back_footnotes(lines)

    # Step 1.5: Excise PDF translation appendix (CALVIN'S VERSION re-translation
    # between "END OF THE COMMENTARIES" and the legitimate FOOTNOTES section).
    # Keeps the [^fN]: defs that follow.
    lines = excise_translation_appendix(lines)

    # Step 2: collect global fn defs
    all_defs = collect_all_definitions(lines)
    print(f'collected {len(all_defs)} fn definitions')

    # Step 3: find chapter starts
    starts = find_chapter_starts(lines)
    fn_section_start = find_footnotes_section_start(lines)
    chapter_keys = sorted([k for k in starts if k != 'preface'], key=int)
    if not chapter_keys:
        sys.exit('ERROR: no chapters found (looking for `^# CHAPTER N`)')
    all_keys = ['preface'] + chapter_keys
    print(f'chapters: {chapter_keys[0]}..{chapter_keys[-1]} ({len(chapter_keys)} total)')

    # Step 4: nav labels
    labels = {'preface': 'Preface'}
    labels.update({k: f'Chapter {k}' for k in chapter_keys})
    nav = {}
    for idx, key in enumerate(all_keys):
        prev_k = all_keys[idx-1] if idx > 0 else ''
        next_k = all_keys[idx+1] if idx < len(all_keys)-1 else ''
        nav[key] = (prev_k, labels.get(prev_k, ''), next_k, labels.get(next_k, ''))

    # Step 5: section boundaries
    section_bounds = {}
    for idx, key in enumerate(all_keys):
        start = starts[key]
        end = starts[all_keys[idx + 1]] if idx + 1 < len(all_keys) else fn_section_start
        section_bounds[key] = (start, end)

    # Step 6: write each section
    for key in all_keys:
        start, end = section_bounds[key]
        body_md = render_section(lines[start:end], all_defs)
        prev_s, prev_l, next_s, next_l = nav[key]

        fm = '---\n'
        fm += 'layout: calvin-en\n'
        fm += f'book_id: {book_id}\n'
        fm += f'book_name: "{book_name}"\n'
        fm += f'title: "{labels[key]}"\n'
        fm += f'date: {DATE}\n'
        if prev_s:
            fm += f'prev_section: {prev_s}\nprev_label: "{prev_l}"\n'
        if next_s:
            fm += f'next_section: {next_s}\nnext_label: "{next_l}"\n'
        fm += '---\n\n'

        out_path = out_dir / f'{key}.md'
        out_path.write_text(fm + body_md, encoding='utf-8')
        print(f'  → {key}.md ({len(body_md):,} chars)')

    # Step 7: index.html (with has_preface: true)
    index_path = out_dir / 'index.html'
    index_path.write_text(
        f'---\n'
        f'layout: calvin-en-book\n'
        f'book_id: {book_id}\n'
        f'book_name: "{book_name}"\n'
        f'chapters: {len(chapter_keys)}\n'
        f'has_preface: true\n'
        f'---\n',
        encoding='utf-8',
    )
    print(f'  → index.html')


if __name__ == '__main__':
    main()
