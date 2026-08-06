#!/usr/bin/env python3
"""publish_joshua_zh.py — 把 calvin_raw/joshua/zh_chapters/N.md 发布到 calvin/joshua/N.md。

joshua 是常规书(非 harmony 学术结构): 正文 `# 第N章` + 「前往」指引 + `**N.**` 注释 + 脚注。
- front matter 本地化: book_id joshua-en→joshua, book_name→约书亚记, title「Chapter N」→第N章,
  prev/next label 英文→中文, 增量(只链已发布章避免404)。
- clean: 剥 <<<END>>>, 「前往约书亚记」补空格。
- index.html: calvin-book-modern, chapters=已发布最大章号。
用法: python3 scripts/publish_joshua_zh.py
"""
import re, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC = ROOT / 'calvin_raw/joshua/zh_chapters'
OUT = ROOT / 'calvin/joshua'
BOOK_ID = 'joshua'
BOOK_NAME = '约书亚记'
CN_NUM = '零一二三四五六七八九十'

def cn_ch(n):
    if n <= 10: return CN_NUM[n]
    if n < 20: return '十' + (CN_NUM[n-10] if n > 10 else '')
    return CN_NUM[n//10] + '十' + (CN_NUM[n%10] if n % 10 else '')

def clean_body(b):
    # 去所有 <<<...>>> 分段标记变体(<<<END>>> / <<</1>>> / <<<END1>>> 等), 含行内残留
    b = re.sub(r'<<<[^>]*?>>>', '', b)
    # 去因此产生的纯空行(仅清标记所在的空行, 保留正常段间空行不作激进处理)
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('前往约书亚记', '前往 约书亚记').replace('前往申命记', '前往 申命记')
    return b

OUT.mkdir(parents=True, exist_ok=True)
present = sorted(int(p.stem) for p in SRC.glob('*.md') if p.stem.isdigit())
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def chapter_date(n):
    """已发布章保留其原有 date(不改历史时间戳); 新章用当前真实时间。"""
    p = OUT / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now

for n in present:
    raw = (SRC / f'{n}.md').read_text(encoding='utf-8')
    body = clean_body(re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL).group(1).strip('\n'))
    fm = ['---', 'layout: calvin-en', f'book_id: {BOOK_ID}', f'book_name: {BOOK_NAME}',
          f'chapter: {n}', f'title: "第{cn_ch(n)}章"', f'date: {chapter_date(n)}']
    prevs = [c for c in present if c < n]
    nexts = [c for c in present if c > n]
    if prevs:
        fm += [f'prev_section: {prevs[-1]}', f'prev_label: "第{cn_ch(prevs[-1])}章"']
    if nexts:
        fm += [f'next_section: {nexts[0]}', f'next_label: "第{cn_ch(nexts[0])}章"']
    fm += ['---', '']
    (OUT / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n', encoding='utf-8')
    print(f'  published joshua/{n}.md  第{cn_ch(n)}章  prev={prevs[-1] if prevs else "-"} next={nexts[0] if nexts else "-"}')

(OUT / 'index.html').write_text(
    f'---\nlayout: calvin-book-modern\nbook_id: {BOOK_ID}\n'
    f'book_name: {BOOK_NAME}\nchapters: {present[-1] if present else 0}\n'
    f'has_preface: false\n---\n', encoding='utf-8')
print(f'  index.html chapters={present[-1] if present else 0}, 已发布={present}')
