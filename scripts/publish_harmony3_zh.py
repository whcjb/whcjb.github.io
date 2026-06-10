#!/usr/bin/env python3
"""Publish raw zh translations → calvin/harmony-3/N.md.

Vol 3 EN chapter numbering 1..9, ZH publication uses same 1..9.

Usage:
    python3 scripts/publish_harmony3_zh.py 1         # publish single ch
    python3 scripts/publish_harmony3_zh.py all       # publish every ready ch
"""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
RAW_DIR = ROOT / 'calvin_raw/harmony3/zh_chapters'
OUT_DIR = ROOT / 'calvin/harmony-3'

# Vol 3 has same 1..9 numbering for EN and ZH.
EN_TO_ZH_CH = {i: i for i in range(1, 10)}

# Display label for nav (matches harmony3/publish.py CHAPTER_STARTS titles).
EN_CH_LABEL = {
    1: '马太福音 21',
    2: '马太福音 22',
    3: '马太福音 23',
    4: '马太福音 24',
    5: '马太福音 25',
    6: '马太福音 26（上）',
    7: '马太福音 26-27（受审）',
    8: '马太福音 27（钉十架）',
    9: '马太福音 28；马可福音 16；路加福音 24（复活与升天）',
}

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
        # 也把 <p class="scripture-ref">Matthew X:Y</p> 类引用标头中文化
        text = re.sub(
            rf'(<p class="scripture-ref">[^<]*?){en} ',
            rf'\1{zh} ',
            text,
        )
    return text


def transform(raw: str, en_ch: int) -> str:
    zh_ch = EN_TO_ZH_CH[en_ch]

    # 1. Strip Claude `<<<END>>>` lines
    lines = [ln for ln in raw.splitlines()
             if not re.match(r'^\s*<<<END\d*>>>\s*$', ln)]
    text = '\n'.join(lines)

    # 2. Merge abut-bold `****`
    text = text.replace('****', '')

    # 3. Italic-quote split fix
    QO = r'["“”\'‘’]'
    QD = r'["“”]'
    text = re.sub(rf'\*({QO})\*([^*]+?)\*([,.;:!?]*{QO})\*',
                  r'*\1\2\3*', text)
    text = re.sub(rf'\*({QO})\*([^*]+?{QD})', r'*\1\2*', text)

    # 4. <th> book names en→zh
    text = fix_th(text)

    # 4.5. Convert [^N] inside HTML <td> cells to explicit <sup> (kramdown
    # doesn't process markdown inside raw HTML)
    def _wrap_sup_in_html_cells(t):
        def repl_td(m):
            cell = m.group(0)
            return re.sub(
                r'\[\^(\d+)\]',
                lambda mm: (
                    f'<sup id="fnref:{mm.group(1)}">'
                    f'<a href="#fn:{mm.group(1)}" class="footnote">'
                    f'{mm.group(1)}</a></sup>'
                ),
                cell,
            )
        return re.sub(r'<td[^>]*>.*?</td>', repl_td, t, flags=re.DOTALL)
    text = _wrap_sup_in_html_cells(text)

    # 4.6. Front-matter key un-translation (must run BEFORE renumber)
    pre_fm_fixes = [
        (r'^章[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',     r'chapter: \1'),
        (r'^章节[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',   r'chapter: \1'),
        # prev_section 多种译法
        (r'^(?:上一节|前一节|前一段|上一段|前段|上一部分)[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',
         r'prev_section: \1'),
        # next_section 多种译法
        (r'^(?:下一节|后一节|后一段|下一段|后段|下一部分)[：:]\s*(?:<sup>)?(\d+)(?:</sup>)?$',
         r'next_section: \1'),
        (r'^chapter:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'chapter: \1'),
        (r'^prev_section:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'prev_section: \1'),
        (r'^next_section:\s*<sup[^>]*>(?:<a[^>]*>)?(\d+)(?:</a>)?</sup>$',
         r'next_section: \1'),
        # prev_label / next_label 多种译法
        (r'^(?:上一节标签|前一节标签|前一段标签|上一段标签)[：:]\s*"',
         r'prev_label: "'),
        (r'^(?:下一节标签|后一节标签|后一段标签|下一段标签)[：:]\s*"',
         r'next_label: "'),
    ]
    for pat, rep in pre_fm_fixes:
        text = re.sub(pat, rep, text, flags=re.M)

    # 4.7. Restore bare 第N章 lines to `chapter: N` key
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
    text = re.sub(r'book_id: harmony-3-en\b', 'book_id: harmony-3', text)
    text = re.sub(r'book_name: "[^"]+"',
                  'book_name: "共观福音（卷三）"', text, count=1)
    text = re.sub(rf'^chapter: {en_ch}$',
                  f'chapter: {zh_ch}', text, count=1, flags=re.M)
    text = re.sub(r'^date: .*$',
                  f'date: {now_minute()}', text, count=1, flags=re.M)

    # Rewrite prev/next nav
    prev_en = en_ch - 1 if en_ch > 1 else None
    next_en = en_ch + 1 if en_ch < 9 else None

    if prev_en is not None:
        zh_prev = EN_TO_ZH_CH[prev_en]
        text = re.sub(r'^prev_section: .*$',
                      f'prev_section: {zh_prev}', text, count=1, flags=re.M)
        text = re.sub(r'^prev_label: ".*"$',
                      f'prev_label: "{EN_CH_LABEL[prev_en]}"',
                      text, count=1, flags=re.M)
    else:
        text = re.sub(r'^prev_section: .*\n', '', text, flags=re.M)
        text = re.sub(r'^prev_label: ".*"\n', '', text, flags=re.M)

    if next_en is not None:
        zh_next = EN_TO_ZH_CH[next_en]
        text = re.sub(r'^next_section: .*$',
                      f'next_section: {zh_next}', text, count=1, flags=re.M)
        text = re.sub(r'^next_label: ".*"$',
                      f'next_label: "{EN_CH_LABEL[next_en]}"',
                      text, count=1, flags=re.M)
    else:
        text = re.sub(r'^next_section: .*\n', '', text, flags=re.M)
        text = re.sub(r'^next_label: ".*"\n', '', text, flags=re.M)

    # 6. Re-run front-matter key fixes (Claude may translate during transform)
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
    ap.add_argument('chapter', help='English chapter number (1..9) or "all"')
    args = ap.parse_args()
    if args.chapter == 'all':
        for en_ch in sorted(EN_TO_ZH_CH):
            if (RAW_DIR / f'{en_ch}.md').exists():
                publish_ch(en_ch)
    else:
        publish_ch(int(args.chapter))


if __name__ == '__main__':
    main()
