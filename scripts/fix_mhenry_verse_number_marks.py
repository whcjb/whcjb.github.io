#!/usr/bin/env python3
"""给经文框里「有经文、缺节号」的节补上节号（audit_mhenry_verse_numbers.py 报的「框里有」类）。

按和合本第 N 节开头 6 字（用字归一）在框内定位：必须唯一，且落在第 N-1 节号之后、第 N+1 节号之前；
插入「 N」。定位不唯一或越界的跳过。
用法：python3 scripts/fix_mhenry_verse_number_marks.py [--apply] [book...]
"""
import glob, json, os, re, sys
import opencc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import han, HAN
from audit_mhenry_verse_boxes import VAR
from audit_mhenry_verse_numbers import ORDER, NUM, verse_numbers

cc = opencc.OpenCC('t2s')
CUV = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'zh_cuv.json'), encoding='utf-8-sig'))
V2 = str.maketrans('阿於裡她祢', '啊于里他你')
N = lambda t: han(cc.convert(t)).translate(VAR).translate(V2)
BOX = re.compile(r'(<div class="mh-verse">)(.*?)(</div>)', re.S)


def num_positions(t):
    out = {}
    for m in NUM.finditer(t):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        for v in range(a, b + 1):
            out.setdefault(v, m.start(1))
    return out


def main():
    args = sys.argv[1:]
    apply = '--apply' in args
    books = [a for a in args if a != '--apply'] or ORDER
    done = skip = 0
    for book in books:
        if book not in ORDER:
            continue
        chs = CUV[ORDER.index(book)]['chapters']
        for md in sorted(glob.glob(f'mhenry/{book}/[0-9]*.md')):
            ch = int(re.search(r'(\d+)\.md', md).group(1))
            if ch > len(chs):
                continue
            s = open(md, encoding='utf-8').read()
            have = set()
            for m in BOX.finditer(s):
                have |= verse_numbers(re.sub(r'<[^>]+>', '', m.group(2)))
            if len(have) < len(chs[ch - 1]) * 0.5:
                continue
            miss = [v for v in range(1, len(chs[ch - 1]) + 1) if v not in have]
            if not miss:
                continue
            changed = False
            for v in sorted(miss, reverse=True):
                raw = cc.convert(chs[ch - 1][v - 1].replace(' ', ''))
                if '并入上节' in raw:
                    continue
                key = N(re.sub(r'[（(][^（）()]{0,60}[）)]', '', raw))[:6]
                if len(key) < 4:
                    continue
                hit = None
                for m in BOX.finditer(s):
                    t = m.group(2)
                    pos = num_positions(t)
                    lo = pos.get(v - 1, -1); hi = pos.get(v + 1, len(t))
                    if lo < 0 and v - 1 >= 1 and (v - 1) in have:
                        continue
                    # 框内汉字流 → 原文位置
                    hp = [i for i, c in enumerate(t) if HAN.match(c)]
                    th = ''.join(t[i] for i in hp)
                    thn = N(th) if False else han(cc.convert(th)).translate(VAR).translate(V2)
                    occ = [k for k in range(len(thn)) if thn.startswith(key, k) and lo < hp[k] < hi]
                    if len(occ) == 1:
                        if hit:
                            hit = 'amb'; break
                        k = hp[occ[0]]
                        # 前移过开引号/开括号
                        while k > 0 and t[k - 1] in '“‘「『（(':
                            k -= 1
                        hit = (m.start(2) + k, m)
                if (book, ch, v) in {('numbers', 1, 22), ('john', 4, 16)}:
                    hit = None                          # 手工处理
                if not hit or hit == 'amb':
                    skip += 1
                    print(f'SKIP {book} {ch}:{v}')
                    continue
                at = hit[0]
                pre = s[at - 1] if at > 0 else ''
                ins = ('' if pre in ' \n' else ' ') + f'{v} '
                print(f'OK   {book} {ch}:{v} | …{s[max(0,at-12):at]}⟨{v}⟩{s[at:at+12]}')
                s = s[:at] + ins + s[at:]
                done += 1; changed = True
            if apply and changed:
                open(md, 'w', encoding='utf-8').write(s)
    print(f'OK {done}  SKIP {skip}')


if __name__ == '__main__':
    main()
