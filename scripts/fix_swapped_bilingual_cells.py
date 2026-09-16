#!/usr/bin/env python3
"""把双语经文表里左右颠倒的那一行换回来。

正常是「左列译文（英文版是英文、中译版是中文）／右列拉丁文」。提取阶段偶尔
把某一行的两列弄反了：左列成了拉丁文，右列成了英文或中文。页面上看就是这一行
与上下各行的语言正好对调。

判定（三条全中）：左列几乎没有英文虚词、却有 ≥4 个拉丁词形（-us/-um/-is/-tur…），
右列要么有 ≥5 个英文虚词、要么有 ≥8 个汉字。只换两格的内容，一个字不改。

中译版换完若左列仍是英文（该节中文当初就没译），按本书通例补和合本经文——
框里其余各节本来就是和合本。补不了就报警留着。

用法：
    python3 scripts/fix_swapped_bilingual_cells.py [--apply]
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROW = re.compile(r'(<tr><td class="scripture-en">)(.*?)(</td><td class="scripture-la">)(.*?)(</td></tr>)',
                 re.S)
NUM = re.compile(r'^\s*(?:<strong>|\*\*)?(\d{1,3})[.．]')
ENW = re.compile(r'\b(the|and|of|that|which|with|shall|will|they|thou|from|unto|his|her|'
                 r'their|because|when|have|hath|are|is|was|were|but|ye|we|you|by|upon|'
                 r'through|into|our|my|him|them|us|thy|thee|also|than|then|all|as|at)\b', re.I)
LATW = re.compile(r'\b\w+(?:us|um|is|orum|ibus|tur|ntur|ae|as|em|arum|ium|it|unt|erunt|ere|quid|que)\b')
# 拉丁常用词：词尾表撞不上的那些（Percussi vos … et rubigine et grandine）
LATC = re.compile(r'\b(et|in|non|est|ad|cum|quod|qui|quae|ut|vos|nos|autem|enim|sic|dicit|'
                  r'Deus|Dei|Domini|Dominus|Jehova|Iehova|ego|sed|ne|per|ex|de|si|quum|atque)\b')
CJK = re.compile(r'[一-鿿]')
REF = re.compile(r'class="verse-range">(\d+):')
# 书目录名 → 和合本书名键（补中文时用）
CUV_BOOK = {'haggai': '該', 'jeremiah-2': '耶', 'jonah': '拿', '2corinthians': '林後',
            '1corinthians': '林前', 'joel': '珥', 'amos': '摩'}

_st = None


def cuv(book: str, ch: int, v: int):
    """和合本经文（繁转简，与各发布脚本注入的那一份同源）。"""
    global _st
    key = CUV_BOOK.get(book)
    if not key:
        return None
    if _st is None:
        spec = importlib.util.spec_from_file_location('st', ROOT / 'scripts/scripture_tool.py')
        _st = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_st)
    got = _st.lookup_verses(key, str(ch), v, v)
    if not got:
        return None
    try:
        from opencc import OpenCC
        return OpenCC('t2s').convert(got[0])
    except Exception:
        return None


def plain(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s).strip()


def is_latin(cell: str) -> bool:
    """这一格是拉丁文：够长、没有汉字、几乎不含英文虚词。

    不按拉丁词形数判——`Numquid omnes dona habent sanationum?` 这种词尾撞不上
    常见拉丁后缀表，会漏。英文经文里 the/of/and/is 这类虚词密度很高，30 字以上
    却只有 ≤1 个，基本只能是拉丁文。"""
    t = plain(cell)
    # 拉丁文格里可能夹着中文校注（约拿书 2:6 那格就带一段），按比例判而不是
    # 「一个汉字都不能有」
    return (len(t) >= 30 and len(CJK.findall(t)) < 0.45 * len(t)
            and len(ENW.findall(t)) <= 1
            and len(LATW.findall(t)) + len(LATC.findall(t)) >= 2)


def is_translation(cell: str) -> bool:
    """这一格是译文（英文或中文）。"""
    t = plain(cell)
    return (len(t) >= 25 and len(ENW.findall(t)) >= 3) or len(CJK.findall(t)) >= 8


def main() -> int:
    apply = '--apply' in sys.argv
    total = warned = 0
    for p in sorted(ROOT.glob('calvin/*/*.md')):
        text = p.read_text(encoding='utf-8')
        if 'scripture-la' not in text:
            continue
        book = p.parent.name
        zh = not book.endswith('-en')
        hits = []

        def swap(m):
            nonlocal total, warned
            left, right = m.group(2), m.group(4)
            if not (is_latin(left) and is_translation(right)):
                return m.group(0)
            new_left, new_right = right, left
            n = NUM.match(plain(left))
            if zh and not CJK.search(plain(new_left)):
                # 中译版换完左列还是英文 → 该节当初没译，补和合本
                mref = REF.search(text[:m.start()][-4000:][::-1][::-1] or '')
                ch = None
                seg = text.rfind('class="verse-range">', 0, m.start())
                if seg > 0:
                    mm = re.match(r'class="verse-range">(\d+):', text[seg:seg + 40])
                    ch = int(mm.group(1)) if mm else None
                got = cuv(book, ch, int(n.group(1))) if (ch and n) else None
                if got:
                    marker = f'<strong>{n.group(1)}.</strong> '
                    new_left = marker + got
                else:
                    warned += 1
                    print(f'  !! {p} 第 {n.group(1) if n else "?"} 节：换回来了，但左列仍是英文'
                          f'（该节中译缺失，和合本也没取到）')
            total += 1
            hits.append((n.group(1) if n else '?', plain(left)[:34]))
            return m.group(1) + new_left + m.group(3) + new_right + m.group(5)

        new_text = ROW.sub(swap, text)
        if hits:
            for v, s in hits:
                print(f'  {p} 第 {v} 节：左右两列换回（左列原本是拉丁文「{s}…」）')
            if apply:
                p.write_text(new_text, encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 行'
          + (f'，{warned} 行仍缺中文' if warned else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
