#!/usr/bin/env python3
"""毕列志（Charles Bridges）《箴言书注释》PDF → 分章 raw markdown。

源：/Users/yanpeifa/Documents/论文/改革宗经典文献/Final-PDF-Proverbs箴言.pdf
    改革宗翻译社（RTF-USA）简体中文版 2023，乔兰山以妲 译，982 页，文字层 PDF。

诊断结论（pdf-pipeline step 1）：非 AGES、非 CCEL，Quartz 导出的单列中文排版。
六类元素，靠「字号 + 字体 + x0」三信号联合判定（principles §0.3：几何信号必须
搭配样式信号）：

| 元素 | 字号 | 字体 | x0 | 产物 |
|---|---|---|---|---|
| 页眉 | 6pt | SourceHanSerifCN-Medium | 57/309 | 丢弃（奇数页页眉本身是字体编码乱码）|
| 页码 | 9pt | SourceHanSerifCN | ≈195 | 丢弃 |
| 单元标题 | 16pt | Bold | ≈150-170 居中 | `## 箴言 N:a-b` |
| 圣经经文 | 10pt | **FZKTK**（楷体）| 88 | 经文块 |
| 首字下沉 | 27pt | Light | ≈77-79 | 与后续正文拼回完整段首 |
| 正文 | 10pt | Light | 58 续行 / 79 段首 / 106 首字旁 | 段落 |

⚠️ 首字下沉必须拼回：27pt 的「箴」是独立 block，后面 x=106 的行是「言书有一个
自然的开端…」——不拼就丢字，且段落开头读不通。

用法:
    python3 scripts/extract_bridges_proverbs.py            # 全书
    python3 scripts/extract_bridges_proverbs.py --chapter 1
    python3 scripts/extract_bridges_proverbs.py --dry-run   # 只报告统计
"""
import argparse, re, sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path('/Users/yanpeifa/Documents/论文/改革宗经典文献/Final-PDF-Proverbs箴言.pdf')
OUT_DIR = ROOT / 'bridges_raw/proverbs/raw'

BODY_START_PAGE = 26        # 0-based：p27 是「箴言1:1-4」第一单元
PREFACE_PAGES = (4, 14)     # 0-based 半开区间：p5–p14 前言
UNIT_RE = re.compile(r'^箴言\s*(\d+)\s*[:：]\s*([\d\-—－,，\s]+)$')

# 段首缩进的 x 区间。正文续行 x≈58，段首缩进 x≈77-79，drop cap 右侧行 x≈104-106。
# 只有落在 [INDENT_LO, INDENT_HI] 的才是新段落起始。
INDENT_LO, INDENT_HI = 70.0, 95.0


def spans_of(block):
    return [s for l in block['lines'] for s in l['spans']]


def classify(block):
    """→ (kind, text, x0)；kind ∈ header/pagenum/unit/scripture/dropcap/body/skip"""
    ss = spans_of(block)
    if not ss:
        return 'skip', '', 0
    text = ''.join(s['text'] for s in ss)
    if not text.strip():
        return 'skip', '', 0
    size = max(round(s['size'], 1) for s in ss)
    fonts = {s['font'] for s in ss}
    x0 = block['bbox'][0]

    if size <= 6.5:
        return 'header', text, x0                    # 页眉（含乱码页眉）
    if size <= 9.5 and text.strip().isdigit():
        return 'pagenum', text, x0                   # 页码
    if size >= 20:
        return 'dropcap', text.strip(), x0           # 首字下沉（27pt）——必须先判，
                                                     # 否则被下面 >=14 当成标题
    if size >= 14:
        return 'unit', text.strip(), x0              # 单元标题（16pt）
    if any('FZKT' in f for f in fonts):
        return 'scripture', text.strip(), x0         # 楷体 = 圣经经文
    return 'body', text.strip(), x0


def extract_page(page):
    """按 y 排序返回 [(kind, text, x0)]，drop cap 单独成项。"""
    items = []
    for b in sorted(page.get_text('dict')['blocks'], key=lambda b: (b['bbox'][1], b['bbox'][0])):
        if b['type'] != 0:
            continue
        ss = spans_of(b)
        if not ss:
            continue
        # 27pt 首字可能与正文同 block，也可能独立 block——按 span 拆
        big = [s for s in ss if round(s['size'], 1) >= 20]
        if big and len(big) < len(ss):
            for s in ss:
                kind = 'dropcap' if round(s['size'], 1) >= 20 else 'body'
                if s['text'].strip():
                    items.append((kind, s['text'].strip(), b['bbox'][0]))
            continue
        kind, text, x0 = classify(b)
        if kind in ('skip', 'header', 'pagenum'):
            continue
        items.append((kind, text, x0))
    return items


def build_chapters(doc):
    """→ {ch: [(unit_title, [('scripture'|'para', text), ...]), ...]}"""
    chapters, cur_ch, cur_unit = {}, None, None
    pending_drop = None          # 上一个 drop cap 首字，等着拼进下一段
    para_buf, scr_buf = [], []

    def flush_para():
        nonlocal para_buf
        if para_buf and cur_unit is not None:
            cur_unit[1].append(('para', ''.join(para_buf)))
        para_buf = []

    def flush_scr():
        nonlocal scr_buf
        if scr_buf and cur_unit is not None:
            cur_unit[1].append(('scripture', '\n'.join(scr_buf)))
        scr_buf = []

    for pno in range(BODY_START_PAGE, len(doc)):
        for kind, text, x0 in extract_page(doc[pno]):
            if kind == 'unit':
                flush_scr(); flush_para()
                m = UNIT_RE.match(text.replace(' ', ''))
                if m:
                    ch = int(m.group(1))
                elif text.strip() == '总结':
                    ch = 'summary'          # 书末总结（p978–981），独立成篇
                else:
                    print(f'  !! p{pno+1} 单元标题解析失败: {text!r}')
                    continue
                cur_ch = ch
                cur_unit = (text, [])
                chapters.setdefault(ch, []).append(cur_unit)
            elif kind == 'scripture':
                flush_para()
                # 以节号开头 = 新节；否则是上一节的 wrap 续行（x≈68），要接回去。
                # 节号可能是合并写法「31-32 酒发红…」「18–19 人欺凌邻舍…」（en dash），
                # 只判 ^\d+\s 会把它当续行粘到上一节末尾（箴言 23:30 踩到）。
                # 「（箴言1:16 的新约引用：罗马书3:15）」这类整行括注在 PDF 里也是
                # 独立一行（同 x=88、同楷体），不是 wrap 续行，不能粘到上一节尾巴。
                if (re.match(r'^\d+(?:\s*[-–—－]\s*\d+)?\s', text)
                        or re.match(r'^[（(]', text) or not scr_buf):
                    scr_buf.append(text)
                else:
                    scr_buf[-1] += text
            elif kind == 'dropcap':
                flush_scr(); flush_para()
                pending_drop = text
            elif kind == 'body':
                flush_scr()
                if pending_drop is not None:
                    para_buf = [pending_drop, text]   # 首字 + 首行拼回
                    pending_drop = None
                elif INDENT_LO <= x0 <= INDENT_HI and para_buf:
                    flush_para()                      # x≈79 缩进 = 新段落
                    para_buf = [text]
                else:
                    # x≈58 续行；x≈106 是 drop cap 右侧的行（首字占两行高），
                    # 也必须续接——按 x>=70 一律开新段会把首段切成两半。
                    para_buf.append(text)
    flush_scr(); flush_para()
    return chapters


def render(ch, units):
    """每单元 → 一个 .bridges-unit：头部（引用 + 经文）sticky 置顶，注释在下滚动。

    kramdown 需要逐层 markdown="1"，否则内层的 ## / {: .bridges-lead} 不解析
    （见 memory: kramdown markdown 属性）。
    """
    head = '# 总结' if ch == 'summary' else f'# 箴言第 {ch} 章'
    lines = [head, '']
    for title, parts in units:
        is_summary = title.strip() == '总结'
        scr = [t for k, t in parts if k == 'scripture']
        paras = [t for k, t in parts if k == 'para']

        if is_summary:                      # 总结无引用无经文，正文直接排
            for i, text in enumerate(paras):
                lines += [text, '']
                if i == 0:
                    lines += ['{: .bridges-lead}', '']
            continue

        norm = re.sub(r'^箴言\s*', '箴言 ', title.replace('：', ':'))
        # 不渲染「箴言 N:a-b」标题——经文本身已带节号，标题是重复信息。
        # 引用仍保留在 data-ref 上，并按「章-节」给单元一个稳定 id（#pv-1-1-4）
        # 供分享/跳转（kramdown 对中文标题只会生成 section / section-1 这类无意义 id）。
        m = UNIT_RE.match(title.replace(' ', '').replace('：', ':'))
        if m:
            verses = re.sub(r'[^\d]+', '-', m.group(2)).strip('-')
            unit_open = f'<div class="bridges-unit" id="pv-{m.group(1)}-{verses}" data-ref="{norm}">'
        else:
            unit_open = f'<div class="bridges-unit" data-ref="{norm}">'
        lines += [unit_open, '<div class="bridges-unit-head" markdown="1">', '']
        if scr:
            # PDF 里经文只是楷体 + 缩进，**没有边框/底色**——§0.0 反向约束
            lines += ['<div class="bridges-scripture" markdown="1">', '']
            for block in scr:
                for ln in block.split('\n'):
                    lines += [ln, '']
            lines += ['</div>', '']
        lines += ['</div>', '', '<div class="bridges-body" markdown="1">', '']
        for i, text in enumerate(paras):
            lines += [text, '']
            if i == 0:
                # PDF 里每单元首段是 27pt 首字下沉，网页用 ::first-letter 还原
                lines += ['{: .bridges-lead}', '']
        lines += ['</div>', '</div>', '']
    return '\n'.join(lines).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter', type=int)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    doc = fitz.open(PDF)
    chapters = build_chapters(doc)

    # 前言
    pre = []
    for pno in range(*PREFACE_PAGES):
        for kind, text, x0 in extract_page(doc[pno]):
            if kind == 'body':
                if x0 >= 70 and pre:
                    pre.append('\n\n' + text)
                else:
                    pre.append(text)
            elif kind == 'unit':
                pre.append(f'\n\n## {text}\n\n')
    doc.close()

    num_ch = sorted(c for c in chapters if isinstance(c, int))
    extra = [c for c in chapters if not isinstance(c, int)]
    print(f'章数 {len(num_ch)}，单元 {sum(len(v) for v in chapters.values())}'
          + (f'，另有 {extra}' if extra else ''))
    for ch in num_ch + extra:
        units = chapters[ch]
        npara = sum(1 for u in units for k, _ in u[1] if k == 'para')
        nscr = sum(1 for u in units for k, _ in u[1] if k == 'scripture')
        chars = sum(len(t) for u in units for _, t in u[1])
        label = str(ch) if isinstance(ch, int) else ch
        print(f'  ch{label:>7s}: {len(units):3d} 单元 {npara:4d} 段 {nscr:3d} 经文块 {chars:6d} 字')
    if args.dry_run:
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    todo = [args.chapter] if args.chapter else num_ch + extra
    for ch in todo:
        p = OUT_DIR / f'{ch}.md'
        p.write_text(render(ch, chapters[ch]), encoding='utf-8')
        print(f'✓ {p} ({p.stat().st_size} bytes)')
    if not args.chapter:
        pp = OUT_DIR / 'preface.md'
        pp.write_text('# 前言\n\n' + ''.join(pre).strip() + '\n', encoding='utf-8')
        print(f'✓ {pp} ({pp.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
