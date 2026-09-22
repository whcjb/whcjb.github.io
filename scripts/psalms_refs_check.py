#!/usr/bin/env python3
"""经文引用的格式错——前面六道闸一个也看不见。

`Deut, xxix. 21`、`Ps. XV. 3`、`ver. 12,13`：拆成词都是真词，标点也不成双，
斜体也配得上，于是判词典、双标点、引号、渲染层全部放行。可它们是实打实的
误读——逗号读成句点、小写罗马数字读成大写。

**这一类只有拿「引用本身的写法」当判据才看得见**：书里的体例是
`<书卷缩写>. <小写罗马数字>. <阿拉伯数字>`，偏离体例的就是可疑。

三条，都只动标点与大小写，不碰字母：
  书卷缩写后是逗号     `Deut, xxix.` → `Deut.`   （逗号与句点在这副字模里常互串）
  数字之间逗号没空格   `ver. 12,13`  → `12, 13`
  章节号是大写罗马     `Ps. XV. 3`   → `Ps. xv. 3`

**大写那条要挡住两种真·大写**：句首、以及 `2 Sam.` 这种数字前缀之后的
`I`/`II`/`V` 其实是卷次不是章节；判据要求它后面跟着句点加阿拉伯数字。

用法：
    python3 scripts/psalms_refs_check.py            # 全书试跑，逐条打印
    python3 scripts/psalms_refs_check.py --apply    # 写进 manual_fixes 并落盘
"""
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'

NAMES = ['Gen', 'Exod', 'Lev', 'Num', 'Deut', 'Josh', 'Judg', 'Ruth', 'Sam',
         'Kings', 'Chron', 'Ezra', 'Neh', 'Esth', 'Job', 'Prov', 'Eccles',
         'Cant', 'Isa', 'Jer', 'Lam', 'Ezek', 'Dan', 'Hos', 'Joel', 'Amos',
         'Obad', 'Jon', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal',
         'Mat', 'Mark', 'Luke', 'John', 'Acts', 'Rom', 'Cor', 'Gal', 'Eph',
         'Phil', 'Col', 'Thess', 'Tim', 'Tit', 'Heb', 'Jam', 'Pet', 'Jude',
         'Rev']

BOOK = (r'(?:Gen|Exod|Lev|Num|Deut|Josh|Judg|Ruth|Sam|Kings|Chron|Ezra|Neh|'
        r'Esth|Job|Ps|Prov|Eccles|Cant|Isa|Jer|Lam|Ezek|Dan|Hos|Joel|Amos|'
        r'Obad|Jon|Mic|Nah|Hab|Zeph|Hag|Zech|Mal|Mat|Mark|Luke|John|Acts|Rom|'
        r'Cor|Gal|Eph|Phil|Col|Thess|Tim|Tit|Philem|Heb|Jam|Pet|Jude|Rev)')

RULES = [
    # 罗马 50 的 `l.` 被读成数字 `1`／大写 `I`——**必须排在加空格那条前面**，
    # 否则 `Jer. xlix. 19,1. 44` 先被插进一个空格，这条的锚就找不到了。
    # 判据要求它落在一串引用里（前面是书卷缩写，或是同一串引用里的逗号），
    # 且后面跟着「句点 + 阿拉伯数字」。全书 43 处，逐条看过上下文：
    # `Gen. l. 7`（约瑟下埃及）、`Isa. l. 4, 5`（唤醒耳朵）、`Ps. l. 23`
    # （凡以感谢献上为祭的）——若当成第 1 章，句句不通。影像核过诗 40、诗 84 两处。
    ('罗马 50 读成数字 1',
     re.compile(rf'(\b{BOOK}\.\s+|[,;]\s?)([1I])(\.\s+\d)'),
     lambda m: m.group(1) + 'l' + m.group(3)),
    ('书卷缩写后是逗号',
     re.compile(rf'\b({BOOK}),(?=\s+[ivxlcIVXLC0-9])'),
     lambda m: m.group(1) + '.'),
    ('数字之间逗号没空格',
     re.compile(r'(?<=[0-9])(,)(?=[0-9])'),
     lambda m: ', '),
    ('章节号是大写罗马数字',
     re.compile(rf'\b({BOOK}\.\s+)([IVXLC]{{1,7}})(\.\s+\d)'),
     lambda m: m.group(1) + m.group(2).lower() + m.group(3)),
    ('章节号首字母误作大写',
     re.compile(rf'\b({BOOK}\.\s+)([IVXLC][ivxlc]+)(\.\s+\d)'),
     lambda m: m.group(1) + m.group(2).lower() + m.group(3)),
]


CORPUS_MIN = 12          # 少于这么多用例，不敢说哪种是「体例」


def corpus_rules():
    """书卷缩写后面该不该有句点，**让全书自己说**。

    不能照搬直觉：这本书里 `Kings`/`Job`/`Amos`/`Luke`/`Acts` 是**全名**，
    一律不带句点（各 100 多处）；`Gen.`/`Deut.`/`Sam.` 是缩写，一律带。
    写死一张表迟早写反——`Job. xxxv. 10` 与 `1 Kings iii. 14` 各错一半，
    直觉反而会把 114 处对的改坏。

    所以判据是**多数形态**：同一个名字两种写法都出现、且多数压倒少数
    （≥12 例且占九成），就把少数那种当误读。
    """
    txt = ''.join(re.sub(r'<[^<>]+>', ' ', p.read_text(encoding='utf-8'))
                  for p in SRC.glob('*.md'))
    out = []
    for nm in NAMES:
        dot = len(re.findall(rf'\b{nm}\.\s+[ivxlcIVXLC]+\.\s+\d', txt))
        bare = len(re.findall(rf'\b{nm}\s+[ivxlcIVXLC]+\.\s+\d', txt))
        tot = dot + bare
        if tot < CORPUS_MIN or min(dot, bare) == 0:
            continue
        if dot >= bare * 9:
            out.append((f'{nm} 后漏了句点（全书 {dot}:{bare}）',
                        re.compile(rf'\b({nm})(\s+[ivxlcIVXLC]+\.\s+\d)'),
                        lambda m: m.group(1) + '.' + m.group(2)))
        elif bare >= dot * 9:
            out.append((f'{nm} 后多了句点（全书 {bare}:{dot}）',
                        re.compile(rf'\b({nm})\.(\s+[ivxlcIVXLC]+\.\s+\d)'),
                        lambda m: m.group(1) + m.group(2)))
    # ver. 同理：全书 1224 处带句点，14 处不带
    out.append(('ver 后漏了句点',
                re.compile(r'\b(ver)(\s+\d)'), lambda m: 'ver.' + m.group(2)))
    return out


def main(apply=False):
    stat = Counter()
    rows = []
    rules = RULES + corpus_rules()
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        t = p.read_text(encoding='utf-8')
        # 规则之间会互相踩上下文（`19,1. 44` 两条规则都想动），所以**单遍顺序**改，
        # 每条的 old/new 都按改动那一刻的正文取，落盘时一条一条按序应用。
        for name, pat, rep in rules:
            while True:
                m = pat.search(t)
                if not m:
                    break
                # 上下文不许跨行、不许含制表符：manual_fixes 是 TSV，
                # 带换行的 old 会把一行撑成两行，读表时直接抛异常、
                # 整批手工修正全部落空——而正文层面看不出任何异常。
                a, b = max(0, m.start() - 34), min(len(t), m.end() + 26)
                while a < m.start() and ('\n' in t[a:m.start()] or '\t' in t[a:m.start()]):
                    a += 1
                while b > m.end() and ('\n' in t[m.end():b] or '\t' in t[m.end():b]):
                    b -= 1
                old = t[a:b]
                new = old[:m.start() - a] + rep(m) + old[m.end() - a:]
                if old == new:
                    break
                t = t[:a] + new + t[b:]
                stat[name] += 1
                rows.append((p.stem, name, old, new))
    for name, _, _ in rules:
        if stat[name]:
            print(f'── {name}：{stat[name]} 处')
    print(f'合计 {len(rows)} 处')
    for sec, name, old, new in rows:
        print(f'  [{sec}] …{old}…\n        → …{new}…')
    if not apply:
        return
    n = skip = 0
    with FIXES.open('a', encoding='utf-8') as fh:
        for sec, name, old, new in rows:
            p = SRC / f'{sec}.md'
            t = p.read_text(encoding='utf-8')
            if t.count(old) != 1:
                skip += 1
                print(f'  !! [{sec}] 定位不唯一，跳过：{old!r}')
                continue
            fh.write(f'{sec}\t{old}\t{new}\trefs: {name}（按全书引用体例）\n')
            p.write_text(t.replace(old, new, 1), encoding='utf-8')
            n += 1
    print(f'落盘 {n} 处，定位不唯一跳过 {skip} 处')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
