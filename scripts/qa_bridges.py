#!/usr/bin/env python3
"""毕列志《箴言书注释》产物校验。

对照三个参照物：
  1. 单元自身声明的引用范围（data-ref="箴言 N:a-b"）——与经文块里实际的节号对得上吗
  2. 和合本（scripts/zh_cuv.json，繁体；PDF 是简体，故只比**节数与字数**，不逐字比）
  3. 章内单元序列——节号是否连续、有无缺口/重叠/越界

检查项：
  [A] 单元引用范围 vs 经文块实际节号
  [B] 章内节号覆盖：缺口 / 重叠 / 超出该章总节数
  [C] 空单元：没有经文或没有注释段
  [D] 经文字数 vs 和合本同节字数（差异过大 = 少字/串节）
  [E] 重复段落（同一段文字在书中出现多次）

用法: python3 scripts/qa_bridges.py [--verbose]
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'bridges/proverbs'
CUV = ROOT / 'scripts/zh_cuv.json'

UNIT_RE = re.compile(
    r'<div class="bridges-unit"[^>]*data-ref="箴言\s*(\d+):([\d\-—－,，\s]+)"[^>]*>(.*?)'
    r'<div class="bridges-body" markdown="1">(.*?)\n</div>\n</div>', re.S)
SCR_RE = re.compile(r'<div class="bridges-scripture" markdown="1">(.*?)</div>', re.S)
# 节号可能是合并写法：「31-32 酒发红…」「18–19 人欺凌邻舍…」（后者是 en dash）。
# 只写 ^(\d+)\s+ 会漏掉整行，误报成缺节。
VERSE_RE = re.compile(r'^\s*(\d+)(?:\s*[-–—－]\s*(\d+))?\s+(\S.*)$')


def cuv_proverbs():
    books = json.load(open(CUV, encoding='utf-8-sig'))
    for b in books:
        if b.get('abbrev') == 'prv':
            return b['chapters']
    raise SystemExit('zh_cuv.json 里没找到箴言')


def expand(expr):
    """'1-4' / '17、29' / '1' → 节号集合"""
    out = set()
    for part in re.split(r'[,，、]', expr):
        part = part.strip()
        if not part:
            continue
        m = re.match(r'^(\d+)\s*[-—－]\s*(\d+)$', part)
        if m:
            out |= set(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()
    cuv = cuv_proverbs()

    issues = defaultdict(list)
    para_seen = defaultdict(list)
    units_by_ch = defaultdict(list)
    n_units = n_verses = 0

    for ch in range(1, 32):
        p = PUB / f'{ch}.md'
        if not p.exists():
            issues['missing-chapter'].append(f'ch{ch} 文件缺失'); continue
        text = p.read_text(encoding='utf-8')
        units = UNIT_RE.findall(text)
        if not units:
            issues['no-unit'].append(f'ch{ch} 解析不到单元')
            continue
        for dch, dexpr, head, body in units:
            n_units += 1
            dch = int(dch)
            declared = expand(dexpr)
            if dch != ch:
                issues['ref-chapter-mismatch'].append(f'ch{ch} 的单元 data-ref 写着第 {dch} 章')

            scr = SCR_RE.search(head)
            actual, verse_text = set(), {}
            if not scr:
                issues['no-scripture'].append(f'箴言 {ch}:{dexpr} 没有经文块')
            else:
                for line in scr.group(1).split('\n'):
                    m = VERSE_RE.match(line.strip())
                    if m:
                        v1 = int(m.group(1))
                        v2 = int(m.group(2)) if m.group(2) else v1
                        for v in range(v1, v2 + 1):
                            actual.add(v)
                        # 合并节的正文算在首节上，字数比对时按合并节总长处理
                        verse_text[v1] = (m.group(3), v1, v2)
                n_verses += len(actual)

            # [A] 声明范围 vs 实际节号
            if scr and declared != actual:
                issues['A-range-mismatch'].append(
                    f'箴言 {ch}:{dexpr} 声明 {sorted(declared)} 实际 {sorted(actual)}')

            # [C] 注释段为空
            paras = [x.strip() for x in body.split('\n\n') if x.strip()
                     and x.strip() != '{: .bridges-lead}']
            if not paras:
                issues['C-empty-body'].append(f'箴言 {ch}:{dexpr} 没有注释正文')
            for para in paras:
                if len(para) > 40:
                    para_seen[para[:120]].append(f'{ch}:{dexpr}')

            # [D] 经文字数 vs 和合本
            for v, (vt, v1, v2) in verse_text.items():
                if v1 < 1 or v2 > len(cuv[ch - 1]):
                    issues['D-verse-out-of-range'].append(f'箴言 {ch}:{v1}-{v2} 超出该章节数 {len(cuv[ch-1])}')
                    continue
                # 繁体和合本自带「（或譯：…）」「（宗：原文是代）」这类括注，
                # PDF 的简体中译本没有——不剥掉会把 4:7 / 14:9 / 30:11 全报成缺字。
                ref = re.sub(r'[（(][^）)]*[）)]', '', ''.join(cuv[ch - 1][v1 - 1:v2]))
                ref = re.sub(r'\s', '', ref)
                got = re.sub(r'\s', '', vt)
                if not ref:
                    continue
                ratio = len(got) / len(ref)
                if ratio < 0.62 or ratio > 1.6:
                    issues['D-length-off'].append(
                        f'箴言 {ch}:{v} 字数 {len(got)} vs 和合本 {len(ref)}'
                        f'（{ratio:.2f}×）产物：{got[:34]}…')
            units_by_ch[ch].append((declared, dexpr))

        # [B] 章内覆盖
        covered, dup = set(), set()
        for declared, _ in units_by_ch[ch]:
            dup |= covered & declared
            covered |= declared
        total = len(cuv[ch - 1])
        gaps = sorted(set(range(1, total + 1)) - covered)
        extra = sorted(covered - set(range(1, total + 1)))
        if dup:
            issues['B-overlap'].append(f'ch{ch} 节号重复出现在多个单元: {sorted(dup)}')
        if gaps:
            issues['B-gap'].append(f'ch{ch} 未被任何单元覆盖的节: {gaps}（该章共 {total} 节）')
        if extra:
            issues['B-beyond'].append(f'ch{ch} 出现超出该章的节号: {extra}')

    # [F] 异常字符（PDF 字体映射错误：汉字被导出成不相干的符号）
    import unicodedata
    OKCH = re.compile(r'[一-鿿㐀-䶿　-〿＀-￯a-zA-Z0-9\s'
                      r'.,;:!?\'"()\[\]{}<>/\\|@#$%^&*+=_~`\-—–…·°′″“”‘’]')
    for ch in range(1, 32):
        p2 = PUB / f'{ch}.md'
        if not p2.exists():
            continue
        body = re.sub(r'<[^>]+>', '', re.sub(r'^---.*?^---', '', p2.read_text(encoding='utf-8'),
                                             flags=re.S | re.M))
        for i, c in enumerate(body):
            if not OKCH.match(c):
                issues['F-bad-glyph'].append(
                    f'ch{ch} U+{ord(c):04X} {unicodedata.name(c,"?")[:26]}：…{body[max(0,i-10):i+11]}…')

    # [E] 重复段落
    for para, where in para_seen.items():
        if len(where) > 1:
            issues['E-duplicate-para'].append(f'{where} 段落重复：{para[:56]}…')

    print(f'扫描 31 章：{n_units} 个单元，{n_verses} 条经文\n')
    order = ['missing-chapter','no-unit','no-scripture','ref-chapter-mismatch',
             'A-range-mismatch','B-overlap','B-gap','B-beyond',
             'C-empty-body','D-verse-out-of-range','D-length-off','E-duplicate-para',
             'F-bad-glyph']
    total_issues = 0
    for k in order:
        v = issues.get(k)
        if not v:
            continue
        total_issues += len(v)
        print(f'【{k}】{len(v)} 处')
        show = v if args.verbose else v[:6]
        for line in show:
            print('   ', line)
        if len(v) > len(show):
            print(f'    …另有 {len(v)-len(show)} 处（--verbose 全看）')
        print()
    print('未发现问题' if total_issues == 0 else f'合计 {total_issues} 处待核')


if __name__ == '__main__':
    main()
