#!/usr/bin/env python3
"""**白名单字符体检**——「这一页上不该出现的字符」。

为什么要这一条：前面所有残渣判据都是**黑名单**，而且都要求可疑符号左右有
字母或数字（`psalms_garbage_sweep` 的正则就是 `[A-Za-z0-9^...]*[\\^\\]\\[|}{~]...`）。
于是**孤零零一个符号**——`(ארץ)• This`、`of *^* perfect`、`thy God* / The very`
——一处也看不见：ABBYY 把墨点读成 `•`，把 `?` 读成 `/`，把 `a` 读成 `^`，
左右都是空格或括号，黑名单正则匹配出来长度为 1，被 `len(s) < 2` 滤掉。
诗篇十四道闸全绿之后，这一条一次扫出 39 处（2026-10-08）。

判据反过来写：**列出允许的字符，其余一律报**。
  · 任何 Unicode 字母（Lu/Ll/Lo —— 含希伯来、希腊、带变音的拉丁）与组合音符（Mn）
  · 数字、空白
  · 一张写死的标点表（见 PUNCT）——这本书的正文只用得上这些
转义星号 `\\*` 先剥掉（kramdown 的转义，不是残渣）；HTML 标记与注释不算正文。

出的是待判清单，**不直接落盘**：`•` 可能是墨点（删）、可能是句点（改），
`^` 可能是 `a`、可能是开引号，只有翻 1864 影像才定得了案。

用法：python3 scripts/alexander_charset_sweep.py [psalms|isaiah] [--limit N]
"""
import argparse
import glob
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r'<[^<>]+>')
CMT = re.compile(r'<!--.*?-->', re.S)
WS = re.compile(r'\s+')
# 正文用得上的标点。**别往里加 `/ ^ • _ | ~ { } [ ] < > = $ % #`**——
# 那些在这本书里一个也不该出现，加进来等于把这条判据关掉。
PUNCT = set(" \t\n.,;:!?'\"()-*—–§&"
            "\u05be")              # 希伯来连字符 maqaf，正当标点
# 「印面如此」台账：每行 `篇<TAB>字符<TAB>说明`，按篇+字符精确放行
def ledger_path(book):
    return ROOT / f'alexander_raw/{book}/charset_printed_as_is.tsv'


def load_ledger(book):
    ok = set()
    p = ledger_path(book)
    if p.exists():
        for line in p.read_text(encoding='utf-8').splitlines()[1:]:
            f = line.split('\t')
            if len(f) >= 2:
                ok.add((f[0], f[1]))
    return ok


def allowed(ch):
    if ch in PUNCT:
        return True
    cat = unicodedata.category(ch)
    return cat in ('Lu', 'Ll', 'Lo', 'Lt', 'Lm', 'Mn', 'Mc', 'Nd')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', nargs='?', default='psalms')
    ap.add_argument('--limit', type=int, default=60)
    a = ap.parse_args()
    ok = load_ledger(a.book)
    rows, stat = [], Counter()
    files = sorted(glob.glob(str(ROOT / f'alexander/{a.book}/*.md')),
                   key=lambda x: (Path(x).stem != 'preface', Path(x).stem))
    for f in files:
        sec = Path(f).stem
        t = Path(f).read_text(encoding='utf-8')
        body = t.split('---', 2)[2] if t.startswith('---') else t
        # 注释与标记按等长空白替换，位置不漂
        body = CMT.sub(lambda m: ' ' * len(m.group(0)), body)
        body = TAG.sub(lambda m: ' ' * len(m.group(0)), body)
        body = body.replace('\\*', '  ')
        for i, ch in enumerate(body):
            if allowed(ch) or (sec, ch) in ok:
                continue
            stat[ch] += 1
            rows.append((sec, ch, WS.sub(' ', body[max(0, i - 70):i + 55]).strip()))
    print(f'{a.book}：不该出现的字符 {len(rows)} 处'
          + (f'（另有台账放行 {len(ok)} 条）' if ok else ''))
    if stat:
        print('  按字符：' + '，'.join(
            f'{c!r}×{n}' for c, n in stat.most_common()))
    for sec, ch, ctx in rows[:a.limit]:
        print(f'  [{sec:>12}] {ch!r}  …{ctx}…')
    if len(rows) > a.limit:
        print(f'  …还有 {len(rows) - a.limit} 处')
    return 1 if rows else 0


if __name__ == '__main__':
    sys.exit(main())
