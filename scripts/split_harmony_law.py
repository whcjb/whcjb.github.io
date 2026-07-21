#!/usr/bin/env python3
"""把 calvin/harmony-law-{v}-en/1.md 单卷大文件按原文顺序切成多章。

规则(方案B):
- 保持原文顺序, 不重排内容。
- 分节点: title-block-h1 / <h2 class="scripture-anchor"> / '## ' 标题。
- 贪心打包成 ~TARGET 行的章; 遇 title-block-h1 且当前章已达 MIN 则起新章(大标题起新章)。
- 末尾 FOOTNOTES 段(全部 [^fN]: 定义)不单独成章; 各章按自身引用把对应定义追加到章尾。
- 每章生成 front matter + prev/next 导航; 更新 index.html 的 chapters 计数。

用法: python3 scripts/split_harmony_law.py [v ...]   (默认 1 2 3 4)
先跑 --dry 只报告章数/标题, 不写文件。
"""
import re, sys, os, glob

ROOT = '/Users/yanpeifa/Documents/whcjb.github.io'
TARGET_MAX = 650   # 单章目标上限(行)
MIN_FOR_H1 = 300   # 当前章达到此行数后, 遇 h1 就起新章

RE_H1   = re.compile(r'class="title-block-h1"')
RE_ANCH = re.compile(r'class="scripture-anchor"')
RE_MDH2 = re.compile(r'^## ')
RE_DEF  = re.compile(r'^\[\^(f[0-9A-Za-z]+)\]:')
RE_REF  = re.compile(r'\[\^(f[0-9A-Za-z]+)\](?!:)')

def strip_tags(s):
    return re.sub(r'<[^>]*>', '', s).strip()

def title_of(line):
    """从 title-block-h1 行或 scripture-anchor 行取简短标题"""
    if RE_H1.search(line):
        return strip_tags(line)
    m = re.search(r'data-ref="([^"]*)"', line)
    if m: return m.group(1)
    if RE_MDH2.match(line):
        return line[3:].strip()
    return None

def split_volume(v, dry=False):
    d = f'{ROOT}/calvin/harmony-law-{v}-en'
    src = f'{d}/1.md'
    raw = open(src, encoding='utf-8').read()
    # 分离 front matter
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', raw, re.S)
    assert m, f'no front matter in {src}'
    body_all = m.group(2)
    lines = body_all.split('\n')

    # FOOTNOTES h1 位置 → 之后是定义池
    fn_line = None
    for i, l in enumerate(lines):
        if RE_H1.search(l) and 'FOOTNOTES' in strip_tags(l):
            fn_line = i; break
    assert fn_line is not None, f'no FOOTNOTES section in vol {v}'
    body = lines[:fn_line]
    foot = lines[fn_line:]

    # 脚注定义池: id -> 整行
    pool = {}
    for l in foot:
        dm = RE_DEF.match(l)
        if dm: pool[dm.group(1)] = l

    # 分节点
    starts = [i for i, l in enumerate(body)
              if RE_H1.search(l) or RE_ANCH.search(l) or RE_MDH2.match(l)]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    secs = [(starts[k], starts[k+1] if k+1 < len(starts) else len(body))
            for k in range(len(starts))]

    # 贪心打包
    chapters = []          # 每章 (start,end)
    cur_start = 0; cur_len = 0
    for (a, b) in secs:
        seclen = b - a
        is_h1 = bool(RE_H1.search(body[a]))
        if cur_len > 0 and (cur_len >= TARGET_MAX or (is_h1 and cur_len >= MIN_FOR_H1)):
            chapters.append((cur_start, a)); cur_start = a; cur_len = 0
        cur_len += seclen
    chapters.append((cur_start, len(body)))

    # 每章标题
    def chap_title(a, b):
        # 优先该章首个 title-block-h1
        for i in range(a, b):
            if RE_H1.search(body[i]):
                t = strip_tags(body[i])
                if t and t != 'FOOTNOTES':
                    return t[:60]
        for i in range(a, b):
            t = title_of(body[i])
            if t: return t[:60]
        return None

    titles = [chap_title(a, b) or f'Chapter {k+1}' for k, (a, b) in enumerate(chapters)]

    if dry:
        print(f'== 卷{v}: {len(chapters)} 章 ==')
        for k, ((a, b), t) in enumerate(zip(chapters, titles), 1):
            print(f'  Ch{k:2d} {b-a:5d}行  {t}')
        # 内容零丢失校验
        assert sum(b-a for a,b in chapters) == len(body)
        return len(chapters)

    # 写各章
    bn = f'harmony-law-{v}-en'
    for k, ((a, b), t) in enumerate(zip(chapters, titles), 1):
        seg = '\n'.join(body[a:b]).strip('\n')
        # 该章引用的脚注 → 追加定义
        refs = []
        seen = set()
        for fid in RE_REF.findall(seg):
            if fid in pool and fid not in seen:
                seen.add(fid); refs.append(pool[fid])
        # 按数字排序
        def keyf(defline):
            mm = re.match(r'\[\^f(\d+)', defline)
            return int(mm.group(1)) if mm else 0
        refs.sort(key=keyf)
        fm = ['---', 'layout: calvin-en', f'book_id: {bn}',
              f'book_name: "Harmony of the Law (Vol. {v})"',
              f'chapter: {k}', f'title: "{t}"', 'date: 2026-06-03 09:15']
        if k == 1:
            fm += ['prev_section: preface', 'prev_label: "Preface"']
        else:
            fm += [f'prev_section: {k-1}', f'prev_label: "{titles[k-2]}"']
        if k < len(chapters):
            fm += [f'next_section: {k+1}', f'next_label: "{titles[k]}"']
        fm.append('---')
        out = '\n'.join(fm) + '\n\n' + seg
        if refs:
            out += '\n\n' + '\n\n'.join(refs) + '\n'
        else:
            out += '\n'
        open(f'{d}/{k}.md', 'w', encoding='utf-8').write(out)

    # 删除原单文件(已被 1.md..N.md 覆盖; 1.md 会被 ch1 覆盖, 其余新建)
    # 若原章数 < 新章数, 无多余旧文件; 若 >, 需清理
    for old in glob.glob(f'{d}/*.md'):
        bnm = os.path.basename(old)
        if bnm in ('preface.md',): continue
        mnum = re.match(r'(\d+)\.md$', bnm)
        if mnum and int(mnum.group(1)) > len(chapters):
            os.remove(old)

    # 更新 index.html chapters 计数
    idx = f'{d}/index.html'
    s = open(idx, encoding='utf-8').read()
    s = re.sub(r'^chapters: \d+', f'chapters: {len(chapters)}', s, flags=re.M)
    open(idx, 'w', encoding='utf-8').write(s)
    print(f'卷{v}: 写入 {len(chapters)} 章, index chapters={len(chapters)}')
    return len(chapters)

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--dry']
    dry = '--dry' in sys.argv
    vols = [int(x) for x in args] if args else [1, 2, 3, 4]
    for v in vols:
        split_volume(v, dry=dry)
