#!/usr/bin/env python3
"""中译页面的标点归一：① 直角引号 `「」` → 弯引号 `“”`；② 夹在中文之间的半角标点 → 全角。

为什么要有这一步
----------------
翻译是逐段调用模型完成的，同一章里两种引号会混着出现——以弗所书中译 7 个文件
里，`「」` 87 对、`“”` 639 对，同一页上下两段就可能不一样。站内既有中译的多数
形态是 `“”`（贺智罗马书 1705 : 230、林前 529 : 164），所以归一到 `“”`。

判据与守卫
----------
1. **只在不嵌套时才换**。`“…「…」…”` 或 `「…“…”…」` 这类嵌套里，内外层必须
   用不同的引号才分得清，碰到就整个文件跳过并报出来。
2. **必须成对**。文件里 `「` 与 `」` 数目不等 → 跳过并报出来，
   免得把一个孤立的半边引号换成另一种孤立的半边。
3. 只动这两个字符，别的一概不碰（「只准动标点」那道闸）。

半角标点
--------
逐段翻译偶尔会漏出半角 `,;:!?`（司布真卷首题记首段就是「这本久盼的书,如今…手中;」）。
判据钉死为「**两侧都是中文字**」：经文引用 `马太福音 3:5`、枚举 `1, 2`、
HTML 属性、markdown 标记两侧都不是中文，一个都不会被动到。
实测全站中译 21 处（罗马书 16、以弗所书 2、司布真 3），中文间的半角句点 0 处，
所以句点不在处理集合里。

用法:
    python3 scripts/normalize_zh_quotes.py hodge/ephesians/zh        # 目录
    python3 scripts/normalize_zh_quotes.py --check hodge/*/zh        # 只报告
"""
import argparse
import re
import sys
from pathlib import Path

_NEST_A = re.compile(r'“[^”]*「[^」]*」[^”]*”')   # 弯引号里套直角
_NEST_B = re.compile(r'「[^」]*“[^”]*”[^」]*」')   # 直角里套弯引号

# 夹在两个中文字之间的半角标点。两侧都要求是中文，是这条规则唯一的守卫。
_HALF_PUNCT = re.compile(r'(?<=[\u4e00-\u9fff])([,;:!?])(?=[\u4e00-\u9fff])')
_FULL = {',': '，', ';': '；', ':': '：', '!': '！', '?': '？'}


def normalize_text(text: str):
    """→ (归一后的文本, 换掉的引号对数, 换掉的半角标点数, 警告)。

    翻译脚本落盘前也调这个函数——否则 `--resume` 重跑一次，直角引号与半角
    标点又从缓存里回来了（2026-09-30 实测：以弗所书重跑后 22 对又冒出来）。
    """
    n_open, n_close = text.count('「'), text.count('」')
    if n_open != n_close:
        return text, 0, 0, f'「{n_open} / 」{n_close} 不成对，跳过'
    if _NEST_A.search(text) or _NEST_B.search(text):
        return text, 0, 0, '存在嵌套引号，跳过（内外层要靠不同引号区分）'
    new = text.replace('「', '“').replace('」', '”')
    n_half = len(_HALF_PUNCT.findall(new))
    new = _HALF_PUNCT.sub(lambda m: _FULL[m.group(1)], new)
    return new, n_open, n_half, ''


def process(path: Path, write: bool):
    text = path.read_text(encoding='utf-8')
    n_open, n_close = text.count('「'), text.count('」')
    if n_open != n_close:
        return 0, 0, f'{path}: 「{n_open} / 」{n_close} 不成对，跳过'
    if _NEST_A.search(text) or _NEST_B.search(text):
        return 0, 0, f'{path}: 存在嵌套引号，跳过（内外层要靠不同引号区分）'
    new = text.replace('「', '“').replace('」', '”')
    n_half = len(_HALF_PUNCT.findall(new))
    new = _HALF_PUNCT.sub(lambda m: _FULL[m.group(1)], new)
    if write and new != text:
        path.write_text(new, encoding='utf-8')
    return n_open, n_half, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+', help='目录或 md 文件')
    ap.add_argument('--check', action='store_true', help='只报告不写入')
    a = ap.parse_args()

    files = []
    for p in a.paths:
        q = Path(p)
        files.extend(sorted(q.glob('*.md')) if q.is_dir() else [q])

    total, total_half, skipped = 0, 0, []
    for f in files:
        n, nh, warn = process(f, not a.check)
        total += n; total_half += nh
        if warn:
            skipped.append(warn)
        elif n or nh:
            print(f'  {f}: 引号 {n} 对 · 半角标点 {nh} 处')
    for w in skipped:
        print('  ⚠ ' + w, file=sys.stderr)
    print(f'合计 {total} 对 `「」` → `“”`，{total_half} 处半角标点 → 全角'
          + ('（--check，未写入）' if a.check else '')
          + (f'；{len(skipped)} 个文件跳过' if skipped else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
