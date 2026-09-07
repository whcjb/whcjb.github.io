#!/usr/bin/env python3
"""修贺智产物里的两类提取误判（伪标题 / 伪居中段）。

来源：AGES 贺智罗马书把每个 ANALYSIS 段的**首行**排成 16pt（正文 12pt），
纯排版手法；提取器按字号判 H2，于是半句话被切成标题、后半句另起一段：

    ## THIS section consists of two parts. The first from vers. 1 to 7 inclusive, is
    a salutatory address; the second, …

同书 ANALYSIS 段两侧内缩（lm 43.5 / rm 37.5），几何上符合「居中」，
跨页续段于是被判成居中标题，网页上单独居中一段。

提取器已加守卫（calvin_extract.py：H2 满幅降级 / 小写散文不判居中），
本脚本把同样的变换落到**已发布**的 md，免得重跑整条发布链。
零丢失：词多重集守恒，脚本内置断言。

用法:
    python3 scripts/fix_hodge_pseudo_blocks.py --check hodge/romans
    python3 scripts/fix_hodge_pseudo_blocks.py hodge/romans
"""
import argparse
import glob
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENTERED_RE = re.compile(
    r'<p style="text-align:center" markdown="1">(.*?)</p>', re.S)


def _words(t):
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'^#{1,6}\s+', '', t, flags=re.M)
    return Counter(re.findall(r'\w+', t))


def fix_text(s):
    n_h2 = n_cen = 0

    # ① 伪标题：`## 半句话`（行尾无句末标点）+ 空行 + 下一段 → 合成一段
    def h2(m):
        nonlocal n_h2
        head, body = m.group(1).strip(), m.group(2)
        if re.search(r'[.!?:]\s*$', re.sub(r'<[^>]+>', '', head)):
            return m.group(0)            # 真标题，不动
        n_h2 += 1
        return head + ' ' + body.lstrip()

    s = re.sub(r'^## (.+?)\n\n(?=\S)(.+?)(?=\n\n)', h2, s, flags=re.M | re.S)

    # ② 伪居中段：小写起首 + ≥6 词的散文 → 并回**上一段**末尾
    #    （它是上一段跨页的续行；居中标题在本语料里一律全大写）
    def cen(m):
        nonlocal n_cen
        inner = m.group(1).strip()
        plain = re.sub(r'<[^>]+>', '', inner).strip()
        if not (re.match(r'^[a-z]', plain) and len(plain.split()) >= 6):
            return m.group(0)
        n_cen += 1
        return '\x00MERGE\x00' + inner

    s = CENTERED_RE.sub(cen, s)
    # 把标记段接到上一段尾巴（段间的空行一并吃掉）
    s = re.sub(r'\n\n+\x00MERGE\x00', ' ', s)
    s = s.replace('\x00MERGE\x00', '')          # 段首无上一段时兜底
    return s, n_h2, n_cen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', help='目录，如 hodge/romans')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    files = sorted(glob.glob(str(ROOT / a.target / '*.md')))
    th = tc = 0
    for f in files:
        s = open(f, encoding='utf-8').read()
        new, nh, nc = fix_text(s)
        if not (nh or nc):
            continue
        if _words(s) != _words(new):
            d = _words(s) - _words(new)
            print(f'  !! {os.path.relpath(f, ROOT)} 词不守恒（少 {sum(d.values())}），跳过')
            continue
        th += nh; tc += nc
        print(f'  {os.path.relpath(f, ROOT)}: 伪标题 {nh} · 伪居中 {nc}')
        if not a.check:
            open(f, 'w', encoding='utf-8').write(new)
    print(f'\n  {"可修" if a.check else "已修"} 伪标题 {th} 处 · 伪居中 {tc} 处')
    return 0


if __name__ == '__main__':
    sys.exit(main())
