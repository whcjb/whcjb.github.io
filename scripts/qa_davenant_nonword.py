#!/usr/bin/env python3
"""qa_davenant_nonword.py —— 全书**非词普查**：不依赖「已知错误类型」的体检。

其余几个闸（Gate W / O1–O4 / Gate ⑤ 残留普查）查的都是**已经认识的**错误类，
所以它们报「残留 9 处」时，指的是那几类的残留，不是全书还剩多少错。这个脚本
反过来问：已发布英文正文里，有多少词形**在词典里查不到、也不是本书固有的词**。

判据
  · 词典 = /usr/share/dict/{words,propernames}，外加常见屈折还原（-s/-ed/-ing…）
  · 「本书固有」= 该词形在已发布英文里出现 ≥3 次（拉丁引文、教父人名、
    19 世纪拼法都靠这条豁免；OCR 错字是稀疏的，一般进不了这条）
剩下的就是候选。**候选不等于错**——本书大量拉丁文与只出现一两次的人名地名
会留在里面，实测约七成是这一类。这个数是用来**看趋势**的：修掉一类错之后
它应当下降，涨上去就说明新引入了错。

用法：
    python3 scripts/qa_davenant_nonword.py            # 只报总数与前 60 条
    python3 scripts/qa_davenant_nonword.py --all      # 全列（存档比对用）
"""
import argparse
import collections
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT = set()
for name in ('words', 'propernames'):
    f = Path('/usr/share/dict') / name
    if f.exists():
        DICT |= {w.strip().lower() for w in f.read_text(errors='ignore').split()}

SUFFIXES = ("'s", '’s', "s'", 's', 'es', 'ed', 'd', 'ing', 'ly', 'er',
            'est', 'eth', 'th', 'en')


def stem_ok(w):
    """词典里查得到，或去掉常见后缀之后查得到（web2 只收词元）。"""
    if w in DICT:
        return True
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[:-len(suf)]
            if base in DICT or base + 'e' in DICT:
                return True
            if len(base) > 2 and base[-1] == base[-2] and base[:-1] in DICT:
                return True              # 双写：stopped → stop
            if base.endswith('i') and base[:-1] + 'y' in DICT:
                return True              # y→i：happiness → happy
    return w.startswith('un') and w[2:] in DICT


def docs():
    files = sorted(set(glob.glob(str(ROOT / 'davenant/colossians/**/*.md'),
                                 recursive=True)))
    for f in files:
        if '/zh/' in f:
            continue                     # 中文页不走这个闸
        t = Path(f).read_text(encoding='utf-8')
        body = t.split('---', 2)[2] if t.startswith('---') else t
        body = re.sub(r'<[^>]+>|&[a-z#0-9]+;|\[\^[a-z0-9]+\]', ' ', body)
        yield Path(f).name, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()

    ds = list(docs())
    allw = collections.Counter()
    for _n, b in ds:
        allw.update(re.findall(r"[A-Za-z][A-Za-z'’-]*", b))
    common = {w.lower() for w, c in allw.items() if c >= 3}

    sus, where = collections.Counter(), {}
    for n, b in ds:
        for m in re.finditer(r"[A-Za-z][A-Za-z'’-]*", b):
            w = m.group(0)
            lw = w.lower().strip("'’-")
            if len(lw) < 2 or lw in common or stem_ok(lw):
                continue
            sus[w] += 1
            where.setdefault(w, (n, b[max(0, m.start() - 46):m.end() + 26]
                                 .replace('\n', ' ')))
    print(f'Gate N 非词普查：已发布英文 {sum(allw.values()):,} 词；'
          f'词典外且全书 <3 次的词形 {len(sus)} 种 / {sum(sus.values())} 处')
    print('  （候选里本就含大量拉丁引文与只出现一两次的人名地名，看趋势不看绝对值）')
    for w, c in sus.most_common(None if a.all else 60):
        n, ctx = where[w]
        print(f'  {c:2}  {w:<20} {n:<16} …{ctx}…')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
