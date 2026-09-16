#!/usr/bin/env python3
"""双语经文框里，跟在表格后面的段落改排成表格行，与上面的节对齐。

`fix_box_verse_spill.py` 把掉在框外的后几节收回了框内，但它们还是原来的段落
形态：上半框是「中文 | 拉丁文」两列，下半框是中文一段、拉丁文一段地堆着，
同一个框里两种排版（约珥书 2:1-11 的第 1-4 节与第 5-11 节）。

这里把那些段落拆成节、按节配对，补成表格行：
  1. 取框内 `</table>` 之后、`</div>` 之前的所有 `<p>` 块，去掉外壳串成一条；
  2. 按节号切片——节号有三种写法：`**5.**`、`<strong>5.</strong>`、裸 `5.`
     （中译常把下一节的中文接在上一节拉丁文末尾，就是裸的）；
  3. 每片按汉字比例判中文还是拉丁文，同节的两片配成一行；
  4. 某一节只有一侧的，另一侧留空（与全库既有的空格写法一致）。

只搬运，不改字：切片的原文（含 `[^fN]`、`<span>`）整段搬进单元格。转完再跑
`fix_td_markdown.py` 把单元格里的 markdown 记号转成 HTML。

用法：
    python3 scripts/fix_box_paragraphs_to_rows.py [--apply] [--only 文件]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
TABLE_END = '</tbody>\n</table>'
PARA = re.compile(r'<p[^>]*>(.*?)</p>', re.S)
# 节号：**5.** / <strong>5.</strong> / 裸 5.
# 节号前面可能是：行首、空白、`>`、右括号，也常常是中文句末标点——译文里
# 「…所盼望之物）。11. 我们若把属灵的种子…」这种，漏了 `。` 就会把第 11 节
# 整段并进第 10 节。
VERSE_SPLIT = re.compile(
    r'(?:(?<=^)|(?<=[\s>）)。！？；：、」』”）]))'
    r'(?:\*\*|<strong>)?(\d{1,3})[.．](?:\*\*|</strong>)?(?=\s|<|$)')
CJK = re.compile(r'[一-鿿]')
PAGE = re.compile(r'<!--\s*PAGE \d+\s*-->')
CODE = re.compile(r'class="ages-code">&lt;(\w+)&gt;')
ROW = re.compile(r'<tr><td class="scripture-en">(.*?)</td>'
                 r'<td class="scripture-la">(.*?)</td></tr>', re.S)
NUM = re.compile(r'^\s*(?:<strong>|\*\*)?(\d{1,3})[.．]')
# 英文版两列都是拉丁字母，得靠虚词密度分：英文经文里 the/of/and 这类密集，
# 拉丁文里则是 et/in/non/est 这些
ENW = re.compile(r'\b(the|and|of|that|which|with|shall|will|they|thou|from|unto|his|her|'
                 r'their|because|when|have|hath|are|is|was|were|but|ye|we|you|by|upon|'
                 r'through|into|our|my|him|them|us|thy|thee|also|than|then|all|as|at)\b', re.I)
LATC = re.compile(r'\b(et|in|non|est|ad|cum|quod|qui|quae|ut|vos|nos|autem|enim|sic|dicit|'
                  r'Deus|Dei|Domini|Dominus|Jehova|Iehova|ego|sed|ne|per|ex|de|si|quum|'
                  r'atque|sunt|erit|esse|ipse|ipsum|suis|suam|suum)\b')


def plain(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s)


def split_verses(text: str):
    """→ [(节号, 原文片段), …]，按节号切。"""
    marks = list(VERSE_SPLIT.finditer(text))
    out = []
    for k, m in enumerate(marks):
        end = marks[k + 1].start() if k + 1 < len(marks) else len(text)
        body = text[m.end():end].strip()
        if body:
            out.append((m.group(1), body))
    return out


def is_left_column(seg: str, zh_edition: bool) -> bool:
    """这一片属于左列（中译版＝中文，英文版＝英文）还是右列（拉丁文）。"""
    t = plain(seg)
    if zh_edition:
        return len(CJK.findall(t)) > 0.3 * max(1, len(t))
    # 英文版：虚词密度谁高算谁
    return len(ENW.findall(t)) > len(LATC.findall(t))


def counterpart_cells(path: Path, code: str, ordinal: int) -> dict:
    """对照版同一个框的 {节号: (左格, 右格)}，用来补这边缺的那一侧。"""
    book = path.parent.name
    other = ROOT / 'calvin' / (book[:-3] if book.endswith('-en') else book + '-en') / path.name
    if not other.exists():
        return {}
    text = other.read_text(encoding='utf-8')
    boxes = list(BOX.finditer(text))
    target = None
    for k, m in enumerate(boxes):
        c = CODE.search(m.group(0))
        if (code and c and c.group(1) == code) or (not code and k == ordinal):
            target = m.group(0)
            break
    if not target:
        return {}
    out = {}
    for a, b in ROW.findall(target):
        mnum = NUM.match(plain(a).strip()) or NUM.match(plain(b).strip())
        if mnum:
            out[mnum.group(1)] = (a, b)
    return out


def convert(box: str, zh_edition: bool = True, fill: dict = None):
    if 'scripture-bilingual' not in box or TABLE_END not in box:
        return box, 0
    head, tail = box.split(TABLE_END, 1)
    paras = PARA.findall(tail)
    if not paras:
        return box, 0
    body = PAGE.sub('', ' '.join(p.strip() for p in paras))
    segs = split_verses(body)
    if not segs:
        return box, 0
    # 同节的中文/拉丁文配对，保持出现次序
    order, zh, la = [], {}, {}
    for v, s in segs:
        if v not in order:
            order.append(v)
        (zh if is_left_column(s, zh_edition) else la).setdefault(v, []).append(s)
    rows = []
    for v in order:
        left = zh.get(v, [])
        right = la.get(v, [])
        # 有的节译者写了两份中文（和合本 + 加尔文的译法），而拉丁文那一侧空着
        # ——因为底本这一节的拉丁文当初就没提取到。左格取第一份（与上面几行的
        # 和合本一致），多出来的放右格占位；随后 fix_latin_column.py 会拿对照版
        # 的拉丁文把它换掉（对照版也没有的就保持原样，总比空着强）。
        if len(left) > 1 and not right:
            right = left[1:]
            left = left[:1]
        z = ' '.join(left).strip()
        l = ' '.join(right).strip()
        z = f'<strong>{v}.</strong> {z}' if z else ''
        l = f'<strong>{v}.</strong> {l}' if l else ''
        # 缺的那一侧去对照版取（底本那边也没有就留空，与全库既有写法一致）
        if fill and v in fill:
            if not z.strip() and plain(fill[v][0]).strip():
                z = fill[v][0]
            if not l.strip() and plain(fill[v][1]).strip():
                l = fill[v][1]
        rows.append(f'<tr><td class="scripture-en">{z}</td>'
                    f'<td class="scripture-la">{l}</td></tr>')
    # 段落之外的内容（脚注桩、页界注释等）原样留在表后
    rest = PARA.sub('', tail)
    rest = re.sub(r'\n{3,}', '\n\n', rest).strip('\n')
    new = head + '\n'.join(rows) + '\n' + TABLE_END + ('\n\n' + rest if rest.strip() else '\n\n</div>')
    if not new.rstrip().endswith('</div>'):
        new = new.rstrip() + '\n\n</div>'
    return new, len(rows)


def main() -> int:
    apply = '--apply' in sys.argv
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]
    total = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        if only and only not in str(p):
            continue
        text = p.read_text(encoding='utf-8')
        if 'scripture-bilingual' not in text:
            continue
        out, last, n = [], 0, 0
        for m in BOX.finditer(text):
            if TABLE_END not in m.group(0):
                continue
            after = m.group(0).split(TABLE_END, 1)[1]
            if not PARA.search(after):
                continue
            code_m = CODE.search(m.group(0))
            fill = counterpart_cells(p, code_m.group(1) if code_m else '',
                                     len([x for x in BOX.finditer(text) if x.start() < m.start()]))
            new_box, rows = convert(m.group(0), not p.parent.name.endswith('-en'), fill)
            if rows == -1:
                ref = re.search(r'class="verse-range">([^<]+)<', m.group(0))
                print(f'  !! {p} [{ref.group(1) if ref else "?"}]: 同一节有两份译文，未转成表格行')
                continue
            if not rows or new_box == m.group(0):
                continue
            out.append(text[last:m.start()] + new_box)
            last = m.end()
            n += 1
            print(f'  {p}: 表后 {len(PARA.findall(after))} 个段落 → {rows} 行')
        if not n:
            continue
        total += n
        if apply:
            p.write_text(''.join(out) + text[last:], encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 个框')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
