#!/usr/bin/env python3
"""红字死标记复活：本书已经有这条脚注的定义了，标记就该变回真引用。

`<span style="color:#800000">f727</span>` 是 fix_orphan_footnote_refs 给
「配不上定义的引用」留的死标记——读者知道此处原有一条注，但点不开。等定义
被找回来（比如 fix_footnote_def_runon 把串在一起的 def 拆开之后），这些标记
就该转回 `[^f727]`。

只动「本书确实有同号 `[^fN]:` 定义」的那些；跨章的定义交给
fix_orphan_footnote_refs 去搬（它配不上时会把引用再退回死标记，等于自带回滚）。

用法：
    python3 scripts/fix_dead_marker_revive.py [--apply] [目录…]   # 默认全库 calvin/
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPAN = re.compile(r'<span style="color:#800000">\s*[Ff][Tt]?(\d+[A-Za-z]?)\.?\s*</span>')
DEF = re.compile(r'^\[\^f(\d+[A-Za-z]?)\]:[ \t]*(.*)$', re.M)


def main() -> int:
    apply = '--apply' in sys.argv
    dirs = [Path(a) for a in sys.argv[1:] if not a.startswith('--')] or [ROOT / 'calvin']
    total = 0
    for d in dirs:
        books = sorted(p for p in d.iterdir() if p.is_dir()) if d.name == 'calvin' else [d]
        for book in books:
            files = sorted(book.glob('*.md'))
            defs = set()
            for f in files:
                # 定义正文为空的不算数：fix_orphan_footnote_refs 认的是「有内容的
                # 定义」，把空定义也当数会让两个脚本互相打架——这个复活、那个退回。
                defs |= {m.group(1).lower()
                         for m in DEF.finditer(f.read_text(encoding='utf-8'))
                         if m.group(2).strip()}
            for f in files:
                src = f.read_text(encoding='utf-8')
                out, n = [], 0
                for line in src.split('\n'):
                    if line.lstrip().startswith('[^'):
                        out.append(line)           # 定义行不碰
                        continue

                    def rep(m):
                        nonlocal n
                        if m.group(1).lower() not in defs:
                            return m.group(0)
                        n += 1
                        return f'[^f{m.group(1).lower()}]'

                    out.append(SPAN.sub(rep, line))
                if not n:
                    continue
                total += n
                print(f'  {f}: 复活 {n} 处')
                if apply:
                    f.write_text('\n'.join(out), encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] 复活 {total} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
