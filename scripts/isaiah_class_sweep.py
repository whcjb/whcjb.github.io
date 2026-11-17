#!/usr/bin/env python3
"""以赛亚书：实读抽章找到的错误「类」→ 全书同类候选。

每一类都来自第 40–43 轮逐页看图（PROOFREAD_STATUS）实际找到的错，写成文字判据，
全书列候选，交给 isaiah_garble_verify 裁图 + isaiah_garble_sheets 拼图逐条看。
只列不改。输出列与 isaiah_garble_detector --broad 相同：章 页 行 词 类 前词 后词 上下文。

类：
  heb-dup      同一希伯来串首尾相连写了两遍（25 章 מדמנהמדמנה）
  stray-quote  孤立的 ' 或 " 贴在小写词前，后面同句没有配对（53 章 'make、25 章 "whether）
  heb-letter   单个拉丁字母/数字顶替希伯来字母（followed by a a;、has a before、equivalent of 2,、the i at）
  heb-missing  讨论希伯来词的句式里那个词整个丢了（whether means、that means to pardon、—is properly）
  glued        两个英文词粘连（beinothe、ungodlybrethren）——只列「拆开后两半都是常用词」的
  heb-comma    希伯来词前的英文句号被读成逗号（filtered, ממחים from…；nations, שמנים properly）

用法：python3 scripts/isaiah_class_sweep.py [--only 类,类] > $S/cls.tsv
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isaiah_garble_detector import known, load_dict   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUB = Path(__import__('os').environ.get('ISAIAH_PUB', ROOT / 'alexander/isaiah'))
HEB = r'[א-ת][א-ת֑-ׇ־]*'

CUE_NOUN = r'(?:word|verb|form|phrase|noun|particle|reading|term|root|suffix|preposition|letter|expression)'
MISSING = [
    # 「whether ___ means」「that ___ means」「—___ is properly」
    re.compile(r'\b(?:whether|that|of|which) (?:means|denotes|signifies) (?:to|the|a|life)\b'),
    re.compile(r'—(?:is|are|was) (?:properly|commonly|strictly|here|not)\b'),
    re.compile(r'\b(?:version|reading|form|verb|word|noun|particle|term) of (?:On|In|The|It|This|But)\b'),
    re.compile(r'\b(?:the|of|word|verb|read|reads|reading) (?:and|or) [א-ת]'),
    re.compile(r'(?<=[.;]) (?:and|or) [א-ת]'),
    re.compile(r'\b(?:explains|takes|gives|makes|derives|reads|read) (?:as|to|the sense|from) (?=[א-ת]|\()'),
]
LETTER = re.compile(r'\b(?:the|of|by|has|a|making|with|before|after|followed by a|preposition|particle|letter|equivalent of) '
                    r'([a-z2-9])(?=[ ,;.)](?:at|and|before|after|in|is|the|;|,|\)|was|has|though| ?[א-ת]))')


def lines():
    for p in sorted(PUB.glob('[0-9]*.md'), key=lambda p: int(p.stem)):
        ch = int(p.stem)
        page = '?'
        body = p.read_text(encoding='utf-8').split('\n---\n', 1)[1]
        for ln, line in enumerate(body.split('\n'), 1):
            m = re.findall(r'<!-- PAGE (\d+) -->', line)
            if m:
                page = m[-1]
            flat = re.sub(r'<[^>]+>', '', line)
            yield ch, page, ln, flat


def row(ch, page, ln, flat, s, e, kind):
    while s > 0 and not flat[s - 1].isspace():
        s -= 1
    e2 = flat.find(' ', s + 1)
    e = len(flat) if e2 < 0 else e2
    toks_before = flat[:s].split()
    toks_after = flat[e:].split()
    tok = flat[s:e].strip() or flat[s:e]
    ctx = ' '.join(toks_before[-7:] + [tok] + toks_after[:6])
    return (ch, page, ln, tok, kind, toks_before[-1] if toks_before else '', toks_after[0] if toks_after else '', ctx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    a = ap.parse_args()
    only = set(a.only.split(',')) if a.only else None
    dic = {w for w in load_dict() if len(w) >= 3 or w in ('a', 'i', 'of', 'to', 'in', 'is', 'it', 'be', 'by', 'as',
                                                            'at', 'or', 'on', 'he', 'we', 'an', 'no', 'so')}
    common = {w.strip().lower() for w in open('/usr/share/dict/words', encoding='latin-1')} & dic
    out = []
    for ch, page, ln, flat in lines():
        def add(s, e, k):
            if only is None or k.split(':')[0] in only:
                out.append(row(ch, page, ln, flat, s, e, k))
        for m in re.finditer(r'(?<![\u05D0-\u05EA\u0591-\u05C7])([\u05D0-\u05EA\u0591-\u05C7]{3,})\1(?![\u05D0-\u05EA\u0591-\u05C7])', flat):
            if len(re.sub(r'[^\u05D0-\u05EA]', '', m.group(1))) >= 3:     # צלצל 这类两字母重叠是真词
                add(m.start(), m.end(), 'heb-dup')
        for m in re.finditer(r"(?<=\s)(['\"])(?=[a-z])", flat):
            q = m.group(1)
            rest = flat[m.end():m.end() + 400]
            close = rest.find("'" if q == "'" else '"')
            if q == "'" and re.search(r"[a-z]'[ ,.;:)]", rest[:close + 2] if close >= 0 else ''):
                pass
            if close < 0 or (q == "'" and close > 300):
                add(m.start(), m.end() + len(rest.split(' ', 1)[0]), 'stray-quote')
        for m in re.finditer(r'(?<=[a-z,] )(["\'])(?=[א-ת])|(?<=[א-ת])(["\'])(?= )', flat):
            add(m.start(), m.end(), 'stray-quote:heb')
        for m in LETTER.finditer(flat):
            add(m.start(1), m.end(1), 'heb-letter')
        for pat in MISSING:
            for m in pat.finditer(flat):
                add(m.start(), m.end(), 'heb-missing')
        for m in re.finditer(r'\b[a-z]{9,}\b', flat):
            w = m.group(0)
            if known(w, dic) or w.endswith(('ness', 'ment', 'ing', 'ed', 'ly', 'ers', 'ion', 'ions')):
                continue
            for i in range(3, len(w) - 2):
                x, y = w[:i], w[i:]
                if x in common and y in common and len(x) >= 3 and len(y) >= 3:
                    add(m.start(), m.end(), f'glued:{x} {y}')
                    break
        for m in re.finditer(r'(?<=[a-z\)]), (' + HEB + r') (?=(?:is|means|properly|from|has|does|denotes|signifies|was|probably|may|must)\b)', flat):
            add(m.start() - 1, m.end(), 'heb-comma')
    for r in out:
        print('\t'.join(map(str, r)))
    import collections
    print('#', collections.Counter(r[4].split(':')[0] for r in out), file=sys.stderr)


if __name__ == '__main__':
    main()
