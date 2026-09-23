#!/usr/bin/env python3
"""页边界上有没有整行被吞掉——前面所有闸子都看不见的一类。

抽取是按页拼的，一页的最后一行或下一页的第一行整行丢失，拼出来的句子往往
**仍然通顺**：判词典每个词都认得、标点不成双、斜体也配得上、节号照样连号。
只有把两边接起来去问「中间是不是少了几个词」才查得出来。

判法：每个 `<!-- PAGE N -->` 处取前 6 词与后 6 词，拿 1850 三卷本当尺子——
  · 前 3 词做锚在证人词流里定位，读出证人在这之后的一段
  · 我们的后 6 词若出现在证人那段里，但**中间隔了 k 个词**，那 k 个词就是我们丢的

两道闸，不过就不报：
  锚唯一    前 3 词在证人里命中次数不能太多，否则读的是隔壁
  形状      我们的后 6 词必须在证人那段里**按顺序**全部找到，否则说明锚落错了

**证人自己也是 OCR，且是另一版排印**，所以出的是待判清单，最后仍要影像定案。

用法：python3 scripts/psalms_pagebreak_gap.py
"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_ocr as A

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
OUT = ROOT / 'logs/alexander_psalms_pagebreak.tsv'
PAGE = re.compile(r'<!-- PAGE (\d+) -->')
WORD = re.compile(r"[A-Za-zæœÆŒ][A-Za-zæœÆŒ'-]*")
SPAN = 6            # 边界两侧各取几个词
ANCHOR = 3          # 几个词做锚
MAX_HITS = 6        # 锚命中超过这么多次就太泛
WINDOW = 40         # 在证人里往后看多少词
# 证人（1850 三卷本）的文本里**带页眉**：`PSALM CXIX`、`PSALM XXXV`。
# 我们这版把页眉剔干净了，于是每个页边界都会「多出」一个页眉，
# 21 处全是这么来的。页眉不是我们丢的字，要滤掉，否则这条判据报的全是噪音。
# 页眉里的罗马数字在证人那一版上也读崩了（`PSALM LXXYJJ` `PSALM LII IT`
# `PSALM LXVIU`），所以「PSALM 后面跟一小段什么」一律当页眉，别去抠罗马数字。
HEAD = re.compile(r'^(?:PSALMS?|P\s*S\s*A\s*L\s*M)\b[\w\s.,]{0,14}$|'
                  r'^[A-Za-z]$|^[A-Z]{1,2}$|^[^A-Za-z]*$')


def main():
    words, _ = A.load_witness()
    low = [w.lower() for w in words]
    idx = {}
    for i in range(len(low) - ANCHOR):
        idx.setdefault(tuple(low[i:i + ANCHOR]), []).append(i)
    print(f'证人词流 {len(words)} 词')

    stat, rows = Counter(), []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        raw = p.read_text(encoding='utf-8')
        plain = re.sub(r'<(?!!--)[^<>]*>', ' ', raw)
        for m in PAGE.finditer(plain):
            before = WORD.findall(plain[max(0, m.start() - 260):m.start()])[-SPAN:]
            after = WORD.findall(plain[m.end():m.end() + 260])[:SPAN]
            if len(before) < SPAN or len(after) < SPAN:
                stat['两侧词不够'] += 1
                continue
            hits = idx.get(tuple(w.lower() for w in before[:ANCHOR]), [])
            if not hits or len(hits) > MAX_HITS:
                stat['锚不唯一或无'] += 1
                continue
            best = None
            for h in hits:
                seg = low[h:h + WINDOW]
                # 我们的 before 尾巴 + after 必须按顺序全在 seg 里
                need = [w.lower() for w in before[ANCHOR:] + after]
                pos, ok = ANCHOR, True
                where = []
                for w in need:
                    try:
                        pos = seg.index(w, pos) + 1
                    except ValueError:
                        ok = False
                        break
                    where.append(pos - 1)
                if not ok:
                    continue
                # before 最后一个词与 after 第一个词之间隔了几个词
                gap = where[SPAN - ANCHOR] - where[SPAN - ANCHOR - 1] - 1
                if best is None or gap < best[0]:
                    best = (gap, h, where)
            if best is None:
                stat['证人对不上'] += 1
                continue
            gap = best[0]
            if gap == 0:
                stat['接得上'] += 1
                continue
            h, where = best[1], best[2]
            miss = ' '.join(words[h + where[SPAN - ANCHOR - 1] + 1:h + where[SPAN - ANCHOR]])
            if HEAD.match(miss.strip()):
                stat['证人的页眉，滤掉'] += 1
                continue
            stat['中间多出词'] += 1
            rows.append((p.stem, m.group(1), str(gap), ' '.join(before),
                         ' '.join(after), miss))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', encoding='utf-8') as fh:
        fh.write('篇\t书页\t隔了几个词\t页末\t页首\t证人里中间那几个词\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')
    print(f'页边界疑似吞词 {len(rows)} 处 → {OUT}')
    for sec, pg, gap, b, a, miss in rows[:40]:
        print(f'  [{sec:>4} p{pg}] 隔 {gap}：…{b} ⟦{miss}⟧ {a}…')


if __name__ == '__main__':
    main()
