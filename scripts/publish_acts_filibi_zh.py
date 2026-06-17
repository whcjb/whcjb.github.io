#!/usr/bin/env python3
"""
publish_acts_filibi_zh.py — 将 acts-filibi 已翻译的中文章节发布到 calvin/acts/

输入：calvin_raw/acts-filibi/zh_chapters/<N>.md  (N = 1..10, 翻译进度)
输出：calvin/acts/<N>.md                          (覆盖旧版章节)
      calvin/acts/index.html                      (calvin-book-modern, chapters=已译数)

样式对齐腓立比书（publish_filibi_zh.py）：
- layout: calvin-en
- book_id: acts
- book_name: 使徒行传·加尔文注释
- index.html: calvin-book-modern

acts-filibi 的 raw 已经把经文渲染为 <div class="scripture-box"> 块，
本脚本不做经文格式转换，只做 frontmatter 规范化 + body 清理。

用法（项目根目录）：
    python3 scripts/publish_acts_filibi_zh.py
"""
import re
import subprocess
from pathlib import Path

SRC_DIR = Path('calvin_raw/acts-filibi/zh_chapters')
OUT_DIR = Path('calvin/acts')

BOOK_ID   = 'acts'
BOOK_NAME = '使徒行传·加尔文注释'

CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
          '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八',
          '十九', '二十', '二十一', '二十二', '二十三', '二十四', '二十五',
          '二十六', '二十七', '二十八']


def cn_chapter(n) -> str:
    if n == 'preface':
        return '前言'
    return f'第{CN_NUM[n]}章'


def get_date() -> str:
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def strip_frontmatter(text: str) -> str:
    """剥去首部 YAML frontmatter，只返回 body"""
    if not text.startswith('---'):
        return text
    m = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
    return text[m.end():] if m else text


def clean_body(body: str) -> str:
    """移除翻译过程中残留的 <<<END>>> 标记行"""
    lines = body.split('\n')
    cleaned = [l for l in lines if l.strip() != '<<<END>>>']
    return '\n'.join(cleaned)


def build_frontmatter(n, total: int, date: str, has_preface: bool) -> str:
    fm  = '---\n'
    fm += 'layout: calvin-en\n'
    fm += f'book_id: {BOOK_ID}\n'
    fm += f'book_name: "{BOOK_NAME}"\n'
    fm += f'title: "{cn_chapter(n)}"\n'
    fm += f'date: {date}\n'
    if n == 'preface':
        fm += 'next_section: 1\n'
        fm += 'next_label: "第一章"\n'
    else:
        if n > 1:
            fm += f'prev_section: {n - 1}\n'
            fm += f'prev_label: "{cn_chapter(n - 1)}"\n'
        elif has_preface:
            fm += 'prev_section: preface\n'
            fm += 'prev_label: "前言"\n'
        if n < total:
            fm += f'next_section: {n + 1}\n'
            fm += f'next_label: "{cn_chapter(n + 1)}"\n'
    fm += '---\n\n'
    return fm


def main():
    chapters = sorted(int(p.stem) for p in SRC_DIR.glob('*.md') if p.stem.isdigit())
    has_preface = (SRC_DIR / 'preface.md').exists()
    if not chapters and not has_preface:
        print(f'错误：{SRC_DIR} 下没有可发布章节')
        return
    if chapters and chapters != list(range(1, len(chapters) + 1)):
        print(f'警告：章节非连续 {chapters}')

    total = max(chapters) if chapters else 0
    items = (['preface'] if has_preface else []) + chapters
    print(f'发现已译：preface={has_preface}, chapters={chapters} (共 {total} 章)', flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date = get_date()

    for n in items:
        src = SRC_DIR / f'{n}.md'
        raw = src.read_text(encoding='utf-8')
        body = strip_frontmatter(raw)
        body = clean_body(body)
        # body 第一行可能是 "# 第N章" 或 "# 前言"，layout 已经渲染 title，不再重复
        body_lines = body.lstrip('\n').split('\n')
        if body_lines and re.match(r'^#\s+(?:第.+?章|前言|Preface)\s*$', body_lines[0]):
            body_lines.pop(0)
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
        body = '\n'.join(body_lines)

        fm = build_frontmatter(n, total, date, has_preface)
        content = fm + body.rstrip() + '\n'

        out = OUT_DIR / f'{n}.md'
        out.write_text(content, encoding='utf-8')
        print(f'  写入 {out}  ({out.stat().st_size:,} bytes)', flush=True)

    # index.html
    idx = OUT_DIR / 'index.html'
    idx_content = (
        '---\n'
        'layout: calvin-book-modern\n'
        f'book_id: {BOOK_ID}\n'
        'book_name: 使徒行传\n'
        f'chapters: {total}\n'
    )
    if has_preface:
        idx_content += 'has_preface: true\n'
    idx_content += '---\n'
    idx.write_text(idx_content, encoding='utf-8')
    print(f'  写入 {idx}', flush=True)

    print(f'\n✓ 发布完成 → {OUT_DIR}/ (chapters={total})')
    print('质检：')
    print(f'  grep -n "<<<END>>>" {OUT_DIR}/*.md     # 应无结果')
    print(f'  grep -c "^layout: calvin-en" {OUT_DIR}/*.md')


if __name__ == '__main__':
    main()
