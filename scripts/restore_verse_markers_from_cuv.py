#!/usr/bin/env python3
"""通过 CUV 短语 fuzzy match 恢复 OCR/publish 丢失的 verse-marker 前缀。

症状：OCR 偶尔产出 `**phrase。** 注释...` 段落但缺 `**书名 N:V。**` 前缀。
渲染在网页上就没有 verse 索引锚点，且 relocate 找不到该段属于哪个 verse，
留在错的 section 里，从胶囊跳不进去。

算法：每个 `**phrase。**` 开头段落，把 phrase 去标点 / 英文括号注 / 省略号
后在该章节 CUV 各 verse 文本里子串匹配，最早匹配的 verse 即为 verse-num。
匹配失败则保留原样（属 Calvin 自创小标题，不该加 marker）。

跑完后必须 sweep `relocate_misplaced_verse_commentary.py +
sort_intra_section_verses.py + dedupe_same_verse_markers.py`，因为恢复的
marker 极可能跨当前 section / 跟同 verse 段重复。

用法：
    python3 scripts/restore_verse_markers_from_cuv.py --book-cn 约翰福音 \
            --cuv-abbrev jo --dir calvin/john
"""
import argparse, json, re
from pathlib import Path
try:
    from opencc import OpenCC
    convert = OpenCC('t2s').convert
except Exception:
    convert = lambda s: s


def find_verse(verse_text, ch, phrase):
    clean = re.sub(r'[ 。，！？、；："“”‘’（）\(\)（）]', '', phrase)
    clean = re.sub(r'[a-zA-Z\d]+', '', clean)
    clean = re.sub(r'[…\.]+', '', clean)
    if len(clean) < 4:
        return None
    if ch not in verse_text:
        return None
    matches = [v for v, txt in verse_text[ch].items() if clean in txt]
    if not matches:
        return None
    return min(matches)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--cuv-abbrev', required=True, help='CUV bibles json abbrev (jo / mt / ...)')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--cuv-json', default='scripts/zh_cuv.json')
    args = ap.parse_args()

    cuv = json.loads(Path(args.cuv_json).read_text(encoding='utf-8-sig'))
    book = next((b for b in cuv if b['abbrev'] == args.cuv_abbrev), None)
    if not book:
        raise SystemExit(f'CUV abbrev {args.cuv_abbrev!r} not found')

    verse_text = {}
    for ch_i, verses in enumerate(book['chapters'], 1):
        verse_text[ch_i] = {}
        for v_i, t in enumerate(verses, 1):
            verse_text[ch_i][v_i] = re.sub(r'\s', '', convert(t))

    book_cn = args.book_cn
    book_token_re = re.compile(r'(约翰福音|约翰|马太|马可|路加|罗马|哥林多|加拉太|希伯来|彼得|启示录)')
    marker_re = re.compile(r'^\*\*([一-鿿][^*\n]{1,60})\*\*(\s+.*)?$')

    total = 0
    for f in sorted(Path(args.dir).glob('*.md')):
        if not f.stem.isdigit():
            continue
        ch = int(f.stem)
        text = f.read_text(encoding='utf-8')
        lines = text.split('\n')
        fixed = 0
        for i, ln in enumerate(lines):
            m = marker_re.match(ln)
            if not m:
                continue
            phrase = m.group(1).rstrip('。.')
            rest = (m.group(2) or '').lstrip()
            if book_token_re.search(phrase):
                continue
            v = find_verse(verse_text, ch, phrase)
            if not v:
                continue
            new = f'**{book_cn} {ch}:{v}。** *{phrase}。* {rest}'.rstrip()
            if new != ln:
                lines[i] = new
                fixed += 1
                print(f'  {f.name}:L{i+1} → {ch}:{v} *{phrase[:24]}*')
        if fixed:
            f.write_text('\n'.join(lines), encoding='utf-8')
            total += fixed
    print(f'\nTotal restored: {total}')


if __name__ == '__main__':
    main()
