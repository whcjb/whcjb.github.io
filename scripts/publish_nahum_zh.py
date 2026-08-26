#!/usr/bin/env python3
"""publish_nahum_zh.py — 加尔文《那鸿书注释》中译发布。

共 3 章，章号与英文 calvin/nahum-en/ 对齐。

- calvin-en 布局；front matter 本地化；prev/next 只在已译章之间连。
- 已发布章保留原 date；新章用当前真实时间。
- 末尾重写 index.html（calvin-book-modern）。

用法: python3 scripts/publish_nahum_zh.py        # 发布所有已翻译
      python3 scripts/publish_nahum_zh.py 1 3    # 只发布指定章
"""
import re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

SRC_DIR = ROOT / 'calvin_raw/nahum/zh_chapters'
OUT_DIR = ROOT / 'calvin/nahum'
BOOK_ID = 'nahum'
BOOK_NAME = '那鸿书'
TOTAL = 3


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)                 # BATCH 分段标记
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('****', '')                          # abut-bold
    b = b.replace('前往那鸿书', '前往 那鸿书')
    b = re.sub(r'[ \t]+([，。；：、？！）」』])', r'\1', b)
    b = re.sub(r'[ \t]+$', '', b, flags=re.M)
    return b



def relocate_anchors_in_body(body):
    """把 scripture-anchor 的 id 从经文块**前面**挪到经文块**后面**。

    Step 7（07-verse-index.md §1）的硬要求：id 若留在 <h2 class="scripture-anchor">
    上，verse-index 胶囊点下去会落在经文块之前——用户视野里全是经文、看不到注释，
    skill 写明「算作没做对」。所以 id 移到经文块闭合之后的 commentary-anchor：

        <h2 class="scripture-anchor" data-ref="...">…</h2>
        <div class="scripture-box">…</div>
        <div class="commentary-anchor" id="BOOK-CH-V"></div>   ← 跳转目标

    特例：h2 后面没有 scripture-box（注释紧贴 h2）时，anchor 紧跟 h2。

    不写死书名前缀——jeremiah-1 这类 book_id 自带数字，`jeremiah-1-1-3`
    拆不清是「卷一 1:3」还是「jeremiah 1-1-3」。
    """
    h2_re = re.compile(r'^(<h2 class="scripture-anchor")\s+id="([^"]+)"(.*?)>(.*)$')
    lines = body.split('\n')
    out, i = [], 0
    while i < len(lines):
        m = h2_re.match(lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        pre, aid, post_attrs, tail = m.groups()
        out_h2 = f'{pre}{post_attrs}>{tail}'
        anchor = f'<div class="commentary-anchor" id="{aid}"></div>'
        j = i + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        if j < len(lines) and lines[j].lstrip().startswith('<div class="scripture-box"'):
            k, depth = j + 1, 1
            while k < len(lines) and depth > 0:
                depth += lines[k].count('<div') - lines[k].count('</div>')
                if depth == 0:
                    break
                k += 1
            if k >= len(lines):
                out.append(lines[i]); i += 1; continue
            out.append(out_h2)
            out.extend(lines[i + 1:k + 1])
            out.append(anchor)
            i = k + 1
        else:
            out.append(out_h2)
            out.append(anchor)
            i += 1
    return '\n'.join(out)

def chapter_date(n):
    p = OUT_DIR / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now


def main():
    want = set(int(a) for a in sys.argv[1:]) if len(sys.argv) > 1 else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nums = sorted(int(p.stem) for p in SRC_DIR.glob('*.md')
                  if p.stem.isdigit()) if SRC_DIR.exists() else []
    translated = set(nums)
    for n in nums:
        if want and n not in want:
            continue
        raw = (SRC_DIR / f'{n}.md').read_text(encoding='utf-8')
        m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
        body = clean_body(m.group(1).strip('\n') if m else raw)
        body = relocate_anchors_in_body(body)
        fm = ['---', 'layout: calvin-en', f'book_id: {BOOK_ID}',
              f'book_name: {BOOK_NAME}', f'chapter: {n}',
              f'total_chapters: {TOTAL}', f'title: "那鸿书 {n}"',
              f'date: {chapter_date(n)}']
        if n > 1 and (n - 1) in translated:
            fm += [f'prev_section: {n-1}', f'prev_label: "那鸿书 {n-1}"']
        if n < TOTAL and (n + 1) in translated:
            fm += [f'next_section: {n+1}', f'next_label: "那鸿书 {n+1}"']
        fm += ['---', '']
        (OUT_DIR / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n',
                                         encoding='utf-8')
        print(f'  published {BOOK_ID}/{n}.md  那鸿书 {n}')
    if nums:
        (OUT_DIR / 'index.html').write_text(
            '---\nlayout: calvin-book-modern\n'
            f'book_id: {BOOK_ID}\nbook_name: {BOOK_NAME}\n'
            f'chapters: {TOTAL}\nhas_preface: false\n---\n', encoding='utf-8')
        print(f'  {BOOK_ID} index.html 已写；已译章: {nums}')
    else:
        print(f'  {BOOK_ID} 暂无译章, 跳过 index')


if __name__ == '__main__':
    main()
