#!/usr/bin/env python3
"""Publish raw zh translations → calvin/harmony-2/N.md.

Vol 2 uses English source numbering 11..22, 25 (continued from vol 1's
1..10). Chinese publication renumbers vol-relative — `harmony-2-en/11.md`
becomes `harmony-2/1.md` ("第二卷第一章"), 12→2, ..., 25→13.

Usage:
    python3 scripts/publish_harmony2_zh.py 11        # publish a single ch
    python3 scripts/publish_harmony2_zh.py all       # publish every ready ch
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
RAW_DIR = ROOT / 'calvin_raw/harmony2/zh_chapters'
OUT_DIR = ROOT / 'calvin/harmony-2'

# Map English chapter number → Chinese (vol-relative) chapter number.
EN_TO_ZH_CH = {11: 1, 12: 2, 13: 3, 14: 4, 15: 5, 16: 6, 17: 7,
               18: 8, 19: 9, 20: 10, 21: 11, 22: 12, 25: 13}

# Display label for the leading book in each English chapter (used in
# prev_label / next_label).
EN_CH_LABEL = {
    11: '马太福音 11', 12: '马太福音 12', 13: '马太福音 13',
    14: '马太福音 14', 15: '马太福音 15', 16: '马太福音 16',
    17: '马太福音 17', 18: '马太福音 18', 19: '马太福音 19',
    20: '马太福音 20', 21: '马太福音 21', 22: '马太福音 22',
    25: '马太福音 25',
}

ZH_LAST_CH = max(EN_TO_ZH_CH.values())   # 13

EN_TO_ZH_BOOK = [
    ('Matthew', '马太福音'),
    ('Mark',    '马可福音'),
    ('Luke',    '路加福音'),
    ('John',    '约翰福音'),
]


def now_minute() -> str:
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def fix_th(text: str) -> str:
    for en, zh in EN_TO_ZH_BOOK:
        text = re.sub(rf'<th>{en} ', f'<th>{zh} ', text)
    return text


def transform(raw: str, en_ch: int) -> str:
    zh_ch = EN_TO_ZH_CH[en_ch]

    # 1. Strip Claude `<<<END>>>` / `<<<END1>>>` lines
    lines = [ln for ln in raw.splitlines()
             if not re.match(r'^\s*<<<END\d*>>>\s*$', ln)]
    text = '\n'.join(lines)

    # 2. Merge abut-bold `****` (Claude sometimes drops the space)
    text = text.replace('****', '')

    # 3. Italic-quote split (cf. 05-publish-zh.md §0.5)
    QO = r'["“”\'‘’]'
    QD = r'["“”]'
    text = re.sub(rf'\*({QO})\*([^*]+?)\*([,.;:!?]*{QO})\*',
                  r'*\1\2\3*', text)
    text = re.sub(rf'\*({QO})\*([^*]+?{QD})', r'*\1\2*', text)

    # 4. <th> book names en→zh
    text = fix_th(text)

    # 4.5. Vol 2 EN uses `<sup>N</sup>` for footnote markers (NOT the
    # kramdown `[^N]` convention used in Vol 1). Claude occasionally
    # converts `<sup>N</sup>` → `[^N]` during translation, which then
    # renders as a literal "[^N]" because there is no matching
    # `[^N]: definition`. Convert any leaked kramdown refs back to
    # `<sup>N</sup>` so they at least render as superscript numbers.
    text = re.sub(r'\[\^(\d+)\]', r'<sup>\1</sup>', text)

    # 4.6. Front-matter key un-translation: must run BEFORE the renumber
    # step below, since the renumber matches the English key `chapter: N`.
    # Also strip <sup>N</sup> wrap from numeric values (leaked from an
    # over-eager bare-digit footnote-wrap on the en source).
    pre_fm_fixes = [
        (r'^章[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',     r'chapter: \1'),
        (r'^章节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',   r'chapter: \1'),
        (r'^上一节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$', r'prev_section: \1'),
        (r'^下一节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$', r'next_section: \1'),
        (r'^chapter:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'chapter: \1'),
        (r'^prev_section:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'prev_section: \1'),
        (r'^next_section:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'next_section: \1'),
        (r'^上一节标签[：:]\s*"',  r'prev_label: "'),
        (r'^下一节标签[：:]\s*"',  r'next_label: "'),
    ]
    for pat, rep in pre_fm_fixes:
        text = re.sub(pat, rep, text, flags=re.M)

    # 4.7. Claude sometimes drops the `chapter:` key entirely and writes
    # `第N章` as a bare line (no key prefix). Restore the key.
    # Detect 第N章 / 第二十章 etc. lines in front matter (between two `---`).
    cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    def _cn_to_int(s):
        s = s.strip()
        if s.isdigit():
            return int(s)
        if s == '十': return 10
        if s.startswith('十'):
            return 10 + cn_num.get(s[1:], 0)
        if s.endswith('十'):
            return cn_num.get(s[:-1], 1) * 10
        if '十' in s:
            tens, ones = s.split('十', 1)
            return cn_num.get(tens or '一', 1) * 10 + cn_num.get(ones, 0)
        return cn_num.get(s)
    def _replace_bare_cn(m):
        n_int = _cn_to_int(m.group(1))
        return f'chapter: {n_int}' if n_int else m.group(0)
    text = re.sub(r'^第([零一二三四五六七八九十百\d]+)章$',
                  _replace_bare_cn, text, count=1, flags=re.M)

    # 5. Front-matter — swap book id/name and renumber chapter
    text = re.sub(r'book_id: harmony-2-en\b', 'book_id: harmony-2', text)
    text = re.sub(r'book_name: "[^"]+"',
                  'book_name: "共观福音（卷二）"', text, count=1)
    text = re.sub(rf'^chapter: {en_ch}$',
                  f'chapter: {zh_ch}', text, count=1, flags=re.M)
    text = re.sub(r'^date: .*$',
                  f'date: {now_minute()}', text, count=1, flags=re.M)

    # Rewrite prev/next nav using the zh-numbering map.
    prev_en, next_en = en_ch - 1, en_ch + 1
    # English files use 11..22 then jump to 25 — handle the gap.
    if en_ch == 22:
        next_en = 25  # vol2 last chapter is 25
    if en_ch == 25:
        next_en = None
    if en_ch == 11:
        prev_en = None  # first chapter of vol 2

    if prev_en is not None and prev_en in EN_TO_ZH_CH:
        zh_prev = EN_TO_ZH_CH[prev_en]
        text = re.sub(r'^prev_section: .*$',
                      f'prev_section: {zh_prev}', text, count=1, flags=re.M)
        text = re.sub(r'^prev_label: ".*"$',
                      f'prev_label: "{EN_CH_LABEL[prev_en]}"',
                      text, count=1, flags=re.M)
    else:
        text = re.sub(r'^prev_section: .*\n', '', text, flags=re.M)
        text = re.sub(r'^prev_label: ".*"\n', '', text, flags=re.M)

    if next_en is not None and next_en in EN_TO_ZH_CH:
        zh_next = EN_TO_ZH_CH[next_en]
        text = re.sub(r'^next_section: .*$',
                      f'next_section: {zh_next}', text, count=1, flags=re.M)
        text = re.sub(r'^next_label: ".*"$',
                      f'next_label: "{EN_CH_LABEL[next_en]}"',
                      text, count=1, flags=re.M)
    else:
        text = re.sub(r'^next_section: .*\n', '', text, flags=re.M)
        text = re.sub(r'^next_label: ".*"\n', '', text, flags=re.M)

    # 6. Front-matter key translation fixes (Claude sometimes translates keys).
    # Also handle <sup>N</sup>-wrapped numeric values: an earlier bare-digit
    # footnote-wrap pass over the en source corrupted the front matter (a
    # `chapter: 14` line became `chapter: <sup>14</sup>` because the digit
    # after `: ` matched the bare-digit pattern). Strip the wrap.
    fm_key_fixes = [
        (r'^章[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',     r'chapter: \1'),
        (r'^章节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',   r'chapter: \1'),
        (r'^上一节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$', r'prev_section: \1'),
        (r'^下一节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$', r'next_section: \1'),
        (r'^chapter:\s*<sup>(\d+)</sup>$',              r'chapter: \1'),
        (r'^prev_section:\s*<sup>(\d+)</sup>$',         r'prev_section: \1'),
        (r'^next_section:\s*<sup>(\d+)</sup>$',         r'next_section: \1'),
        (r'^上一节标签[：:]\s*"',  r'prev_label: "'),
        (r'^下一节标签[：:]\s*"',  r'next_label: "'),
    ]
    for pat, rep in fm_key_fixes:
        text = re.sub(pat, rep, text, flags=re.M)

    return text


def publish_ch(en_ch: int) -> Path:
    raw_p = RAW_DIR / f'{en_ch}.md'
    if not raw_p.exists():
        raise SystemExit(f'raw not found: {raw_p}')
    raw = raw_p.read_text(encoding='utf-8')
    out = transform(raw, en_ch)
    zh_ch = EN_TO_ZH_CH[en_ch]
    out_p = OUT_DIR / f'{zh_ch}.md'
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_p.write_text(out, encoding='utf-8')
    print(f'✓ {raw_p.name} → {out_p} ({out_p.stat().st_size} bytes)')
    return out_p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('chapter', help='English chapter number (11..22, 25) or "all"')
    args = ap.parse_args()
    if args.chapter == 'all':
        for en_ch in sorted(EN_TO_ZH_CH):
            if (RAW_DIR / f'{en_ch}.md').exists():
                publish_ch(en_ch)
    else:
        publish_ch(int(args.chapter))


if __name__ == '__main__':
    main()
