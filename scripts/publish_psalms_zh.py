#!/usr/bin/env python3
"""publish_psalms_zh.py — 诗篇中译发布，**两卷**对齐英文(psalms-1-en / psalms-2-en)。

- 卷一：诗篇 1-78 → calvin/psalms-1/N.md (book_id psalms-1, 诗篇（卷一）)
- 卷二：诗篇 79-150 → calvin/psalms-2/N.md (book_id psalms-2, 诗篇（卷二）)
- 篇号用绝对值(与英文一致，切换 psalms-1↔psalms-1-en 对得上)。
- calvin-en 布局；front matter 本地化；prev/next 卷内 N±1。
- 已发布章保留原 date；新章用当前真实时间。
- index.html: calvin-book-modern（chapter 字段使 titled_book 为真, 只渲染已译篇）。
用法: python3 scripts/publish_psalms_zh.py            # 发布所有已翻译
      python3 scripts/publish_psalms_zh.py 1 3        # 只发布指定篇号
"""
import json, re, sys, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

# 每卷: (源 zh_chapters, 输出目录, book_id, book_name, 篇号下限, 篇号上限, index chapters)
VOLS = [
    (ROOT / 'calvin_raw/psalms-1/zh_chapters', ROOT / 'calvin/psalms-1',
     'psalms-1', '诗篇（卷一）', 1, 78, 78),
    (ROOT / 'calvin_raw/psalms-2/zh_chapters', ROOT / 'calvin/psalms-2',
     'psalms-2', '诗篇（卷二）', 79, 150, 150),
]


ZH_FOOTNOTES = {}          # {vol: {code: 中文定义}}，main() 里按卷载入


def clean_body(b, zh_defs=None):
    b = re.sub(r'<<<[^>]*?>>>', '', b)
    b, used = restore_footnotes(b, zh_defs or {})
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('前往诗篇', '前往 诗篇')
    if used:
        b = b.rstrip() + '\n\n' + '\n\n'.join(
            f'[^{c}]: {zh_defs[c]}' for c in used) + '\n'
    return b


def restore_footnotes(b, zh_defs):
    """正文里的 fa/fb/fc 死标记 → 真脚注引用 [^faN]。

    标记本身是从英文源翻译时原样带过来的，位置就是 PDF 里上标的位置，不用猜。
    只有中文定义已经译好（zh_footnote_defs.json 里有）的 code 才转换——转了却
    没有定义，kramdown 会把 [^faN] 原样吐在正文里。

    `[a-e]` 是 skill 定的范围：排除 ft（附录定义标签）和单个 f，
    避免误伤 phil/heb/john 等书的 [^fN] 引用。
    """
    used = []

    def repl(m):
        code = m.group(1)
        if code not in zh_defs:
            return m.group(0)
        if code not in used:
            used.append(code)
        return f'[^{code}]'

    b = re.sub(r'<span style="color:#800000">\s*(f[a-e]\d+[A-Za-z]?)\s*</span>', repl, b)
    # 锚点脚本直接插进 raw 的引用同样要在章末补定义
    for c in re.findall(r'\[\^(f[a-e]\d+[A-Za-z]?)\](?!:)', b):
        if c in zh_defs and c not in used:
            used.append(c)
    # 标记前后可能有多余空格（原文上标前有空格），中文正文不留
    b = re.sub(r'([　-〿＀-￯一-鿿])[ \t]+(\[\^f)', r'\1\2', b)
    b = re.sub(r'(\[\^f[a-e]\d+[A-Za-z]?\])[ \t]+([　-〿＀-￯一-鿿])', r'\1\2', b)
    b = re.sub(r'[ \t]+([，。；：、？！）」』])', r'\1', b)
    b = re.sub(r'[ \t]+$', '', b, flags=re.M)
    # 查不到定义的引用**只报警，不删**。删掉等于把线索一起抹了：ch45 曾出现的
    # [^f004] 根本不是脚注，而是 AGES 经文编码 <19F004> 在英文提取阶段被误拆成
    # <19[^f004]>，源头修好即可，删引用只会掩盖问题。
    orphan = sorted({c for c in re.findall(r'\[\^([a-z]{1,3}\d+[A-Za-z]?)\](?!:)', b)
                     if c not in zh_defs})
    if orphan:
        print(f'    ⚠ 引用无对应中文定义（未删除，请查源头）: {orphan}')
    # 含脚注引用的 <p> 必须带 markdown="1"，否则 kramdown 跳过整块 HTML，
    # [^fcN] 会原样显示（见 reference_kramdown_markdown_attr）
    def add_md(m):
        tag, inner = m.group(1), m.group(2)
        if 'markdown=' in tag or '[^' not in inner:
            return m.group(0)
        return tag[:-1] + ' markdown="1">' + inner + '</p>'
    b = re.sub(r'(<p\b[^>]*>)((?:(?!</p>).)*)</p>', add_md, b, flags=re.S)
    used.sort(key=lambda c: (c[:2], int(re.sub(r'\D', '', c))))
    return b, used


def chapter_date(out_dir, n):
    p = out_dir / f'{n}.md'
    if p.exists():
        m = re.search(r'^date:\s*(.+)$', p.read_text(encoding='utf-8'), re.M)
        if m:
            return m.group(1).strip()
    return now


def main():
    want = set(int(a) for a in sys.argv[1:]) if len(sys.argv) > 1 else None
    for src_dir, out_dir, book_id, book_name, lo, hi, idx_chapters in VOLS:
        # 该卷已译好的脚注定义（没有就按无脚注发布，正文里的死标记原样保留）
        zh_fn_path = src_dir.parent / 'zh_footnote_defs.json'
        zh_defs = (json.loads(zh_fn_path.read_text(encoding='utf-8'))
                   if zh_fn_path.exists() else {})
        out_dir.mkdir(parents=True, exist_ok=True)
        nums = sorted(int(p.stem) for p in src_dir.glob('*.md')
                      if p.stem.isdigit()) if src_dir.exists() else []
        translated = set(nums)
        for n in nums:
            if want and n not in want:
                continue
            raw = (src_dir / f'{n}.md').read_text(encoding='utf-8')
            m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
            body = clean_body(m.group(1).strip('\n') if m else raw, zh_defs)
            fm = ['---', 'layout: calvin-en', f'book_id: {book_id}',
                  f'book_name: {book_name}', f'chapter: {n}',
                  'total_chapters: 150', f'title: "诗篇 {n}"',
                  f'date: {chapter_date(out_dir, n)}']
            # prev/next 只在**已译**篇之间连；否则会链到未发布篇 → 404
            if n > lo and (n - 1) in translated:
                fm += [f'prev_section: {n-1}', f'prev_label: "诗篇 {n-1}"']
            if n < hi and (n + 1) in translated:
                fm += [f'next_section: {n+1}', f'next_label: "诗篇 {n+1}"']
            fm += ['---', '']
            (out_dir / f'{n}.md').write_text('\n'.join(fm) + '\n' + body + '\n',
                                             encoding='utf-8')
            print(f'  published {book_id}/{n}.md  诗篇 {n}')
        # index.html: 仅当该卷已有译章时写(空卷写了会渲染满屏 404 占位;
        # 主页会把无内容的卷显示为 pending 非链接)。
        if nums:
            (out_dir / 'index.html').write_text(
                '---\nlayout: calvin-book-modern\n'
                f'book_id: {book_id}\nbook_name: {book_name}\n'
                f'chapters: {idx_chapters}\nhas_preface: false\n---\n', encoding='utf-8')
            print(f'  {book_id} index.html 已写；该卷已译篇: {nums}')
        else:
            print(f'  {book_id} 暂无译章, 跳过 index(主页显示为 pending)')


if __name__ == '__main__':
    main()
