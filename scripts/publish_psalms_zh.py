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
import re, sys, datetime
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


def clean_body(b):
    b = re.sub(r'<<<[^>]*?>>>', '', b)
    b = strip_dead_footnote_marks(b)
    b = re.sub(r'\n[ \t]*\n[ \t]*\n', '\n\n', b)
    b = b.replace('前往诗篇', '前往 诗篇')
    return b


def strip_dead_footnote_marks(b):
    """去掉正文里的 fa/fb/fc… 死标记（skill 方案 B）。

    这些标记的定义在英文版已经还原（附录一直埋在 ch78/ch150 里），但中文版
    还没有译出脚注正文，标记留在正文里就是一串裸露的红色 "fc266"。按 skill
    在 publish 层去掉——**只动发布产物，不动 zh_chapters raw**，位置信息保留，
    等脚注正文译出后可直接照英文版的做法还原成真脚注。

    `[a-e]` 是 skill 定的范围：排除 ft（附录定义标签）和单个 f，避免误伤
    phil/heb/john 等书的 [^fN] 引用。
    """
    def cut(m):
        # 标记两侧都是中文时把空格一并吃掉（中文正文不留空格）；
        # 一侧是拉丁字母/数字则保留一个空格，避免把词粘连起来。
        left, right = m.group(1), m.group(2)
        cjk = r'[　-〿＀-￯一-鿿]'
        if re.search(cjk + r'$', left) and re.match(cjk, right or ' '):
            return left + (right or '')
        return left + (' ' if left and right else '') + (right or '')

    b = re.sub(r'([\s\S]?)[ \t]*<span style="color:#800000">\s*f[a-e]\d+[a-z]?\s*</span>'
               r'[ \t]*([\s\S]?)', cut, b)
    b = re.sub(r'[ \t]+([，。；：、？！）」』])', r'\1', b)
    b = re.sub(r'[ \t]+$', '', b, flags=re.M)      # 行末残留空格
    return b


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
        out_dir.mkdir(parents=True, exist_ok=True)
        nums = sorted(int(p.stem) for p in src_dir.glob('*.md')
                      if p.stem.isdigit()) if src_dir.exists() else []
        translated = set(nums)
        for n in nums:
            if want and n not in want:
                continue
            raw = (src_dir / f'{n}.md').read_text(encoding='utf-8')
            m = re.match(r'^---\n.*?\n---\n(.*)$', raw, re.DOTALL)
            body = clean_body(m.group(1).strip('\n')) if m else clean_body(raw)
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
