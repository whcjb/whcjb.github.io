#!/usr/bin/env python3
"""Cross-chapter verse-commentary relocation.

When OCR splits one bible chapter's last few verse-commentary paragraphs
into the NEXT chapter's file (because the page-break happened mid-section
and `_split_by_chapter` got fooled), we end up with paragraphs like
`22 可见上帝的恩慈...` at the start of `12.md` even though Rom 12 only
has 21 verses.

This script:
  1. Walks each chapter file N.
  2. For paragraphs whose verse-opener K > max_verse(chapter N), checks
     whether K is a valid verse in chapter N-1.
  3. If so, MOVES the paragraph to the END of chapter N-1's last
     matching section (i.e., the section whose hi >= K, or the LAST
     section if none).
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

VERSE_COUNTS = {
    '罗马书': {
        1: 32, 2: 29, 3: 31, 4: 25, 5: 21, 6: 23, 7: 25, 8: 39,
        9: 33, 10: 21, 11: 36, 12: 21, 13: 14, 14: 23, 15: 33, 16: 27,
    },
}


def parse_sections(text: str, book_cn: str):
    lines = text.split('\n')
    hdr_re = re.compile(rf'^## {re.escape(book_cn)} (\d+):(\d+)(?:-(\d+))?')
    secs = []
    for i, ln in enumerate(lines):
        m = hdr_re.match(ln)
        if m:
            secs.append({
                'start': i,
                'end': len(lines),
                'lo': int(m.group(2)),
                'hi': int(m.group(3)) if m.group(3) else int(m.group(2)),
                'chapter': int(m.group(1)),
            })
    for j in range(len(secs) - 1):
        secs[j]['end'] = secs[j + 1]['start']
    return lines, secs


def find_overflow_paragraphs(lines, secs, max_verse):
    """Return list of (verse, start_line, end_line) where verse > max_verse."""
    out = []
    opener_re = re.compile(r'^(\d{1,3})[ 、.]\s*\*{0,2}[一-鿿]')
    for sec in secs:
        i = sec['start'] + 1
        while i < sec['end']:
            if not lines[i].strip():
                i += 1; continue
            if lines[i].lstrip().startswith(('<h2', '<div', '<a ', '</div>', '<p ', '[^', '{:.')):
                while i < sec['end'] and lines[i].strip():
                    i += 1
                continue
            ps = i
            while i < sec['end'] and lines[i].strip():
                i += 1
            pe = i
            m = opener_re.match(lines[ps])
            if m:
                v = int(m.group(1))
                if v > max_verse and v <= 199:
                    out.append((v, ps, pe))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--dir', required=True)
    args = ap.parse_args()

    book_cn = args.book_cn
    dir_path = Path(args.dir).expanduser().resolve()
    vc = VERSE_COUNTS.get(book_cn, {})

    moved_total = 0
    for path in sorted(dir_path.glob('*.md')):
        if not path.stem.isdigit():
            continue
        ch = int(path.stem)
        if ch <= 1:
            continue  # nothing to move INTO ch0
        text = path.read_text(encoding='utf-8')
        lines, secs = parse_sections(text, book_cn)
        if not secs:
            continue
        max_verse_n = vc.get(ch, 999)
        max_verse_prev = vc.get(ch - 1, 999)
        overflows = find_overflow_paragraphs(lines, secs, max_verse_n)
        if not overflows:
            continue
        # Only keep ones that fit in chapter N-1
        valid = [(v, ps, pe) for (v, ps, pe) in overflows if v <= max_verse_prev]
        if not valid:
            continue

        # Remove from current file
        remove = set()
        prev_paras = []  # list of (verse, paragraph_lines)
        for v, ps, pe in valid:
            for j in range(ps, pe):
                remove.add(j)
            # collapse trailing blank lines from para
            prev_paras.append((v, lines[ps:pe]))
        new_lines = [ln for i, ln in enumerate(lines) if i not in remove]
        # Collapse 3+ blanks
        new_text = re.sub(r'\n{3,}', '\n\n', '\n'.join(new_lines))
        path.write_text(new_text, encoding='utf-8')

        # Append to prev chapter file: insert into LAST section that contains
        # the verse (or last section)
        prev_path = path.with_name(f'{ch - 1}.md')
        if not prev_path.exists():
            print(f'  ⚠ no prev chapter file: {prev_path}')
            continue
        prev_text = prev_path.read_text(encoding='utf-8')
        prev_lines, prev_secs = parse_sections(prev_text, book_cn)
        if not prev_secs:
            print(f'  ⚠ no sections in prev file: {prev_path}')
            continue

        # Group by target section
        by_target = {}
        for v, para in prev_paras:
            target = None
            for si, s in enumerate(prev_secs):
                if s['lo'] <= v <= s['hi']:
                    target = si
                    break
            if target is None:
                target = len(prev_secs) - 1  # fallback: last section
            by_target.setdefault(target, []).append((v, para))

        # Insert at end of each target section (in reverse so indices stay)
        out_lines = list(prev_lines)
        for target_idx in sorted(by_target.keys(), reverse=True):
            end_idx = prev_secs[target_idx]['end']
            insert_at = end_idx
            paras = sorted(by_target[target_idx], key=lambda x: x[0])
            chunks = []
            for v, para in paras:
                chunks.append('')
                chunks.extend(para)
            chunks.append('')
            out_lines[insert_at:insert_at] = chunks

        new_prev_text = re.sub(r'\n{3,}', '\n\n', '\n'.join(out_lines))
        prev_path.write_text(new_prev_text, encoding='utf-8')
        print(f'  {path.name} → {prev_path.name}: moved {len(valid)} paragraphs ({[v for v,_,_ in valid]})')
        moved_total += len(valid)

    print(f'\nTotal cross-chapter relocations: {moved_total}')


if __name__ == '__main__':
    main()
