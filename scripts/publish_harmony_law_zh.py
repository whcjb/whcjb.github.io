#!/usr/bin/env python3
"""把 calvin_raw/harmony-law-{V}/zh_chapters/N.md 发布到 calvin/harmony-law-{V}/N.md。

- front matter 本地化: book_id -en 去掉、book_name→中文卷名、
  title/prev_label/next_label 英文标题→中文(EXODUS→出埃及记 / 诫命名 等)
- clean: 剥 <<<END>>>、"前往出埃及记"补空格、去 scripture-anchor 上 display:none
- 增量: 只发布已有 raw 的章; prev/next 只链到已发布章(避免 404)
- index.html: calvin-book-modern, chapters=已发布数
用法: python3 scripts/publish_harmony_law_zh.py [--vol 1]
"""
import re, argparse, datetime
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')

CN_BOOK = {'GENESIS': '创世记', 'EXODUS': '出埃及记', 'LEVITICUS': '利未记',
           'NUMBERS': '民数记', 'DEUTERONOMY': '申命记'}
CN_ORD = {'FIRST': '第一', 'SECOND': '第二', 'THIRD': '第三', 'FOURTH': '第四',
          'FIFTH': '第五', 'SIXTH': '第六', 'SEVENTH': '第七', 'EIGHTH': '第八',
          'NINTH': '第九', 'TENTH': '第十'}
CN_SPECIAL = {
    'Preface': '序言', 'TABLES OF SCRIPTURE': '经文汇编',
    'THE SONG OF MOSES': '摩西之歌', 'RETURN TO THE HISTORY': '回到历史叙事',
    'THE SUM OF THE LAW': '律法的总义', 'THE USE OF THE LAW': '律法的功用',
    'SANCTIONS OF THE LAW': '律法的赏罚', 'PREFACE TO THE LAW': '律法序言',
    'EXPOSITION OF THE SECOND COMMANDMENT': '第二诫的阐释',
}


def localize_title(t: str) -> str:
    t = t.strip()
    if t in CN_SPECIAL:
        return CN_SPECIAL[t]
    m = re.match(r'^(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)?\s*'
                 r'THE\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+COMMANDMENT$', t)
    m2 = re.match(r'^THE\s+(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)\s+COMMANDMENT$', t)
    if m2:
        return CN_ORD[m2.group(1)] + '诫'
    if t.startswith('TENTH COMMANDMENT'):
        return '第十诫'
    # 书卷章节, 如 "EXODUS 1" / "DEUTERONOMY 30:11-14"
    mb = re.match(r'^([A-Z]+)\s+([\d:,\-\s]+)$', t)
    if mb and mb.group(1) in CN_BOOK:
        return f'{CN_BOOK[mb.group(1)]} {mb.group(2).strip()}'
    return t  # 兜底保留原文


def clean_body(body: str) -> str:
    body = re.sub(r'<<<[^>]*?>>>', '', body)          # 剥 <<<END>>>/<<<END1>>>/<<</1>>> 等变体(含行内)
    body = body.replace('前往出埃及记', '前往 出埃及记')
    body = body.replace('前往申命记', '前往 申命记')
    body = body.replace('前往利未记', '前往 利未记')
    body = body.replace('前往民数记', '前往 民数记')
    body = re.sub(r'(<h2 class="scripture-anchor"[^>]*?) style="display:none"(>)', r'\1\2', body)
    # 合参注释头 → 完整「书卷 章:节」引用(05-publish-zh §1b)
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from add_verse_refs_harmony import transform as _add_verse_refs
    body, _, _ = _add_verse_refs(body)
    return body


def parse_fm(text):
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', text, re.DOTALL)
    fm = {}
    for line in m.group(1).split('\n'):
        km = re.match(r'^(\w+):\s*(.*)$', line)
        if km:
            fm[km.group(1)] = km.group(2).strip().strip('"')
    return fm, m.group(2)


def publish(vol: int):
    src_dir = ROOT / f'calvin_raw/harmony-law-{vol}/zh_chapters'
    out_dir = ROOT / f'calvin/harmony-law-{vol}'
    out_dir.mkdir(parents=True, exist_ok=True)
    book_id = f'harmony-law-{vol}'
    cn_vol = {1: '卷一', 2: '卷二', 3: '卷三', 4: '卷四'}[vol]
    book_name = f'摩西五经合参（{cn_vol}）'

    present = set()
    for f in src_dir.glob('*.md'):
        s = f.stem
        present.add(0 if s == 'preface' else int(s)) if (s == 'preface' or s.isdigit()) else None

    # 收集各章英文标题(本地化用)
    titles = {}
    for f in src_dir.glob('*.md'):
        s = f.stem
        fm, _ = parse_fm(f.read_text(encoding='utf-8'))
        key = 0 if s == 'preface' else (int(s) if s.isdigit() else None)
        if key is not None:
            titles[key] = localize_title(fm.get('title', s))

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    chapters = sorted(k for k in present if k != 0)
    published = 0
    for f in sorted(src_dir.glob('*.md')):
        s = f.stem
        if s != 'preface' and not s.isdigit():
            continue
        n = 0 if s == 'preface' else int(s)
        fm, body = parse_fm(f.read_text(encoding='utf-8'))
        body = clean_body(body)
        title = titles.get(n, localize_title(fm.get('title', s)))
        # front matter
        out = ['---', 'layout: calvin-en', f'book_id: {book_id}',
               f'book_name: "{book_name}"', f'title: "{title}"', f'date: {now}']
        if n == 0:
            if chapters:
                out += [f'next_section: {chapters[0]}', f'next_label: "{titles.get(chapters[0], "")}"']
        else:
            # prev: 前一已发布章(或 preface)
            prevs = [c for c in chapters if c < n]
            if prevs:
                out += [f'prev_section: {prevs[-1]}', f'prev_label: "{titles.get(prevs[-1], "")}"']
            elif 0 in present:
                out += ['prev_section: preface', 'prev_label: "序言"']
            nexts = [c for c in chapters if c > n]
            if nexts:
                out += [f'next_section: {nexts[0]}', f'next_label: "{titles.get(nexts[0], "")}"']
        out.append('---')
        (out_dir / f'{s}.md').write_text('\n'.join(out) + '\n\n' + body.lstrip('\n'), encoding='utf-8')
        published += 1
        print(f'  写入 {out_dir.name}/{s}.md  «{title}»')

    # index.html
    idx = out_dir / 'index.html'
    has_pref = 0 in present
    idx.write_text(
        f'---\nlayout: calvin-book-modern\nbook_id: {book_id}\n'
        f'book_name: {book_name}\nchapters: {chapters[-1] if chapters else 0}\n'
        f'has_preface: {"true" if has_pref else "false"}\n---\n', encoding='utf-8')
    print(f'✓ 发布 {published} 个文件 → {out_dir}/ (chapters={chapters[-1] if chapters else 0}, 已译章={chapters})')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, default=1)
    a = ap.parse_args()
    publish(a.vol)
