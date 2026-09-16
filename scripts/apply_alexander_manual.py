#!/usr/bin/env python3
"""把「只存在于已发布正文里」的人工判读落回正文，让整条链可以重跑。

为什么需要它：`adjudicate_alexander_image.py` / 裁图判读 / 逐张读影像这几轮
改的都是**已发布的** `alexander/psalms/*.md`，而 `publish_alexander_en.py`
是从 `en_chapters/` 全量重写这些文件的——重跑一次 publish，这些判读就全没了。
其中裁图那一轮的落盘脚本当时写在会话里，没留下来，读数（round1/round2.tsv）
还在，但复现不出当时的落盘。

于是把这批改动整体固化成数据：拿「链条跑到 image 判读为止」的产物与已发布
正文逐词 diff，每一处差异连同刚好唯一的上下文写进
`alexander_raw/psalms/manual_fixes.tsv`（chapter / old / new / src）。
src 记来源：crop2 = 裁图两遍互证，crop2-sim = 按相似度择位，
crop2-dictgate-manual = 判词闸拦下后逐条看影像放行，hand = 逐张读影像手工落定。

规则是**按篇**匹配的，且要求 old 在该篇里唯一——MANUAL_TEXT 那种全书纯字符串
替换踩过太多次（`lliou`→`Thou` 把 rebellious 改成 rebeThous）。

用法：
    python3 scripts/apply_alexander_manual.py            # 只报告
    python3 scripts/apply_alexander_manual.py --apply    # 落盘
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
SRC = ROOT / 'alexander/psalms'


def load():
    rules = {}
    with TSV.open(encoding='utf-8') as fh:
        head = next(fh).rstrip('\n').split('\t')
        assert head == ['chapter', 'old', 'new', 'src'], head
        for line in fh:
            if not line.strip():
                continue
            ch, old, new, src = line.rstrip('\n').split('\t')
            rules.setdefault(ch, []).append((old, new, src))
    return rules


def main(apply=False):
    rules = load()
    stat = Counter()
    bad = []
    for ch, lst in sorted(rules.items()):
        path = SRC / f'{ch}.md'
        if not path.exists():
            bad.append((ch, '', '篇不存在'))
            continue
        text = path.read_text(encoding='utf-8')
        spots = []
        for old, new, src in lst:
            n = text.count(old)
            if n == 1:
                i = text.index(old)
                spots.append((i, old, new))
                stat['hit'] += 1
                continue
            # 找不到 old：先看是不是已经是修复后的形态（幂等重跑的常态）。
            # 两种形态都找不到，或者 old 命中多处，才是真故障——上游文本
            # 变了，这条规则再落盘就会改错位置。
            if n == 0 and text.count(new) >= 1:
                stat['已是修复后形态'] += 1
            elif n == 0:
                stat['失效'] += 1
                bad.append((ch, old, '原串与修复后形态都找不到'))
            else:
                stat['不唯一'] += 1
                bad.append((ch, old, f'在本篇里出现 {n} 次，不敢动'))
        # 上下文锚是彼此独立取的，可能互相搭界；搭界就只落先出现的那条，
        # 另一条留给下一轮（正文变了它会自己报失效）。
        spots.sort()
        keep, end = [], -1
        for i, old, new in spots:
            if i < end:
                stat['重叠跳过'] += 1
                bad.append((ch, old, '与前一条锚重叠'))
                continue
            keep.append((i, old, new))
            end = i + len(old)
        for i, old, new in reversed(keep):
            text = text[:i] + new + text[i + len(old):]
        if apply and keep:
            path.write_text(text, encoding='utf-8')
    print(f'manual_fixes {sum(len(v) for v in rules.values())} 条：' +
          '，'.join(f'{k} {v}' for k, v in stat.items()))
    if bad:
        print(f'!! {len(bad)} 条需要人看：')
        for ch, old, why in bad[:20]:
            print(f'   [{ch}] {old!r}  {why}')
    return 1 if stat['失效'] or stat['不唯一'] else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    sys.exit(main(ap.parse_args().apply))
