#!/usr/bin/env python3
"""修双语经文表的空单元格：某节的文字被吸进上一节的格子里。

形态（jeremiah-1-en/4.md ref 4:11-12）：

    <tr><td class="scripture-en"><strong>11.</strong> …not to cleanse, 12. Even a
        full wind…</td><td class="scripture-la"><strong>11.</strong> In tempore…</td></tr>
    <tr><td class="scripture-en"></td>            ← 空
        <td class="scripture-la"><strong>12.</strong> Ventus plenior…</td></tr>

根因在 extractor 的 `_split_verses`：节号后的后视字符类不含 `<`，而该节首词
常是斜体（`12. <sty …>Even</sty>`），于是切不出来。**但不能靠重跑提取修**——
这些卷的 raw 是早期版本提取器产出的，用当前提取器重跑本身就丢内容
（jeremiah-1 少 14.5 万字符，实测，已回滚）。所以在 markdown 层做局部搬移：
把上一格里从 `M.` 起的尾巴搬进空格子，并把 `M.` 包成 `<strong>M.</strong>`。

零丢失：搬移前后逐词多重集必须一致（脚本内置断言，不一致就跳过该文件）。
幂等：空格子填上后不再命中。

用法:
    python3 scripts/fix_bilingual_empty_cells.py --check          # 只报告
    python3 scripts/fix_bilingual_empty_cells.py --book jeremiah-1
    python3 scripts/fix_bilingual_empty_cells.py                  # 全部
"""
import argparse
import glob
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROW_RE = re.compile(r'<tr>(.*?)</tr>', re.S)
CELL_RE = re.compile(r'<td class="scripture-(en|la)">(.*?)</td>', re.S)
TAG = re.compile(r'<[^>]+>')


def _num(cell):
    m = re.search(r'<strong>\s*(\d{1,3})\s*\.?\s*</strong>', cell)
    return m.group(1) if m else None


def _toks(s):
    """忽略空白的**字符**多重集。

    不能按词比：源里常有 `10.Yet` 这种数字与首词相连的写法，搬移后变成
    `10.` + `Yet` 两个词，按词比会误判成「少 1 多 2」而白白跳过该文件
    （实测 7 个文件因此被跳过）。搬移是表内局部换位，顺序会变，所以也
    不能按顺序比——字符多重集正好：既抓得住真丢失，又不受换位与分词影响。
    """
    return Counter(re.sub(r'\s+', '', TAG.sub(' ', s)))


def fix_text(text):
    """→ (新文本, 搬移次数)"""
    moved = 0

    def fix_table(tbl_match):
        nonlocal moved
        tbl = tbl_match.group(0)
        rows = ROW_RE.findall(tbl)
        cells = []           # [{'en': html, 'la': html}]
        for r in rows:
            d = {k: v for k, v in CELL_RE.findall(r)}
            cells.append(d)
        for idx, d in enumerate(cells):
            for side in ('en', 'la'):
                if TAG.sub('', d.get(side, '')).strip():
                    continue
                other = 'la' if side == 'en' else 'en'
                num = _num(d.get(other, '') or '')
                if not num:
                    continue
                # 往前找同侧最近的非空格子
                src = None
                for k in range(idx - 1, -1, -1):
                    if TAG.sub('', cells[k].get(side, '')).strip():
                        src = k
                        break
                if src is None:
                    continue
                body = cells[src][side]
                # 在 ` num. ` 处切开（后面可以紧跟标记）
                sm = re.search(r'(?:(?<=\s)|(?<=>))' + num + r'\.\s*(?=<|\w|[“"(])', body)
                if not sm:
                    continue
                head, tail = body[:sm.start()].rstrip(), body[sm.end():].lstrip()
                if not TAG.sub('', tail).strip():
                    continue
                cells[src][side] = head
                cells[idx][side] = f'<strong>{num}.</strong> ' + tail
                moved += 1
        new_rows = ''.join(
            f'<tr><td class="scripture-en">{d.get("en", "")}</td>'
            f'<td class="scripture-la">{d.get("la", "")}</td></tr>\n'
            for d in cells)
        head = tbl[:tbl.index('<tr>')]
        tailpart = tbl[tbl.rindex('</tr>') + len('</tr>'):]
        return head + new_rows.rstrip('\n') + tailpart

    new = re.sub(r'<table class="scripture-bilingual">.*?</table>', fix_table,
                 text, flags=re.S)
    return new, moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', action='append', default=[])
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    dirs = ([ROOT / 'calvin' / b for b in a.book]
            if a.book else sorted(Path(str(ROOT / 'calvin')).glob('*')))
    if a.book:
        dirs += [ROOT / 'calvin' / (b + '-en') for b in a.book]

    total, files = 0, 0
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(glob.glob(str(d / '*.md'))):
            old = open(f, encoding='utf-8').read()
            new, n = fix_text(old)
            if not n:
                continue
            if _toks(old) != _toks(new):
                d1, d2 = _toks(old) - _toks(new), _toks(new) - _toks(old)
                print(f'  !! {f} 逐词不一致，跳过：少 {sum(d1.values())} '
                      f'多 {sum(d2.values())} {list(d1)[:3]} {list(d2)[:3]}')
                continue
            total += n
            files += 1
            print(f'  {os.path.relpath(f, ROOT)}: 搬移 {n} 处')
            if not a.check:
                open(f, 'w', encoding='utf-8').write(new)
    verb = '可修' if a.check else '已修'
    print(f'\n  {verb} {total} 处，涉及 {files} 个文件')
    return 0


if __name__ == '__main__':
    sys.exit(main())
