#!/usr/bin/env python3
"""贺智著作英文版发布：`hodge_raw/<book>/hodge_<book>.md` → `hodge/<book>/*.md` + `index.html`。

为什么要有这个脚本
------------------
罗马书 / 林前 / 林后三本上线时，这一步是**临时写在会话里跑完就丢**的，脚本没落盘
（`git log` 里那次提交只改了 extract / structured_to_md / verse-index，没有任何
publish 脚本）。结果是：产物在、规则不在，下一本书要从产物反推分章与脚注归位的
口径。本脚本把那套口径固化下来，并用「重跑罗马书，与已提交产物逐字节比对」做验收。

分章判据
--------
正文里居中的 `CHAPTER <罗马数字>` 段。两本书的字形不同（罗马书 size 20 → 进管道是
`title-block-h2`；以弗所书 size 12 → 只是普通居中段），所以判据看的是**段落文字**
而不是 class：剥掉标签与 `**` 后整段恰好是 `CHAPTER <罗马数字>`（可带句点）。
`VERSES 17-32 — CHAPTER V 1-2` 这类节头因此不会误命中。

罗马数字允许 `l` 冒充 `I`——以弗所书 p240 的第六章在 AGES 源里就印成 `CHAPTER Vl`。

脚注归位
--------
文末 NOTES/FOOTNOTES 区在 `structured_to_md` 阶段已转成 `[^fN]: …` 定义，但它们
全部堆在文档末尾。发布时按「哪一章的正文里出现了 `[^fN]` 引用」把定义搬到那一章
文件末尾；无人引用的定义会报出来（不静默丢弃）。

发布后必跑的四步（顺序固定，少一步就少一样东西，且本脚本每次重跑都会把它们
冲掉，所以每次重发都要照跑一遍）：

    1. python3 scripts/fix_page_split_paragraphs.py hodge/<book>   # Gate 5g，须归零
    2. python3 scripts/fix_hodge_pseudo_blocks.py hodge/<book> --check
    3. python3 scripts/add_hodge_verse_anchors.py --book <book>
    4. python3 scripts/build_hodge_verse_index.py --book <book>

再跑两条「忠于 PDF」的闸（skill 强制，其余 Gate 只验产物内部自洽）：

    python3 scripts/qa_ages_typography.py <pdf> hodge/<book> --skip-head N --skip-tail 2
    python3 scripts/qa_ages_text.py       <pdf> hodge/<book> --skip-head N --skip-tail 2 \
            --fn-section-title NOTES      # 正文相似度须 ≥0.995

用法:
    python3 scripts/publish_hodge_en.py ephesians --name "Hodge on Ephesians"
    python3 scripts/publish_hodge_en.py romans --out-dir /tmp/romans_check   # 回归用
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 中文版放在书首页、英文退到 …/en/ 的书卷（用户 2026-09-30 指定，从以弗所书起）。
# 这一步必须写在发布脚本里：index.html 每次重发都会被重写，
# 不认这个集合的话，一重发就把书首页打回英文，中文入口又没了。
ZH_PRIMARY = {'ephesians'}

# 段落里的章头：剥掉 HTML 标签与 markdown 粗体后整段是 `CHAPTER <罗马数字>`。
# 字符集含 l/O：AGES 数字化时罗马数字里混进字母是老毛病（以弗所书 `CHAPTER Vl`）。
_CHAP_TEXT_RE = re.compile(r'^CHAPTER\s+([IVXLCDMlO]+)\.?$')
_TAG_RE = re.compile(r'<[^>]+>')
_FN_DEF_RE = re.compile(r'^\[\^(f\w+)\]:')

_ROMAN_VAL = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def roman_to_int(s: str):
    """罗马数字转整数；先把 AGES 那两个假字母纠回来（l→I、O→D 从未见过，只处理 l）。"""
    s = s.replace('l', 'I')
    total = prev = 0
    for ch in reversed(s):
        v = _ROMAN_VAL.get(ch)
        if v is None:
            return None
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def para_text(line: str) -> str:
    """取段落的纯文字（剥标签、剥 markdown 粗体、归一空白）。"""
    t = _TAG_RE.sub('', line)
    t = t.replace('**', '').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', t).strip()


def split_chapters(md: str):
    """→ (preface_body, [(chapter_no, body), …], [def_line, …])。"""
    lines = md.split('\n')
    # 1. 先把文末的脚注定义区切出来：从第一条 `[^fN]:` 起到文末。
    #    定义之间只隔空行，不会再夹正文——structured_to_md 已保证。
    first_def = next((i for i, l in enumerate(lines) if _FN_DEF_RE.match(l)), None)
    if first_def is None:
        body_lines, def_lines = lines, []
    else:
        body_lines = lines[:first_def]
        # 定义可能跨多行（长拉丁引文里有空行分段），必须按「下一条定义开始」
        # 分组，不能只挑 `[^fN]:` 那一行——罗马书 84 条定义里有 13 行续行，
        # 只挑首行会把它们整段丢掉。
        def_lines = []
        for l in lines[first_def:]:
            if _FN_DEF_RE.match(l):
                def_lines.append(l)
            elif l.strip() and def_lines:
                def_lines[-1] += '\n' + l
        

    # 2. 按章头切
    marks = []
    for i, l in enumerate(body_lines):
        m = _CHAP_TEXT_RE.match(para_text(l))
        if m and l.lstrip().startswith('<p'):
            n = roman_to_int(m.group(1))
            if n:
                marks.append((i, n, m.group(1)))
    if not marks:
        raise SystemExit('没找到任何章头，分章判据要重看')

    preface = '\n'.join(body_lines[:marks[0][0]])
    chapters = []
    for k, (i, n, raw) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(body_lines)
        chapters.append((n, raw, '\n'.join(body_lines[i:end])))
    return preface, chapters, def_lines


def attach_footnotes(sections, def_lines):
    """把文末定义搬到引用它的那一节。sections: [(key, body), …]，就地返回新 body。"""
    defs = {}
    for l in def_lines:
        m = _FN_DEF_RE.match(l)
        if m:
            defs[m.group(1)] = l
    owner = {}
    for key, body in sections:
        for label in re.findall(r'\[\^(f\w+)\](?!:)', body):
            owner.setdefault(label, key)
    out, used = {}, set()
    for key, body in sections:
        mine = [defs[lab] for lab in defs if owner.get(lab) == key]
        mine.sort(key=lambda l: int(re.sub(r'\D', '', _FN_DEF_RE.match(l).group(1)) or 0))
        used.update(lab for lab in defs if owner.get(lab) == key)
        text = body.rstrip('\n')
        if mine:
            text += '\n\n' + '\n\n\n'.join(mine) + '\n\n'
        out[key] = text + '\n'
    orphan = [lab for lab in defs if lab not in used]
    if orphan:
        print(f'  ⚠ {len(orphan)} 条脚注定义没有任何正文引用，未落地: '
              + ', '.join(sorted(orphan)[:10]), file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book', help='hodge_raw/<book>/ 子目录名，如 ephesians')
    ap.add_argument('--name', help='book_name，默认 "Hodge on <Book>"')
    ap.add_argument('--src', help='源 md，默认 hodge_raw/<book>/hodge_<book>.md')
    ap.add_argument('--out-dir', help='输出目录，默认 hodge/<book>')
    ap.add_argument('--date', help='front matter 的 date（YYYY-MM-DD HH:MM），默认当前时刻')
    ap.add_argument('--name-zh', help='中文 book_name（ZH_PRIMARY 的书卷用在书首页）')
    args = ap.parse_args()

    book = args.book
    src = Path(args.src) if args.src else ROOT / 'hodge_raw' / book / f'hodge_{book}.md'
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / 'hodge' / book
    book_name = args.name or f'Hodge on {book.capitalize()}'
    stamp = args.date or datetime.now().strftime('%Y-%m-%d %H:%M')

    md = src.read_text(encoding='utf-8')
    preface, chapters, def_lines = split_chapters(md)
    print(f'{book}: preface + {len(chapters)} 章，脚注定义 {len(def_lines)} 条')
    seq = [n for n, _, _ in chapters]
    if seq != list(range(1, len(chapters) + 1)):
        print(f'  ⚠ 章号不连续: {seq}', file=sys.stderr)

    sections = [('preface', preface)] + [(str(n), b) for n, _, b in chapters]
    bodies = attach_footnotes(sections, def_lines)

    keys = [k for k, _ in sections]
    labels = {'preface': 'Preface',
              **{str(n): f'Chapter {n}' for n, _, _ in chapters}}
    titles = dict(labels)

    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, key in enumerate(keys):
        fm = ['---', 'layout: hodge-chapter', f'book_id: {book}',
              f'book_name: "{book_name}"', f'title: "{titles[key]}"',
              f'zh_url: "/hodge/{book}/zh/{key}/"', f'date: {stamp}']
        if book in ZH_PRIMARY:
            # 英文章节的「← 书名」要回英文目录页，不能回中文书首页
            fm.append(f'book_home: "/hodge/{book}/en/"')
        if idx > 0:
            prev = keys[idx - 1]
            fm += [f'prev_section: {prev}', f'prev_label: "{labels[prev]}"']
        if idx + 1 < len(keys):
            nxt = keys[idx + 1]
            fm += [f'next_section: {nxt}', f'next_label: "{labels[nxt]}"']
        fm.append('---')
        (out_dir / f'{key}.md').write_text(
            '\n'.join(fm) + '\n\n' + bodies[key], encoding='utf-8')

    def _index(path: Path, name: str, extra: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\n'
                        'layout: hodge-book\n'
                        f'book_id: {book}\n'
                        f'book_name: "{name}"\n'
                        f'chapters: {len(chapters)}\n'
                        'has_preface: true\n'
                        + extra + '---\n', encoding='utf-8')

    if book in ZH_PRIMARY:
        # 书首页 = 中文；英文退到 …/en/
        _index(out_dir / 'index.html', args.name_zh or book_name,
               f'zh: true\nen_index: /hodge/{book}/en/\n')
        _index(out_dir / 'en' / 'index.html', book_name,
               f'zh_index: /hodge/{book}/\n')
    else:
        _index(out_dir / 'index.html', book_name, '')
    print(f'  → {out_dir}/ 共 {len(keys)} 个页面 + index.html')


if __name__ == '__main__':
    sys.exit(main())
