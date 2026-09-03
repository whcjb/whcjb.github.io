#!/usr/bin/env python3
"""从 AGES PDF 定点回填双语经文表的空单元格。

为什么要定点取而不是重跑提取：§11.5——重跑整卷会丢经文（已实测多次并回滚）。
本脚本**只读 PDF、只补空格子**，不动其他任何内容。

原理
----
1. 从产物的 `<p class="scripture-ref">` 拿到 AGES 六位码（如 `<241106>`）
   或 `verse-range`，在 PDF 里定位那一页。
2. 在该页找「以该节号起首」的行块。节号写法要全收：`6.` / `6,` / `6 `
   （jeremiah 的 PDF 里就有 `6, Ex dixit Jehova ad me` 用逗号的）。
3. 同一节在页面上通常有两块——英文与拉丁。判别不靠 x 位置
   （jeremiah 的拉丁块也会落在 x0=40 的左列位置，实测），
   而是**与产物里已有那一侧比相似度**：像的那块是已有的，另一块就是缺的。
4. 汉字页无法比相似度（PDF 是英/拉），此时取「不像英文的那块」——
   即与本页 KJV 风格英文块相似度低的那块。

输出提案，人工过一眼再落刀（--apply）。

用法:
    python3 scripts/recover_verse_from_pdf.py --list
    python3 scripts/recover_verse_from_pdf.py --apply
"""
import argparse
import difflib
import glob
import os
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
TAG = re.compile(r'<[^>]+>')


def volumes():
    import calvin_extract as C
    return C.VOLUMES


def find_empties(md):
    """→ [(box_start, box_end, tr_html, side, verse, other_text, ages_code)]"""
    s = open(md, encoding='utf-8').read()
    out = []
    for box in re.finditer(r'<div class="scripture-box[^"]*"[^>]*>(.*?)</div>', s, re.S):
        inner = box.group(1)
        code = re.search(r'<span class="ages-code">&lt;(\d{6,7})&gt;</span>', inner)
        code = code.group(1) if code else None
        for tm in re.finditer(r'<tr>.*?</tr>', inner, re.S):
            cs = dict(re.findall(r'<td class="scripture-(en|la)">(.*?)</td>',
                                 tm.group(0), re.S))
            if not cs:
                continue
            for k in ('en', 'la'):
                if k in cs and not TAG.sub('', cs[k]).strip():
                    o = 'la' if k == 'en' else 'en'
                    oth = TAG.sub('', cs.get(o, '')).strip()
                    vm = re.match(r'(\d{1,3})', oth)
                    if not vm:
                        continue
                    rt = re.search(r'<span class="book-name">([^<]*)</span>\s*'
                                   r'<span class="verse-range">([^<]*)</span>', inner)
                    ref_text = (rt.group(1) + ' ' + rt.group(2)) if rt else None
                    out.append((tm.group(0), k, vm.group(1), oth, code, ref_text))
    return s, out


def page_of(doc, code, verse, ref_text=None):
    if code:
        for i in range(doc.page_count):
            if f'<{code}>' in doc[i].get_text():
                return i
    # 没有 ages-code 的 box（合参卷、部分单章书）→ 按 ref 文本找
    if ref_text:
        pat = re.compile(re.escape(ref_text.strip()).replace(r'\ ', r'\s+'), re.I)
        for i in range(doc.page_count):
            if pat.search(doc[i].get_text()):
                return i
    return None


def blocks_for_verse(page, verse):
    """→ [该页与该节号相关的候选文本]

    两级：
      ① 以该节号**起首**的块（最干净）；
      ② 块**内部**含该节号的，就地切出「该节号 → 下一个节号 / 块尾」这一段。
         缺侧常与 H2 或相邻节合在同一块里（jeremiah 的英文经文就与
         `<241106>JEREMIAH 11:6-8` 同块），只认①会取不到。
    """
    res = []
    inner = []
    for b in page.get_text('dict')['blocks']:
        if b['type']:
            continue
        txt = ' '.join(''.join(s['text'] for s in l['spans']).strip()
                       for l in b.get('lines', []))
        txt = re.sub(r'\s+', ' ', txt).strip()
        if re.match(rf'^{verse}\s*[.,)]?\s+\S', txt):
            res.append(re.sub(rf'^{verse}\s*[.,)]?\s*', '', txt))
            continue
        m = re.search(rf'(?:(?<=\s)|^){verse}\s*[.,)]\s+(\S.*)$', txt)
        if m:
            seg = m.group(1)
            nxt = re.search(r'(?:(?<=\s))(\d{1,3})\s*[.,)]\s+\S', seg)
            if nxt:
                seg = seg[:nxt.start()].strip()
            if len(seg) > 20:
                inner.append(seg)
    return res + inner


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    V = volumes()

    targets = {}
    for md in sorted(glob.glob(str(ROOT / 'calvin' / '*' / '*.md'))):
        book = Path(md).parent.name
        key = book[:-3] if book.endswith('-en') else book
        if key not in V:
            continue
        s, empties = find_empties(md)
        if empties:
            targets[md] = (key, s, empties)

    n_ok = n_no = 0
    for md, (key, s, empties) in targets.items():
        pdf = V[key].get('pdf')
        if not pdf or not os.path.exists(pdf):
            continue
        doc = fitz.open(pdf)
        new = s
        for tr, side, verse, oth, code, ref_text in empties:
            pi = page_of(doc, code, verse, ref_text)
            if pi is None:
                n_no += 1
                print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} {side}: PDF 页定位失败'
                      f'（code={code}）')
                continue
            # ⚠️ 中文页的 scripture-en 装的是**中文**，PDF 里只有英/拉，
            # 取不到——填英文进去就是错。中文页只允许补 la（拉丁）。
            if side == 'en' and not md.endswith('-en/' + os.path.basename(md)) \
                    and '-en/' not in md:
                n_no += 1
                print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} en: '
                      f'中文页的正文列是中文，PDF 无从回填（须走翻译）')
                continue
            cands = blocks_for_verse(doc[pi], verse)
            if not cands:
                n_no += 1
                print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} {side}: '
                      f'PDF p{pi} 未找到该节起首的块')
                continue

            def sim(x):
                return difflib.SequenceMatcher(None, x[:120], oth[:120]).ratio()

            # ⚠️ 语种判别：只按「与已有列不相似」挑，会把**英文**填进拉丁列
            # （jeremiah-1/19.md v4 la 的候选是 `Because they have forsaken
            # me…`，实测）。用停用词计分把语种钉死。
            EN_W = re.compile(r'\b(the|and|of|that|have|they|unto|shall|with|'
                              r'which|their|been|from)\b', re.I)
            LA_W = re.compile(r'\b(est|sunt|quia|quod|ad|et|non|ejus|eorum|'
                              r'autem|enim|vel|hoc|illud|Jehova|Dominus|in)\b', re.I)
            def lang_ok(x):
                e = len(EN_W.findall(x)); l = len(LA_W.findall(x))
                return (l > e) if side == 'la' else (e > l)
            cands = [c for c in cands if lang_ok(c)]
            if not cands:
                n_no += 1
                print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} {side}: '
                      f'候选语种不符（要 {"拉丁" if side=="la" else "英文"}），放弃')
                continue

            cands.sort(key=sim)
            # 只有一块时：它若与已有列**不像**，那它就是缺的那侧。
            # jeremiah 11:6 就是这种——PDF 页上英文与 H2 同块（不以节号起首），
            # 只有拉丁 `6, Ex dixit Jehova ad me` 单独成块，正是要补的。
            # 要求 <0.5 以避免把已有列自己抄回去。
            if len(cands) == 1:
                if sim(cands[0]) >= 0.5:
                    n_no += 1
                    print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} {side}: '
                          f'唯一候选与已有列过于相似（{sim(cands[0]):.2f}），放弃')
                    continue
                pick = cands[0]
            else:
                pick = cands[0]
                if sim(cands[-1]) < 0.3:
                    n_no += 1
                    print(f'  ✗ {os.path.relpath(md, ROOT)} v{verse} {side}: '
                          f'两块都不像已有列，放弃（避免猜错）')
                    continue
            n_ok += 1
            print(f'  ✓ {os.path.relpath(md, ROOT)} v{verse} {side} ← PDF p{pi}: '
                  f'{pick[:70]}')
            if a.apply:
                filled = tr.replace(
                    f'<td class="scripture-{side}"></td>',
                    f'<td class="scripture-{side}"><strong>{verse}.</strong> {pick}</td>')
                new = new.replace(tr, filled, 1)
        doc.close()
        if a.apply and new != s:
            open(md, 'w', encoding='utf-8').write(new)
    print(f'\n  可回填 {n_ok} 处 · 无法判定 {n_no} 处')
    return 0


if __name__ == '__main__':
    sys.exit(main())
