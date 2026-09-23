#!/usr/bin/env python3
"""**孤立的虚词斜体**——ABBYY 斜体检测漏判的形态。

亚历山大的斜体是有意义的：它标出「这是我对希伯来文的译文」或「我正在讨论
这个词」。所以虚词排斜体**本身完全正常**（`The *for* at the beginning`、
`the copulative *and*`、`The translation *are* is contrary to Hebrew usage`）,
光看词频判不出对错。

两条判据叠起来才准：
  孤立    前后 60 字符内没有别的 `<em>`。他的译词引用总是成簇出现
          （`*By waters*, not simply *to* them, but *along* them`），
          孤零零一个虚词斜体才可疑
  非元语言 前面没有「particle / preposition / copulative / emphatic /
          the … at the beginning」这类提示词——有提示就是在讨论那个词，斜体对

**必须看渲染后的 `<em>`，不能在 markdown 层面数星号**：`earth.* The *not hid*`
里的 `The` 会被误算成一个强调，第一版判据就是这么把 286 处虚假放大到 2110 处的。

出的是待判清单，最后仍要影像定案（实测 20 处里真误判 6 处）。

用法：python3 scripts/psalms_italic_stray.py
"""
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
NEAR = 60
FUNC = {'and', 'the', 'or', 'to', 'in', 'for', 'with', 'on', 'from', 'they',
        'this', 'all', 'but', 'he', 'a', 'is', 'are', 'it', 'as', 'at', 'that',
        'not', 'be', 'by', 'of', 'so', 'my', 'me', 'his', 'was', 'when', 'if',
        'him', 'their', 'we', 'you', 'which'}
META = re.compile(
    r'\b(particle|preposition|conjunction|pronoun|noun|verb|adverb|copulative|'
    r'emphatic|article|word|words|phrase|expression|term|translation|form|'
    r'construction|reading|rendering|clause|sense|meaning|use|usage|insertion|'
    r'introduction|repetition|omission|explanation|substitution|instead of|'
    r'at the beginning|suggests|denotes|connects|relates|means|refers)\b'
    r'[^.]{0,30}$', re.I)
# 元语言提示常落在斜体**后面**：`The *and* at the beginning`、
# `The *for* connects it with…`、`a *but* instead of the simple copulative`。
# 只看左边会漏掉一多半。
META_R = re.compile(
    r'^\s*(at the beginning|connects|suggests|denotes|relates|refers|means\b|'
    r'instead of|in that case|has reference|is contrary|would have required|'
    r'in either case)', re.I)
# 逐处核过影像、印面确是斜体的，记下来不再报（「已有结论的桶不再被后续判据覆盖」）
VERIFIED = ROOT / 'alexander_raw/psalms/italic_printed_italic.tsv'
TAG = re.compile(r'<[^<>]+>')


def load_verified():
    d = set()
    if VERIFIED.exists():
        for line in VERIFIED.read_text(encoding='utf-8').splitlines():
            if line.startswith('#') or not line.strip():
                continue
            f = line.split('\t')
            if len(f) >= 3:
                d.add((f[0], f[1].strip().lower(), f[2].strip()))
    return d


def main():
    verified = load_verified()
    rows = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        body = p.read_text(encoding='utf-8')
        body = body.split('---', 2)[2] if body.startswith('---') else body
        out = subprocess.run(['kramdown', '--input', 'GFM'], input=body,
                             capture_output=True, text=True).stdout
        ems = [(m.start(), m.end(),
                html.unescape(TAG.sub('', m.group(1))).strip())
               for m in re.finditer(r'<em>(.*?)</em>', out, re.S)]
        for a, b, w in ems:
            if w.lower() not in FUNC:
                continue
            if any(s[0] != a and s[0] < b + NEAR and s[1] > a - NEAR for s in ems):
                continue
            left = html.unescape(TAG.sub('', out[max(0, a - 100):a]))
            if META.search(left):
                continue
            right = html.unescape(TAG.sub('', out[b:b + 60]))
            if META_R.search(right):
                continue
            key = re.sub(r'\W+', '', html.unescape(TAG.sub('', out[max(0, a - 40):a])))[-18:]
            if (p.stem, w.lower(), key) in verified:
                continue
            ctx = re.sub(r'\s+', ' ',
                         html.unescape(TAG.sub('', out[max(0, a - 72):b + 44])))
            rows.append((p.stem, w, ctx))
    print(f'孤立虚词斜体待判 {len(rows)} 处')
    for sec, w, ctx in rows:
        print(f'  [{sec:>4}] *{w}*  …{ctx}…')
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
