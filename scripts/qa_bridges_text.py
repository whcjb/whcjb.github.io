#!/usr/bin/env python3
"""注释正文逐字校验：PDF 字符流 vs 产物字符流。

刻意走**另一条提取路径**做交叉验证：PDF 侧用 page.get_text() 的纯文本
（不经过 extract_bridges_proverbs 的字号/字体判断），产物侧把 raw md 还原成
同序字符流，然后 difflib 比对。能查出丢字、串行、重复、错序——这些是单纯
比字符总数发现不了的。

页眉/页码在纯文本里靠内容特征剔除：
  「箴言第 N 章」、编码坏掉的那串页眉、以及独占一行的纯数字页码。

用法: python3 scripts/qa_bridges_text.py [--context 60] [--max 20]
"""
import argparse, difflib, re, sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path('/Users/yanpeifa/Documents/论文/改革宗经典文献/Final-PDF-Proverbs箴言.pdf')
RAW = ROOT / 'bridges_raw/proverbs/raw'
BODY_START = 26                     # 0-based, p27 起是正文

# 书末「总结」部分的页眉就是「总结」二字，不加进来会混入正文流（还会插进
# 句子中间，如「有损属总结灵生命力」）。产物侧走 6pt 字号判断，本来就丢对了。
HDR = re.compile(r'^\s*(?:箴言第\s*\d+\s*章|总结)\s*$')
HDR_GARBLED = re.compile(r'^\s*[嬢⮬䗅▫峜ꓤ箴言]{4,}\s*$')   # 奇数页页眉字体编码坏掉
PAGENUM = re.compile(r'^\s*\d{1,4}\s*$')


def pdf_stream():
    doc = fitz.open(PDF)
    buf = []
    for pno in range(BODY_START, len(doc)):
        for line in doc[pno].get_text().split('\n'):
            if not line.strip() or HDR.match(line) or HDR_GARBLED.match(line) or PAGENUM.match(line):
                continue
            buf.append(line)
    doc.close()
    return re.sub(r'\s+', '', ''.join(buf))


def md_stream():
    order = [str(i) for i in range(1, 32)] + ['summary']
    buf = []
    for key in order:
        p = RAW / f'{key}.md'
        t = p.read_text(encoding='utf-8')
        t = re.sub(r'^# (箴言第 \d+ 章|总结)\s*$', '', t, flags=re.M)   # H1 是产物加的
        # 单元标题在产物里存进 data-ref 属性，还原到该单元开头以保持同序
        t = re.sub(r'<div class="bridges-unit"[^>]*data-ref="([^"]+)"[^>]*>', r'\1', t)
        t = re.sub(r'</?div[^>]*>', '', t)
        t = re.sub(r'\{: \.bridges-lead\}', '', t)
        buf.append(t)
    return re.sub(r'\s+', '', ''.join(buf))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--context', type=int, default=52)
    ap.add_argument('--max', type=int, default=20)
    args = ap.parse_args()

    # PDF 里部分单元标题用全角冒号（「箴言9：1-6」），产物统一成半角以生成锚点，
    # 属有意规范化，比对前先归一化，否则 56 处噪声盖住真差异。
    # PDF 文字层里有字体映射错误（⛿=住、✀=佐，见 extract 的 GLYPH_FIX），产物
    # 已修正，比对时对 PDF 侧应用同一张表，否则 217 处「差异」全是这个噪声。
    # 用 fix_glyphs 而不是直接遍历 GLYPH_FIX：修正表后来多了一张按上下文
    # 替换的 GLYPH_FIX_CTX（绿→练，但「灯红酒绿」要保留），只查前一张会漏。
    from extract_bridges_proverbs import fix_glyphs
    def norm(s):
        s = fix_glyphs(s)
        return (s.replace('：', ':').replace('－', '-')
                 .replace('—', '-').replace('–', '-'))
    a, b = norm(pdf_stream()), norm(md_stream())
    print(f'PDF 字符流 {len(a):,}   产物字符流 {len(b):,}   差 {len(a)-len(b):+,}\n')
    if a == b:
        print('逐字完全一致 ✓')
        return

    # 字符级 SequenceMatcher 在 50 万字符上是 O(n²)，跑不完。先按句切分做
    # 句子级比对（元素数 ~1.4 万，秒级），定位到差异句再看字符细节。
    def sents(s):
        return [x for x in re.split(r'(?<=[。！？；”）])', s) if x]
    sa, sb = sents(a), sents(b)
    sm_s = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
    ops = [op for op in sm_s.get_opcodes() if op[0] != 'equal']
    print(f'句子级：PDF {len(sa):,} 句 / 产物 {len(sb):,} 句，'
          f'差异块 {len(ops)} 处（相似度 {sm_s.ratio():.6f}）\n')
    for n, (tag, i1, i2, j1, j2) in enumerate(ops[:args.max], 1):
        print(f'── #{n} {tag}  PDF句[{i1}:{i2}] 产物句[{j1}:{j2}]')
        if tag in ('delete', 'replace'):
            print(f'   PDF有 →「{"".join(sa[i1:i2])[:170]}」')
        if tag in ('insert', 'replace'):
            print(f'   产物有→「{"".join(sb[j1:j2])[:170]}」')
        ctx = "".join(sa[max(0,i1-1):i1])[-40:]
        print(f'   前文 …{ctx}\n')
    if len(ops) > args.max:
        print(f'…另有 {len(ops)-args.max} 处')
    return

    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    diffs = [op for op in sm.get_opcodes() if op[0] != 'equal']
    print(f'差异块 {len(diffs)} 处（相似度 {sm.ratio():.6f}）\n')
    for n, (tag, i1, i2, j1, j2) in enumerate(diffs[:args.max], 1):
        c = args.context
        print(f'── #{n} {tag}  PDF[{i1}:{i2}] 产物[{j1}:{j2}]')
        print(f'   前文 …{a[max(0,i1-c):i1]}')
        if tag in ('delete', 'replace'):
            print(f'   PDF有 →「{a[i1:i2][:160]}」')
        if tag in ('insert', 'replace'):
            print(f'   产物有→「{b[j1:j2][:160]}」')
        print(f'   后文 {a[i2:i2+c]}…\n')
    if len(diffs) > args.max:
        print(f'…另有 {len(diffs)-args.max} 处')


if __name__ == '__main__':
    main()
