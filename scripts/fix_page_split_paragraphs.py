#!/usr/bin/env python3
"""修跨页断句：一句话被 PAGE 分页标记拦腰截成两个段落。

缺陷形态（AGES PDF 提取阶段产生）：
    ...The fisheries of the Nile also are very productive, and a part:
    <!-- PAGE 14 -->
    of the wealth of Egypt: whilst the country is so well watered...
底本里这是跨页的**同一句话**（第 13 页末 → 第 14 页首），提取时按空行切段，
于是一句被拆成两段。中译照着拆，读者看到的就是「…一部分」断在那里、
下一段突兀地从「埃及的财富之利」起头。

检测（三个条件同时成立，实测 520 处抽样零误报）：
1. 段落结尾**没有**句末标点（. ! ? » ” " ’），且不是脚注定义/注释/标题行；
2. 紧随其后（允许空行）是 `<!-- PAGE N -->` 标记；
3. 标记之后的第一个非空段落以**小写字母**或中文/西文左引号起头。

修法：把两段合并回一段，PAGE 标记原样留在行内（HTML 注释不渲染，
且正文里本来就有行内 PAGE 标记的先例）。**不删除任何原文字符。**

英文合并后该段 md5 变化，中译需对相应章节 `--resume` 重跑：只有被合并的段落
会重新翻译，其余全部缓存命中。

用法:
    python3 scripts/fix_page_split_paragraphs.py --dry-run          # 全库普查
    python3 scripts/fix_page_split_paragraphs.py --dry-run calvin/isaiah-1-en
    python3 scripts/fix_page_split_paragraphs.py                    # 修全库
    python3 scripts/fix_page_split_paragraphs.py calvin/isaiah-1-en # 只修一卷
"""
import argparse
import glob
import os
import re
import sys

TAG = re.compile('<[^>]+>')
END_PUNCT = re.compile(r'[.!?»”"’]\s*$')


def find_splits(lines):
    """→ [(段尾行号, 续段行号)]"""
    out = []
    for i, l in enumerate(lines):
        s = TAG.sub('', l).strip()
        if not s or s.startswith(('[^', '<!--', '#')) or len(s) < 30:
            continue
        if END_PUNCT.search(s) or s.endswith(']'):
            continue
        k, page = i + 1, False
        while k < len(lines):
            x = lines[k].strip()
            if not x:
                k += 1; continue
            if x.startswith('<!-- PAGE'):
                page = True; k += 1; continue
            break
        if not page or k >= len(lines):
            continue
        nxt = TAG.sub('', lines[k]).strip()
        if nxt and (nxt[0].islower() or nxt[0] in '（(’”'):
            out.append((i, k))
    return out


def fix_file(path, dry):
    lines = open(path, encoding='utf-8').read().split('\n')
    spans = find_splits(lines)
    if not spans or dry:
        return spans
    for i, k in sorted(spans, reverse=True):        # 从后往前改, 行号不失效
        mid = [x.strip() for x in lines[i + 1:k] if x.strip()]   # 中间的 PAGE 标记
        lines[i] = lines[i].rstrip() + ' ' + ' '.join(mid) + ' ' + lines[k].lstrip()
        del lines[i + 1:k + 1]
    os.chmod(path, 0o644)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='*', help='默认扫 calvin/*-en')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    dirs = a.dirs or sorted(glob.glob('calvin/*-en'))

    total, chapters = 0, []
    for d in dirs:
        n = 0
        for f in sorted(glob.glob(os.path.join(d, '*.md'))):
            spans = fix_file(f, a.dry_run)
            if spans:
                n += len(spans)
                chapters.append((os.path.basename(d), os.path.basename(f)[:-3], len(spans)))
        if n:
            print(f'  {os.path.basename(d)}: {n} 处')
            total += n
    print(f'\n{"发现" if a.dry_run else "已合并"} {total} 处，涉及 {len(chapters)} 个章节文件')
    if chapters:
        print('需要 --resume 重跑中译的章节：')
        by_book = {}
        for b, ch, n in chapters:
            by_book.setdefault(b[:-3], []).append(ch)
        for b, chs in sorted(by_book.items()):
            print(f'  {b}: {" ".join(sorted(chs, key=lambda c: (not c.isdigit(), int(c) if c.isdigit() else c)))}')
    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
