#!/usr/bin/env python3
"""
publish_filibi_zh.py — 将中文翻译 MD 发布为腓立比书中文注释网页

读取 ocr_output/phil/calvin_filibi_zh.md，按章节切分，
转换 Markdown 经文表格为 HTML，写入 calvin/philippians/，
使用与英文版相同的 calvin-en layout。

用法（从项目根目录）：
    python3 scripts/publish_filibi_zh.py
"""
import re, os, subprocess
from pathlib import Path

MD_PATH = Path('ocr_output/phil/calvin_filibi_zh.md')
OUT_DIR = Path('calvin/philippians')

BOOK_ID   = 'philippians'
BOOK_NAME = '腓立比书·加尔文注释'

# ── 章节边界（对应翻译后MD的行号，与英文原文相同）────────────────────────────
# 用 `grep -n "^# " ocr_output/phil/calvin_filibi_zh.md` 验证
SECTIONS = {
    'preface': (0,    223),
    '1':       (223,  523),   # lines[223:523] → 第一章标题(idx 223)..idx 522
    '2':       (523,  918),   # lines[523:918] → 第二章标题(idx 523)..idx 917（排除第三章标题 idx 918）
    '3':       (918,  1219),  # lines[918:1219] → 第三章标题(idx 918)..idx 1218（排除第四章标题 idx 1219）
    '4':       (1219, 1457),  # lines[1219:1457] → 第四章标题(idx 1219)..idx 1456（排除 # FOOTNOTES idx 1457）
}
FN_SECTIONS = {
    'preface': (1458, 1536),
    '1':       (1536, 1782),
    '2':       (1782, 2010),
    '3':       (2010, 2157),
    '4':       (2157, None),   # None → 到文件末尾
}

LABELS = {
    'preface': '前言',
    '1': '第一章',
    '2': '第二章',
    '3': '第三章',
    '4': '第四章',
}

ALL_KEYS = ['preface', '1', '2', '3', '4']
CH_KEYS  = ['1', '2', '3', '4']


def get_date() -> str:
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def md_table_to_html(body: str) -> str:
    """
    将 Markdown 经文表格转换为 HTML，带 colspan 合并表头。

    输入格式：
        | **腓立比书 1:1-6** | |
        |---|---|
        | 1 . 中文 | 1 . Latin |

    输出格式：
        <table class="calvin-scripture">
        <thead><tr><th colspan="2" style="text-align:center">腓立比书 1:1-6</th></tr></thead>
        <tbody>
        <tr><td>1 . 中文</td><td>1 . Latin</td></tr>
        </tbody>
        </table>
    """
    lines = body.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 检测表格标题行：| **...** | |
        m = re.match(r'^\| \*\*(.+?)\*\* \| \|$', line.strip())
        if m:
            title = m.group(1)
            # 跳过 |---|---| 分隔行
            rows = []
            i += 1
            if i < len(lines) and re.match(r'^\|[-| :]+\|$', lines[i].strip()):
                i += 1
            # 收集内容行
            while i < len(lines):
                row_m = re.match(r'^\| (.+?) \| (.+?) \|$', lines[i].strip())
                if row_m:
                    rows.append((row_m.group(1), row_m.group(2)))
                    i += 1
                else:
                    break
            # 输出 HTML 表格
            out.append('<table class="calvin-scripture">')
            out.append(f'<thead><tr><th colspan="2" style="text-align:center">{title}</th></tr></thead>')
            out.append('<tbody>')
            for left, right in rows:
                # 转义竖线（非表格分隔符的竖线）
                left  = left.replace('\\|', '|')
                right = right.replace('\\|', '|')
                out.append(f'<tr><td>{left}</td><td>{right}</td></tr>')
            out.append('</tbody>')
            out.append('</table>')
            continue
        out.append(line)
        i += 1
    return '\n'.join(out)


def filter_fn(lines_slice) -> str:
    """过滤脚注区的 ## 分节标题（PDF 组织标记，不应出现在网页上）"""
    return ''.join(l for l in lines_slice if not re.match(r'^## ', l))


def build_frontmatter(key: str, date: str) -> str:
    idx = ALL_KEYS.index(key)
    prev_k = ALL_KEYS[idx - 1] if idx > 0 else ''
    next_k = ALL_KEYS[idx + 1] if idx < len(ALL_KEYS) - 1 else ''

    fm = '---\n'
    fm += 'layout: calvin-en\n'
    fm += f'book_id: {BOOK_ID}\n'
    fm += f'book_name: "{BOOK_NAME}"\n'
    fm += f'title: "{LABELS[key]}"\n'
    fm += f'date: {date}\n'
    if prev_k:
        fm += f'prev_section: {prev_k}\n'
        fm += f'prev_label: "{LABELS[prev_k]}"\n'
    if next_k:
        fm += f'next_section: {next_k}\n'
        fm += f'next_label: "{LABELS[next_k]}"\n'
    fm += '---\n\n'
    return fm


def main():
    if not MD_PATH.exists():
        print(f'错误：找不到 {MD_PATH}')
        print('请先运行：python3 scripts/translate_filibi.py --resume')
        return

    print(f'读取 {MD_PATH} ...', flush=True)
    with open(MD_PATH, encoding='utf-8') as f:
        all_lines = f.readlines()

    total = len(all_lines)
    print(f'共 {total} 行', flush=True)

    date = get_date()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for key in ALL_KEYS:
        body_start, body_end = SECTIONS[key]
        fn_start, fn_end = FN_SECTIONS[key]
        fn_end = fn_end if fn_end is not None else total

        body_raw = ''.join(all_lines[body_start:body_end])
        fn_raw   = all_lines[fn_start:fn_end]

        # 转换 Markdown 表格 → HTML
        body = md_table_to_html(body_raw)
        # 过滤脚注区分节标题
        fn = filter_fn(fn_raw)

        fm = build_frontmatter(key, date)
        content = fm + body.rstrip() + '\n\n---\n\n' + fn.rstrip() + '\n'

        out_path = OUT_DIR / f'{key}.md'
        out_path.write_text(content, encoding='utf-8')
        print(f'  写入 {out_path}  ({out_path.stat().st_size:,} bytes)', flush=True)

    # index.html
    idx_path = OUT_DIR / 'index.html'
    idx_path.write_text(
        f'---\nlayout: calvin-zh-book\n'
        f'book_id: {BOOK_ID}\n'
        f'book_name: "{BOOK_NAME}"\n'
        f'chapters: {len(CH_KEYS)}\n'
        f'---\n',
        encoding='utf-8'
    )
    print(f'  写入 {idx_path}', flush=True)

    print(f'\n✓ 发布完成 → {OUT_DIR}/')
    print('发布质检（运行以下命令）：')
    print(f'  grep -c "^# " {OUT_DIR}/*.md          # 每个文件应 ≤1')
    print(f'  grep -n "^| [0-9]" {OUT_DIR}/*.md      # 应无结果（表格已转HTML）')
    print(f'  grep -n "^## " {OUT_DIR}/*.md           # 应无结果')


if __name__ == '__main__':
    main()
