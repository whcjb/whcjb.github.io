#!/usr/bin/env python3
"""
publish_2cor_zh.py — 将 2cor 已翻译的中文章节发布到 calvin/2corinthians/

输入：calvin_raw/2cor/zh_chapters/<N>.md  (1..13, 渐进发布)
输出：calvin/2corinthians/<N>.md         (覆盖旧版)

样式对齐 publish_1cor_zh.py：
- layout: calvin-en
- book_id: 2corinthians
- book_name: 哥林多后书·加尔文注释
- 内联 relocate_anchors_in_body + add_verse_anchors_in_body

ch4-13 仍是旧 calvin-chapter 格式，prev/next 链 ch3→ch4 跨格式但 URL 可达。
等 ch4-13 全部重译后再统一改 index.html 为 calvin-book-modern。

用法（项目根目录）：
    python3 scripts/publish_2cor_zh.py
"""
import json
import re
import subprocess
from pathlib import Path

SRC_DIR = Path('calvin_raw/2cor/zh_chapters')
OUT_DIR = Path('calvin/2corinthians')

BOOK_ID   = '2corinthians'
BOOK_NAME = '哥林多后书·加尔文注释'
TOTAL_CHAPTERS = 13   # hardcode；让 next_section 链不断


# ── 和合本经文查找（左列英文换中文，右列保留拉丁文）──
_BIBLE_PATH = Path(__file__).parent / 'zh_cuv.json'
_bible = json.load(open(_BIBLE_PATH, encoding='utf-8-sig'))
_2cor_chapters = next(b for b in _bible if b['abbrev'] == '2co')['chapters']

import opencc as _opencc
_t2s = _opencc.OpenCC('t2s')


def lookup_cuv(ch: int, v: int):
    if ch - 1 >= len(_2cor_chapters):
        return None
    chapter = _2cor_chapters[ch - 1]
    if v - 1 >= len(chapter) or v < 1:
        return None
    return _t2s.convert(chapter[v - 1].replace(' ', ''))


_BOX_RE = re.compile(
    r'(<div class="scripture-box scripture-box--bilingual"[^>]*>\s*'
    r'<p class="scripture-ref">.*?<span class="verse-range">(\d+):\d+(?:-\d+)?</span></p>\s*'
    r'<table class="scripture-bilingual">.*?</table>)',
    re.DOTALL,
)

_TR_RE = re.compile(
    r'<tr><td class="scripture-en">.*?<strong>(\d+)\.</strong>.*?</td>'
    r'(<td class="scripture-la">.*?</td>)</tr>',
    re.DOTALL,
)


def inject_chinese_scripture(body: str) -> str:
    def process_box(m_box):
        full = m_box.group(1)
        ch = int(m_box.group(2))

        def replace_tr(tr_m):
            n_str = tr_m.group(1)
            la_td = tr_m.group(2)
            zh = lookup_cuv(ch, int(n_str))
            if not zh:
                return tr_m.group(0)
            return (f'<tr><td class="scripture-en"><strong>{n_str}.</strong> {zh}</td>'
                    f'{la_td}</tr>')

        return _TR_RE.sub(replace_tr, full)

    return _BOX_RE.sub(process_box, body)


CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
          '十一', '十二', '十三']


def cn_chapter(n) -> str:
    if n == 'preface':
        return '前言'
    return f'第{CN_NUM[n]}章'


def get_date() -> str:
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def strip_frontmatter(text: str) -> str:
    if not text.startswith('---'):
        return text
    m = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
    return text[m.end():] if m else text


def clean_body(body: str) -> str:
    """移除翻译残留 <<<END>>>；剥 scripture-anchor 上 inline display:none；
    清理 abut-bold ****。"""
    lines = body.split('\n')
    cleaned = [l for l in lines if l.strip() != '<<<END>>>'
               and not re.match(r'^\s*<<<END\d*>>>\s*$', l)]
    body = '\n'.join(cleaned)
    body = body.replace('****', '')
    body = re.sub(
        r'(<h2 class="scripture-anchor"[^>]*?) style="display:none"(>)',
        r'\1\2',
        body,
    )
    # front-matter 键名漏译修正（保险，stripped 之后再扫一遍 body 不会动到，
    # 留给 strip_frontmatter 之后的 fm 重建过程兜底）
    return body


def build_frontmatter(n, date: str, has_preface: bool) -> str:
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
        if n < TOTAL_CHAPTERS:
            fm += f'next_section: {n + 1}\n'
            fm += f'next_label: "{cn_chapter(n + 1)}"\n'
    fm += '---\n\n'
    return fm


VERSE_MARK_RE = re.compile(r'^\*\*(\d{1,3})\.\*\*[\s<]')


def add_verse_anchors_in_body(body: str, ch) -> str:
    if not isinstance(ch, int):
        return body
    lines = body.split('\n')
    out = []
    in_box = False
    seen: dict[int, int] = {}
    for raw in lines:
        s = raw.strip()
        if s.startswith('<div class="scripture-box"'):
            in_box = True
            out.append(raw)
            continue
        if in_box:
            if s == '</div>':
                in_box = False
            out.append(raw)
            continue
        m = VERSE_MARK_RE.match(raw)
        if m:
            v = int(m.group(1))
            seen[v] = seen.get(v, 0) + 1
            suffix = '' if seen[v] == 1 else f'-{seen[v]}'
            out.append(f'<div class="commentary-anchor" id="{BOOK_ID}-{ch}-{v}{suffix}"></div>')
        out.append(raw)
    return '\n'.join(out)


def relocate_anchors_in_body(body: str) -> str:
    h2_re = re.compile(
        r'^(<h2 class="scripture-anchor")\s+id="([^"]+)"(.*?)>(.*)$'
    )
    lines = body.split('\n')
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = h2_re.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        pre, aid, post_attrs, h2_tail = m.groups()
        new_h2 = f'{pre}{post_attrs}>{h2_tail}'
        anchor = f'<div class="commentary-anchor" id="{aid}"></div>'

        j = i + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        if j < len(lines) and lines[j].lstrip().startswith('<div class="scripture-box"'):
            k = j + 1
            depth = 1
            while k < len(lines) and depth > 0:
                depth += lines[k].count('<div') - lines[k].count('</div>')
                if depth == 0:
                    break
                k += 1
            if k >= len(lines):
                out.append(lines[i])
                i += 1
                continue
            out.append(new_h2)
            out.extend(lines[i + 1:k + 1])
            out.append(anchor)
            i = k + 1
        else:
            out.append(new_h2)
            out.append(anchor)
            i += 1
    return '\n'.join(out)


def main():
    chapters = sorted(int(p.stem) for p in SRC_DIR.glob('*.md') if p.stem.isdigit())
    has_preface = (SRC_DIR / 'preface.md').exists()
    if not chapters and not has_preface:
        print(f'错误：{SRC_DIR} 下没有可发布章节')
        return
    items = (['preface'] if has_preface else []) + chapters
    print(f'发现已译：preface={has_preface}, chapters={chapters} '
          f'(book total={TOTAL_CHAPTERS})', flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date = get_date()

    for n in items:
        src = SRC_DIR / f'{n}.md'
        raw = src.read_text(encoding='utf-8')
        body = strip_frontmatter(raw)
        body = clean_body(body)
        body = inject_chinese_scripture(body)
        body = relocate_anchors_in_body(body)
        if isinstance(n, int):
            body = add_verse_anchors_in_body(body, n)
        body_lines = body.lstrip('\n').split('\n')
        if body_lines and re.match(r'^#\s+(?:第.+?章|前言|Preface)\s*$', body_lines[0]):
            body_lines.pop(0)
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
        body = '\n'.join(body_lines)

        fm = build_frontmatter(n, date, has_preface)
        content = fm + body.rstrip() + '\n'

        out = OUT_DIR / f'{n}.md'
        out.write_text(content, encoding='utf-8')
        print(f'  写入 {out}  ({out.stat().st_size:,} bytes)', flush=True)

    print(f'\n✓ 发布完成 → {OUT_DIR}/  (本次已发布 {len(items)} 章)')
    print(f'  注：ch4-{TOTAL_CHAPTERS} 仍为旧 calvin-chapter 格式，'
          f'index.html 暂不动；待全书重译后改 calvin-book-modern。')


if __name__ == '__main__':
    main()
