#!/usr/bin/env python3
"""括号里的补词是**正体**，斜体在括号处断开。

亚历山大的体例：斜体是他对希伯来文的译文，圆括号里是他**补出来的词**
（`(is)` `(are)` `(those)` `(One)` `(with)`），印面上一律正体——这正是
「这几个字不在原文里」的记号。我们全书 690 处把括号包在了斜体里面，
那个记号就丢了。

**这不是抽取弄丢的，是 ABBYY 的斜体检测不稳**：同一份 XML 里，
它有 513 处正确地把括号断成了正体段，另有 690 处漏了。两边的括号内容
是同一类东西（`(which)` `(the midst of)` vs `(is)` `(things)`），
说明印面体例统一，只是检测漏了一半。

影像核过 7 处（诗 45 `(One)`、诗 117 `(is)`、诗 131 `(things)`、
诗 134 `(ones)`/`(is the influence)`、诗 66 `(with)`/`(exaltation)`、
诗 22 `(as belonging)`），无一例外是正体。

**不动的三种**：
  · `(or …)` `(and …)` `(but …)` —— 那是交替译法，括号里的词本身是译文，
    印面上「or」正体、后面的词斜体（`(or *repose)`），混排，不能一刀切
  · 括号里已经有 `*` 的 —— 已经是混排，别碰
  · 括号里有希伯来/希腊字母的 —— 那是原文引用，另一回事

用法：
    python3 scripts/psalms_italic_parens.py            # 只报告
    python3 scripts/psalms_italic_parens.py --apply    # 改 en_chapters
"""
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw/psalms/en_chapters'
SPAN = re.compile(r'(?<!\\)\*([^*\n]{1,600}?)(?<!\\)\*')
PAREN = re.compile(r'\([^()]{1,40}\)')
SKIP_HEAD = re.compile(r'\(\s*(or|and|but)\s', re.I)
FOREIGN = re.compile(r'[֐-׿Ͱ-Ͽἀ-῿]')


def split_span(inner):
    """把一段斜体里的括号挑出来，返回新的（带断开的）写法，连同断开处数。

    星号只包**去掉首尾空白之后的实词内容**：`*of wicked *(men)*` 这种写法
    会让空白落进 `<em>`，渲染层校验里叫「斜体跑飞」。纯标点的尾巴
    （`*of righteous* (men)*.*`）也不单独包——包出来是个 `<em>.</em>`。
    """
    pieces, last, n = [], 0, 0
    for m in PAREN.finditer(inner):
        g = m.group(0)
        if SKIP_HEAD.match(g) or '*' in g or FOREIGN.search(g):
            continue
        pieces.append(('it', inner[last:m.start()]))
        pieces.append(('ro', g))
        last = m.end()
        n += 1
    if not n:
        return None, 0
    pieces.append(('it', inner[last:]))

    out = []
    for kind, s in pieces:
        if kind == 'ro':
            out.append(s)
            continue
        if not s:
            continue
        core = s.strip()
        if not core or not re.search(r'[A-Za-z֐-׿]', core):
            out.append(s)                      # 只有空白或标点，原样留着
            continue
        lead = s[:len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        out.append(f'{lead}*{core}*{trail}')
    return ''.join(out), n


def main(apply=False):
    stat = Counter()
    samples = []
    for p in sorted(RAW.glob('*.md')):
        t = p.read_text(encoding='utf-8')

        def repl(m):
            new, n = split_span(m.group(1))
            if not n:
                return m.group(0)
            stat['断开的括号'] += n
            stat['动到的斜体段'] += 1
            if len(samples) < 12:
                samples.append((p.stem, m.group(0)[:64], new[:70]))
            return new

        t2 = SPAN.sub(repl, t)
        if apply and t2 != t:
            p.write_text(t2, encoding='utf-8')
    print('，'.join(f'{k} {v}' for k, v in stat.items()) or '没有要改的')
    for sec, a, b in samples:
        print(f'  [{sec}] {a!r}\n        → {b!r}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
