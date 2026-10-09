#!/usr/bin/env python3
"""印面比对的结果 → johnstone_raw/philippians/manual_fixes.tsv

比对报出来的本来就是**带上下文的 before/after**（`MISMATCH: 我们的 ||| 印面的`），
不必再从里面反推规则——直接按上下文定位替换就行，比规则精确得多。

**必须落成表、由 repair 阶段消费**，不能直接改 en_chapters/：
那个目录是 extract 重新生成的，直接改等于没改（feedback_publish_overwrites_handfixes）。
验收口径：重跑整条链条后产物逐字节不变。

四道闸：
  ① 引号样式差异一律不要（弯直引号之争不是错）
  ② 印面那一侧带括注的不要（`(not in image)` 这类是模型在说明，不是正文）
  ③ before 必须在全书**只出现一次**——出现多次说明上下文给得不够，
     放过去会连带改掉别处
  ④ before 必须真能在产物里找到（归一化后比对）；找不到的单独记账

    python3 scripts/johnstone_pageproof_to_fixes.py            # 试跑
    python3 scripts/johnstone_pageproof_to_fixes.py --write
"""
import argparse
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'logs', 'johnstone_pageproof.tsv')
SRC = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'en_chapters')
TBL = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'manual_fixes.tsv')
PAIR = re.compile(r'MISMATCH:\s*(.+?)\s*\|\|\|\s*(.+?)\s*$')
NOTE = re.compile(r'\((?:not|no |line |heading)[^)]*\)|\[[^\]]*\]')
QUOTE = str.maketrans({'‘': "'", '’': "'", '“': '"',
                       '”': '"', '′': "'", '—': '-',
                       '–': '-'})


def norm(s):
    """定位用的归一：引号、破折号、空白、斜体标记都抹平。"""
    s = s.translate(QUOTE).replace('*', '').replace('\\', '')
    return re.sub(r'\s+', ' ', s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()

    texts = {f: open(os.path.join(SRC, f), encoding='utf-8').read()
             for f in sorted(os.listdir(SRC)) if f.endswith('.md')}
    flat = {f: norm(t) for f, t in texts.items()}

    rows, why = [], Counter()
    seen = set()
    for line in open(LOG, encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if not p or not p[0].isdigit() or len(p) < 4:
            continue
        for chunk in p[3].split(' ⟂ '):
            m = PAIR.search(chunk)
            if not m:
                continue
            ours, printed = m.group(1), m.group(2)
            if NOTE.search(printed) or NOTE.search(ours):
                why['② 印面侧是说明不是正文'] += 1; continue
            if norm(ours) == norm(printed):
                why['① 只差引号/破折号样式'] += 1; continue
            key = (norm(ours), norm(printed))
            if key in seen:
                why['重复条目'] += 1; continue
            seen.add(key)
            no, np_ = norm(ours), norm(printed)
            if len(no) < 8:
                why['before 太短，定位不住'] += 1; continue
            hits = [(f, t.count(no)) for f, t in flat.items() if no in t]
            total = sum(c for _, c in hits)
            if total == 0:
                why['④ 产物里找不到'] += 1; continue
            if total > 1:
                why['③ 全书出现多次'] += 1; continue
            rows.append((hits[0][0], p[0], no, np_))

    print(f'可落位 {len(rows)} 条')
    for k, v in why.most_common():
        print(f'  跳过 {v:4d}  {k}')
    if a.write:
        with open(TBL, 'w', encoding='utf-8') as fh:
            fh.write('# 印面比对落下来的人工条目。每行：文件\tleaf\t我们的\t印面的\n')
            fh.write('# 由 scripts/johnstone_pageproof_to_fixes.py 生成，'
                     'repair_johnstone_ocr.py 消费。\n')
            for r in rows:
                fh.write('\t'.join(r) + '\n')
        print(f'→ {TBL}')
    else:
        for r in rows[:12]:
            print(f'  {r[0]:12s} leaf {r[1]:>4s}  {r[2][:62]}')
            print(f'  {"":12s}           → {r[3][:62]}')


if __name__ == '__main__':
    main()
