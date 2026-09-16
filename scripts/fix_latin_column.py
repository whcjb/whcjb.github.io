#!/usr/bin/env python3
"""双语经文表右列该是拉丁文，装了中文或英文的，从对照版把拉丁文取回来。

正常一行是「左列译文／右列拉丁文」。有几行右列里装的是同一节的另一份中文
（译者把整节又译了一遍），或是英文经文——页面上看就是一行里两列同一种语言，
拉丁文不见了。

修法：按框的 AGES 码 + 节号，去对照版（中译↔英文版）取那一格的拉丁文。取不到
的（底本里这一节压根没有拉丁文）只报告，不动——不删也不编。

用法：
    python3 scripts/fix_latin_column.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
ROW = re.compile(r'(<tr><td class="scripture-en">)(.*?)(</td><td class="scripture-la">)(.*?)(</td></tr>)',
                 re.S)
CODE = re.compile(r'class="ages-code">&lt;(\w+)&gt;')
NUM = re.compile(r'^\s*(?:<strong>|\*\*)?(\d{1,3})[.．]')
CJK = re.compile(r'[一-鿿]')
ENW = re.compile(r'\b(the|and|of|that|which|with|shall|will|they|thou|from|unto|his|her|'
                 r'their|because|when|have|hath|are|is|was|were|but|ye|we|you|by|upon|'
                 r'through|into|our|my|him|them|us|thy|thee|also|than|then|all|as|at)\b', re.I)
LATC = re.compile(r'\b(et|in|non|est|ad|cum|quod|qui|quae|ut|vos|nos|autem|enim|sic|dicit|'
                  r'Deus|Dei|Domini|Dominus|Jehova|Iehova|ego|sed|ne|per|ex|de|si|quum|'
                  r'atque|sunt|erit)\b')
LATW = re.compile(r'\b\w+(?:us|um|is|orum|ibus|tur|ntur|ae|as|em|arum|ium|unt|erunt|quid|que)\b')


def plain(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s).strip()


def num(cell: str):
    m = NUM.match(plain(cell))
    return m.group(1) if m else None


def not_latin(cell: str) -> bool:
    t = plain(cell)
    if len(t) < 20:
        return False
    # 拉丁文格里夹中文校注是常态，所以看比例，不看有没有
    return (len(CJK.findall(t)) > 0.5 * len(t)
            or (len(ENW.findall(t)) >= 6 and not LATC.search(t)))


def latin_index(path: Path) -> dict:
    """对照版的 {(AGES 码, 节号): 拉丁文格原样}。"""
    if not path.exists():
        return {}
    out = {}
    for ordinal, m in enumerate(BOX.finditer(path.read_text(encoding='utf-8'))):
        code = CODE.search(m.group(0))
        key = code.group(1) if code else f'#{ordinal}'
        for rm in ROW.finditer(m.group(0)):
            n = num(rm.group(2)) or num(rm.group(4))
            # 取的那一格必须**确实是拉丁文**：只判「不是中文/英文」不够——
            # 对照版里那一格也可能是英文（底本本来就缺拉丁文），照搬过去等于
            # 把英文塞进中译版的拉丁列
            cell = plain(rm.group(4))
            if n and len(LATC.findall(cell)) + len(LATW.findall(cell)) >= 2 \
                    and not not_latin(rm.group(4)) and len(ENW.findall(cell)) <= 2:
                out[(key, n)] = rm.group(4)
    return out


def main() -> int:
    apply = '--apply' in sys.argv
    fixed = missing = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        text = p.read_text(encoding='utf-8')
        if 'scripture-la' not in text:
            continue
        book = p.parent.name
        other = (ROOT / 'calvin' / (book[:-3] if book.endswith('-en') else book + '-en') / p.name)
        idx = None
        out, last = [], 0
        for ordinal, bm in enumerate(BOX.finditer(text)):
            code = CODE.search(bm.group(0))
            # 有的框没有 AGES 码（撒迦利亚书 14 就没有），退回按框序号配对——
            # 中英两版框的个数与次序一致
            key = code.group(1) if code else f'#{ordinal}'
            new_box, changed = bm.group(0), False
            for rm in ROW.finditer(bm.group(0)):
                if not not_latin(rm.group(4)):
                    continue
                n = num(rm.group(2)) or num(rm.group(4))
                if not n:
                    continue
                if idx is None:
                    idx = latin_index(other)
                src = idx.get((key, n))
                if not src:
                    missing += 1
                    print(f'  !! {p} 第 {n} 节：右列不是拉丁文，对照版也没有'
                          f'（「{plain(rm.group(4))[:28]}…」，保留原样）')
                    continue
                new_box = new_box.replace(rm.group(0),
                                          rm.group(1) + rm.group(2) + rm.group(3) + src + rm.group(5), 1)
                changed = True
                fixed += 1
                print(f'  {p} 第 {n} 节：右列换回拉丁文「{plain(src)[:32]}…」'
                      f'（原本是「{plain(rm.group(4))[:22]}…」）')
            if changed:
                out.append(text[last:bm.start()] + new_box)
                last = bm.end()
        if out and apply:
            p.write_text(''.join(out) + text[last:], encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] 换回 {fixed} 格，{missing} 格底本无拉丁文')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
