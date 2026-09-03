#!/usr/bin/env python3
"""跨页断句检查 —— **按 PDF 真值判定**，不猜标点。

为什么另起一个脚本
------------------
`fix_page_split_paragraphs.py` 是在**产物**里用标点正则猜「这一段有没有结句」。
2026-09-03 做贺智罗马书时，同一条判据一天内被戳穿四次：

  1. 续段守卫只认小写起首 → 断在专有名词前的全漏（Christ / Ahab / Jesus）
  2. END_PUNCT 只有 ASCII → 中文页以「。」收尾的段落全被当成没结句
  3. 右引号算句末 → 句中引语 `“of Christ,”` 被放过（美式标点逗号在引号内）
  4. 缩写句点算句末 → `found (i.e.` 被放过

每次都是「补一条正则」，而每本新书的排版习惯又能变出新的例外。**机制本身
不可靠**：产物里没有句子边界的真值，只有猜。

判据换成 PDF 几何 + 文本对齐
----------------------------
1. **PDF 侧判「这一页是不是断在段落中间」**：两端对齐的正文，段落中间的行都
   顶到右边距，只有段落**最后一行**是短的。所以「第 N 页末行齐右边距」⇒
   这一段续到第 N+1 页。几何信号，与标点、语言、作者习惯全都无关。
2. **锚点用文本，不用 PAGE 标记**：产物里 `<!-- PAGE N -->` 的位置**不可靠**
   ——提取器合并跨页段落时会把标记推到段与段之间，按标记位置对齐会刷出大片
   假阳性（实测 139 处全假）。改成取「页末若干词 + 次页首若干词」当指纹，
   在产物段落序列里找：落在同一段内 = 正常；分落相邻两段 = 断句。

只用 ASCII 词做指纹：PDF 侧是 AGES 希腊转写码、产物侧已转 Unicode，
希腊/希伯来词两边对不上，一律跳过不参与匹配。

用法:
    python3 scripts/qa_page_break_pdf.py <pdf> <产物目录> [--skip-head N] [--skip-tail N]
    python3 scripts/qa_page_break_pdf.py ... --fix        # 合并（PAGE 标记留在行内）
"""
import argparse
import glob
import os
import re
import sys
from collections import Counter

import fitz

TAG = re.compile(r'<[^>]+>')
PAGE_MARK = re.compile(r'^<!--\s*PAGE\s+(\d+)\s*-->$')
NON_BODY = re.compile(r'^\s*(?:#|\[\^[^\]]+\]:|<!--|<div\s|<p\s+class="title-block)')
WORD = re.compile(r'[A-Za-z]{2,}')

NEEDLE = 4          # 页末 / 次页首各取几个 ASCII 词做指纹


def _words(s):
    return WORD.findall(s.lower())


def pdf_boundaries(pdf_path, skip_head, skip_tail, tol=2.0):
    """→ [(页末指纹词, 次页首指纹词)]，只收「页末行齐右边距」的边界。"""
    doc = fitz.open(pdf_path)
    lo, hi = skip_head, doc.page_count - skip_tail

    x1s, x0s = Counter(), Counter()
    for i in range(lo, hi):
        for b in doc[i].get_text('dict')['blocks']:
            if b['type']:
                continue
            for l in b.get('lines', []):
                x1s[round(l['bbox'][2])] += 1
                x0s[round(l['bbox'][0])] += 1
    if not x1s:
        doc.close()
        return []
    right = max(x1s, key=lambda x: x1s[x])
    body_left = max(x0s, key=lambda x: x0s[x])       # 正文左边距（众数）

    def body_lines(i):
        page, label = doc[i], str(i + 1)
        out = []
        for b in page.get_text('dict')['blocks']:
            if b['type']:
                continue
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans']).strip()
                if not t or t == label:
                    continue
                out.append((l['bbox'][1], l['bbox'][2], t, round(l['bbox'][0])))
        out.sort()
        return out

    res = []
    prev = body_lines(lo)
    for i in range(lo, hi - 1):
        cur, nxt = prev, body_lines(i + 1)
        prev = nxt
        if not cur or not nxt:
            continue
        if cur[-1][1] < right - tol:                 # 页末行短 → 段落在此结束
            continue
        # tol 收到 2.0：4.0 时 x1=382（右边距 386）也被算作「齐边」，把
        # 「前页末行本已结段、次页首是 VERSE 6. 新段」误判成断句（罗马书
        # PAGE 652）。齐边判定要严，宁可漏报交给别的信号。
        #
        # 第二个信号：次页首行有没有段首缩进。
        # 「页末行齐右边距」单独用不够——段落最后一行偶尔正好填满整个行宽，
        # 实测 262 个边界里约 5% 是这种（罗马书 12 处全假）。AGES 排版里
        # 续行落在正文左边距、新段首行缩进（贺智实测 x26 / x44），所以
        # 次页首行缩进 = 新段开始 = 这个边界不是断句。
        if nxt[0][3] > body_left + 6:
            continue
        # 结构性段首：小型大写节号头 `VERSE N.` / `VERSES N, M.` 在 PDF 里
        # **不缩进**（贺智全书 404 处一律 x=26），所以上面的缩进信号识别不了，
        # 必须按内容排除，否则会把「节号头起新段」误判成续行。
        if re.match(r'^V\s*ERSES?\s*[:.]?\s*\d', nxt[0][2]):
            continue
        tail = _words(cur[-1][2])[-NEEDLE:]
        head = _words(' '.join(t for _, _, t, _x in nxt[:2]))[:NEEDLE]
        if len(tail) < NEEDLE or len(head) < NEEDLE:  # 指纹不足（希腊文行等）
            continue
        res.append((i + 2, tail, head))
    doc.close()
    return res


OPENERS = {'(': ')', '（': '）', '[': ']', '【': '】'}


def unbalanced_tail(text):
    """段末是否留着未闭合的括号 → 这一段必定续到下一段。

    确定性信号，不是猜：`The apostle had authority (i.e.` 少一个 `)`，
    中译的 `使徒有权柄（即` 少一个 `）`。几何判据在这里失效——这本 PDF 的
    两端对齐并不一致，页末行 x1=377 而右边距 385，「齐右边距」测不出来
    （2cor PAGE 256，2026-09-03）。括号配平与排版、语言、标点习惯全无关。
    """
    stack = []
    for pos, ch in enumerate(text):
        if ch in OPENERS:
            stack.append((OPENERS[ch], pos))
        elif stack and ch == stack[-1][0]:
            stack.pop()
    if not stack:
        return None
    closer, pos = stack[-1]
    # 未闭合的开括号必须落在**段末**：段落中间遗留的孤立 `(`（源里本就有，
    # 如 `(comp.` 之类）不是跨页断句，收进来会刷假阳性（罗马书 4 处）。
    if len(text) - pos > 20:
        return None
    return closer


def read_paragraphs(path):
    """→ (原始行, [(行下标, 该段的 ASCII 词序列)])，只收正文段。"""
    lines = open(path, encoding='utf-8').read().split('\n')
    paras = []
    for idx, l in enumerate(lines):
        if not l.strip() or NON_BODY.match(l) or PAGE_MARK.match(l.strip()):
            continue
        txt = TAG.sub('', l)
        txt = txt.replace('**', '').replace('*', '')
        w = _words(txt)
        if w or txt.strip():
            paras.append((idx, w, txt))
    return lines, paras


def find_splits(paras, bounds):
    """指纹分落相邻两段 → 断句。返回 [(段尾行号, 续段行号, 页标号)]。"""
    hits = []
    for num, tail, head in bounds:
        for j in range(len(paras) - 1):
            a_idx, a_w, _a = paras[j]
            b_idx, b_w, _b = paras[j + 1]
            if a_w[-len(tail):] == tail and b_w[:len(head)] == head:
                hits.append((a_idx, b_idx, num))
                break
    return hits


def unbalanced_splits(lines, paras):
    """规则 B：段末括号未闭合，且与下一段之间只隔空行/页标记 → 断句。"""
    hits = []
    for j in range(len(paras) - 1):
        a_idx, _aw, a_txt = paras[j]
        b_idx, _bw, _b = paras[j + 1]
        closer = unbalanced_tail(a_txt)
        if not closer:
            continue
        # 下一段开头必须真的把它闭上，且本身不是标题/列举标签
        if closer not in _b[:40]:
            continue
        if re.match(r'^\s*(?:\*\*|\([a-z]\)|[（(][a-z][)）])', _b):
            continue
        mid = lines[a_idx + 1:b_idx]
        if any(x.strip() and not PAGE_MARK.match(x.strip()) for x in mid):
            continue                      # 中间有别的内容，不是纯页界分隔
        hits.append((a_idx, b_idx, 0))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('out', help='产物目录或单个 md')
    ap.add_argument('--skip-head', type=int, default=0)
    ap.add_argument('--skip-tail', type=int, default=0)
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--show', type=int, default=8)
    a = ap.parse_args()

    bounds = pdf_boundaries(a.pdf, a.skip_head, a.skip_tail)
    print(f'  PDF 判定：{len(bounds)} 个页边界断在段落中间（末行齐右边距）')

    paths = (sorted(glob.glob(os.path.join(a.out, '*.md')))
             if os.path.isdir(a.out) else [a.out])
    total, shown = 0, 0
    for p in paths:
        lines, paras = read_paragraphs(p)
        hits = find_splits(paras, bounds) + unbalanced_splits(lines, paras)
        seen, uniq = set(), []
        for h in sorted(hits):
            if h[0] not in seen:
                seen.add(h[0]); uniq.append(h)
        hits = uniq
        if not hits:
            continue
        total += len(hits)
        for i, k, num in hits:
            if shown < a.show:
                print(f'  [{os.path.basename(p)}] PAGE {num}  L{i+1}→L{k+1}')
                print(f'      末: …{TAG.sub("", lines[i]).strip()[-52:]}')
                print(f'      续: {TAG.sub("", lines[k]).strip()[:52]}…')
                shown += 1
        if a.fix:
            for i, k, _ in sorted(hits, reverse=True):
                mid = [x.strip() for x in lines[i + 1:k] if x.strip()]
                lines[i] = (lines[i].rstrip() + ' ' + ' '.join(mid) + ' '
                            + lines[k].lstrip())
                del lines[i + 1:k + 1]
            os.chmod(p, 0o644)
            open(p, 'w', encoding='utf-8').write('\n'.join(lines))

    verb = '已合并' if a.fix else '发现'
    print(f'  {verb} {total} 处')
    return 0 if (total == 0 or a.fix) else 1


if __name__ == '__main__':
    sys.exit(main())
