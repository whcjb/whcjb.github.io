#!/usr/bin/env python3
"""字形特征普查：把发布产物与源 PDF 逐项对数，抓「样式在管道里被吃掉」。

为什么必须有这一步
------------------
pdf-pipeline 原有的 Gate 全是**标记类**检查（`****`、`<<<END`、脚注配对、
`markdown="1"`…），它们只能证明「产物内部自洽」，证明不了「产物忠于 PDF」。
贺智《哥林多前后书》一次性暴露了三处，全都躲过了所有既有 Gate：

  1. **粗体整个丢失** —— 共用的 `_render_spans_with_italic` 只抓颜色+斜体，
     黑色粗体当普通正文吐出。1cor 那些 **First,** / **Secondly,** 段首提示
     词全成了平文。
  2. **居中标题偏左** —— `starts_with_list_item` 把「4. DATE. — CONTENTS…」
     当列表项，取消居中判定，落成 [INDENT]。
  3. **目录层级压平** —— INDENT 不带深度，两级目录都渲染成 margin-left:2em。

三处都是「PDF 里有、产物里没有」，只有对着源头数数才查得出来。

判据
----
按 PDF span 统计各类字形的**字符数**，与产物里对应标记的字符数比对，
超出容差即报。容差存在的原因：产物会做合并（相邻同 style span 合并）、
剥离（页码、AGES 编码），所以不追求逐字相等，只抓数量级差异。

用法:
    python3 scripts/qa_ages_typography.py <pdf> <产物目录或md>
    python3 scripts/qa_ages_typography.py --volume hodge-1cor
"""
import argparse
import glob
import os
import re
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOL = 0.15          # 允许 ±15% 偏差
MIN_ABS = 40        # 少于这么多字符的类别不报（噪声）


def pdf_census(pdf_path: str, skip_head: int = 0, skip_tail: int = 0) -> dict:
    doc = fitz.open(pdf_path)
    c = {'bold': 0, 'italic': 0, 'red': 0, 'greek': 0, 'centered_blocks': 0}
    lo, hi = skip_head, doc.page_count - skip_tail
    for i in range(lo, hi):
        page = doc[i]
        W = page.rect.width
        for b in page.get_text('dict')['blocks']:
            if b['type']:
                continue
            lm, rm = b['bbox'][0], W - b['bbox'][2]
            btxt = ''.join(sp['text'] for ln in b.get('lines', []) for sp in ln['spans']).strip()
            # 页码块本身就是居中的（410 宽的页面上 x≈198），1cor 有 401 个，
            # 不排掉会把「居中内容」这一项彻底淹没（466 里 401 是页码）。
            if abs(lm - rm) < 8 and lm > 30 and not btxt.isdigit():
                c['centered_blocks'] += 1
            for l in b.get('lines', []):
                for s in l['spans']:
                    t = s['text']
                    n = len(t.strip())
                    if not n:
                        continue
                    if s['flags'] & 16 or 'Bold' in s.get('font', ''):
                        c['bold'] += n
                    if s['flags'] & 2:
                        c['italic'] += n
                    if s.get('color') == 0x800000:
                        c['red'] += n
                    if s.get('font', '').startswith('Koine'):
                        # 按 span 计数而非字符数：AGES 转写码到 Unicode 不是
                        # 1:1（lo>gov 6 字符 → λόγος 5 字符），字符数天然缩水
                        # 约 18%，会一直误报。
                        # 按**词**计：一个 span 可能含多个希腊词
                        # （'ejn panti>' 是 1 个 span、2 个词），按 span 计会
                        # 一直少报；产物侧的 [Ͱ-Ͽἀ-῿]+ 词块与之对应。
                        c['greek'] += len(t.split())
    doc.close()
    return c


def md_census(paths: list[str]) -> dict:
    txt = ''
    for p in paths:
        raw = open(p, encoding='utf-8').read()
        txt += raw.split('---', 2)[2] if raw.startswith('---') else raw
    # 粗体 **X**（排除 ***X*** 的重复计数由正则顺序保证）
    # 排除 `**N.**` 节号：那是发布阶段按站内约定加的（bold_leading_verse_num），
    # PDF 里并非粗体，算进来会一直多出 40% 以上。
    bold = sum(len(m.group(1)) for m in re.finditer(r'\*\*([^*]+)\*\*', txt)
               if not re.fullmatch(r'\d+\.', m.group(1)))
    ital = sum(len(m.group(1)) for m in re.finditer(r'(?<!\*)\*([^*\n]+)\*(?!\*)', txt))
    red = sum(len(re.sub(r'<[^>]+>|\*', '', m.group(1)))
              for m in re.finditer(r'<span style="color:#800000">(.*?)</span>', txt, re.S))
    greek = len(re.findall(r'[Ͱ-Ͽἀ-῿]+', txt))    # 按词块数，与 PDF 的 span 数对应
    # 只数块级居中段：title-block-h1/h2 与独立 <p style="text-align:center">。
    # 不能把所有 text-align:center 都算进来——scripture-box 的表格单元格、
    # 发布阶段加的装饰块也带这个属性，会虚高 30%~50%。
    centered = (len(re.findall(r'class="title-block-h[12]"', txt))
                + len(re.findall(r'^<p style="text-align:\s*center', txt, re.M)))
    return {'bold': bold, 'italic': ital, 'red': red,
            'greek': greek, 'centered_blocks': centered}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('out', help='发布目录或单个 md')
    ap.add_argument('--skip-head', type=int, default=0, help='跳过卷首页数（AGES 版权页等）')
    ap.add_argument('--skip-tail', type=int, default=0, help='跳过卷尾页数（AGES 广告页）')
    a = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(a.out, '*.md'))) if os.path.isdir(a.out) else [a.out]
    p = pdf_census(a.pdf, a.skip_head, a.skip_tail)
    m = md_census(paths)

    print(f'  {"特征":<16}{"PDF":>10}{"产物":>10}{"偏差":>10}   判定')
    bad = 0
    for k in ('bold', 'italic', 'red', 'greek', 'centered_blocks'):
        pv, mv = p[k], m[k]
        if pv < MIN_ABS and mv < MIN_ABS:
            verdict = '—（量太小，跳过）'
        else:
            d = (mv - pv) / pv if pv else (1.0 if mv else 0.0)
            if abs(d) <= TOL:
                verdict = '✓'
            else:
                verdict = f'✗ 相差 {d:+.0%}'
                bad += 1
        dd = f'{(mv - pv):+d}' if pv or mv else '0'
        print(f'  {k:<16}{pv:>10,}{mv:>10,}{dd:>10}   {verdict}')
    print(f'\n  {"通过" if not bad else f"{bad} 项超出容差 ±{TOL:.0%}，需查管道是否吃掉了该样式"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
