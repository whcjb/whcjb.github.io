#!/usr/bin/env python3
"""J. A. Alexander《诗篇注释》：ABBYY XML → 逐篇英文 raw markdown。

底本：Internet Archive `commentaryonpsal00alex`——1864 年 Scribner 单卷修订版
的影印重排。选它不选 1850 年三卷本（psalmstranslated0{1,2,3}alex）的理由：
同一部书，这一版扫描字号大、ABBYY 误识率低一个数量级，且篇题已是阿拉伯数字
"Psalm 1"，不必再跟罗马数字的 OCR 变体缠斗。1850 三卷本留作**第二证人**，
见 adjudicate_alexander_ocr.py。

不收录的部分：
    p12–13  Kregel 1991 年新写的 FOREWORD —— 版权在世，只有 Alexander 本人
            的文字是公有领域
    p578–  出版社书目广告
"""
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_abbyy import IT_ON, IT_OFF

# 字面星号（OCR 自带、非斜体标记）的待判哨兵，由 repair 阶段裁决
LIT_STAR = '\ue002'

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/psalms/src'
OUT = ROOT / 'alexander_raw/psalms/en_chapters'

PREFACE_PAGES = range(14, 22)      # Alexander 自序（Kregel 的 foreword 在 12–13，不取）
BODY_START = 22

# 页眉：'570 Psalm 149:1 - 6' / 'Psalm 150:1,2 571' / '10 Preface' / 'Preface 11'
#
# 章节号与页码之间的分隔符 OCR 出来有 ':' 也有 '.'，数字还常被读成 J / l / I /
# O / ] / [。第一版只认 ':' + 纯数字，17 条页眉因此漏网**混进正文**，还把跨页
# 断词 'connec- tion' 撑开成两截。宁可把字符类放宽，也不能让页眉进正文。
_D = r'[\dJjIl\]\[O]'
RUNHEAD = re.compile(
    r'^\s*(?:' + _D + r'{1,3}\s+)?'
    r'(?:Psalm\s*' + _D + r'{1,3}\s*[:.]\s*[' + _D[1:-1] + r',.\s\-–—]*'
    r'|Preface|Foreword|THE\s+PSALMS)'
    r'\s*(?:' + _D + r'{1,3})?\s*$', re.I)
HEAD = re.compile(r'^Psalm\s*(\d{1,3})\s*$', re.I)
VERSE_START = re.compile(r'^\s*(\d{1,3})\s*(?:\(\d{1,3}\.?\)\s*)?\.')


def bare(t):
    return t.replace(IT_ON, '').replace(IT_OFF, '')


def normalize_italics(t):
    """哨兵 → markdown `*…*`，并修好 ABBYY 切碎的斜体段边界。

    三类必修（不修的后果见 principles §0.5：kramdown 会把星号原样吐出来）：
      1. 空白落在标记内侧 —— `«the man! »` → `«the man!» `
      2. 同一句斜体被切成相邻两段 —— `«How completely» «happy»` → `«How completely happy»`
      3. 空段 `«»`
    """
    # 1. 边界空白外移
    t = re.sub(IT_ON + r'(\s+)', r'\1' + IT_ON, t)
    t = re.sub(r'(\s+)' + IT_OFF, IT_OFF + r'\1', t)
    # 2. 相邻斜体段合并（中间只有空白）
    prev = None
    while prev != t:
        prev = t
        t = re.sub(IT_OFF + r'(\s*)' + IT_ON, r'\1', t)
    # 3. 空段
    t = re.sub(IT_ON + r'\s*' + IT_OFF, '', t)
    # 收尾标点：ABBYY 常把结束引号/逗号漏在斜体外，无从判断，保持原状
    return t.replace(IT_ON, '*').replace(IT_OFF, '*')


def fix_literal_asterisks(t):
    """OCR 文本里**自带**的 `*` 字符——必须在哨兵转成 `*` 之前处理掉。

    不处理的后果：这些字面星号与斜体标记混在一起，段落里的 `*` 个数变成奇数，
    kramdown 的强调配对整段错位——从那一点起，该斜体的变正体、该正体的变斜体
    （诗篇 107 v.4 整段后半全反了）。

    对着扫描页看过，它们的来源只有三类：
      `*'` / `**`  开引号 `"` 被读错（19 世纪的双撇号排版）
      `*.` + `e.`  `i. e.` 的 `i` 被读成 `*`
      其余          希伯来文活字读崩后的残渣（`7J*1`、`*T*DrT`）
    前两类有确定的正解，直接还原；第三类无从还原，转义成 `\*` 原样保留
    ——那本来就是页面上读不出来的地方，删掉等于假装它不存在。
    """
    t = re.sub(r"\*\*|\*'|'\*", '"', t)
    t = re.sub(r'\*(\.\s*' + IT_ON + r'?\s*e\.)', r'i\1', t)
    return t.replace('*', LIT_STAR)


def fix_ocr_brackets(t):
    """`{Oh)` / `[felicities` —— 左圆括号被读成花/方括号。

    只在「左括号变体 … 右圆括号」这种配对成立时才改，避免动到真正的方括号。
    """
    return re.sub(r'[\[{](?=[^\[\]{}()]*\))', '(', t)


def cleanup(t):
    t = fix_literal_asterisks(t)
    t = normalize_italics(t)
    t = fix_ocr_brackets(t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = re.sub(r'\s+([,.;:!?])', r'\1', t)
    return t.strip()


PAGENO = re.compile(r'^\s*(\d{1,3})\b|\b(\d{1,3})\s*$')


def printed_page_numbers(pages):
    """扫描页序号 → 书页页码（页眉上印的那个数）。

    `<!-- PAGE n -->` 标的若是扫描页序号，别人拿任何一本实体书或另一份扫描件
    都对不上——IA 的这份 ABBYY XML 有 590 页，同一 item 的 PDF 只有 584 页，
    两者本身就错位。页眉上印的页码才是跨版本通用的坐标。

    页码从页眉里取（'116 Psalm 23:3, 4' / 'Psalm 23:3,4 116'）；页眉缺失或
    数字被 OCR 读崩的，按前一页 +1 推。推完校验一遍是否严格递增。
    """
    out, last = {}, None
    for pg in pages:
        if not (BODY_START <= pg['index'] <= 577):
            continue
        num = None
        for par in pg['pars'][:2]:
            b = bare(par['text']).strip()
            if par['nlines'] == 1 and RUNHEAD.match(b):
                m = PAGENO.search(b)
                if m:
                    cand = int(m.group(1) or m.group(2))
                    # 只信「比上一页大 1」的读数，别的一律当误识
                    if last is None or cand == last + 1:
                        num = cand
                break
        if num is None:
            num = last + 1 if last is not None else None
        out[pg['index']] = num
        last = num
    return out


def merge(chunk):
    """[(page, par)] → [(page, text)]；无 startIndent 的段是上一段的跨页续行"""
    paras = []
    for page, par in chunk:
        t = par['text'].strip()
        if not t:
            continue
        new = 'startIndent' in par['attrs'] or bool(VERSE_START.match(bare(t)))
        if new or not paras:
            paras.append([page, t])
        else:
            prev = paras[-1][1]
            tail = prev.rstrip(IT_OFF)
            if tail.endswith('-') and bare(t)[:1].islower():
                paras[-1][1] = tail[:-1] + (IT_OFF if prev.endswith(IT_OFF) else '') + t
            else:
                paras[-1][1] = prev + ' ' + t
    return paras


def main():
    pages = pickle.load(open(SRC / 'pages1864.pkl', 'rb'))
    by_index = {p['index']: p for p in pages}
    OUT.mkdir(parents=True, exist_ok=True)

    # ── 篇题定位 ──────────────────────────────────────────
    heads = {}
    for pg in pages:
        if pg['index'] < BODY_START:
            continue
        for i, par in enumerate(pg['pars']):
            if par['nlines'] != 1:
                continue
            m = HEAD.match(bare(par['text']).strip())
            if m:
                n = int(m.group(1))
                if 1 <= n <= 150 and n not in heads:
                    heads[n] = (pg['index'], i)
    missing = [n for n in range(1, 151) if n not in heads]
    if missing:
        raise SystemExit(f'篇题缺失: {missing}')

    def slice_pars(pg0, pi0, pg1, pi1):
        out = []
        for idx in range(pg0, pg1 + 1):
            pg = by_index.get(idx)
            if not pg:
                continue
            for i, par in enumerate(pg['pars']):
                if idx == pg0 and i <= pi0:
                    continue
                if idx == pg1 and i >= pi1:
                    continue
                if par['nlines'] == 1 and RUNHEAD.match(bare(par['text']).strip()):
                    continue
                out.append((idx, par))
        return out

    def write(name, chunk, header, pmap=None):
        paras = merge(chunk)
        lines = [header, '']
        cur = None
        for page, t in paras:
            if page != cur:
                shown = (pmap or {}).get(page) or page
                lines.append(f'<!-- PAGE {shown} -->')
                cur = page
            txt = cleanup(t)
            if txt:
                lines.append(txt)
                lines.append('')
        (OUT / f'{name}.md').write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
        return len(paras)

    # ── 自序 ──────────────────────────────────────────────
    chunk = []
    for idx in PREFACE_PAGES:
        pg = by_index.get(idx)
        if not pg:
            continue
        for par in pg['pars']:
            if par['nlines'] == 1 and RUNHEAD.match(bare(par['text']).strip()):
                continue
            if bare(par['text']).strip().upper() == 'PREFACE':
                continue
            chunk.append((idx, par))
    n = write('preface', chunk, '<!-- preface | 扫描页 14-21 -->')
    print(f'preface: {n} paragraphs')

    # ── 150 篇 ────────────────────────────────────────────
    pmap = printed_page_numbers(pages)
    seq = [pmap[i] for i in sorted(pmap) if pmap[i] is not None]
    breaks = [(a, b) for a, b in zip(seq, seq[1:]) if b != a + 1]
    if breaks:
        print(f'⚠ 页码不连续 {len(breaks)} 处: {breaks[:5]}')

    order = sorted(heads.items())
    total = 0
    for k, (num, (pg0, pi0)) in enumerate(order):
        if k + 1 < len(order):
            pg1, pi1 = order[k + 1][1]
        else:
            pg1, pi1 = 577, 10 ** 6
        chunk = slice_pars(pg0, pi0, pg1, pi1)
        c = write(str(num), chunk,
                  f'<!-- psalm {num} | 书页 {pmap.get(pg0)}-{pmap.get(pg1)} '
                  f'| 扫描页 {pg0}-{pg1} -->', pmap)
        total += c
    print(f'psalms 1-150: {total} paragraphs')


if __name__ == '__main__':
    main()
