#!/usr/bin/env python3
"""达文南特《歌罗西书注释》hOCR 行数据 → 结构化 raw。

输入  davenant_raw/colossians/vol{1,2}_lines.jsonl（scripts/ocr_davenant.py 产出，
      每行一页，含每个文本行的 bbox / x_size / text）
输出  davenant_raw/colossians/davenant_colossians_structured.txt

为什么走几何+字号而不是纯文本
------------------------------
第一版按空行猜段落、按「页面后 40%」找脚注区，vol1 p88 就翻车：脚注区起点
在 42% 处（Allport 那条编辑长注占了半页），阈值漏掉，脚注被当正文输出。
本书两样东西恰好都有可测的样式信号（vol1 p88 实测，见 DIAGNOSIS.md）：

    脚注   x_size 30–35   ┐ 双峰，谷底在 36
    正文   x_size 37–45   ┘
    段首行 x0 比续行大 ≈ 48 px（续行 ±5），400 dpi 下约合一个 em

⚠️ 不能用「页内字号中位数」做阈值：p88 有 26/44 行是脚注，中位数 34.65
落在脚注一侧。阈值按**卷**做全局校准（直方图找谷底）。

结构标签
--------
    [H1] CHAP. I          歌罗西书章（全书 4 个）
    [SECTION] Verses 3, 4.  节组标题，本书的经节锚点
    [SCRIPTURE] 3|…       该节组的经文，逐节一条（与 KJV 比对定边界）
    [BODY] …              注释正文
    [LEMMA] An Apostle    被注释的词句（原书斜体 + `]` 收尾）
    [FN] …                页脚脚注

用法:
    python3 scripts/extract_davenant.py --vol 1 --pages 86-170   # 试跑
    python3 scripts/extract_davenant.py                          # 全书
"""
import argparse
import collections
import difflib
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'

# 注释正文页范围（0-based 扫描页号，含两端）。DIAGNOSIS.md §2：
# vol1 前 86 页是 Allport 的达文南特传；vol2 p320 起是另一部著作《论基督之死》。
RANGES = {1: (86, 631), 2: (14, 318)}

HEAD_RES = [
    re.compile(r'^\s*[VY][ce][rn]?[.,]?\s*[\dixvl.,\s\'’]{0,12}\s*'
               r'[EKR]?P[Ii1l]STLE\s+T[Oo0]\s+THE\s+C[Oo0][Ll]', re.I),
    re.compile(r'^\s*\d*\s*[Aa][Nn]\s+EXP[Oo0][Ss5][IiL1l]T[IiL1l][Oo0][Nn]\s+[Oo0]F\s+ST',
               re.I),
]
# 签名/页码等版面碎片：极短、或全大写卷次标记
JUNK_RE = re.compile(r'^\s*(?:[A-Z]\s?\d?|\d{1,4}|VOL[.,]?\s*[IVX0-9]+\.?\s*[A-Z]?\s?\d?'
                     r'|[a-z]\s?\d)\s*$')
# 节号既有阿拉伯数字（`Verses 3, 4.`）也有罗马数字（`Vers. I.`，vol2 p223）
SECTION_RE = re.compile(r'^\s*Vers?e?s?\.?\s*'
                        r'((?:\d+|[IVXLivxl]{1,6})(?:\s*[,&]\s*(?:\d+|[IVXLivxl]{1,6}))*)'
                        r'\s*[.,;]')
_ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
          'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
          'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18,
          'xix': 19, 'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23,
          'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27, 'xxviii': 28,
          'xxix': 29}


def parse_nums(s):
    out = []
    for tok in re.findall(r'\d+|[IVXLivxl]{1,6}', s):
        if tok.isdigit():
            out.append(int(tok))
        elif tok.lower() in _ROMAN:
            out.append(_ROMAN[tok.lower()])
    return out
# `CHAP. IV.—Vers. I.`：章标题与节号常挤在同一行，中间可能是破折号
# （vol2 p223 实测；只允许 `.`/`,` 时这一章整个漏掉）。
CHAP_RE = re.compile(r'^\s*CHAP[.,;]?\s*([IVX]{1,4})\s*[.,;：—–-]*\s*')
LEMMA_RE = re.compile(r'^([^\]\n]{1,140}?)\s*\.?\s*\]\s*')
# 段首缩进阈值由 calibrate() 按卷算（两卷像素尺度不同），此处仅作兜底


def calibrate(pages):
    """按卷校准 (脚注字号上限, 段首缩进阈值)。**尺度无关**。

    ⚠️ 两卷的绝对像素尺寸不同：扫描件逐卷页面物理尺寸不一样（vol1 约
    266×452 pt、vol2 约 326×564 pt），而渲图用的是固定 400 dpi，于是
    vol2 的字号整体是 vol1 的 1.27 倍：

        vol1  脚注峰 34   正文峰 44   谷底 36
        vol2  脚注峰 49   正文峰 56   谷底 51

    第一版把峰值搜索区间写死成 [24,37] / [37,52]，vol2 直接失效——
    低峰落在 34 处只有 4 行，守卫触发退回 36.0，而 36 在 vol2 是正文
    以下的空区，于是整卷「含脚注页 0」（实测）。
    改法：正文峰 = 全局众数；脚注峰 = 其下方的次峰（计数 ≥ 正文峰 5%、
    间隔 ≥ 4）；阈值取两峰之间的谷底。缩进阈值按正文峰字号取 0.55 倍。
    """
    h = collections.Counter(int(l['size']) for p in pages for l in p['lines'])
    if not h:
        return 36.0, 25
    body = max(h, key=lambda s: h[s])
    indent = max(12, int(round(body * 0.55)))
    # 一维 Otsu：取使类间方差最大的阈值。
    # 曾用「正文峰下方的次峰」找脚注峰，但正文簇本身很宽（vol1 是 37–46
    # 且内部有多个局部峰），次峰搜到 38 这个**正文**字号，阈值 41.5 把
    # 大量正文判成脚注（实测 vol1 含脚注页 173 → 248）。Otsu 不依赖峰形。
    ks = sorted(h)
    tot = sum(h.values())
    best, best_var = None, -1.0
    for t in ks[:-1]:
        w0 = sum(h[k] for k in ks if k <= t)
        w1 = tot - w0
        if w0 == 0 or w1 == 0:
            continue
        m0 = sum(k * h[k] for k in ks if k <= t) / w0
        m1 = sum(k * h[k] for k in ks if k > t) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best, best_var = t, var
    if best is None:
        return float(body) - 4.5, indent
    return float(best) + 0.5, indent


def page_body_x0(lines):
    """本页正文行的 x0 众数（5px 桶）。扫描件逐页有偏移/歪斜，必须逐页取。"""
    if not lines:
        return 0
    c = collections.Counter(round(l['x0'] / 5) * 5 for l in lines)
    return c.most_common(1)[0][0]


FN_MARK = re.compile(r'^\s*(\*|\+|†|‡|[ftJI])\s+(?=[A-Z(“"\d])')


def split_page(lines, fn_max):
    """→ (body_lines, fn_lines)，按**行距**分脚注区。

    为什么不用字号：tesseract 的 x_size 逐行噪声很大，同一页正文能从 37
    跳到 46（vol2 是 48–58）。按它做全局阈值两卷都翻车——vol1 阈值被
    正文簇内部的局部峰带到 40.5/41.5，vol2 把 p14 一整页普通正文
    （x_size 48–51）判成脚注（实测「89 页有脚注」全是假阳性）。

    行距稳得多，且是尺度无关的比值：
        vol1  正文 53–54 px   脚注 42–45 px   注区上方空隙 104 px
    参考行距取**页顶**前若干行——像 p88 那样整页大半是脚注的，全页中位数
    已经落在脚注一侧（45），拿它当参考就分不出来了。

    三个信号互为守卫：行距偏小 + 位于页尾连续一段 + 该段必须含脚注符
    （`*` / `†` / `‡`，OCR 常读成 `+` `f` `t` `J` `I`）。缺一不判，
    宁可漏也不把正文吞进脚注。
    """
    L = list(lines)
    if len(L) < 8:
        return L, []
    gaps = [L[i + 1]['y0'] - L[i]['y0'] for i in range(len(L) - 1)]
    top = [g for g in gaps[:8] if g > 0]
    if not top:
        return L, []
    lead = statistics.median(top)

    # 注区上方有一道**明显大**的空隙（p88：104 px vs 正文行距 54）。
    # ⚠️ 不能「自底向上吃所有行距偏小的行」——两条脚注之间的间隙
    # （p88 是 59 px）比注内行距大，会把注区截断，只吃到最后一条
    # （实测 p88 前两条漏进正文）。所以找的是那道大空隙，取**最靠上**的一道。
    best = None
    for i, g in enumerate(gaps):
        # 下限放到 1/4：Allport 的编辑长注能占到 2/3 页，注区起点最高
        # 出现在 31% 处（vol1 p92 实测，用 1/3 会被这条守卫挡掉）。
        if i < len(gaps) // 4:
            continue
        if g < lead * 1.5:
            continue
        zone = L[i + 1:]
        if not zone or not any(FN_MARK.match(x['text']) for x in zone[:3]):
            continue
        zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
        if zg and statistics.median(zg) >= lead * 0.92:
            continue                      # 区内行距不小 → 不是脚注
        best = i + 1
        break
    if best is None:
        # 兜底：有些页注区上方**没有**额外空隙（vol1 p95/p99 实测，
        # 该行上方空隙 50/47 vs 正文行距 53.5/53）。此时只认「脚注符起首
        # + 其后到页尾行距确实偏小」，位置限定在页面后 55% 以内。
        for i in range(len(L) * 45 // 100, len(L)):
            if not FN_MARK.match(L[i]['text']):
                continue
            zone = L[i:]
            zg = [zone[k + 1]['y0'] - zone[k]['y0'] for k in range(len(zone) - 1)]
            if len(zone) >= 2 and zg and statistics.median(zg) < lead * 0.95:
                best = i
                break
    if best is None:
        return [x for x in L if not JUNK_RE.match(x['text'])], []
    fns = [x for x in L[best:] if not JUNK_RE.match(x['text'])]
    body = [x for x in L[:best] if not JUNK_RE.match(x['text'])]
    return body, fns


def clean(t):
    """行内噪声：左边距的孤立标点（扫描斑点被读成 `.` / `-`）。"""
    return re.sub(r'^\s*[.\-—·,]\s+(?=[a-zA-Z])', '', t).strip()


def dehyph(a, b):
    """行末连字合并。`-` 后接大写视为破折号，不并。"""
    if a.endswith('-') and b[:1].islower():
        return a[:-1] + b
    return a + ' ' + b


def build_paragraphs(vol, lo, hi, fn_max, indent_min):
    """→ ([(kind, text)], footnotes, stats)  kind ∈ {para}"""
    paras, fns, stats = [], [], collections.Counter()
    cur, cur_pages = '', set()          # 段落跨了哪几页——脚注配对要按页对齐
    for rec in load(vol):
        p = rec['page']
        if not (lo <= p <= hi):
            continue
        lines = sorted(rec['lines'], key=lambda r: r['y0'])
        n0 = len(lines)
        for _ in range(2):                    # 剥页眉（页码有时单独一行在前）
            if lines and any(r.search(lines[0]['text']) for r in HEAD_RES):
                lines.pop(0)
                stats['head'] += 1
                continue
            if lines and JUNK_RE.match(lines[0]['text']):
                lines.pop(0)
                continue
            break
        body, fn = split_page(lines, fn_max)
        if fn:
            stats['fn_pages'] += 1
            fns.append((p, fn))
        x0 = page_body_x0(body)
        for l in body:
            txt = clean(l['text'])
            if not txt:
                continue
            if l['x0'] - x0 > indent_min and cur:
                paras.append((cur, sorted(cur_pages)))
                cur, cur_pages = txt, {p}
            elif cur:
                cur = dehyph(cur, txt)
                cur_pages.add(p)
            else:
                cur, cur_pages = txt, {p}
        stats['pages'] += 1
        stats['lines'] += n0
    if cur:
        paras.append((cur, sorted(cur_pages)))
    return paras, fns, stats


def load(vol):
    for ln in (RAW / f'vol{vol}_lines.jsonl').open(encoding='utf-8'):
        yield json.loads(ln)


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', '', s.lower())).strip()


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def norm_map(s):
    """→ (归一化串, 归一化位置 → 原串位置)。只留小写字母与空格。"""
    out, idx = [], []
    for i, ch in enumerate(s):
        c = ch.lower()
        if c.isalpha() and c.isascii():
            out.append(c); idx.append(i)
        elif c.isspace() and out and out[-1] != ' ':
            out.append(' '); idx.append(i)
    idx.append(len(s))
    return ''.join(out), idx


def split_scripture(cand, chap, nums, kjv):
    """把「经文 + 可能紧跟的注释」切开。

    边界不靠启发式：节组标题已给出节号，拿 KJV 该几节的原文做序列对齐，
    找到「对齐到 KJV 末尾」的那个位置切开。这一步同时产出相似度，
    就是本卷「经文忠于底本」的检查（Gate T 在本卷不适用，见 DIAGNOSIS.md §3）。
    """
    exp = ' '.join(kjv.get(f'{chap}:{v}', '') for v in nums).strip()
    if not exp or not cand:
        return cand, '', 0.0
    en, _ = norm_map(exp)
    cn, cidx = norm_map(cand)
    sm = difflib.SequenceMatcher(None, en, cn, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= 8]
    if not blocks:
        return cand, '', 0.0
    last = max(blocks, key=lambda b: b.a + b.size)
    cut = cidx[min(last.b + last.size, len(cidx) - 1)]
    scr, rest = cand[:cut].strip(), cand[cut:].strip()
    ratio = difflib.SequenceMatcher(None, en, norm_map(scr)[0]).ratio()
    return scr, rest, round(ratio, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages', help='如 86-170，需配 --vol')
    a = ap.parse_args()
    kjv = json.loads((RAW / 'kjv_colossians.json').read_text(encoding='utf-8'))

    plan = ([(a.vol, *(int(x) for x in a.pages.split('-')))] if a.pages
            else [(v, *RANGES[v]) for v in ([a.vol] if a.vol else (1, 2))])

    out, total = [], collections.Counter()
    for vol, lo, hi in plan:
        pages = [r for r in load(vol) if RANGES[vol][0] <= r['page'] <= RANGES[vol][1]]
        fn_max, indent_min = calibrate(pages)
        paras, fns, st = build_paragraphs(vol, lo, hi, fn_max, indent_min)
        total.update(st)
        print(f'  vol{vol}: 页 {lo}-{hi}  脚注字号上限 {fn_max} 缩进阈值 {indent_min}  '
              f'段落 {len(paras)}  含脚注页 {st["fn_pages"]}  剥页眉 {st["head"]}')

        seen_chap, cur_chap, pend = False, None, None
        i = 0
        while i < len(paras):
            para, ppages = paras[i]
            i += 1
            # 段落的页码跨度：脚注按页配对要用（publish_davenant_en.py）
            pg = (f'<!--p{ppages[0]}-->' if len(ppages) == 1
                  else f'<!--p{ppages[0]}-{ppages[-1]}-->') if ppages else ''
            # 前一条标记（章首或节组）声明了要吃经文 → 先做 KJV 对齐
            if pend is not None:
                # 经文常被悬挂缩进切成好几段（歌 1:1-2 就是 5 段），
                # 所以往后**按相似度贪心增长**，取相似度最高的那个长度。
                # 曾把上限写死 4 段，第 5 段（含 `Father and the Lord Jesus
                # Christ`）被排除，经文尾巴被切进正文（实测）。
                nums = pend
                pool = [para]
                j = i
                while len(pool) < 10 and j < len(paras) and \
                        not (CHAP_RE.match(paras[j][0])
                             or SECTION_RE.match(paras[j][0])):
                    pool.append(paras[j][0]); j += 1
                best = None
                for k in range(1, len(pool) + 1):
                    c = ' '.join(pool[:k])
                    sc, rs, rr = split_scripture(c, cur_chap, nums, kjv)
                    if best is None or rr > best[3] + 1e-9:
                        best = (c, sc, rs, rr, k)
                cand, scr, rest, r, take = best
                i += take - 1
                if r >= 0.55:
                    out.append(f'[SCRIPTURE] {pg}{cur_chap}:'
                               f'{",".join(map(str, nums))}|{r}| {scr}')
                    total['scr'] += 1
                    total['scr_sim'] += r
                    if rest:
                        out.append(f'[BODY] {pg}{rest}')
                else:                     # 对不上就原样留正文，不硬切
                    total['scr_fail'] += 1
                    out.append(f'[BODY] {pg}{cand}')
                pend = None
                continue
            m = CHAP_RE.match(para)
            if not seen_chap and not m and re.match(
                    r'^(AN EXPOSITION|OF THE|EPISTLE OF ST|COLOSSIANS\.?)\s*$', para):
                out.append(f'[TITLE] {para}')       # 卷首书名块，发布时不进正文
                continue
            if m:
                seen_chap = True
                cur_chap = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}.get(m.group(1))
                out.append(f'[H1] CHAP. {m.group(1)}')
                total['chap'] += 1
                # 章首直接接经文，没有 `Verses 1, 2.` 标题
                rest = clean(para[m.end():])
                # 同段后面若紧跟节号标题（`CHAP. IV.—Vers. I.`），
                # 退回队列交给 SECTION 分支，不要当成章首的 1,2 节
                if rest and SECTION_RE.match(rest):
                    pend = None
                    paras.insert(i, (rest, ppages))
                else:
                    pend = [1, 2] if cur_chap else None
                    if rest:
                        paras.insert(i, (rest, ppages))
                continue
            m = SECTION_RE.match(para)
            if m:
                nums = parse_nums(m.group(1))
                out.append(f'[SECTION] {pg}{m.group(0).strip()}')
                total['sec'] += 1
                rest = clean(para[m.end():])
                if rest:
                    scr, more, r = split_scripture(rest, cur_chap, nums, kjv)
                    if r >= 0.55:
                        out.append(f'[SCRIPTURE] {pg}{cur_chap}:'
                                   f'{",".join(map(str, nums))}|{r}| {scr}')
                        total['scr'] += 1; total['scr_sim'] += r
                        if more:
                            out.append(f'[BODY] {pg}{more}')
                    else:
                        # 对不上说明经文在后续段落里：把本段退回队列，
                        # 交给 pend 分支连着后面几段一起做 KJV 对齐
                        pend = nums
                        paras.insert(i, (rest, ppages))
                else:
                    pend = nums
                continue
            m = LEMMA_RE.match(para)
            if m and 0 < len(m.group(1).split()) <= 20:
                out.append(f'[LEMMA] {pg}{m.group(1).strip()}')
                total['lemma'] += 1
                rest = clean(para[m.end():])
                if rest:
                    out.append(f'[BODY] {rest}')
                continue
            out.append(f'[BODY] {pg}{para}')

        for p, fn in fns:
            x0 = page_body_x0(fn)
            cur = ''
            for l in fn:
                t = clean(l['text'])
                if l['x0'] - x0 > indent_min and cur:
                    out.append(f'[FN] <!--p{p}--> {cur}')
                    cur = t
                elif cur:
                    cur = dehyph(cur, t)
                else:
                    cur = t
            if cur:
                out.append(f'[FN] <!--p{p}--> {cur}')

    dst = RAW / ('davenant_colossians_structured.txt' if not a.pages
                 else 'sample_structured.txt')
    dst.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f'[ok] → {dst.name}  {dst.stat().st_size:,} 字节  {len(out)} 行')
    print(f'  CHAP {total["chap"]} · 节组 {total["sec"]} · 经文块 {total["scr"]}'
          f'（对不上 {total["scr_fail"]}）· lemma {total["lemma"]} · '
          f'共 {total["pages"]} 页 {total["lines"]} 行')
    return 0


if __name__ == '__main__':
    sys.exit(main())
