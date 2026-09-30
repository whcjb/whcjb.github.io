#!/usr/bin/env python3
"""达拉谟《启示录注释》提取：原生数字版 PDF → markdown。

底本
----
`~/Documents/论文/durham/durham_revelation.pdf`（Monergism 放出的数字版，
1,657 页，2022 年生成，**原生文本层，不是扫描**）。

先前那条 archive.org 1788 扫描件 + hOCR 几何重排的路子已作废：那边要清
f/长 s 混淆（实测词级疑似错字 2.9%）、要从残破页眉（`Cnayl.`／`Le r. II.`）
抠章号再做单调性平滑；这份数字版一样都不用——正文零 OCR 错，章/讲/经文范围
直接印在标题里。

版式（Step 1 诊断实测）
----------------------
| 项 | 值 |
|---|---|
| 页面 | 612×792（Letter），1,657 页 |
| 正文 | Georgia 15.0，x0=77，**单栏、无首行缩进** |
| 标题 | Georgia-Bold，21.2（章/讲）与 15.0（离题论述） |
| 斜体 | **全书 0 处**——转写把强调排版抹平了，不是我们丢的 |
| 段落 | PyMuPDF 的 block 与段落一一对应，不必按缩进或行距猜 |

结构
----
  p3      书名页
  p4–9    Table of Contents（94 条）
  p10–14  To the Judicious and Christian Reader / READER（作者序）
  p15–1643  正文：CHAP. 1 … CHAP. 22，章下分 LECTURE，讲中夹「离题论述」
  p1644–  A Brief View of the Series… / An INDEX

标题三类，按字形分：
  `CHAP. N`            Bold 21.2  → H1
  `LECTURE N (a:b–c)`  Bold（21.2 或 15.0）→ H2，括号里是经文范围
  其余 Bold 15.0       → H3，达拉谟著名的那些离题论述（Concerning…）

用法:
    python3 scripts/extract_durham_revelation.py
    python3 scripts/extract_durham_revelation.py --pages 55-57 --dump
"""
import argparse
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path.home() / 'Documents' / '论文' / 'durham' / 'durham_revelation.pdf'

# 目录横跨 p4–p9（共 94 条 `CHAP. N: LECTURE M (a:b–c)`，21/22 章也在内，
# 早先只读 p4–8 才误以为目录漏收那两章）。p10 起是致读者的序，p15 是 CHAP. 1。
BODY_FIRST_PAGE = 10
BODY_LAST_PAGE = 1643         # 之后是 Brief View / INDEX

_CHAP_RE = re.compile(r'^CHAP\.?\s*(\d{1,2})\s*$', re.I)
# 经文范围的左括号可以缺：正文 p1076 与目录里都写作 `LECTURE V 11:15–19)`
# ——转写本自己的排印错，两处一致，不是我们读漏。少这一个括号会让第 11 章
# 少认一讲（目录 5 讲对提取 4 讲，就是这一处）。输出时把括号补齐。
# 讲次号也可以缺：第 10 章只有一讲，原书就写作 `LECTURE (10:1–11)` 不带罗马
# 数字（目录里也没收这一条，所以目录计 93 讲、正文实为 94 讲）。
# 要求必须有编号会把它降级成普通小标题，那一整章 11 节就一个锚点都没有。
_LECT_RE = re.compile(r'^LECTURE\s*([IVXL]+)?\s*(?:\(?([\d]+:[\d–\-]+)\)?)?\s*$', re.I)

# 行尾断字：接合还是保留连字符，判据与贺智/司布真那条线一致——
# 合并形在词表里 → 是排版断字，去掉连字符；不在 → 本来就带杠，留着。
_DICT_PATHS = [ROOT / 'scripts' / 'words_alpha.txt',
               Path.home() / 'Documents' / '论文' / 'hodge' / 'words_alpha.txt',
               Path('/usr/share/dict/words')]
_DICT = None


def _dict():
    global _DICT
    if _DICT is None:
        for p in _DICT_PATHS:
            if p.exists():
                _DICT = {w.strip().lower() for w in
                         p.read_text(encoding='utf-8', errors='ignore').splitlines() if w.strip()}
                break
        else:
            _DICT = set()
    return _DICT


def join_hyphen(prev: str, nxt: str) -> str:
    a = re.search(r'([A-Za-z]+)-$', prev)
    b = re.match(r'([A-Za-z]+)', nxt)
    if a and b and (a.group(1) + b.group(1)).lower() in _dict():
        return prev[:-1] + nxt
    return prev + nxt if prev.endswith('-') else prev + ' ' + nxt


def block_text(block):
    """块内各行拼成一段。行尾连字符按词表判接合。"""
    out = ''
    for ln in block.get('lines', []):
        t = ''.join(s['text'] for s in ln['spans']).strip()
        if not t:
            continue
        out = t if not out else join_hyphen(out, t)
    return re.sub(r'\s{2,}', ' ', out).strip()


def block_style(block):
    """→ ('chapter'|'lecture'|'section'|'body', 附加信息)"""
    spans = [s for ln in block.get('lines', []) for s in ln['spans'] if s['text'].strip()]
    if not spans:
        return None, None
    text = block_text(block)
    # ⚠️ 讲次标题**不能只靠粗体认**。这份转写的字形不统一：全书 92 个讲次标题
    # 里粗体 21.2 有 71 个、粗体 15.0 有 19 个，还有 2 个是**常规 15.0**
    # （p15 的 `LECTURE I (1:1–4)`、p385 的 `LECTURE I (3:1–6)`），
    # 正是拿目录对账时少掉的那两条。单看字形属于 principles §0.3 说的
    # 「单一信号做语义判断」，所以这里补内容信号：整行完全匹配
    # `LECTURE <罗马数字> (章:节–节)` 就算讲次头，不论粗细——这个模式带括号
    # 经文范围，正文句子不可能同形。
    m = _LECT_RE.match(text)
    if m:
        return 'lecture', ((m.group(1) or '').upper(), (m.group(2) or '').strip())
    if 'Bold' not in spans[0]['font']:
        return 'body', None
    m = _CHAP_RE.match(text)
    if m:
        return 'chapter', int(m.group(1))
    return 'section', None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', default=str(PDF))
    ap.add_argument('--out', default='durham_raw/revelation/durham_revelation.md')
    ap.add_argument('--pages', help='只处理某段，如 55-57')
    ap.add_argument('--dump', action='store_true')
    a = ap.parse_args()

    lo, hi = BODY_FIRST_PAGE, BODY_LAST_PAGE
    if a.pages:
        lo, hi = (int(x) for x in a.pages.split('-'))

    doc = fitz.open(a.pdf)
    out, stats = [], {'chapter': 0, 'lecture': 0, 'section': 0, 'body': 0}
    for i in range(lo, min(hi + 1, len(doc))):
        out.append(f'<!-- PAGE {i + 1} -->')
        for b in doc[i].get_text('dict')['blocks']:
            if b['type']:
                continue
            kind, info = block_style(b)
            if not kind:
                continue
            text = block_text(b)
            if not text:
                continue
            stats[kind] += 1
            if kind == 'chapter':
                out.append(f'\n# CHAP. {info}\n')
            elif kind == 'lecture':
                num, rng = info
                head = '## LECTURE' + (f' {num}' if num else '')
                out.append('\n' + head + (f' ({rng})' if rng else '') + '\n')
            elif kind == 'section':
                out.append(f'\n### {text}\n')
            else:
                out.append(text + '\n')
    doc.close()

    body = '\n'.join(out)
    body = re.sub(r'\n{3,}', '\n\n', body)
    if a.dump:
        print(body[:4000])
    else:
        p = ROOT / a.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body + '\n', encoding='utf-8')
        print(f'{p}  {len(body):,} 字符')
    print('  章 {chapter} · 讲 {lecture} · 离题论述 {section} · 正文段 {body}'.format(**stats))
    return 0


if __name__ == '__main__':
    sys.exit(main())
