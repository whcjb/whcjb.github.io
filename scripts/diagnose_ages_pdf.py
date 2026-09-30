#!/usr/bin/env python3
"""AGES 单列注释 PDF 的 Step 1 诊断器。

把 hodge-romans 那次手工诊断（见 hodge_raw/romans/DIAGNOSIS.md）固化成脚本：
同一批量（AGES Digital Library 的 410×626 单列注释）再开新书时，一条命令拿到
skill 起手清单要的全部数字，并直接吐出可粘贴的 VOLUMES 条目。

为什么要脚本化：手工诊断漏掉任何一项，后面都是静默出错——
  · 漏看脚注区标题是 NOTES 不是 FOOTNOTES → detect_fn_start_page 返回 None，
    全书脚注定义丢光（romans 踩过）
  · 漏看 x0 次峰是页码不是第二列 → 误判双语，scripture-mode 空转
  · 漏记字形基线 → Gate T 没有比对基准，"产物忠于 PDF" 无从验证

用法:
    python3 scripts/diagnose_ages_pdf.py <pdf> [--name hodge-ephesians]
        [--out hodge_raw/ephesians/hodge_ephesians_structured.txt]
        [--book-cn 以弗所书]
"""
import argparse
import collections
import os
import re
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_ages_typography import pdf_census            # noqa: E402  Gate T 的同一口径

RED = '800000'       # AGES 经文引语红
BLUE = '0000d4'      # 标签蓝（同时是希腊文 Koine 的颜色，判标签必须排除 Koine 字体）
GREEN = '006411'     # 章节头绿

FLAG_ITALIC = 2
FLAG_BOLD = 16


def color_hex(span):
    return f'{span.get("color", 0):06x}'


def iter_spans(page):
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0:
            continue
        for line in b.get('lines', []):
            for s in line.get('spans', []):
                yield b, line, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--name', default='NEW-BOOK', help='VOLUMES 键名，如 hodge-ephesians')
    ap.add_argument('--out', default='', help='raw 产物路径（写进 VOLUMES 条目）')
    ap.add_argument('--book-cn', default='', help='中文书名，仅用于打印')
    ap.add_argument('--skip-head', type=int, default=3,
                    help='字形基线跳过的卷首页数（默认 3：封面/TOC/书名页）')
    ap.add_argument('--skip-tail', type=int, default=2,
                    help='字形基线跳过的卷尾页数（默认 2：AGES 广告）')
    args = ap.parse_args()

    doc = fitz.open(args.pdf)
    n = len(doc)
    page0 = doc[0]
    meta = doc.metadata or {}

    print(f'# {args.name} 诊断  {args.book_cn}')
    print(f'源 {args.pdf}')
    print()
    print('## 起手清单')
    print(f'  页数        {n}  ({page0.rect.width:.0f}×{page0.rect.height:.0f})')
    print(f'  title       {meta.get("title")}')
    print(f'  producer    {meta.get("producer")}')
    print(f'  creationDate{meta.get("creationDate")}')

    head_text = '\n'.join(doc[i].get_text() for i in range(min(3, n)))
    print(f'  AGES 指纹   封面含 "AGES DIGITAL LIBRARY": '
          f'{"✓" if "AGES DIGITAL LIBRARY" in head_text.upper() else "✗"}')

    anchors = sum(len(re.findall(r'<\d{6}>', doc[i].get_text()))
                  for i in range(min(60, n)))
    print(f'  <NNNNNN> 锚点 {anchors}'
          '   （贺智三卷都是 0，这是 Calvin-AGES 的特征，别拿来当贺智判据）')

    # ── x0 分布（行级），区分正文 / 段首缩进 / 页码 ──────────────────────────
    xs = collections.Counter()
    xs_pagenum = collections.Counter()
    for i in range(min(40, n - 1), min(120, n)):
        for b in doc[i].get_text('dict')['blocks']:
            if b['type'] != 0:
                continue
            for line in b.get('lines', []):
                if not any(s['text'].strip() for s in line.get('spans', [])):
                    continue
                x0 = round(line['bbox'][0])
                if line['bbox'][1] < 40:        # 页顶 → 多半是页码/页眉
                    xs_pagenum[x0] += 1
                else:
                    xs[x0] += 1
    print()
    print('## x0 分布（正文页 40–120 行级，页顶另计）')
    for x, c in xs.most_common(6):
        print(f'  x0={x:4d}: {c:5d} 行')
    if xs_pagenum:
        top = xs_pagenum.most_common(3)
        print('  页顶（页码/页眉）: ' + ', '.join(f'x0={x}:{c}' for x, c in top))
    body_x = xs.most_common(1)[0][0] if xs else 26
    indent_x = next((x for x, _ in xs.most_common(6) if x > body_x + 6), body_x + 18)
    para_indent = max(8, indent_x - body_x - 6)
    print(f'  → 正文 x={body_x} / 段首 x={indent_x}（实测缩进 {indent_x - body_x}）')
    print(f'  → para_indent={para_indent}'
          '  ← 配置里这个值是**下限阈值**，要比实测缩进小几个点，'
          '否则临界行会被判成续行（1cor/2cor/romans 实测 18，配 12）')

    # ── 字号谱 / 字体（诊断用，全书）─────────────────────────────────────
    sizes = collections.Counter()
    fonts = collections.Counter()
    colors = collections.Counter()
    hebrew_chars = 0
    for i in range(n):
        for b, line, s_ in iter_spans(doc[i]):
            t = s_['text']
            if not t.strip():
                continue
            sizes[round(s_['size'], 1)] += 1
            fonts[s_['font']] += len(t)
            ch = color_hex(s_)
            if ch in (RED, BLUE, GREEN):
                colors[ch] += len(t)
            if 'Gideon' in s_['font']:
                hebrew_chars += len(t)

    print()
    print('## 字号谱（span 数）')
    for sz, c in sizes.most_common(8):
        print(f'  {sz:5.1f}pt: {c:6d}')
    print()
    print('## 字体（字符数）')
    for f, c in fonts.most_common(8):
        print(f'  {f:32s} {c:8d}')

    # 字形基线直接调 Gate T 的 pdf_census —— 两处若各写一套口径，
    # 基线和日后 Gate T 的读数就对不上（centered_blocks 尤其敏感：
    # 页码块本身居中，不排掉会把这一项淹掉）。
    base = pdf_census(args.pdf, args.skip_head, args.skip_tail)
    print()
    print(f'## 字形基线（Gate T 口径，skip_head={args.skip_head} skip_tail={args.skip_tail}）')
    for k in ('bold', 'italic', 'red', 'greek', 'centered_blocks'):
        print(f'  {k:16s} {base[k]}')
    print(f'  blue #{BLUE} (全书)  {colors.get(BLUE, 0)}'
          '    ← 标签蓝，与希腊文 Koine 同色，判标签必须排除 Koine 字体')
    print(f'  green #{GREEN} (全书) {colors.get(GREEN, 0)}')
    print(f'  hebrew Gideon (全书) {hebrew_chars}')

    # ── 结构：卷首 / 章起始 / 脚注区 / 卷尾 ────────────────────────────────
    print()
    print('## 卷首 5 页首行')
    for i in range(min(5, n)):
        first = next((ln for ln in doc[i].get_text().splitlines() if ln.strip()), '')
        print(f'  p{i}: {first[:70]}')

    print()
    print('## 卷尾 4 页首行')
    for i in range(max(0, n - 4), n):
        first = next((ln for ln in doc[i].get_text().splitlines() if ln.strip()), '')
        print(f'  p{i}: {first[:70]}')

    # 罗马数字里混进字母 l/O 是 AGES 数字化的老毛病（以弗所书 p240 就是
    # `CHAPTER Vl`，小写 L 冒充 I）。字符集必须放宽到 lO，否则整章检测不到，
    # 发布阶段会静默少一章。
    chap_re = re.compile(r'^\s*CHAPTER\s+([IVXLClO]+)\.?\s*$', re.M)
    chapters = []
    for i in range(n):
        m = chap_re.search(doc[i].get_text())
        if m:
            chapters.append((m.group(1), i))
    print()
    print(f'## 章起始页（{len(chapters)} 章）')
    print('  ' + '  '.join(f'{r}={p}' for r, p in chapters))
    bad = [(r, p) for r, p in chapters if set(r) & set('lO')]
    if bad:
        print('  ⚠ 罗马数字里有假字母（源里的错字，不是我们读错）: '
              + ', '.join(f'p{p} 写作 {r!r}' for r, p in bad))
        print('    → 发布阶段的章头正则必须认这个变体，否则少一章')

    # 卷首该跳几页：封面 / HYPERTEXT TOC / 纯书名页。**不能照抄别卷的 {0,1,2}**
    # —— 以弗所书的 p2 是「书名 + INTRODUCTION 正文」同页，照抄会把导论首页丢掉。
    skip = []
    for i in range(min(6, n)):
        txt = doc[i].get_text()
        up = txt.upper()
        body = max((len(ln) for ln in txt.splitlines()), default=0)
        is_cover = 'AGES DIGITAL LIBRARY' in up or 'SAGE DIGITAL LIBRARY' in up
        is_toc = 'HYPERTEXT TABLE OF CONTENTS' in up
        # 纯书名页没有成句的正文行。别拿作者名当判据——罗马书 p2 是
        # 'BY\nCHARLES HODGE, D.D.'，换行把字符串切开了，一查就漏。
        is_titleonly = body < 60
        if is_cover or is_toc or is_titleonly:
            skip.append(i)
        else:
            break
    print()
    print(f'## 卷首应跳过 {skip}  （逐页判封面/TOC/纯书名页，勿照抄别卷）')

    fn_page = None
    fn_label = None
    for i in range(int(n * 0.5), n):
        m = re.search(r'^\s*(FOOTNOTES|NOTES)\s*$', doc[i].get_text(), re.M)
        if m:
            fn_page, fn_label = i, m.group(1)
            break
    print()
    print(f'## 脚注区  {"p%d  标题=%s" % (fn_page, fn_label) if fn_page else "未找到"}')
    if fn_page is None:
        print('  ⚠ detect_fn_start_page 会返回 None → 脚注定义会全丢，必须查清楚')

    # 卷尾 AGES 广告页
    tail_ad = 0
    for i in range(n - 1, max(0, n - 6), -1):
        txt = doc[i].get_text().upper()
        if 'AGES SOFTWARE' in txt or 'AGES DIGITAL LIBRARY' in txt:
            tail_ad += 1
        else:
            break
    stop_page = n - tail_ad
    print(f'## 卷尾 AGES 广告 {tail_ad} 页 → stop_page={stop_page}')

    skip_set = ', '.join(str(i) for i in skip)
    skip_why = ' / '.join(['封面', 'HYPERTEXT TOC', '纯书名页'][:len(skip)])
    out = args.out or f'hodge_raw/{args.name.split("-")[-1]}/{args.name.replace("-", "_")}_structured.txt'
    print()
    print('## 可粘贴的 VOLUMES 条目')
    print(f"""    '{args.name}': {{
        'format': 'ages_phil',
        'inline_sup_footnotes': True,
        'para_indent': {para_indent},   # 正文 x{body_x} / 段首 x{indent_x}，实测
        'skip_pages': {{{skip_set}}},   # {skip_why}
        'stop_page': {stop_page},          # 之后是 AGES 出版广告
        'pdf':  '{args.pdf}',
        'out':  os.path.join(BASE, '{out}'),
    }},""")
    doc.close()


if __name__ == '__main__':
    sys.exit(main())
