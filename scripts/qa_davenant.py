#!/usr/bin/env python3
"""达文南特《歌罗西书注释》结构化产物的检查。

本卷**不适用 Gate T**（字形普查）：底本是扫描件，OCR 层没有任何字体信息，
源侧根本数不出粗体/斜体/红色（DIAGNOSIS.md §3）。改用两条：

Gate W  零丢失：结构化产物的词多重集 == OCR 原文（正文页范围）扣掉
        「页眉 + 版面碎片」、并按同一规则合并行末连字之后的词多重集。
        分开报差异，不许拿总数相抵。

Gate S  经文忠于底本：每个 [SCRIPTURE] 块与 KJV 该几节的相似度；
        低于 0.8 的逐条列出。

用法: python3 scripts/qa_davenant.py
"""
import collections
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
sys.path.insert(0, str(ROOT / 'scripts'))
from extract_davenant import (HEAD_RES, JUNK_RE, SPECK_RE, RANGES, clean,  # noqa
                              dehyph, is_foot, norm_map)


def words(t):
    return collections.Counter(re.findall(r'[A-Za-z]+', t))


def expected():
    """按提取器的同一套规则，从 OCR 原文重建「应有」的词多重集。"""
    c = collections.Counter()
    for vol, (lo, hi) in RANGES.items():
        # ⚠️ 连字必须**跨页**合并，与提取器一致。曾按页各自合并，
        # 于是跨页的那几十处连字在两侧记法不同：这一侧留 `de`+`rived`
        # 两个碎片、产物是 `derived` 一个词，白报 203/150 的差。
        joined_vol = ''
        t = (RAW / f'vol{vol}_ocr.txt').read_text(encoding='utf-8')
        for n, body in re.findall(r'<!-- PAGE (\d+) -->\n(.*?)(?=\n<!-- PAGE |\Z)',
                                  t, re.S):
            if not (lo <= int(n) <= hi):
                continue
            lines = [l for l in body.split('\n') if l.strip()]
            # 剥页眉 / 页脚签名——必须与 build_paragraphs 完全同步，
            # 否则 Gate W 报的差全是版面碎片，真丢字反而被淹掉。
            for _ in range(3):
                if lines and any(r.search(lines[0]) for r in HEAD_RES):
                    lines.pop(0)
                    continue
                if lines and (JUNK_RE.match(lines[0]) or SPECK_RE.match(lines[0])):
                    lines.pop(0)
                    continue
                break
            for _ in range(2):
                if lines and is_foot(lines[-1]):
                    lines.pop()
                    continue
                break
            lines = [clean(l) for l in lines if not JUNK_RE.match(l)]
            for l in lines:
                joined_vol = dehyph(joined_vol, l) if joined_vol else l
        c += words(joined_vol)
    return c


def main():
    prod = words(re.sub(r'<!--[^>]*-->|^\[[A-Z]+\]\s*|^\d+:[\d,]+\|[\d.]+\|',
                        '', (RAW / 'davenant_colossians_structured.txt')
                        .read_text(encoding='utf-8'), flags=re.M))
    exp = expected()
    miss, extra = exp - prod, prod - exp
    print(f'Gate W 零丢失：产物 {sum(prod.values()):,} 词 / 应有 {sum(exp.values()):,} 词')
    print(f'  应有而缺 {sum(miss.values()):,} · 多出 {sum(extra.values()):,}')
    if miss:
        print('  缺得最多:', dict(miss.most_common(10)))
    if extra:
        print('  多得最多:', dict(extra.most_common(10)))

    kjv = json.loads((RAW / 'kjv_colossians.json').read_text(encoding='utf-8'))
    low = []
    for m in re.finditer(r'^\[SCRIPTURE\] (?:<!--[^>]*-->)?(\d+):([\d,]+)'
                         r'\|([\d.]+)\| (.*)$',
                         (RAW / 'davenant_colossians_structured.txt')
                         .read_text(encoding='utf-8'), re.M):
        ch, nums, r, txt = m.group(1), m.group(2), float(m.group(3)), m.group(4)
        if r < 0.8:
            low.append((f'{ch}:{nums}', r, txt[:70]))
    print(f'\nGate S 经文忠于底本：{len(low)} 条相似度 < 0.8')
    for k, r, t in low:
        print(f'  {k:10s} {r:.3f}  {t}')
    return 0 if not miss and not extra else 1


if __name__ == '__main__':
    sys.exit(main())
