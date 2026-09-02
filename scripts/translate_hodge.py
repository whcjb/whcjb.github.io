#!/usr/bin/env python3
"""贺智《哥林多前后书注释》英译中。

复用 translate_filibi 的 CLI 调用与 md5 缓存（`tf.call_claude` / `tf.cached_translate`）。
CLI 一律带 CLI_TRIM_FLAGS —— 不发工具定义、MCP、CLAUDE.md、skills、hooks，
实测 29,142 → 287 token/次，见 scripts/claude_usage.py。

产物：
  中文页  hodge/<book>/zh/<N>.md    （URL /hodge/<book>/zh/<N>/，不覆盖英文）
  中文raw hodge_raw/<book>/zh/<N>.md（chmod 444）
  缓存    hodge_raw/zh_cache/       （md5 键，入 git，重跑全命中零 token）

用法:
    python3 scripts/translate_hodge.py --book 1corinthians --sections preface,1,2 --publish
    python3 scripts/translate_hodge.py --book 1corinthians --all --resume --publish
"""
import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate_filibi as tf                     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BOOK_CN = {'1corinthians': '哥林多前书', '2corinthians': '哥林多后书'}

# {book_cn} 由 build_system() 按当前书卷填入（前书/后书用词不同，不能写死）。
SYSTEM_TMPL = (
    "你是改革宗神学文献的专业译者，正在翻译查尔斯·贺智（Charles Hodge, "
    "1797-1878，普林斯顿神学院）的《{book_cn}注释》。只输出译文，不要任何说明。\n"
    "\n"
    "★优先级（冲突时一律按此让步）：①意思正确 ②中文读者读得懂 ③文风沉稳。"
    "为求典雅而让读者读不懂，是错译不是好译；宁可用平实说法，也不用现代人"
    "分辨不出的古词。\n"
    "文风：庄重的现代书面语，可略带文言色彩，但以清楚达意为先。忌口语词"
    "（力度/搞/到位/的话）。贺智行文是逐节释义加教义论证，长句多，可按中文"
    "语序拆分重组，但不得增删义。\n"
    "术语：经文、书卷名、人名一律照和合本（{book_cn}/使徒/称义/成圣/预表/"
    "中保/恩典/信心/良心/圣礼）。神学术语按改革宗惯用译法。\n"
    "\n"
    "【必须原样保留、不得翻译或改写的部分】\n"
    "1. 所有 HTML 标签与属性，如 <p ...>、<span style=\"color:#800000\">、"
    "</span>、markdown=\"1\"、class=\"enum-num\"。\n"
    "2. markdown 标记：**加粗**、*斜体*、行首的 <span class=\"enum-num\">N.</span>。\n"
    "3. 脚注标记 [^f12]、页界注释 <!-- PAGE 51 -->。\n"
    "4. 希腊文、希伯来文原文原样保留，不音译不意译；其后若有英文释义则译出。\n"
    "5. 圣经引用的书卷章节号（1 Corinthians 3:5 → 哥林多前书 3:5，"
    "2 Corinthians 3:5 → 哥林多后书 3:5）。\n"
    "\n"
    "红色 span 里是英文钦定本经文，按和合本语感译成庄重的经文体，仍留在原 span 内。"
)


def build_system(book: str) -> str:
    return SYSTEM_TMPL.replace('{book_cn}', BOOK_CN.get(book, book))


def split_page(text: str):
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    return (m.group(1), m.group(2)) if m else ('', text)


def translatable(line: str) -> bool:
    """哪些行需要送翻。"""
    s = line.strip()
    if not s or s.startswith('<!--'):
        return False
    if re.fullmatch(r'-{3,}|<p[^>]*>|</p>', s):
        return False
    # 纯希腊文/纯符号行不送翻
    if not re.search(r'[A-Za-z]{3}', s):
        return False
    return True


def translate_section(book: str, sec: str, resume: bool, publish: bool):
    src = ROOT / 'hodge' / book / f'{sec}.md'
    if not src.exists():
        print(f'  {src} 不存在，跳过', flush=True)
        return
    fm, body = split_page(src.read_text(encoding='utf-8'))
    lines = body.split('\n')
    idxs = [i for i, l in enumerate(lines) if translatable(l)]
    print(f'{book}/{sec}: {len(idxs)} 个可译单元', flush=True)

    zh_lines = tf.cached_translate([lines[i] for i in idxs], resume)
    out = list(lines)
    for i, zh in zip(idxs, zh_lines):
        out[i] = re.sub(r'<<<[^>]*>>>', '', zh).strip()

    def fv(k, default=''):
        m = re.search(rf'^{k}:\s*(.+)$', fm, re.M)
        return m.group(1).strip().strip('"') if m else default

    zh_dir = ROOT / 'hodge' / book / 'zh'
    zh_out = zh_dir / f'{sec}.md'
    # 时间戳用**本次翻译完成的真实时间**；已发布页重跑沿用原值
    date = ''
    if zh_out.exists():
        m = re.search(r'^date:\s*(.+)$', zh_out.read_text(encoding='utf-8'), re.M)
        date = m.group(1).strip() if m else ''
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M')

    title = fv('title')
    m = re.match(r'Chapter (\d+)', title)
    zh_title = f'第 {m.group(1)} 章' if m else ('导论' if sec == 'preface' else title)
    nav = ''
    for k, label in (('prev_section', 'prev_label'), ('next_section', 'next_label')):
        v = fv(k)
        if v:
            lb = fv(label)
            mm = re.match(r'Chapter (\d+)', lb)
            nav += f'{k}: {v}\n{label}: "{"第 " + mm.group(1) + " 章" if mm else lb}"\n'

    zh_fm = ('---\n'
             'layout: hodge-chapter\n'
             f'book_id: {book}\n'
             f'book_name: "贺智《{BOOK_CN.get(book, book)}注释》"\n'
             f'title: "{zh_title}"\n'
             f'date: {date}\n'
             + nav
             + f'en_url: "/hodge/{book}/{sec}/"\n'
             'zh: true\n'
             '---\n')
    page = zh_fm + '\n'.join(out)

    raw_dir = ROOT / 'hodge_raw' / book / 'zh'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f'{sec}.md'
    if raw.exists():
        raw.chmod(0o644)
    raw.write_text(page, encoding='utf-8')
    raw.chmod(0o444)
    hit = sum(1 for i in idxs
              if (tf.CACHE_DIR / f'{tf.md5key(lines[i])}.txt').exists())
    print(f'  缓存命中 {hit} / {len(idxs)}', flush=True)

    if publish:
        zh_dir.mkdir(parents=True, exist_ok=True)
        zh_out.write_text(page, encoding='utf-8')
        print(f'✓ 中文页 → {zh_out}', flush=True)
        # 英文页回填 zh_url（切换用）
        t = src.read_text(encoding='utf-8')
        if 'zh_url:' not in t:
            t = t.replace('\ndate:', f'\nzh_url: "/hodge/{book}/zh/{sec}/"\ndate:', 1)
            src.write_text(t, encoding='utf-8')
            print('✓ 英文页回填 zh_url', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='1corinthians')
    ap.add_argument('--sections', help='逗号分隔，如 preface,1,2')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    a = ap.parse_args()

    tf.SYSTEM = build_system(a.book)
    tf.CACHE_DIR = ROOT / 'hodge_raw' / 'zh_cache'
    tf.BATCH = 1

    if a.all:
        secs = ['preface'] + [p.stem for p in sorted(
            (ROOT / 'hodge' / a.book).glob('[0-9]*.md'), key=lambda x: int(x.stem))]
    else:
        secs = [s.strip() for s in (a.sections or '').split(',') if s.strip()]
    if not secs:
        print('需要 --sections 或 --all', file=sys.stderr)
        return 1
    for s in secs:
        translate_section(a.book, s, a.resume, a.publish)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except tf.SessionLimitError as e:
        print(f'\n!! 会话额度用尽，停止：{e}', flush=True)
        print('   已翻段落都在 zh_cache 里，恢复后 --resume 直接续。', flush=True)
        sys.exit(42)
