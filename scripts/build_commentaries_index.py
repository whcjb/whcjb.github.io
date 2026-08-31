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
# work_cn 用站内既有的称呼（各家自己首页的 title）；
# work_en 用**该著作的真实书名**，不是站内导航文案：
#   毕列志   An Exposition of the Book of Proverbs（1846）
#   马太亨利 An Exposition of the Old and New Testaments（1708–1710）
#   约翰欧文 An Exposition of the Epistle to the Hebrews
#   加尔文   各卷独立，站内英文页用的是 AGES 版书名 "Calvin on <卷>"，
#            那是本站所据版本的实际书名，故按卷生成（work_en 留空表示按卷取）
# 曾误用首页资源卡片的副标题（"Charles Bridges · Proverbs"）——那是导航
# 文案不是书名，被用户指出。
AUTHORS = OrderedDict([
    ('calvin',  dict(name='约翰·加尔文', short='加尔文',  en='John Calvin',     years='1509–1564', dir='calvin',
                     work_cn='加尔文圣经注释',        work_en='')),
    ('owen',    dict(name='约翰·欧文',   short='欧文',    en='John Owen',       years='1616–1683', dir='owen',
                     work_cn='约翰欧文·希伯来书注释',
                     work_en='An Exposition of the Epistle to the Hebrews')),
    ('mhenry',  dict(name='马太·亨利',   short='亨利',    en='Matthew Henry',   years='1662–1714', dir='mhenry',
                     work_cn='马太亨利圣经注释',
                     work_en='An Exposition of the Old and New Testaments')),
    ('bridges', dict(name='查理·毕列志', short='毕列志',  en='Charles Bridges', years='1794–1869', dir='bridges',
                     work_cn='箴言书注释',
                     work_en='An Exposition of the Book of Proverbs')),
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

# 加尔文有两套合参，都不按单卷成书，所以相关书卷名下的加尔文入口一律指向
# 各自的合参索引页，由那里再进具体章节：
#   共观福音合参 → 马太／马可／路加
#   摩西五经合参 → 出／利／民／申（创世记他另有单独注释，不在此列）
# 英文书名照各自 AGES 版实际所题：共观那套带 Calvin，五经那套不带。
# ── 分卷 ────────────────────────────────────────────────────
# 加尔文有几部书拆成多册。以前只链到卷一、标一句「（全二卷）」，等于把卷二
# 藏了起来——用户要求逐卷罗列并写明各卷多少章。
#
# 下面每一项 = (目录, 中文卷名, 英文卷名, 首章, 末章)。
# 中文名取各册 index.html 的 book_name，英文名取对应 *-en 的 book_name
# （AGES 版实际书名，如 "Calvin on Psalms (Vol. 1)"），章号范围由目录下的
# N.md 实际编号统计，全部是查出来的，不要凭印象填。
#
# 注意两类分卷的章号含义不同：
#   诗篇/以赛亚/耶利米 —— N.md 就是该卷书的篇/章号，所以卷二从 79 / 38 / 24 起；
# 合参（共观福音、摩西五经合参）**不在此表**：它们的册是按合参体例编的，
# 与被注释书卷不对应，入口一律落在合参索引页，由那页按经文检索。
VOLUMES = {
    'psalms': [('psalms-1',  '诗篇注释（卷一）', 'Calvin on Psalms (Vol. 1)',  1,  78),
               ('psalms-2',  '诗篇注释（卷二）', 'Calvin on Psalms (Vol. 2)', 79, 150)],
    'isaiah': [('isaiah-1',  '以赛亚书注释（卷一）', 'Calvin on Isaiah (Vol. 1)',  1, 37),
               ('isaiah-2',  '以赛亚书注释（卷二）', 'Calvin on Isaiah (Vol. 2)', 38, 66)],
    'jeremiah': [('jeremiah-1', '耶利米书注释（卷一）', 'Calvin on Jeremiah (Vol. 1)',  1, 23),
                 ('jeremiah-2', '耶利米书注释（卷二）', 'Calvin on Jeremiah (Vol. 2)', 24, 52)],
}

# ── 书脊布面色 ──────────────────────────────
# 12 色按 CIELAB 均匀排布：色相 30° 均分一圈，彩度锁在 C<=19（再高就艳，丢掉
# 旧书布面的沉着），明度在 L*26 / L*38 之间交替——同一明度下 30° 的色相差只
# 有约 dE 11，靠明度错开才拉得到最小 dE 15.5。
# 上一组是凭感觉挑的，「靛灰 #3a4a5a」与「石板灰 #2f3b46」dE 仅 7.2、「藏青」
# 与「紫灰」9.7——低于 12 肉眼认不出是两个色。用户反映这几个色「没看到在哪」，
# 其实都在，只是糊成了一片蓝灰。
CLOTH = ['#59323a', '#775047', '#503923', '#605a3b', '#344226', '#3d614d',
         '#0c4541', '#28616c', '#144258', '#4b5978', '#443854', '#705065']
#         酒红      栗褐      深褐      橄榄      苔绿      墨绿
#         深青      靛青      藏青      石板蓝    紫灰      梅紫

# 上色次序是离线退火搜出来的，不是按公式取模。取模公式必然带周期，排到墙上
# 就是看得见的花纹：i*4 出过「酒红 苔绿 藏青」三色循环三遍；i*5 虽能出满 12 色，
# 但恰好排成 12 列时正下方撞色。退火的优化目标是：12 色全用上、相邻及近距离
# 不同色、8 至 20 列的任何视口宽度下正下方尽量不撞、且不出现重复的二连三连
# 片段（重复片段比单点撞色更显眼）。长度按两架的书卷数定，不够时按长度取模。
CLOTH_ORDER = {
    'ot': [10, 4, 1, 11, 8, 4, 2, 10, 1, 9, 5, 8, 7, 2, 6, 9, 0, 5, 7, 3, 6, 11, 7, 0, 10, 6, 3, 11, 0, 1, 4, 10, 3, 8, 1, 2, 9, 4, 5],
    'nt': [3, 1, 10, 7, 6, 9, 0, 3, 8, 10, 11, 9, 5, 0, 4, 8, 2, 11, 6, 5, 4, 3, 2, 10, 1, 6, 7],
}

# 合参覆盖的书卷 → (入口路径, 中文书名, 英文书名)
# 中文名取站内既有写法，勿另造：
#   calvin/harmony-index/index.html      title: 共观福音注释
#   calvin/harmony-law-index/index.html  title: 摩西五经合参
# 分册页也印证：harmony-1 = 「共观福音（卷一）」，harmony-law-1 = 「摩西五经合参（卷一）」
HARMONY_MAP = {
    'matthew':     ('/calvin/harmony-index/',     '共观福音注释', 'Calvin on the Harmony of the Evangelists'),
    'mark':        ('/calvin/harmony-index/',     '共观福音注释', 'Calvin on the Harmony of the Evangelists'),
    'luke':        ('/calvin/harmony-index/',     '共观福音注释', 'Calvin on the Harmony of the Evangelists'),
    'exodus':      ('/calvin/harmony-law-index/', '摩西五经合参', 'Harmony of the Law'),
    'leviticus':   ('/calvin/harmony-law-index/', '摩西五经合参', 'Harmony of the Law'),
    'numbers':     ('/calvin/harmony-law-index/', '摩西五经合参', 'Harmony of the Law'),
    'deuteronomy': ('/calvin/harmony-law-index/', '摩西五经合参', 'Harmony of the Law'),
}

# 合参组已无内容——两套合参都并进了对应书卷
HARMONY = []

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
    """返回 {book_id: (入口路径, 册数)}。分卷聚合到第一册，册数用来标「全二卷」。"""
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
        prev = found.get(book)
        n = (prev[2] if prev else 0) + 1
        if prev is None or vol < prev[0]:
            found[book] = (vol, f'/{AUTHORS[author_id]["dir"]}/{d.name}/', n)
        else:
            found[book] = (prev[0], prev[1], n)
    return {k: (v[1], v[2]) for k, v in found.items()}


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
                  # 原书名要输出到 yml：扉页那块「本页收录」按各家真实书名列一次，
                  # 索引行里就只出现注释家的名字，不必把同一个书名重复 116 遍。
                  f'    work_cn: {yaml_escape(a["work_cn"])}',
                  f'    work_en: {yaml_escape(a["work_en"])}',
                  f'    books: {n}']
    lines += ['', 'books:']
    total_links = 0
    seen = {'ot': 0, 'nt': 0}   # 各架已排了几本，用来取布面色
    for bid, cn, testament, en in BOOKS:
        entries = [(aid, by_author[aid][bid][0], by_author[aid][bid][1])
                   for aid in AUTHORS if bid in by_author[aid]]
        # 合参覆盖的书卷：加尔文没有分卷注释，补一条指向对应的合参索引页。
        # 放在最前，与其他卷「加尔文在先」的次序一致。
        if bid in HARMONY_MAP:
            entries.insert(0, ('calvin', HARMONY_MAP[bid][0], 1))
        # 分卷逐册罗列：把加尔文那一条展开成 N 条，各带章数。
        # 以前只链到卷一、标一句「（全二卷）」，等于把卷二藏起来了。
        expanded = []
        for _aid, _path, _n in entries:
            if _aid != 'calvin':
                expanded.append((_aid, _path, None, None, None))
            elif bid in VOLUMES:
                unit = '篇' if bid == 'psalms' else '章'
                for d, vcn, ven, lo, hi in VOLUMES[bid]:
                    expanded.append((_aid, f'/calvin/{d}/', vcn, ven,
                                     f'第 {lo}–{hi} {unit} · 共 {hi - lo + 1} {unit}'))
            elif bid in HARMONY_MAP:
                # 合参**不逐册罗列**：太可路／出利民申的入口一律落在合参索引页，
                # 由那一页按经文检索。合参各册是按合参体例编的，册与被注释书卷
                # 不对应（卷一未必就是马太前十章），列出来反而添乱。
                expanded.append((_aid, _path, HARMONY_MAP[bid][1], HARMONY_MAP[bid][2], None))
            else:
                expanded.append((_aid, _path, None, None, None))
        entries = expanded
        if not entries:
            continue
        total_links += len(entries)
        order = CLOTH_ORDER[testament]
        cloth = CLOTH[order[seen[testament] % len(order)]]
        seen[testament] += 1
        lines += [f'  - id: {bid}',
                  f'    name: {yaml_escape(cn)}',
                  f'    en: {yaml_escape(en)}',
                  f'    testament: {testament}',
                  f'    cloth: {yaml_escape(cloth)}',
                  '    links:']
        for aid, path, ov_cn, ov_en, note in entries:
            # 中英书名都**按卷**生成，一一对应。曾经中文一律输出各家的总书名
            # （「加尔文圣经注释」），于是马可福音那一条中文写总名、英文写
            # Calvin on the Harmony of the Evangelists，两边对不上，且 41 卷
            # 中文完全相同，等于没有信息——被用户指出。
            #
            # 各家著作形态不同，命名方式因此也不同，不要强行统一：
            #   加尔文   逐卷独立成书 → 用该卷书名「创世记注释」；合参覆盖的
            #            四卷（太可路／出利民申）用合参书名，与英文一致
            #   马太亨利 全本圣经一部通注 → 「马太亨利圣经注释·马可福音」，
            #            点明是总注中的哪一卷，英文仍是那部书的真实书名
            #   欧文/毕列志 本就只注一卷，站内标题已经具体，照用
            if ov_cn:                    # 分卷／合参各册，书名已在 VOLUMES 里查定
                t_cn, t_en = ov_cn, ov_en
            elif aid == 'calvin':
                t_cn, t_en = cn + '注释', 'Calvin on ' + en
            elif aid == 'mhenry':
                t_cn = AUTHORS[aid]['work_cn'] + '·' + cn
                t_en = AUTHORS[aid]['work_en']
            else:
                t_cn, t_en = AUTHORS[aid]['work_cn'], AUTHORS[aid]['work_en']
            note_f = f', note: {yaml_escape(note)}' if note else ''
            lines.append(f'      - {{author: {aid}, path: {yaml_escape(path)}, '
                         f'title_cn: {yaml_escape(t_cn)}, title_en: {yaml_escape(t_en)}'
                         f'{note_f}}}')
    lines += ['', 'harmony:']
    for aid, dirname, cn in HARMONY:
        d = ROOT / AUTHORS[aid]['dir'] / dirname
        if not has_content(d):
            continue
        total_links += 1
        path = '/' + AUTHORS[aid]['dir'] + '/' + dirname + '/'
        lines += [f'  - name: {yaml_escape(cn)}',
                  f'    author: {aid}',
                  f'    title_cn: {yaml_escape(AUTHORS[aid]["work_cn"])}',
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
