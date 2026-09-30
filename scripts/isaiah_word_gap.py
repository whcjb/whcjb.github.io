#!/usr/bin/env python3
"""两个词之间该有的词距没了：`of-the subject`、`Bethlehem,where`、`in.Hebrew`。

三种写法，同一个后果——读者一眼就看得见，而既有的十几道闸一个也看不见：
判词典按空白分段，`of-the` 在它眼里是 `of` + `the` 两个好词；多证人判读的
TOKEN 正则也在连字符和标点处断开，比的还是那两个真词；渲染层、节号、斜体
闸更与它无关。

  ① **墨点被读成连字符**：`of-the`、`the Jews-and half-Jews`、`but-of`。
     影像上那一点比同行真连字符细得多、位置偏下（核过 v1 p183 / p155 /
     p187 / p571，v2 p284 / p301 / p391）。判据：连字符右边是虚词——
     真复合词右边不会是虚词，除非是固定说法（`father-in-law`、
     `good-for-nothing`、`both-and`），那些走白名单。
  ② **标点后的词距整个丢了**：`Bethlehem,where`、`Hendewerk),or`。
     这一类不用翻影像：英文排印里逗号后面必有词距，两边又都是真词。
  ③ **墨点被读成句点**：`in.Hebrew`、`and.Aaronic`。与 ① 同源，只是读成了
     句点而不是连字符。缩写（`ch.`、`ver.`、`etc.`）要排除掉。

左边是希伯来/希腊残串的一律放行（`nt-a`、`oai-a`、`Ji:aa`）：那里本来就不是
英文词，不归这条判据管。

只报告，不自动改。`--emit` 把每一处写成 `manual_fixes.tsv` 的一行（带足上下文
保证全书唯一），人核过之后再追加进表——落表而不是直接改产物，是因为
publish 每次都会把正文重写一遍，只改产物等于没改。

用法：
    python3 scripts/isaiah_word_gap.py             # 只报告
    python3 scripts/isaiah_word_gap.py --emit      # 输出可直接追加的修复表行
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'

FUNC = {'the', 'its', 'of', 'and', 'in', 'to', 'a', 'is', 'it', 'that', 'this',
        'with', 'be', 'as', 'was', 'his', 'her', 'their', 'not', 'by', 'for',
        'on', 'or', 'but', 'he', 'they', 'we', 'you', 'which', 'who', 'from',
        'an', 'at'}
# 印面上本来就是连字符的固定说法
KEEP = {'good-for', 'bag-of', 'sword-in', 'arm-in', 'God-with', 'father-in',
        'man-at', 'both-and', 'either-or', 'et-et', 'aut-aut', 'half-Jews',
        'to-day', 'to-morrow', 'so-called', 'well-to'}
# 缩写后面的点不是墨点
ABBREV = {a.lower() for a in A.ABBREV} | {'etc', 'ad', 'loc', 'ed', 'vo', 'fol'}

HYPHEN = re.compile(r'\b([A-Za-z]{2,})-([a-z]{1,5})\b')
JOIN = re.compile(r'\b([A-Za-z]{2,}\)?)([,;:])([A-Za-z][a-z]{1,})\b')
DOT = re.compile(r'\b([A-Za-z]{2,})\.([A-Za-z][a-z]{1,})\b')

LEX = L.build()
# 判词典对两字母串一律放行（`Ji`、`aa` 都算「词」），这三条判据两边都靠
# 「是不是真词」立住，放行两字母串就等于把希伯来残串 `Ji:aa`、`'is-a`
# 也收进来。两字母的真词是个封闭集合，直接列出来。
TWO = {'of', 'to', 'in', 'is', 'it', 'as', 'at', 'by', 'be', 'he', 'we', 'or',
       'on', 'an', 'no', 'so', 'do', 'if', 'us', 'my', 'me', 'up', 'am'}


def word(w):
    if len(w) <= 2:
        return w.lower() in TWO
    return L.is_word(w, LEX)


def scan():
    out = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: x.stem):
        text = p.read_text(encoding='utf-8')
        masked = A._mask_markup(text)

        def ctx(m):
            return masked[max(0, m.start() - 38):m.end() + 20].replace('\n', ' ')

        def row(m, kind):
            # 掩码与原文同长同位，所以位置可以直接拿回原文切片
            return (p.stem, kind, m.group(0), ctx(m), text, m.start(), m.end())

        for m in HYPHEN.finditer(masked):
            left, right = m.group(1), m.group(2)
            if right.lower() not in FUNC or m.group(0) in KEEP or not word(left):
                continue
            # 左边必须是一个词的开头。`as 'is-a is to` 里那个 `'` 说明这一串
            # 是希伯来活字的残渣，不是两个英文词粘在了一起
            if m.start() and not masked[m.start() - 1].isspace():
                continue
            out.append(row(m, '① 墨点读成连字符'))
        for m in JOIN.finditer(masked):
            left, right = m.group(1).rstrip(')'), m.group(3)
            if not (word(left) and word(right)):
                continue
            out.append(row(m, '② 标点后缺词距'))
        for m in DOT.finditer(masked):
            left, right = m.group(1), m.group(2)
            if left.lower() in ABBREV or not word(left):
                continue
            if not word(right) or right[0].isupper() == right[1:].isupper():
                continue
            out.append(row(m, '③ 墨点读成句点'))
    return out


NOTE = {
    '① 墨点读成连字符': '墨点被读成连字符（影像：那一点比同行真连字符细得多、位置偏下）',
    '② 标点后缺词距': '标点后的词距整个丢了（英文排印里逗号后必有词距，两边又都是真词）',
    '③ 墨点读成句点': '墨点被读成句点（与连字符那一类同源，只是读成了句点）',
}


def repair(token, kind):
    """把粘住的两个词分开。**只动那一个字符**，别的一律不碰。"""
    if kind.startswith('①'):
        return token.replace('-', ' ', 1)
    if kind.startswith('③'):
        return token.replace('.', ' ', 1)
    i = min(j for j, c in enumerate(token) if c in ',;:')
    return token[:i + 1] + ' ' + token[i + 1:]


def emit(hits):
    """每一处写成修复表的一行，左串补上下文直到全书唯一。"""
    book = ''.join(p.read_text(encoding='utf-8') for p in SRC.glob('*.md'))
    for sec, kind, token, _, text, a, b in hits:
        new = repair(token, kind)
        for pad in (0, 16, 34, 60):
            head = text[max(0, a - pad):a]
            if book.count(head + token) == 1:
                print(f'{head + token}\t{head + new}\tgap-{sec}: {NOTE[kind]}')
                break
        else:
            print(f'# 定位不唯一，手工补上下文：[{sec}] {token!r}')


def main(do_emit=False):
    hits = scan()
    if do_emit:
        emit(hits)
        return 0
    for sec, kind, token, c, *_ in hits:
        print(f'[{sec}] {kind} {token}\t…{c}…')
    print(f'词距丢失：{len(hits)} 处'
          + ('（全部落盘 ✓）' if not hits else '，逐处核过后落 manual_fixes.tsv'))
    return 1 if hits else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--emit', action='store_true')
    sys.exit(main(ap.parse_args().emit))
