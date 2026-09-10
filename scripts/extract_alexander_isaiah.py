#!/usr/bin/env python3
"""J. A. Alexander《以赛亚书注释》：ABBYY XML → 逐章英文 raw markdown。

底本：Internet Archive 的多伦多 Knox College（Caven Library）藏本
    卷一 `propheciesisaiah01alexuoft` = The Earlier Prophecies of Isaiah
                                       (New-York & London: Wiley and Putnam, 1846)
    卷二 `propheciesisaiah02alexuoft` = The Later Prophecies of Isaiah (同社，1847)

同一部书在 IA 上有十来份不同馆藏的扫描件，逐份量过 OCR 错词率后选的这一对：
卷一 4.22%、卷二 2.83%，都是各自的最低值，且 39 个章题一次全中。
1865 年 Scribner 重排本（propheciesofisai01alex）反而更差（5.33%），弃用。
卷一唯一的代价是首章开头的小型大写被读成 `THE fteJ£n`，一处，人工改掉。

不收录：卷一 p731 起的出版社书目广告。

版式与《诗篇注释》同源，只有三处正则不同（见下），其余走 alexander_common。
"""
import pickle
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_common import (bare, check_page_sequence, collect_compounds,
                              find_roman_heads, printed_page_numbers,
                              slice_pars, write_chapter)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/isaiah/src'
OUT = ROOT / 'alexander_raw/isaiah/en_chapters'

# 两卷各自的版面坐标（扫描页序号，不是书页页码）
VOLUMES = {
    'v1': dict(pkl='pages_v1.pkl', chapters=(1, 39), body=(79, 730),
               preface=(9, 14), intro=(15, 77),
               preface_name='preface', intro_name='introduction'),
    'v2': dict(pkl='pages_v2.pkl', chapters=(40, 66), body=(47, 547),
               preface=(9, 10), intro=(11, 46),
               preface_name='later-preface', intro_name='later-introduction'),
}

# 节号：全书统一是 `V. 1.`（诗篇是裸数字 `1.`，这是两本书最大的版式差别）。
# 允许节号前有一个 OCR 噪点标点（`. V. 5.`）——merge 靠这个判「这一段是新节，
# 不是上一段的续行」，认漏了会把整节并进上一段。
VERSE_START = re.compile(r'^\s*[.,;]?\s*V+\s*\.\s*\d{1,3}')

# 页眉字形归一：OCR 把 O 读成 0、C 读成 K/G 是常事。数字先剥掉（页码不参与
# 比对），剩下的字母再做字形归一。
_HEAD_OCR = str.maketrans({'K': 'C', 'G': 'C', 'Q': 'O'})
_KEYWORDS = ('INTRODUCTION', 'PREFACE', 'COMMENTARY')


def is_runhead(b):
    """页眉/页脚判据。

    三类，判法各不相同：
      `xxn INTRODUCTION.` / `I N T R O D U 0 T I O N.`
          字母被逐个拆开、页码是罗马数字且常读崩，所以只看**关键词在不在**，
          再限一个长度上限防止误伤正文短句。
      `2 ISAIAH, CHAP. I.` / `ISAIAH, CHAP. I.`（卷一）
          带书名 `ISAIAH`，正文里的章题从不这么写，**不要求页码**——
          OCR 经常把页码整个吞掉，要求页码会让这类页眉漏进正文。
      `2 CHAPTER XL.` / `CHAPTERXL. 3`（卷二）
          与章题只差一个页码，**必须要求页码**，否则把章题一起删了。
    """
    if not b or len(b) > 46:
        return False
    letters = re.sub(r'[^A-Za-z]', '', b).upper().translate(_HEAD_OCR)
    for kw in _KEYWORDS:
        if kw in letters and len(letters) <= len(kw) + 8:
            return True
        # `P 11 E F A C E.` —— 字母被逐个拆开时 OCR 还会漏字母（这里漏了 R），
        # 子串匹配就不够了，用相似度兜底。
        if abs(len(letters) - len(kw)) <= 2 and \
                SequenceMatcher(None, letters, kw).ratio() >= 0.85:
            return True
    if re.fullmatch(r'ISAIAHCHAP(TER)?[IVXLC]{1,8}', letters):
        return True
    # `ISATAH, CHAP. VITI. 145` —— 书名与章号双双读崩（I→T 两处）。
    # 全书就这一条漏网，但它卡在段落中间，不认出来会把一句话劈成两段。
    # 判法：去掉数字后拆成「书名部分 + 章号部分」，书名与 ISAIAHCHAP 相似度
    # ≥0.8，章号部分只由罗马字母（外加常被误读成 I 的 T）组成。
    m = re.fullmatch(r'(.{8,12}?)([IVXLCT]{2,8})', re.sub(r'\d', '', letters))
    if m and re.search(r'\d', b) and \
            SequenceMatcher(None, m.group(1), 'ISAIAHCHAP').ratio() >= 0.8:
        return True
    if re.fullmatch(r'CHAPTER[IVXLC]{1,8}', letters) and re.search(r'\d', b):
        return True
    return False


# 合并章题：`CHAPTERS II, III, IV.` / `CHAPTERS XIII, XIV.` / `CHAPTERS XV, XVI.`
# Alexander 把若干章当一篇预言处理时，会在它们前面先写一段合并的解题，
# 然后才是各章自己的 `CHAPTER N.`。这段解题属于**后面那一组**的第一章，
# 不处理的话会被并到上一章的尾巴上（第 2/13/15 章的解题曾落到 1/12/14 章）。
COMBINED = re.compile(r'^CHAPTERS\s+([IVXLC]+)\s*[,.]', re.I)
# 切片内部残留的章题行（合并解题之后紧跟的 `CHAPTER XIII.`）：页面标题已经
# 写明是第几章，正文里再来一行是重复，删掉。
PLAIN_HEAD = re.compile(r'^CHAPTER\s+[IVXLC]{1,8}\.?$', re.I)


def _roman_val(r):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    n = 0
    for i, c in enumerate(r.upper()):
        v = vals.get(c, 0)
        n += -v if i + 1 < len(r) and vals.get(r[i + 1].upper(), 0) > v else v
    return n


def apply_combined_heads(pages, heads):
    """合并解题的位置若早于该章自己的章题，就把章的起点提前到解题处。"""
    moved = []
    for pg in pages:
        for i, par in enumerate(pg['pars']):
            if par['nlines'] > 2:
                continue
            m = COMBINED.match(bare(par['text']).strip())
            if not m:
                continue
            n = _roman_val(m.group(1))
            if n in heads and (pg['index'], i) < heads[n]:
                heads[n] = (pg['index'], i)
                moved.append(n)
    return moved


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0

    for vol, cfg in VOLUMES.items():
        pages = pickle.load(open(SRC / cfg['pkl'], 'rb'))
        by_index = {p['index']: p for p in pages}
        compounds = collect_compounds(pages)
        lo, hi = cfg['chapters']
        body_lo, body_hi = cfg['body']

        pmap = printed_page_numbers(pages, cfg['body'], is_runhead, first_page=1)
        breaks = check_page_sequence(pmap)
        if breaks:
            print(f'⚠ {vol} 页码不连续 {len(breaks)} 处: {breaks[:5]}')

        # ── 序与导论：整段页范围照收，只剥页眉 ──────────────
        for key, name, label in (('preface', cfg['preface_name'], '序'),
                                 ('intro', cfg['intro_name'], '导论')):
            p0, p1 = cfg[key]
            chunk = []
            for idx in range(p0, p1 + 1):
                pg = by_index.get(idx)
                if not pg:
                    continue
                for par in pg['pars']:
                    if par['nlines'] == 1 and is_runhead(bare(par['text']).strip()):
                        continue
                    chunk.append((idx, par))
            n = write_chapter(OUT / f'{name}.md',
                              f'<!-- {name} | {vol} 扫描页 {p0}-{p1} -->',
                              chunk, VERSE_START, compounds=compounds)
            print(f'{vol} {label}({name}): {n} 段')
            total += n

        # ── 章题定位 ────────────────────────────────────────
        heads = find_roman_heads(pages, body_lo, lo, hi, runhead=is_runhead)
        missing = [n for n in range(lo, hi + 1) if n not in heads]
        if missing:
            raise SystemExit(f'{vol} 章题缺失: {missing}')
        moved = apply_combined_heads(pages, heads)
        if moved:
            print(f'{vol} 合并解题归位: 第 {moved} 章')

        order = sorted(heads.items())
        for k, (num, (pg0, pi0)) in enumerate(order):
            if k + 1 < len(order):
                pg1, pi1 = order[k + 1][1]
            else:
                pg1, pi1 = body_hi, 10 ** 6
            chunk = [(idx, par) for idx, par in
                     slice_pars(by_index, pg0, pi0, pg1, pi1, is_runhead)
                     if not (par['nlines'] == 1
                             and PLAIN_HEAD.match(bare(par['text']).strip()))]
            n = write_chapter(
                OUT / f'{num}.md',
                f'<!-- isaiah {num} | 书页 {pmap.get(pg0)}-{pmap.get(pg1)} '
                f'| {vol} 扫描页 {pg0}-{pg1} -->',
                chunk, VERSE_START, pmap, compounds)
            total += n
        print(f'{vol} 第 {lo}-{hi} 章：{len(order)} 章')

    print(f'合计 {total} 段 → {OUT}')


if __name__ == '__main__':
    main()
