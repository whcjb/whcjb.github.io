#!/usr/bin/env python3
"""成对符号自查：段落里的圆括号、方括号数不上。

结构性判据比字形判据狠——它不需要知道「错成了什么」，只要数一数就知道
这一段有问题。诗篇那边靠它捞出过断掉的经文框，以赛亚这一路一直没数过。

两个坑，都是以赛亚自己的形态：

  · **希伯来/希腊活字的残渣里到处是孤立的括号**（`*3p.\\*\\*`、`(ululd)`、
    `^=n ii.a`）。这一类不是我们弄丢的，是页面上那几个字母 OCR 读崩了，
    按 [[feedback_preserve_pdf_artifacts]] 不能删。所以段落里只要还有
    非拉丁残串，就只报不判。
  · **跨页的一对会被切开**：`(e. g. ch. 8:9. 18: 3.` 在 363 页、配对的 `)`
    在 364 页，中间隔着 `<!-- PAGE -->`，照 `\n\n` 切就是两段。
    **不要靠「把两段并回去」解决**——并回去之后，同一段里另一处真正落单的
    括号会被这一对多出来的半边抵消掉，真错反而消失（ch28 `(he sledge`、
    ch65 `(hern`、ch66 `vs. 5, (5.` 三处就是这么被藏起来的）。照切，
    跨页那一对由人看指针一眼认出来。

所以这只是一份**清单**，不是闸——真正的判据是逐条核影像。

用法：python3 scripts/isaiah_pairs_check.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
AS_IS = ROOT / 'alexander_raw/isaiah/ref_printed_as_is.tsv'
# 拉丁字母、数字、常见标点之外的东西 → 这一段里有外文或残渣
FOREIGN = re.compile(r'[^\x00-\x7FÀ-ɏ]')
PAGE_BREAK = re.compile(r'\n\n<!-- PAGE \d+ -->\n')


def printed_as_is():
    """已核定「印面本来就没有配对」的段落：章 → [那一截原文]。

    核过一次就不该再报第二次（[[feedback_repeatable_fix_needs_manifest]]）——
    赛 65 那一处 `(See Ps. 36: 5. Ezek. 36: 31.` 印本自己就漏了右括号，
    影像上下一行直接是 *Thoughts,*。
    """
    out = {}
    if not AS_IS.exists():
        return out
    for line in AS_IS.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        f = line.split('\t')
        if len(f) < 2:
            continue
        for snippet in re.findall(r'`([^`]+)`', f[1]):
            out.setdefault(f[0], []).append(snippet)
    return out


def unmatched(body, pair):
    """指出**哪一个**括号没配上——报「这一段差一个」等于没报，
    一段能有两千字，人要一个一个找。用栈扫一遍，落单的那个位置就是答案。"""
    op, cl = pair
    stack = []
    for i, ch in enumerate(body):
        if ch == op:
            stack.append(i)
        elif ch == cl:
            if stack:
                stack.pop()
            else:
                return i          # 多出来的收括号
    return stack[-1] if stack else -1


def main():
    as_is = printed_as_is()
    rows = []
    for p in sorted(SRC.glob('*.md'), key=lambda x: x.stem):
        raw = p.read_text(encoding='utf-8')
        # 页码标记把一个自然段劈成两半（`(e. g. ch. 8:9. 18: 3.` 在 363 页，
        # 配对的 `)` 在 364 页），照 `\n\n` 切就会报一对假的不配对。
        # publish 发标记时前面空一行、后面只换一行，所以把「空行 + 标记 + 换行」
        # 整个换成一个空格，段落就接回去了。
        # 跨页的那一对（`(e. g. ch. 8:9. 18: 3.` 在 363 页、配对的 `)` 在
        # 364 页）会被 `\n\n` 切成两段，看着像不配对。**不能靠「把两段并回去」
        # 解决**：并回去之后，同一段里另一处真正落单的括号会被这一对里
        # 多出来的那半边抵消掉，反而把真错藏起来（ch28 `(he sledge`、
        # ch65 `(hern`、ch66 `vs. 5, (5.` 三处就是这么消失的）。
        # 所以照切不误，只在报告里标一句「紧挨着页码标记」，交给人判。
        masked = A._mask_markup(raw)
        for i, para in enumerate(masked.split('\n\n')):
            body = para.strip()
            if not body or body.startswith(('---', '<')):
                continue
            d = body.count('(') - body.count(')')
            db = body.count('[') - body.count(']')
            if not d and not db:
                continue
            if any(sn in body for sn in as_is.get(p.stem, ())):
                continue
            rows.append((p.stem, i, d, db, bool(FOREIGN.search(body)), body))
    clean = [r for r in rows if not r[4]]
    for sec, i, d, db, foreign, body in rows:
        if foreign:
            continue
        for pair, diff in (('()', d), ('[]', db)):
            if not diff:
                continue
            k = unmatched(body, pair)
            where = body[max(0, k - 45):k + 30].replace('\n', ' ') if k >= 0 else ''
            print(f'[{sec}] 第{i}段 {pair} 差 {diff:+d}\t…{where}…')
    print(f'括号数不上的段落：{len(rows)} 段，其中不含外文残渣的 {len(clean)} 段'
          '（含残渣的那些多半是 OCR 读崩的活字，按原样保留）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
