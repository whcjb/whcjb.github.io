#!/usr/bin/env python3
"""正文字符流比对：产物 vs 源 PDF，逐字对。

Gate T（qa_ages_typography.py）只比**字形特征的数量**，证明不了正文一个字
都没丢。本脚本比的是正文本身——把两边都归一到「纯文字流」后逐字 diff。

归一规则（两边都做，务求可比）：
  · PDF 侧：AGES 希腊转写码 → Unicode（与产物同一函数 convert_ages_greek），
    去页码行、去 AGES 卷首版权页/卷尾广告页。
  · 产物侧：剥 HTML 标签、markdown 强调标记（* **）、脚注标记 [^fN]、
    页界注释 <!-- PAGE N -->、发布阶段加的 `**N.**` 节号粗体。
  · 两侧：折叠所有空白，去掉引号/破折号的样式差异。

用法:
    python3 scripts/qa_ages_text.py <pdf> <发布目录> [--skip-head N] [--skip-tail N]
    python3 scripts/qa_ages_text.py ... --show 20     # 打印前 20 处差异
"""
import argparse
import difflib
import glob
import os
import re
import sys

# 文末集中脚注区的标题文字（--fn-section-title 追加）
FN_TITLES = {'FOOTNOTES'}

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from structured_to_md import convert_ages_greek, collapse_spaced_caps   # noqa: E402


def norm(s: str) -> str:
    s = s.replace('’', "'").replace('‘', "'")
    s = s.replace('“', '"').replace('”', '"')
    s = s.replace('—', '-').replace('–', '-').replace('‒', '-')
    s = s.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


def words(s: str) -> list:
    """切成词序列。百万字符上按字符跑 SequenceMatcher 要几十分钟，
    按词跑是秒级；定位到差异段之后再看字符也够用。"""
    return s.split(' ')


def pdf_stream(pdf: str, skip_head: int, skip_tail: int) -> tuple:
    """-> (正文流, 脚注流)。AGES 把脚注全收在书末 FOOTNOTES 之后，而产物把
    每条 def 归到它所属的章里——位置天差地别，混在一起比会刷出大片假差异。
    所以按 FOOTNOTES 标题切开，正文与脚注各比各的。"""
    doc = fitz.open(pdf)
    out, notes, in_notes = [], [], False
    for i in range(skip_head, doc.page_count - skip_tail):
        page_label = str(i + 1)
        for b in doc[i].get_text('dict')['blocks']:
            if b['type']:
                continue
            for l in b.get('lines', []):
                t = ''.join(sp['text'] for sp in l['spans'])
                # 页码行（整行就是页码数字）不算正文
                if t.strip() == page_label:
                    continue
                # 只认书末那个 FOOTNOTES 标题：卷首的超链接目录里也有一行
                # 「Footnotes」，不设页数下限会从第 5 页就切开，把整本正文
                # 都算进脚注流（实测踩过）。
                # 标题按卷而异：贺智哥林多前后书是 FOOTNOTES，罗马书是 NOTES。
                # 只认书末那个（i > 0.75），卷首超链接目录里的同名行不算。
                if (t.strip().upper() in FN_TITLES
                        and i > doc.page_count * 0.75):
                    in_notes = True
                    continue
                (notes if in_notes else out).append(t)
    doc.close()
    prep = lambda xs: norm(collapse_spaced_caps(convert_ages_greek('\n'.join(xs))))
    return prep(out), prep(notes)


def md_stream(out_dir: str) -> tuple:
    paths = sorted(glob.glob(os.path.join(out_dir, '*.md'))) if os.path.isdir(out_dir) else [out_dir]
    # preface 排前面，章节按数字序——与 PDF 顺序一致
    def key(p):
        stem = os.path.basename(p)[:-3]
        return (0, 0) if stem == 'preface' else (1, int(stem) if stem.isdigit() else 99)
    bd, nt = [], []
    for p in sorted(paths, key=key):
        raw = open(p, encoding='utf-8').read()
        body = raw.split('---', 2)[2] if raw.startswith('---') else raw
        body = re.sub(r'<!--.*?-->', '', body, flags=re.S)      # 页界注释
        # ⚠️ 必须先剥 HTML 再剥脚注标记：脚注引用常被包在 <sup>/<span> 里，
        # 顺序反了会剩下 `[^]` 之类的残骸（实测踩过）。
        body = re.sub(r'<[^>]+>', '', body)                     # HTML
        body = re.sub(r'^#{1,6}\s+', '', body, flags=re.M)      # markdown 标题号
        body = body.replace('**', '').replace('*', '')          # 强调标记
        body = body.replace('&quot;', '"').replace('&amp;', '&')
        body = body.replace('&lt;', '<').replace('&gt;', '>')
        # 脚注定义单独成流（PDF 里它们在书末，产物里按章分散）
        for line in body.split('\n'):
            m = re.match(r'^\[\^f?\w+\]:\s*(.*)$', line)
            (nt if m else bd).append(m.group(1) if m else line)
    # 脚注引用还原成裸数字：PDF 里它就是个上标数字（"Nero. 1"），产物里是
    # `[^f1]`。删掉的话 PDF 侧会多出一堆孤立数字，刷成假差异；换成数字两边
    # 就对齐了。
    strip_ref = lambda x: re.sub(r'\[\^f?t?(\w+?)\]', r' \1 ', x)
    return norm(strip_ref('\n'.join(bd))), norm(strip_ref('\n'.join(nt)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('out')
    ap.add_argument('--skip-head', type=int, default=0)
    ap.add_argument('--skip-tail', type=int, default=0)
    ap.add_argument('--fn-section-title', action='append', default=[],
                    help='文末脚注区标题（罗马书是 NOTES），可多次给')
    ap.add_argument('--show', type=int, default=12)
    a = ap.parse_args()
    FN_TITLES.update(t.strip().upper() for t in a.fn_section_title)

    A, An = pdf_stream(a.pdf, a.skip_head, a.skip_tail)
    B, Bn = md_stream(a.out)
    for label, x, y in (('脚注', An, Bn),):
        wx, wy = words(x), words(y)
        r = difflib.SequenceMatcher(None, wx, wy, autojunk=False).ratio() if (wx or wy) else 1.0
        print(f'  [{label}] PDF {len(wx):,} 词 / 产物 {len(wy):,} 词   相似度 {r:.5f}')
    print()
    wa, wb = words(A), words(B)
    ca, cb = len(A.replace(' ', '')), len(B.replace(' ', ''))
    print(f'  PDF  {ca:,} 字符 / {len(wa):,} 词')
    print(f'  产物 {cb:,} 字符 / {len(wb):,} 词   差 {cb-ca:+,} 字符 / {len(wb)-len(wa):+,} 词')
    if wa == wb:
        print('\n  逐词完全一致 ✓')
        return 0
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    print(f'  相似度 {sm.ratio():.5f}')
    A, B = wa, wb
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    print(f'  差异段 {len(ops)} 处，前 {a.show} 处：\n')
    for tag, i1, i2, j1, j2 in ops[:a.show]:
        print(f'   [{tag}] PDF@{i1}')
        j = lambda xs: ' '.join(xs)
        if tag in ('replace', 'delete'):
            print(f'     PDF : …{j(A[max(0,i1-6):i1])} «{j(A[i1:i2])[:100]}» {j(A[i2:i2+6])}…')
        if tag in ('replace', 'insert'):
            print(f'     产物: …{j(B[max(0,j1-6):j1])} «{j(B[j1:j2])[:100]}» {j(B[j2:j2+6])}…')
        print()
    return 1


if __name__ == '__main__':
    sys.exit(main())
