#!/usr/bin/env python3
"""双语经文块审计 —— 按 pdf-pipeline 02a §11 的规定检查产物。

skill 定的形态（§11.0 用户底线，被反复打回过）：
    <div class="scripture-box scripture-box--bilingual" markdown="1">
      <p class="scripture-ref">…<span class="verse-range">A:B-C</span></p>
      <table class="scripture-bilingual"><tbody>
        <tr><td class="scripture-en">…</td><td class="scripture-la">…</td></tr>
      </tbody></table>
    </div>
**不可**简化成「只保留英文」，也**不可**中文段/拉丁段交替单列。

两类缺陷（都在 §11.4 反例表里）：

  [A] 整块漏成散段：经文根本没进 box，渲染成
      `<p style="margin-left:2em">中文</p>` + `<p style="text-align:right">拉丁</p>`
      交替。俄巴底亚书就是整章如此（2026-09-03 用户发现）。

  [B] box 截断：ref 写 `A:B-C` 但 box 里 `<tr>` 行数 < (C-B+1)，
      余下的节漏在 box 外作散段。skill 原文：「`<tr>` 行数 < (C-B+1) 必须 0 命中」。

判「拉丁散段」用的是**字符构成**而非猜测：右对齐段里拉丁字母占比高、且以
节号起首。中文注释段不会满足（中文页里右对齐段几乎只有拉丁经文）。

用法:
    python3 scripts/qa_bilingual_scripture.py                 # 全部书卷
    python3 scripts/qa_bilingual_scripture.py --ot            # 只查旧约
    python3 scripts/qa_bilingual_scripture.py --book obadiah
    python3 scripts/qa_bilingual_scripture.py --book obadiah --detail
"""
import argparse
import glob
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 旧约（含分卷）。harmony-law-* 是摩西五经合参，也算旧约。
OT = ['genesis', 'harmony-law-1', 'harmony-law-2', 'harmony-law-3', 'harmony-law-4',
      'joshua', 'psalms-1', 'psalms-2', 'isaiah-1', 'isaiah-2',
      'jeremiah-1', 'jeremiah-2', 'lamentations', 'ezekiel', 'daniel',
      'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum',
      'habakkuk', 'zephaniah', 'haggai', 'zechariah', 'malachi']

BOX_RE = re.compile(
    r'<div class="scripture-box[^"]*"[^>]*>(.*?)</div>', re.S)
RANGE_RE = re.compile(r'<span class="verse-range">(\d+):(\d+)(?:\s*[-–]\s*(\d+))?')
TR_RE = re.compile(r'<tr>')
RIGHT_P_RE = re.compile(r'^<p style="text-align:\s*right;?"[^>]*>(.*?)</p>\s*$', re.M | re.S)
TAG = re.compile(r'<[^>]+>')


def latin_ratio(s):
    """拉丁字母 / (拉丁字母 + 汉字)。拉丁经文段应该很高。"""
    lat = len(re.findall(r'[A-Za-z]', s))
    han = len(re.findall(r'[一-鿿]', s))
    return lat / (lat + han) if (lat + han) else 0.0


def audit_file(path):
    """→ (漏成散段的拉丁段数, [(box_ref, tr数, 应有节数)]) """
    text = open(path, encoding='utf-8').read()

    # 先把所有 box 的区间记下来，box 内的右对齐段不算「漏在外面」
    spans = [(m.start(), m.end()) for m in BOX_RE.finditer(text)]

    def in_box(pos):
        return any(a <= pos < b for a, b in spans)

    stray = []
    for m in RIGHT_P_RE.finditer(text):
        if in_box(m.start()):
            continue
        inner = TAG.sub('', m.group(1)).strip()
        # 节号后可以带点：`11. Die quo stabas…`。原先写 `^\d+\s` 要求紧跟
        # 空白，于是带点的一律漏报——俄巴底亚 v.11-14/19-20 六处就这么漏的，
        # 我据此误报过一次「0 处」（2026-09-03）。
        if not re.match(r'^\d{1,3}\.?\s', inner):     # 不以节号起首 → 不是经文
            continue
        if latin_ratio(inner) < 0.35:                # 汉字为主 → 不是拉丁经文
            continue
        # ⚠️ 必须紧邻 box / anchor 才算缺陷。加尔文以赛亚书的体例是：章首一个
        # box 给整章经文，之后**每节的拉丁引句紧接该节注释**散在正文里——那是
        # 原书体例，不是漏出框外。不加这条限制，以赛亚两卷会虚报近千处
        # （我据此报过 1167 的错数字，2026-09-03）。
        head = text[max(0, m.start() - 300):m.start()]
        if not re.search(r'scripture-box|scripture-anchor', head):
            continue
        stray.append(inner[:70])

    # [C] 单元格错位：某一行的中文格或拉丁格是空的，说明配对没对上——
    # 该节的文字被并进了上一行的格子里（jeremiah-1/4.md ref 4:11-12：
    # 第 1 行中文格里塞了 11、12 两节，第 2 行中文格空着，拉丁格才是 12 节）。
    # 这比「节号缺失」精确：节号本身可能以纯文本 `12.` 混在上一格里，
    # 求差集查不出来，空格子却是硬信号。
    empty_cells = []
    for tr in re.findall(r'<tr>(.*?)</tr>', text, re.S):
        cells = re.findall(r'<td class="scripture-(en|la)">(.*?)</td>', tr, re.S)
        for side, inner in cells:
            if not TAG.sub('', inner).strip():
                other = next((TAG.sub('', v).strip()[:44]
                              for k, v in cells if k != side), '')
                empty_cells.append(f'{side} 空 ← 对侧: {other}')

    truncated = []
    for m in BOX_RE.finditer(text):
        body = m.group(1)
        rm = RANGE_RE.search(body)
        if not rm:
            continue
        a, b, c = rm.group(1), int(rm.group(2)), rm.group(3)
        if not c:
            continue                                 # 单节 ref，无从比对
        # 不能拿 <tr> 行数直接比节数：加尔文常把两三节并作一行
        # （`**1, 2.**`），行数天然少于节数，那样会一直误报。
        # 改成从每行的节号里求**实际覆盖的节**，再与 B..C 求差集。
        covered = set()
        for td in re.findall(r'<td class="scripture-en">(.*?)</td>', body, re.S):
            for num in re.findall(r'<strong>\s*([\d,，、\s\-–]+?)\.?\s*</strong>', td):
                for part in re.split(r'[,，、]', num):
                    part = part.strip()
                    rm2 = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', part)
                    if rm2:
                        covered.update(range(int(rm2.group(1)), int(rm2.group(2)) + 1))
                    elif part.isdigit():
                        covered.add(int(part))
        if not covered:
            continue                                 # 行里没有节号，无从判断
        missing = sorted(set(range(b, int(c) + 1)) - covered)
        if missing:
            truncated.append((f'{a}:{b}-{c}', missing, len(TR_RE.findall(body))))
    return stray, truncated, empty_cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', action='append', default=[])
    ap.add_argument('--ot', action='store_true', help='只查旧约')
    ap.add_argument('--detail', action='store_true')
    a = ap.parse_args()

    if a.book:
        books = a.book
    elif a.ot:
        books = [b for b in OT]
    else:
        books = sorted({os.path.basename(p.rstrip('/')).removesuffix('-en')
                        for p in glob.glob(str(ROOT / 'calvin' / '*/'))})

    bad_books = 0
    tot_stray = tot_trunc = tot_empty = 0
    for book in books:
        for suffix in ('', '-en'):
            d = ROOT / 'calvin' / (book + suffix)
            if not d.is_dir():
                continue
            s_n = t_n = e_n = 0
            rows = []
            for f in sorted(glob.glob(str(d / '*.md'))):
                stray, trunc, empties = audit_file(f)
                if stray or trunc or empties:
                    rows.append((os.path.basename(f), stray, trunc, empties))
                s_n += len(stray)
                t_n += len(trunc)
                e_n += len(empties)
            if s_n or t_n or e_n:
                bad_books += 1
                tot_stray += s_n
                tot_trunc += t_n
                tot_empty += e_n
                print(f'  {book + suffix:22s} 漏成散段 {s_n:3d} · 缺节 {t_n:2d}'
                      f' · 空单元格 {e_n:3d}')
                if a.detail:
                    for name, stray, trunc, empties in rows:
                        for x in stray:
                            print(f'      [{name}] 散段: {x}')
                        for ref, missing, nrow in trunc:
                            print(f'      [{name}] 缺节: ref {ref} 表内 {nrow} 行，'
                                  f'缺 {missing}')
                        for x in empties:
                            print(f'      [{name}] 错位: {x}')
    print(f'\n  {bad_books} 个书卷有问题：漏成散段 {tot_stray} · 缺节 {tot_trunc}'
          f' · 空单元格 {tot_empty}')
    return 1 if bad_books else 0


if __name__ == '__main__':
    sys.exit(main())
