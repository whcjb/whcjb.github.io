#!/usr/bin/env python3
"""修双语经文表左右两列错开一节的行（中译版）。

发布脚本把 bilingual 表左列的英文换成和合本时，用的正则是

    <tr><td class="scripture-en">.*?<strong>(\\d+)\\.</strong>.*?</td>(<td class="scripture-la">.*?</td>)</tr>

`.*?` 加 re.DOTALL 不受单元格边界约束。中译 raw 里节号有两种写法——
`<strong>7.</strong>` 和 markdown 的 `**7.**`——碰上后者时，正则在左格里找不到
`<strong>`，就一路扫到右格的 `<strong>7.</strong>`，再往后吞掉下一行：两行并成
一行，左列是第 7 节的中文、右列却是第 8 节的拉丁文，第 8 节的中文整条消失。
页面上看是「中文与拉丁文对不上，且少了一节」。

15 个 publish_*_zh.py 的正则已改成单元格内自闭、同时认两种节号写法。本脚本修
既有产物：受影响的框按 raw（raw 里行是对齐的）重建一遍——就是用修好的发布逻辑
重跑这一个框，别处一律不动。

用法：
    python3 scripts/fix_bilingual_row_shift.py [--apply]
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
ROW = re.compile(r'<tr><td class="scripture-en">(.*?)</td>'
                 r'<td class="scripture-la">(.*?)</td></tr>', re.S)
NUM = re.compile(r'^\s*(?:<strong>|\*\*)?(\d{1,3})[.．]')
CODE = re.compile(r'class="ages-code">&lt;(\w+)&gt;')

# 已发布目录 → (发布脚本, zh_chapters 目录)
BOOKS = {
    '1corinthians': ('publish_1cor_zh.py', '1cor'),
    '2corinthians': ('publish_2cor_zh.py', '2cor'),
    '2peter': ('publish_2peter_zh.py', '2peter'),
    'james': ('publish_james_zh.py', 'james'),
}


def _num(cell: str):
    m = NUM.match(cell.lstrip())
    return m.group(1) if m else None


def misaligned(box: str) -> bool:
    for m in ROW.finditer(box):
        a, b = _num(m.group(1)), _num(m.group(2))
        if a and b and a != b:
            return True
    return False


def load_publisher(script: str):
    spec = importlib.util.spec_from_file_location('pub_' + script, ROOT / 'scripts' / script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    apply = '--apply' in sys.argv
    total = 0
    for book, (script, raw_dir) in BOOKS.items():
        mod = None
        for pub in sorted((ROOT / 'calvin' / book).glob('*.md')):
            text = pub.read_text(encoding='utf-8')
            boxes = [m for m in BOX.finditer(text) if misaligned(m.group(0))]
            if not boxes:
                continue
            raw = ROOT / f'calvin_raw/{raw_dir}/zh_chapters/{pub.name}'
            if not raw.exists():
                print(f'  ?? 找不到 raw: {raw}')
                continue
            raw_text = raw.read_text(encoding='utf-8')
            raw_boxes = {}
            for m in BOX.finditer(raw_text):
                c = CODE.search(m.group(0))
                if c:
                    raw_boxes[c.group(1)] = m.group(0)
            if mod is None:
                mod = load_publisher(script)
            new_text, shift = text, 0
            for m in boxes:
                c = CODE.search(m.group(0))
                src = raw_boxes.get(c.group(1)) if c else None
                if not src:
                    print(f'  !! {pub} 框 {c.group(1) if c else "?"} 在 raw 里找不到，跳过')
                    continue
                rebuilt = mod.inject_chinese_scripture(src)
                if misaligned(rebuilt):
                    print(f'  !! {pub} 框 {c.group(1)} 重建后仍错位，跳过')
                    continue
                s, e = m.start() + shift, m.end() + shift
                new_text = new_text[:s] + rebuilt + new_text[e:]
                shift += len(rebuilt) - (m.end() - m.start())
                total += 1
                print(f'  {pub} 框 {c.group(1)}: 按 raw 重建，'
                      f'{len(ROW.findall(m.group(0)))} 行 → {len(ROW.findall(rebuilt))} 行')
            if apply and new_text != text:
                pub.write_text(new_text, encoding='utf-8')
    print(f'[{"applied" if apply else "dry-run"}] {total} 个框')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
