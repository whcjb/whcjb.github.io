#!/usr/bin/env python3
"""正文里配不上定义的脚注引用：能补的补定义，补不了的退回红色死标记。

kramdown 对配不上定义的 `[^f422]` 原样输出，页面上就露出这几个字符。全库 194
处。两种成因、两种修法：

  1. 定义其实在同一本书的**别的章**里（发布按章拆分，引用与定义分了家，
     isaiah-1-en 25 处、harmony-2-en 13 处）。→ 把定义补进引用所在的章。
  2. 定义在底本提取阶段就丢了，全书连 raw md 都查不到（daniel-en 33、
     hosea-en 22、2cor 27 等，共 150 余处，见
     [[project_calvin_en_footnote_audit]] 的不可恢复清单）。→ 引用退回成
     `<span style="color:#800000">f422</span>` 这种红色死标记，与全库其它
     「有标记无定义」的脚注同一形态。标记还在（读者知道此处原有一条脚注），
     只是不再露出 markdown 语法。

不碰隐藏的 `{:.scripture-fnref-stub}` 行——那是双语经文表给 kramdown 留的
跳转桩，CSS display:none，看不见。也不碰 `[^译注]` 这种非编号引用，留着报告。

用法：
    python3 scripts/fix_orphan_footnote_refs.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = re.compile(r'\[\^([^\]\s]{1,12})\](?!:)')
DEF = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$', re.M)
CODE = re.compile(r'^[A-Za-z]{0,3}\d+[A-Za-z]?$')
# 已发布目录名 → calvin_raw 目录名（对不上就按同名找）
RAW_DIR = {'1corinthians': '1cor', '2corinthians': '2cor', 'acts': 'acts'}


def book_defs(book: str) -> dict:
    """全书（含 raw md）的定义表，用来给分了家的引用找回定义。"""
    out = {}
    for p in sorted((ROOT / 'calvin' / book).glob('*.md')):
        for code, body in DEF.findall(p.read_text(encoding='utf-8')):
            out.setdefault(code, body.strip())
    raw = RAW_DIR.get(book.replace('-en', ''), book.replace('-en', ''))
    rawmd = ROOT / f'calvin_raw/{raw}/calvin_{raw}.md'
    if rawmd.exists():
        for code, body in DEF.findall(rawmd.read_text(encoding='utf-8')):
            out.setdefault(code, body.strip())
    return out


def main() -> int:
    apply = '--apply' in sys.argv
    added = degraded = skipped = 0
    for d in sorted((ROOT / 'calvin').iterdir()):
        if not d.is_dir():
            continue
        defs_all = None
        for p in sorted(d.glob('*.md')):
            lines = p.read_text(encoding='utf-8').split('\n')
            text = '\n'.join(lines)
            have = {c for c, _ in DEF.findall(text)}
            orphan = []
            for i, line in enumerate(lines):
                if i + 1 < len(lines) and lines[i + 1].strip() == '{:.scripture-fnref-stub}':
                    continue            # 隐藏桩，跳过
                for c in REF.findall(line):
                    if c not in have:
                        orphan.append(c)
            if not orphan:
                continue
            if defs_all is None:
                defs_all = book_defs(d.name)
            new_defs, dead = [], []
            for c in dict.fromkeys(orphan):
                if defs_all.get(c):
                    new_defs.append(c)
                elif CODE.match(c):
                    dead.append(c)
                else:
                    skipped += 1
            if new_defs:
                text = text.rstrip('\n') + '\n\n' + '\n\n'.join(
                    f'[^{c}]: {defs_all[c]}' for c in new_defs) + '\n'
            for c in dead:
                text = re.sub(r'\[\^' + re.escape(c) + r'\](?!:)',
                              f'<span style="color:#800000">{c}</span>', text)
            added += len(new_defs)
            degraded += len(dead)
            print(f'  {p}: 补定义 {len(new_defs)} 条，退回死标记 {len(dead)} 处')
            if apply:
                p.write_text(text, encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] 补定义 {added} 条，'
          f'退回死标记 {degraded} 处，非编号引用跳过 {skipped} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
