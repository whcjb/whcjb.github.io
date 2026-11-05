#!/usr/bin/env python3
"""马太亨利中文版：经文框里每个「节号 N + 文字」的开头，是否对得上和合本第 N 节的开头（只读）。

用来抓：补节/挪节时节号挂错、补进半节经文（「6 神就以此为他的义」）、注释混进框里冒充经文等。
比较前做和合本用字归一；PDF 版和合本与本站 json 版本有个别用字差异，所以按「前 8 字里至少 5 字
按序吻合」判定，并允许诗篇诗题（括号）在前。

用法：python3 scripts/audit_mhenry_verse_starts.py [book...]
"""
import difflib, glob, json, os, re, sys
import opencc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_verse_numbers import ORDER, NUM
from audit_mhenry_unit_seams import han
from audit_mhenry_verse_boxes import VAR

ROOT = os.environ.get('MH_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cc = opencc.OpenCC('t2s')
CUV = json.load(open(f'{ROOT}/scripts/zh_cuv.json', encoding='utf-8-sig'))
VAR2 = str.maketrans('阿於裡', '啊于里')


def norm(t):
    return han(cc.convert(t)).translate(VAR).translate(VAR2)


def check_box(book, ch, text):
    chs = CUV[ORDER.index(book)]['chapters']
    if ch > len(chs):
        return []
    bad = []
    t = re.sub(r'<[^>]+>', '', text)
    for m in NUM.finditer(t):
        n = int(m.group(1))
        if n < 1 or n > len(chs[ch - 1]):
            continue
        after = t[m.end():m.end() + 60]
        raw_e = cc.convert(chs[ch - 1][n - 1].replace(' ', ''))
        if '并入上节' in raw_e:
            continue
        # 两边都去掉括号里的内容（诗题、整节括号、或译注），再比开头
        after = re.sub(r'[（(][^（）()]{0,60}[）)]', '', after)
        e_txt = re.sub(r'[（(][^（）()]{0,60}[）)]', '', raw_e)
        a = norm(after)[:8]
        e = norm(e_txt)
        if len(a) < 5 or len(e) < 5:
            continue
        sm = difflib.SequenceMatcher(None, a, e[:12], autojunk=False)
        hit = sum(b.size for b in sm.get_matching_blocks())
        if hit < 5:
            bad.append((n, after[:24].strip(), e[:16]))
    return bad


def main():
    want = sys.argv[1:] or ORDER
    total = 0
    for book in want:
        for md in sorted(glob.glob(f'{ROOT}/mhenry/{book}/[0-9]*.md'),
                         key=lambda p: int(re.match(r'(\d+)', os.path.basename(p)).group(1))):
            ch = int(re.match(r'(\d+)', os.path.basename(md)).group(1))
            s = open(md, encoding='utf-8').read()
            for ui, m in enumerate(re.finditer(r'<div class="mh-verse">(.*?)</div>', s, re.S), 1):
                for n, got, exp in check_box(book, ch, m.group(1)):
                    total += 1
                    print(f'{book} {ch} u{ui} 节{n} | 框里：{got} | 和合本：{exp}')
    print('TOTAL', total)


if __name__ == '__main__':
    main()
