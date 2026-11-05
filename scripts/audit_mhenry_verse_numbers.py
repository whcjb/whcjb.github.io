#!/usr/bin/env python3
"""马太亨利中文版：按和合本节数查每章经文框里缺了哪几节（只读）。

接缝/经文框比对都看不到「单元第一节整节丢失」（框从下一节开始），这里直接数节号：
章内所有 mh-verse 框出现过的节号（含 9-10 这类合并节）与和合本该章节数比对。
节号是小号上标、框里不带节号的卷（林前等）整章节号过少时跳过。

用法：python3 scripts/audit_mhenry_verse_numbers.py [book...]
"""
import glob, json, os, re, sys
import yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ['genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy', 'joshua', 'judges', 'ruth', '1samuel', '2samuel',
         '1kings', '2kings', '1chronicles', '2chronicles', 'ezra', 'nehemiah', 'esther', 'job', 'psalms', 'proverbs',
         'ecclesiastes', 'songofsolomon', 'isaiah', 'jeremiah', 'lamentations', 'ezekiel', 'daniel', 'hosea', 'joel',
         'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah', 'haggai', 'zechariah', 'malachi',
         'matthew', 'mark', 'luke', 'john', 'acts', 'romans', '1corinthians', '2corinthians', 'galatians', 'ephesians',
         'philippians', 'colossians', '1thessalonians', '2thessalonians', '1timothy', '2timothy', 'titus', 'philemon',
         'hebrews', 'james', '1peter', '2peter', '1john', '2john', '3john', 'jude', 'revelation']
VERSE_BOX = re.compile(r'<div class="mh-verse">(.*?)</div>', re.S)
NUM = re.compile(r'(?:(?<=[^\d][：:.．])|(?<=^[：:.．])|(?<![\d：:.．\-–]))(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?[ab]?[.．]?(?=\s*[“‘「『（(〈〔]{0,3}[一-鿿])')


def verse_numbers(text):
    out = set()
    for m in NUM.finditer(text):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        if 0 < a <= b <= a + 10:
            out.update(range(a, b + 1))
    return out


def main():
    cuv = json.load(open(f'{ROOT}/scripts/zh_cuv.json', encoding='utf-8-sig'))
    want = sys.argv[1:] or ORDER
    total = 0
    for book in want:
        if book not in ORDER:
            continue
        chs = cuv[ORDER.index(book)]['chapters']
        for md in sorted(glob.glob(f'{ROOT}/mhenry/{book}/[0-9]*.md'),
                         key=lambda p: int(re.match(r'(\d+)', os.path.basename(p)).group(1))):
            ch = int(re.match(r'(\d+)', os.path.basename(md)).group(1))
            if ch > len(chs):
                continue
            n = len(chs[ch - 1])
            s = open(md, encoding='utf-8').read()
            have = set()
            for m in VERSE_BOX.finditer(s):
                have |= verse_numbers(re.sub(r'<[^>]+>', '', m.group(1)))
            if len(have) < n * 0.5:
                continue                     # 框里基本不带节号，没法数
            # 和合本数据里标「a」/「并入上节」的是与上一节合并的节，不算缺
            merged = {v for v in range(1, n + 1) if chs[ch - 1][v - 1].strip() in ('a', '') or re.search('[并併]入上', chs[ch - 1][v - 1].replace(' ', ''))}
            miss = sorted(set(range(1, n + 1)) - have - merged)
            if miss:
                total += len(miss)
                print(f'{book} {ch}: 缺 {miss}（共 {n} 节）')
    print('TOTAL', total)


if __name__ == '__main__':
    main()
