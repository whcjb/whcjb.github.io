#!/usr/bin/env python3
"""把误塞进经文框的注释段搬出来（加尔文注释，全库 3 处）。

症状与「经文掉在框外」正好相反：双语经文表的 `<td class="scripture-en">`
里装的不是经文，而是该节的注释（红色斜体经文短语 + 大段议论），读者看到的是
一整段注释被框在米黄色经文框里。成因是旧版转换器在英文那一列为空时，把紧随
其后的注释 BODY 当成了经文填了进去。

现版 `structured_to_md.py` 已经不会这么干了（同一份 structured 重新生成，
罗马书 3:29 那一格是空的、约翰福音两处根本不出框），所以这 3 处是旧产物的
残留。重新发布整章会连带动到别的后处理结果，风险不值当，这里按站点定点修：

  · john-en/6.md  59-64   全书 14 处经文都是居中 <p>，就这一处是框 →
                          还原成居中 <p>（经文取表里的 la 格 + 第二行 en 格）
  · john-en/19.md 25-27   同上
  · romans-en/3.md 29-30  全章 11 处都是框，保留框与拉丁文列，只把 en 格
                          清空（英文经文在 PDF 提取阶段就丢了，现版生成器
                          出的也是空格），注释搬到框后

注释原文一字不改，只把行内 HTML 还原成本文件通用的 markdown 写法
（`<strong>` → `**`、`<em>` → `*`、`<sup id="fnref:N">` → `[^N]`），
好让 kramdown 照常配对脚注。

用法：
    python3 scripts/fix_commentary_in_box.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (文件, 框里第一节的节号, 处理方式)
SITES = [
    ('calvin/john-en/6.md', '59', 'unbox'),
    ('calvin/john-en/19.md', '25', 'unbox'),
    ('calvin/romans-en/3.md', '29', 'keep-box'),
]

BOX_RE = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
ROW_RE = re.compile(r'<tr><td class="scripture-en">(.*?)</td>'
                    r'<td class="scripture-la">(.*?)</td></tr>', re.S)
COMMENT_CELL = re.compile(r'^<strong>(\d+)\.</strong>\s*<span style="color:#800000">')


def html_to_md(s: str) -> str:
    s = re.sub(r'<sup id="fnref:([^"]+)"><a[^>]*>[^<]*</a></sup>', r'[^\1]', s)
    s = re.sub(r'<strong>(.*?)</strong>', r'**\1**', s, flags=re.S)
    s = re.sub(r'<em>(.*?)</em>', r'*\1*', s, flags=re.S)
    return s.strip()


def fix_file(path: Path, first_verse: str, mode: str, apply: bool) -> bool:
    text = path.read_text(encoding='utf-8')
    for box in BOX_RE.finditer(text):
        rows = ROW_RE.findall(box.group(0))
        if not rows:
            continue
        m = COMMENT_CELL.match(rows[0][0].strip())
        if not m or m.group(1) != first_verse:
            continue
        commentary = html_to_md(rows[0][0])
        if mode == 'unbox':
            # 经文＝第一行的 la 格（这本书第二列装的就是英文经文）+ 其余行的 en 格
            verses = [rows[0][1].strip()] + [r[0].strip() for r in rows[1:] if r[0].strip()]
            new_box = ('<p style="text-align:center" markdown="1">'
                       + ' '.join(html_to_md(v) for v in verses) + '</p>')
        else:
            # 保留框与拉丁文列，只把注释从 en 格里拿走
            head = box.group(0)[:box.group(0).index('<tr><td class="scripture-en">')]
            body = [f'<tr><td class="scripture-en"></td>'
                    f'<td class="scripture-la">{rows[0][1]}</td></tr>']
            body += [f'<tr><td class="scripture-en">{a}</td>'
                     f'<td class="scripture-la">{b}</td></tr>' for a, b in rows[1:]]
            new_box = head + '\n'.join(body) + '\n</tbody>\n</table>\n\n</div>'
        new = text[:box.start()] + new_box + '\n\n' + commentary + text[box.end():]
        print(f'  {path}: 第 {first_verse} 节的注释搬出经文框'
              f'（{"整框还原成居中段落" if mode == "unbox" else "保留框，清空英文格"}）')
        if apply:
            path.write_text(new, encoding='utf-8')
        return True
    return False


def main() -> int:
    apply = '--apply' in sys.argv
    n = 0
    for rel, verse, mode in SITES:
        if fix_file(ROOT / rel, verse, mode, apply):
            n += 1
    print(f'[{"applied" if apply else "dry-run"}] {n}/{len(SITES)} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
