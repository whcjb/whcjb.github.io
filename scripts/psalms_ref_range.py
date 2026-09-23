#!/usr/bin/env python3
"""引用里的章节号超出该卷实际范围——数字误读的**结构性**判据。

`Jer. l. 88`：耶利米书第 50 章只有 46 节，88 节不存在，所以这个 88 必错
（印面是 38）。这类错前面所有闸子都看不见：`88` 是个好好的数字，词是真词，
标点也成双。只有拿**圣经本身**当尺子才量得出来。

尺子用 `scripts/zh_cuv.json`（和合本全 66 卷），量两件事：
  · 章号 > 该卷章数
  · 节号 > 该章节数

两处必须留余量，否则全是假阳性：
  · **诗篇按希伯来编号**。亚历山大正文一律写希伯来节号，括号里才是英文
    （`Ps. li. 18 (16)`）。希伯来把诗题也算一节，最多多 2 节。
  · 约珥书、玛拉基书等的**分章**两种传统差一章（`Joel iv. 13 (iii. 13)`），
    他自己就并写了两套，章号同样放宽。

出的是待判清单，不直接落盘——数字改多少得看影像。

用法：python3 scripts/psalms_ref_range.py
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
CUV = ROOT / 'scripts/zh_cuv.json'

# 亚历山大的缩写 → zh_cuv 的 abbrev。带数字前缀的卷单列。
BOOKS = {
    'Gen': 'gn', 'Exod': 'ex', 'Ex': 'ex', 'Lev': 'lv', 'Num': 'nm',
    'Deut': 'dt', 'Josh': 'js', 'Judges': 'jud', 'Judg': 'jud', 'Ruth': 'rt',
    'Ezra': 'ezr', 'Neh': 'ne', 'Esth': 'et', 'Job': 'job', 'Ps': 'ps',
    'Prov': 'prv', 'Eccles': 'ec', 'Cant': 'so', 'Isa': 'is', 'Jer': 'jr',
    'Lam': 'lm', 'Ezek': 'ez', 'Dan': 'dn', 'Hos': 'ho', 'Joel': 'jl',
    'Amos': 'am', 'Obad': 'ob', 'Jon': 'jn', 'Mic': 'mi', 'Nah': 'na',
    'Hab': 'hk', 'Zeph': 'zp', 'Hag': 'hg', 'Zech': 'zc', 'Mal': 'ml',
    'Mat': 'mt', 'Matt': 'mt', 'Mark': 'mk', 'Luke': 'lk', 'John': 'jo',
    'Acts': 'act', 'Rom': 'rm', 'Gal': 'gl', 'Eph': 'eph', 'Phil': 'ph',
    'Col': 'cl', 'Tit': 'tt', 'Philem': 'phm', 'Heb': 'hb', 'James': 'jm',
    'Jam': 'jm', 'Jude': 'jd', 'Rev': 're',
}
NUMBERED = {'Sam': ('1sm', '2sm'), 'Kings': ('1kgs', '2kgs'),
            'Chron': ('1ch', '2ch'), 'Cor': ('1co', '2co'),
            'Thess': ('1ts', '2ts'), 'Tim': ('1tm', '2tm'),
            'Pet': ('1pe', '2pe'), 'John': ('1jo', '2jo')}
# `John` 既是福音书也是书信：带 `1 `/`2 ` 前缀时走 NUMBERED，裸写时走 BOOKS。
# 章号可以差一章的：分章传统两套
LOOSE_CHAP = {'jl', 'ml', 'ho'}

ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
NAME = '|'.join(sorted(set(BOOKS) | set(NUMBERED), key=len, reverse=True))
# 节号串两处要收紧，否则假阳性比真错还多：
#   · `\s{1,2}` —— 不许跨段。`on Ps. xxiv.⏎⏎20. *This* (is)` 里那个 20
#     是下一节的节号，不是 xxiv 的节
#   · 结尾的负向断言 —— `Deut. xxix. 24, 2 Sam. iii. 30` 里，贪婪的数字串会把
#     `2 Sam.` 的卷次 `2` 一起吞掉，于是下一处引用被当成《撒母耳记上》
REF = re.compile(rf'\b(?:([12])\s+)?({NAME})\.?\s{{1,2}}([ivxlcdm]+)\.\s{{1,2}}'
                 rf'((?:\d+(?!\s+(?:{NAME})\b)[,\s-]{{0,2}})+)')


def roman(s):
    n = 0
    for i, c in enumerate(s):
        v = ROMAN[c]
        n += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return n


def main():
    books = {b['abbrev']: b['chapters'] for b in
             json.loads(CUV.read_text(encoding='utf-8-sig'))}
    stat = Counter()
    bad = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        t = re.sub(r'<[^<>]+>', ' ', p.read_text(encoding='utf-8'))
        for m in REF.finditer(t):
            pre, name, rom, nums = m.groups()
            key = (NUMBERED[name][int(pre) - 1] if (name in NUMBERED and pre)
                   else BOOKS.get(name)
                   or (NUMBERED[name][0] if name in NUMBERED else None))
            # 引用后面紧跟一个括号数字的，是**希伯来编号**，正文给希伯来、
            # 括号给英文（`Lev. v. 23 (vi. 4)`、`Num. xvii. 23 (8)`、
            # `Mal. iii. 24 (iv. 6)`）。希伯来的分节与和合本差得多，
            # 拿和合本的节数去卡它全是假阳性——这一类直接跳过。
            if re.match(r'\s*\(', t[m.end():m.end() + 3]):
                stat['希伯来编号，跳过'] += 1
                continue
            if not key:
                continue
            ch = roman(rom)
            chs = books[key]
            stat['查过的引用'] += 1
            slack_c = 1 if key in LOOSE_CHAP else 0
            if ch < 1 or ch > len(chs) + slack_c:
                stat['章号越界'] += 1
                bad.append((p.stem, '章号越界', f'{key} 共 {len(chs)} 章，这里是 {ch}',
                            t[max(0, m.start() - 34):m.end() + 20]))
                continue
            if ch > len(chs):
                continue                       # 差一章那种，节号就不查了
            nv = len(chs[ch - 1])
            # 诗篇按希伯来编号，诗题也算节，最多多 2
            slack_v = 2 if key == 'ps' else 0
            for v in re.findall(r'\d+', nums):
                if int(v) > nv + slack_v:
                    stat['节号越界'] += 1
                    bad.append((p.stem, '节号越界',
                                f'{key} {ch} 章共 {nv} 节，这里是 {v}',
                                t[max(0, m.start() - 34):m.end() + 20]))
                    break
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    for sec, why, detail, ctx in bad:
        print(f'  [{sec}] {why}：{detail}\n        …{re.sub(chr(10), " ", ctx)}…')
    return len(bad)


if __name__ == '__main__':
    main()
