#!/usr/bin/env python3
"""发布稿 ↔ 底本 PDF 文本层 逐字比对（零 API 成本）。

用途：核查 Qwen OCR 出来的中译本有没有「改词意」——那类错误字形合法、
语法通顺，形近字检测与语法检测都抓不到，**只有对照底本逐字比才能发现**。

前提：底本 PDF **带文本层**。以弗所书的
`49_以弗所书注释-加尔文著-任以撒译.pdf` 有（109 页，78,837 字）；
另一本 `M0372…` 是扫描件无文本层，当年 OCR 就是从那本做的。

比对策略
--------
只比 **CJK 字符流**：两侧都剥掉标点、空白、HTML、markdown。
- 标点在 PDF 抽取与网页排版之间本来就不一致，留着会把真错字淹没；
- 繁简差异用 opencc 归一（发布稿繁 → 简，与 PDF 同字集）；
- 剩下的差异就是**字不一样**，那才是 OCR 错误的形态。

对齐用锚点搜索而非整体 diff：整本 8 万字做 SequenceMatcher 太慢，
且一处错位会污染后续。按发布稿的段落逐段在 PDF 流里定位。

用法：
    python3 scripts/audit_ocr_vs_pdf.py --book ephesians
    python3 scripts/audit_ocr_vs_pdf.py --book ephesians --chapter 1 --show 40
"""
import argparse
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    'ephesians': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/49_以弗所书注释-加尔文著-任以撒译.pdf',
        'pub': 'calvin/ephesians',
        # 页眉三种形式，缺一不可：
        #   偶数页  `以弗所书注释  加尔文 著---13`
        #   奇数页  `12---第一章`      ← 页码在前、章名在后，与上一种反向
        #   独占行  `第一章`
        # 章名那种夹在正文流中间，不剥就会在 diff 里表现为
        # 「PDF 侧凭空多出『第一章』」（全书 14 处假差异）。
        # 目录页的 `第一章 ......` 也一并被前缀匹配吃掉。
        'header': re.compile(
            r'^(?:以弗所书注释\s+加尔文\s+著-+\d+'
            r'|\d+-+第[一二三四五六七八九十]+章'
            r'|第[一二三四五六七八九十]+章[\s.．…]*)\s*$'),
    },
    # 加拉太书：底本 PDF 自带文本层（150 页，与 raw OCR 页数 1:1），但它
    # **本身也是 OCR**（`教义件的阐沭`、`毋宁说插入了-----个劝告`），
    # 所以和约翰福音那本一样**没有裁判效力**——它只用来「出候选」：
    # 两侧不一致的地方拿去裁扫描图人眼定夺（零 API 成本）。
    'galatians': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/加拉太书注释-加尔文.pdf',
        'pub': 'calvin/galatians',
        # 页眉/页脚：独占一行的「第N章」与纯页码
        'header': re.compile(r'^(?:第[一二三四五六七八九十]+章[\s.．…]*|\d{1,3})\s*$'),
    },
    'john': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/加尔文--约翰福音注释.pdf',
        'pub': 'calvin/john',
        # 这本 PDF 的文本层本身是 OCR 出来的，页眉被打得七零八落
        # （`第一章余-`、`’第六章舍―`、`■—`、`,—49—,`）。乱码部分会被
        # cjk_only 自然滤掉，真正要剥的是残留的「第N章」及其粘连字。
        # 注意：正文质量抽样过，与以弗所书那本相当（乱码率同为 1.3%），
        # 先前只看首末行以为很差，是取样取在页眉上了。
        'header': re.compile(r'^.{0,3}第[一二三四五六七八九十百]+章.{0,3}$'),
        # ⚠️ 实测**不可用，勿再试**：本 PDF 的文本层自身就是 OCR 产物，
        # 与站上的 Qwen OCR 两边都有错，分歧时没有裁判，不知哪边对。
        # 1797 段中 988 段（55%）无法定位；锚点由 20 字缩到 8 字，定位率
        # 45%→72%，证明失败源于文本层噪声打断长锚点，而非版本不同
        # （首段最高相似度 0.86，内容确系同一译本）。
        # 硬跑会吐 5,615 处「差异」，全是噪声，且有照 PDF 的错去「改正」
        # 站上的风险。要核这一卷只能渲染扫描页交模型判读。
        'unusable': '文本层自身是 OCR，无裁判效力',
    },
}

CJK = re.compile(r'[一-鿿]')

# 异体字/用字惯例归一。**这些不是 OCR 错误**：
# 站上那版沿用台港用字（著/藉/甚么/裡），文本层 PDF 是陆版用字（着/借/什么/里），
# opencc 的 t2s 不管这一层。不归一的话它们会刷屏，把真正的错字淹掉
# （以弗所书第一章实测：43 处差异里 30 余处属于此类）。
VARIANT = str.maketrans({
    '著': '着', '藉': '借', '甚': '什', '裡': '里', '佈': '布',
    '衹': '只', '祇': '只', '傚': '效', '菸': '于', '嚐': '尝',
})

# 段首的经文引用头（如「以弗所书 1:1。」），PDF 版式里未必在同一位置，
# 用它做锚点会定位失败（实测第一章 63 段中 21 段因此失联）。
VERSE_HEAD = re.compile(r'^(?:[一-鿿]{2,6}书?\s*\d+[:：]\d+[-–—]?\d*\s*[。．.]?)+')


def cjk_only(s: str) -> str:
    """只留汉字并做异体字归一。标点/空白/拉丁/数字全部丢弃。"""
    return ''.join(CJK.findall(s)).translate(VARIANT)


def load_pdf(cfg) -> str:
    import fitz
    d = fitz.open(cfg['pdf'])
    out = []
    for i in range(len(d)):
        for line in d[i].get_text().split('\n'):
            if line.strip() and not cfg['header'].match(line.strip()):
                out.append(line)
    d.close()
    return cjk_only('\n'.join(out))


def load_published(cfg, chapter=None):
    """→ [(章节文件, 段序, 原文段落, CJK流)]，只取注释正文。

    经文框（scripture-box）跳过：那是 scripture_tool 按和合本生成的，
    不是 OCR 产物，与 PDF 的经文排版也不一定逐字相同，比它只会制造噪声。
    """
    import opencc
    cc = opencc.OpenCC('t2s')
    items = []
    files = sorted((ROOT / cfg['pub']).glob('*.md'))
    for f in files:
        if chapter and f.stem != str(chapter):
            continue
        raw = f.read_text(encoding='utf-8')
        body = raw.split('---', 2)[2] if raw.startswith('---') else raw
        # 剥经文框整块
        body = re.sub(r'<div class="scripture-box".*?</div>', '', body, flags=re.S)
        body = re.sub(r'<h2 class="scripture-anchor".*?</h2>', '', body, flags=re.S)
        body = re.sub(r'<[^>]+>', '', body)
        body = re.sub(r'^#.*$', '', body, flags=re.M)
        for n, para in enumerate(p.strip() for p in body.split('\n\n')):
            # 先剥段首经文引用头再转 CJK 流（见 VERSE_HEAD 说明）
            core = VERSE_HEAD.sub('', para.lstrip('*  　'))
            s = cjk_only(cc.convert(core))
            if len(s) >= 24:          # 太短的段无法可靠定位
                items.append((f.stem, n, para, s))
    return items


def audit(cfg, chapter=None, show=25):
    pdf = load_pdf(cfg)
    items = load_published(cfg, chapter)
    print(f'PDF 汉字流 {len(pdf):,}；待核段落 {len(items)}\n')

    cursor = 0
    unlocated, diffs = [], []
    for stem, n, para, s in items:
        # 从上次位置往后找锚点，保证顺序推进、避免跨章误配
        anchor = s[:20]
        i = pdf.find(anchor, cursor)
        if i < 0:
            i = pdf.find(anchor)            # 回退：全局找一次
        if i < 0:
            unlocated.append((stem, n, s[:28]))
            continue
        # 窗口比段落长一截：等长窗口一旦 PDF 侧多出几个字（页眉残留等），
        # 窗口尾部就会被截掉，diff 里表现为「站上多出一截」的假删除。
        slack = max(12, len(s) // 8)
        seg = pdf[i:i + len(s) + slack]
        cursor = i + len(s) - 10
        sm = difflib.SequenceMatcher(None, s, seg, autojunk=False)
        ops = sm.get_opcodes()
        for k, (tag, i1, i2, j1, j2) in enumerate(ops):
            if tag == 'equal':
                continue
            # 末尾那条 opcode 落在窗口尾部 = slack 造成的边界效应，不是真差异
            if k == len(ops) - 1 and i2 >= len(s):
                continue
            diffs.append({
                'file': stem, 'para': n, 'tag': tag,
                'pub': s[i1:i2], 'pdf': seg[j1:j2],
                'ctx': s[max(0, i1 - 12):i1] + '⟦' + s[i1:i2] + '⟧' + s[i2:i2 + 12],
            })

    print(f'=== 无法定位的段落：{len(unlocated)} ===')
    for stem, n, head in unlocated[:10]:
        print(f'   {stem}.md #{n}  {head}…')
    print(f'\n=== 字级差异：{len(diffs)} 处 ===')
    for d in diffs[:show]:
        print(f"   [{d['file']}.md #{d['para']}] {d['tag']}: "
              f"站上={d['pub'][:20]!r} ↔ PDF={d['pdf'][:20]!r}")
        print(f"      …{d['ctx']}…")
    if len(diffs) > show:
        print(f'   （另有 {len(diffs) - show} 处，用 --show 调整）')
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='ephesians', choices=sorted(BOOKS))
    ap.add_argument('--chapter')
    ap.add_argument('--show', type=int, default=25)
    a = ap.parse_args()
    cfg = BOOKS[a.book]
    if not Path(cfg['pdf']).exists():
        sys.exit(f'找不到底本 PDF：{cfg["pdf"]}')
    audit(cfg, a.chapter, a.show)


if __name__ == '__main__':
    main()
