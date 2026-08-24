#!/usr/bin/env python3
"""拆开以赛亚书两卷末章吞下的卷末附录（中英各两个文件）。

现状：末章文件把整套卷末附录都吞了——
  isaiah-1-en/37.md 377KB = ch37 正文 100KB + 加尔文译本 270KB + FOOTNOTES
                            + TRANSLATOR'S PREFACE + PREFACE
  isaiah-2-en/66.md 526KB = ch66 正文 70KB + 译本 222KB + 经文索引表 213KB
                            + FOOTNOTES + 亚哈斯日晷 + 译文脚注
  中文版当年照英文源整章翻，同样吞了（isaiah-1/37.md 247KB、isaiah-2/66.md 283KB）

⚠️ 各章注释的脚注**不在此列**：以赛亚书英文源那部分早已是规范的 [^N] 引用+定义，
   散在各章、配对完好。66.md 里那 132 条 fa/fta 属于**译本附录自己的**脚注
   （PDF p657–783 全在译本段内），不对应任何一章注释，所以不能「按章分配」。
   本脚本把它们连同译本一起搬走，并在同一文件内配成标准 [^faN]。

用法: python3 scripts/isaiah_split_appendix.py [--dry-run]
"""
import argparse, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = re.compile(r'<span style="color:#800000">\s*(fa\d+[a-z]?)\s*</span>')
DEF = re.compile(r'<span style="color:#800000">\s*fta(\d+[a-z]?)\s*</span>')

# (末章文件, 书卷 id, [(切分锚点正则, 产物后缀, 中文标题)])
JOBS = [
    ('calvin/isaiah-1-en/37.md', 'isaiah-1-en', [
        (r'<p style="text-align:center" markdown="1"><span style="color:#000080">GO TO COMMENTARY 1:1-31</span></p>',
         'appendix-version', "Calvin's Version of Isaiah"),
        (r'<span style="color:#0000d4">FOOTNOTES</span>', 'appendix-footnotes', 'Footnotes'),
        (r'<span style="color:#006411">TRANSLATOR’S PREFACE</span>', 'appendix-preface', 'Prefaces'),
    ]),
    ('calvin/isaiah-2-en/66.md', 'isaiah-2-en', [
        (r'<span style="color:#006411">CALVINS VERSION OF', 'appendix-version', "Calvin's Version of Isaiah"),
        (r'<span style="color:#0000d4">TABLES OF SCRIPTURE</span>', 'appendix-tables', 'Tables of Scripture'),
        (r'<span style="color:#0000d4">FOOTNOTES</span>', 'appendix-footnotes', 'Footnotes'),
        (r'<span style="color:#006411">THE SUN-DIAL OF AHAZ', 'appendix-sundial', 'The Sun-Dial of Ahaz'),
    ]),
    ('calvin/isaiah-1/37.md', 'isaiah-1', [
        # 中文版译本段没有绿色大标题，起点是第一个「前往 注释 1:1-31」
        # （英文侧对应 GO TO COMMENTARY 1:1-31）
        (r'<p style="text-align:center" markdown="1"><span style="color:#000080">前往 注释 1:1-31</span></p>',
         'appendix-version', '加尔文的以赛亚书译本'),
        (r'<span style="color:#0000d4">脚注</span>', 'appendix-footnotes', '脚注'),
        (r'<span style="color:#006411">译者序', 'appendix-preface', '译者序与序言'),
    ]),
    ('calvin/isaiah-2/66.md', 'isaiah-2', [
        (r'<span style="color:#006411">加尔文的译本', 'appendix-version', '加尔文的以赛亚书译本'),
        (r'<span style="color:#0000d4">圣经索引表', 'appendix-tables', '圣经索引表'),
        (r'<span style="color:#006411">亚哈斯的日晷', 'appendix-sundial', '亚哈斯的日晷'),
    ]),
]


def fm(book_id, title, date):
    return (f'---\nlayout: calvin-en\nbook_id: {book_id}\n'
            f'book_name: "以赛亚书注释 · 附录"\ntitle: "{title}"\n'
            f'date: {date}\n---\n\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for path, book_id, marks in JOBS:
        p = ROOT / path
        t = p.read_text(encoding='utf-8')
        head = re.match(r'^---\n.*?\n---\n', t, re.S)
        date = re.search(r'^date:\s*(.+)$', head.group(0), re.M).group(1).strip()
        # 找每个切分点
        cuts = []
        for pat, suffix, title in marks:
            m = re.search(pat, t)
            if m:
                # 切点要落在**段落边界**，不能停在标题 span 处：标题外面的
                # <p class="title-block-h1" …> 开标签在 span 之前，切在 span 上
                # 会把这个开标签留在上一段末尾，随后追加的脚注定义就被包进那个
                # <p> 里，kramdown 不再识别为脚注定义（实测 263 处字面残留）。
                pos = m.start()
                nl = t.rfind('\n\n', 0, pos)
                if nl != -1 and pos - nl < 400:
                    pos = nl + 2
                cuts.append((pos, suffix, title))
            else:
                print(f'  !! {path}: 找不到切分锚点 {suffix}，跳过该段')
        cuts.sort()
        if not cuts:
            continue
        body = t[:cuts[0][0]].rstrip() + '\n'
        segs = []
        for i, (pos, suffix, title) in enumerate(cuts):
            end = cuts[i + 1][0] if i + 1 < len(cuts) else len(t)
            segs.append((suffix, title, t[pos:end].rstrip() + '\n'))

        # 散落的 fta 定义收拢到含对应 fa 引用的那一段（英文版才有）
        all_defs = {}
        for i, (suffix, title, seg) in enumerate(segs):
            for m in DEF.finditer(seg):
                # 定义体：从该 span 结束到下一个定义 span
                nxt = DEF.search(seg, m.end())
                raw = seg[m.end(): nxt.start() if nxt else len(seg)]
                raw = re.sub(r'<!--\s*PAGE\s+\d+\s*-->', ' ', raw)
                raw = re.sub(r'^\s*[.、,]\s*', '', re.sub(r'\s*\n\s*', ' ', raw)).strip()
                if raw:
                    all_defs.setdefault(m.group(1), raw)
            segs[i] = (suffix, title, DEF.sub('', seg))
        placed = 0
        for i, (suffix, title, seg) in enumerate(segs):
            used = {}
            def rep(m):
                code = m.group(1)
                key = code[2:]
                if key in all_defs:
                    used[code] = all_defs[key]
                    return f'[^{code}]'
                return m.group(0)
            new = REF.sub(rep, seg)
            if used:
                new = new.rstrip() + '\n\n' + '\n'.join(f'[^{c}]: {v}' for c, v in used.items()) + '\n'
                placed += len(used)
            segs[i] = (suffix, title, new)

        print(f'══ {path}  {len(t):,} → 正文 {len(body):,}')
        for suffix, title, seg in segs:
            print(f'     {suffix:20s} {len(seg):>9,} bytes  {title}')
        if all_defs:
            print(f'     脚注定义 {len(all_defs)} 条，配上引用 {placed} 条')
        if args.dry_run:
            continue
        p.write_text(body, encoding='utf-8')
        for suffix, title, seg in segs:
            out = p.parent / f'{suffix}.md'
            out.write_text(fm(book_id, title, date) + seg, encoding='utf-8')


if __name__ == '__main__':
    main()
