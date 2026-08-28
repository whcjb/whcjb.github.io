#!/usr/bin/env python3
"""扫描各注释家目录，生成「历代解经」版面的数据文件 _data/commentaries.yml。

版面按**书卷**组织：每卷列出有哪几位注释家注过，点胶囊跳到该注释家现有的
页面。现有的 calvin/ mhenry/ bridges/ owen/ 各自的页面一概不动，这里只做
入口聚合。

新增注释家：往 AUTHORS 加一条，注明目录前缀与目录命名规则即可。
新增书卷：BOOKS 是和合本 66 卷全表，一般不用动。

分卷与合参的处理：
- 一位注释家把一卷书拆成多册（如加尔文的 isaiah-1/2、jeremiah-1/2、
  psalms-1/2），聚合成同一卷下的一个入口，链到第一册；
- 合参类（harmony-1/2/3 共观福音、harmony-law-1..4 摩西五经）不对应单一
  书卷，单列成「合参」组；
- *-en 是英文版目录，跳过；*-index 是索引页，不是正文。

用法: python3 scripts/build_commentaries_index.py
"""
import re
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 注释家：生卒年皆为确凿史实，勿凭印象改
# short 是卡片色块里的简称：一卷若有三位注释家，每格只剩 50 余像素，
# 全名放不下会被截断
AUTHORS = OrderedDict([
    ('calvin',  dict(name='约翰·加尔文', short='加尔文',  en='John Calvin',     years='1509–1564', dir='calvin')),
    ('owen',    dict(name='约翰·欧文',   short='欧文',    en='John Owen',       years='1616–1683', dir='owen')),
    ('mhenry',  dict(name='马太·亨利',   short='亨利',    en='Matthew Henry',   years='1662–1714', dir='mhenry')),
    ('bridges', dict(name='查理·毕列志', short='毕列志',  en='Charles Bridges', years='1794–1869', dir='bridges')),
])

# 和合本 66 卷：(目录 id, 中文名, 新旧约, 英文名)
# 英文名显示在卡片上（照加尔文主页的做法：中文名下缀一行英文）
BOOKS = [
    ('genesis','创世记','ot','Genesis'), ('exodus','出埃及记','ot','Exodus'), ('leviticus','利未记','ot','Leviticus'),
    ('numbers','民数记','ot','Numbers'), ('deuteronomy','申命记','ot','Deuteronomy'), ('joshua','约书亚记','ot','Joshua'),
    ('judges','士师记','ot','Judges'), ('ruth','路得记','ot','Ruth'), ('1samuel','撒母耳记上','ot','1 Samuel'),
    ('2samuel','撒母耳记下','ot','2 Samuel'), ('1kings','列王纪上','ot','1 Kings'), ('2kings','列王纪下','ot','2 Kings'),
    ('1chronicles','历代志上','ot','1 Chronicles'), ('2chronicles','历代志下','ot','2 Chronicles'), ('ezra','以斯拉记','ot','Ezra'),
    ('nehemiah','尼希米记','ot','Nehemiah'), ('esther','以斯帖记','ot','Esther'), ('job','约伯记','ot','Job'),
    ('psalms','诗篇','ot','Psalms'), ('proverbs','箴言','ot','Proverbs'), ('ecclesiastes','传道书','ot','Ecclesiastes'),
    ('songofsolomon','雅歌','ot','Song of Solomon'), ('isaiah','以赛亚书','ot','Isaiah'), ('jeremiah','耶利米书','ot','Jeremiah'),
    ('lamentations','耶利米哀歌','ot','Lamentations'), ('ezekiel','以西结书','ot','Ezekiel'), ('daniel','但以理书','ot','Daniel'),
    ('hosea','何西阿书','ot','Hosea'), ('joel','约珥书','ot','Joel'), ('amos','阿摩司书','ot','Amos'),
    ('obadiah','俄巴底亚书','ot','Obadiah'), ('jonah','约拿书','ot','Jonah'), ('micah','弥迦书','ot','Micah'),
    ('nahum','那鸿书','ot','Nahum'), ('habakkuk','哈巴谷书','ot','Habakkuk'), ('zephaniah','西番雅书','ot','Zephaniah'),
    ('haggai','哈该书','ot','Haggai'), ('zechariah','撒迦利亚书','ot','Zechariah'), ('malachi','玛拉基书','ot','Malachi'),
    ('matthew','马太福音','nt','Matthew'), ('mark','马可福音','nt','Mark'), ('luke','路加福音','nt','Luke'),
    ('john','约翰福音','nt','John'), ('acts','使徒行传','nt','Acts'), ('romans','罗马书','nt','Romans'),
    ('1corinthians','哥林多前书','nt','1 Corinthians'), ('2corinthians','哥林多后书','nt','2 Corinthians'),
    ('galatians','加拉太书','nt','Galatians'), ('ephesians','以弗所书','nt','Ephesians'), ('philippians','腓立比书','nt','Philippians'),
    ('colossians','歌罗西书','nt','Colossians'), ('1thessalonians','帖撒罗尼迦前书','nt','1 Thessalonians'),
    ('2thessalonians','帖撒罗尼迦后书','nt','2 Thessalonians'), ('1timothy','提摩太前书','nt','1 Timothy'),
    ('2timothy','提摩太后书','nt','2 Timothy'), ('titus','提多书','nt','Titus'), ('philemon','腓利门书','nt','Philemon'),
    ('hebrews','希伯来书','nt','Hebrews'), ('james','雅各书','nt','James'), ('1peter','彼得前书','nt','1 Peter'),
    ('2peter','彼得后书','nt','2 Peter'), ('1john','约翰一书','nt','1 John'), ('2john','约翰二书','nt','2 John'),
    ('3john','约翰三书','nt','3 John'), ('jude','犹大书','nt','Jude'), ('revelation','启示录','nt','Revelation'),
]

# 合参：不对应单一书卷，单列一组
HARMONY = [
    ('calvin', 'harmony-1', '共观福音合参（卷一）'),
    ('calvin', 'harmony-2', '共观福音合参（卷二）'),
    ('calvin', 'harmony-3', '共观福音合参（卷三）'),
    ('calvin', 'harmony-law-1', '摩西五经合参（卷一）'),
    ('calvin', 'harmony-law-2', '摩西五经合参（卷二）'),
    ('calvin', 'harmony-law-3', '摩西五经合参（卷三）'),
    ('calvin', 'harmony-law-4', '摩西五经合参（卷四）'),
]

SKIP = re.compile(r'-en$|-index$')


def has_content(d: Path) -> bool:
    """目录里得有实际章节，光有 index.html 的空壳不算。

    两种章节组织都要认：
      calvin / mhenry / bridges → 每章一个 .md（1.md、preface.md）
      owen                      → 每章一个子目录（owen/hebrews/1/）
    只认 .md 的话欧文会被判成空目录、整卷漏掉。
    """
    if not d.is_dir():
        return False
    if any(p.stem.isdigit() or p.stem == 'preface' for p in d.glob('*.md')):
        return True
    return any(p.is_dir() and (p.name.isdigit() or p.name == 'preface')
               for p in d.iterdir())


def scan(author_id: str) -> dict:
    """返回 {book_id: 该注释家该卷的入口路径}。分卷聚合到第一册。"""
    base = ROOT / AUTHORS[author_id]['dir']
    if not base.is_dir():
        return {}
    found = {}
    for d in sorted(base.iterdir()):
        if not d.is_dir() or SKIP.search(d.name) or not has_content(d):
            continue
        # 分卷：isaiah-1 / psalms-2 → 归到 isaiah / psalms，取序号最小的那册
        m = re.match(r'^(.+)-(\d+)$', d.name)
        if m and not d.name.startswith('harmony'):
            book, vol = m.group(1), int(m.group(2))
        else:
            book, vol = d.name, 0
        if book.startswith('harmony'):
            continue
        if book not in found or vol < found[book][0]:
            found[book] = (vol, f'/{AUTHORS[author_id]["dir"]}/{d.name}/')
    return {k: v[1] for k, v in found.items()}


def yaml_escape(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    by_author = {a: scan(a) for a in AUTHORS}

    lines = ['# 由 scripts/build_commentaries_index.py 生成，勿手改。',
             '# 新增注释家改脚本里的 AUTHORS，新增书卷改 BOOKS，然后重跑。',
             '', 'authors:']
    for aid, a in AUTHORS.items():
        n = len(by_author[aid])
        lines += [f'  - id: {aid}',
                  f'    name: {yaml_escape(a["name"])}',
                  f'    short: {yaml_escape(a["short"])}',
                  f'    en: {yaml_escape(a["en"])}',
                  f'    years: {yaml_escape(a["years"])}',
                  f'    books: {n}']
    lines += ['', 'books:']
    total_links = 0
    for bid, cn, testament, en in BOOKS:
        entries = [(aid, by_author[aid][bid]) for aid in AUTHORS if bid in by_author[aid]]
        if not entries:
            continue
        total_links += len(entries)
        lines += [f'  - id: {bid}',
                  f'    name: {yaml_escape(cn)}',
                  f'    en: {yaml_escape(en)}',
                  f'    testament: {testament}',
                  '    links:']
        for aid, path in entries:
            lines.append(f'      - {{author: {aid}, path: {yaml_escape(path)}}}')
    lines += ['', 'harmony:']
    for aid, dirname, cn in HARMONY:
        d = ROOT / AUTHORS[aid]['dir'] / dirname
        if not has_content(d):
            continue
        total_links += 1
        path = '/' + AUTHORS[aid]['dir'] + '/' + dirname + '/'
        lines += [f'  - name: {yaml_escape(cn)}',
                  f'    author: {aid}',
                  f'    path: {yaml_escape(path)}']

    out = ROOT / '_data' / 'commentaries.yml'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    covered = sum(1 for bid, _, _, _ in BOOKS if any(bid in by_author[a] for a in AUTHORS))
    print(f'✓ {out.relative_to(ROOT)}')
    for aid in AUTHORS:
        print(f'    {AUTHORS[aid]["name"]:<12} {len(by_author[aid]):>2} 卷')
    print(f'    覆盖 {covered}/66 卷，共 {total_links} 个入口')


if __name__ == '__main__':
    main()
