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
# 「历代解经」只收录**加尔文与马太亨利之外**的注释家。那两位各有自己的书卷
# 主页（/calvin/ 与 /mhenry/），在这里再列一遍等于把 100 多个重复入口铺满
# 整版，真正新增的信息（还有谁注过这卷）反而被淹掉。
# 目前符合的只有两条：毕列志·箴言、欧文·希伯来书。其余书卷在版面上画成虚线
# 框——那是「尚无别家注释」，不是「无人注过」。
EXCLUDED_AUTHORS = {'calvin', 'mhenry'}

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
    # 贺智：1857 与 1859 各自成册，不是合订本，所以 work_* 只作「本页收录」
    # 那一栏的集合名，逐卷书名走下面的 BOOK_TITLES。
    ('hodge',   dict(name='查尔斯·贺智', short='贺智',    en='Charles Hodge',   years='1797–1878', dir='hodge',
                     work_cn='罗马书、哥林多前后书注释',
                     work_en='')),
])

# ── 主题色 ─────────────────────────────────────────────────────
# **按注释家一色**：同一位注释家的所有书卷共用（用户 2026-08-31 指定）。
# 曾按卷分色（贺智前书靛蓝 / 后书酒红），已撤回——一人一色才看得出「这是谁
# 的注释」，逐卷分色会把作者这层信息打散。
# 选色按 CIELAB 量过，两两之间与既有色的 ΔE 都够大：
#   欧文绿 #1f5a4b · 毕列志棕 #96613F · 贺智靛蓝 #1f3a5f
#   贺智靛蓝 vs 欧文绿 ΔE 39.7，vs 毕列志棕 59.4，vs 加尔文蓝 33.2。
# 每项是 (深, 浅) 两端，页面按 135° 渐变，与首页资源卡片一致。
AUTHOR_COLORS = {
    'owen':    ('#14382f', '#1f5a4b'),
    'bridges': ('#5B3A29', '#96613F'),
    'hodge':   ('#152840', '#2b5080'),
}

# 逐卷书名（同一注释家的不同分册书名不同时用）。取各卷扉页的实际书名。
BOOK_TITLES = {
    ('hodge', 'romans'):       ('罗马书注释',
                                'Commentary on the Epistle to the Romans'),
    ('hodge', '1corinthians'): ('哥林多前书注释',
                                'An Exposition of the First Epistle to the Corinthians'),
    ('hodge', '2corinthians'): ('哥林多后书注释',
                                'An Exposition of the Second Epistle to the Corinthians'),
}



# ── 对比注释数据源（供 _includes/compare-commentary.html 用）──────────
# 「点击章顶空白 → 弹出对照其他注释」这个功能原先是每个 layout 各写一份
# （calvin-en 的隐形热区版、calvin-chapter 与 mhenry-chapter 的按钮版），
# 新增一位注释家就得再抄一遍。现改为：这里按**实际发布的目录**扫出所有
# 可对照的源，写进 _data/compare_sources.yml，layout 只需 include 一次。
#
# 为什么不用 books[].links：那份只收 5 个入口（加尔文与马太亨利覆盖全 66 卷、
# 被 EXCLUDED_AUTHORS 排除在「历代解经」版面之外），对比功能恰恰最需要它们。
#
# 分卷书（jeremiah-1 / jeremiah-2、psalms-1 / psalms-2）按**章号区间**分别
# 记一条，区间由目录里实际的 <N>.md 推出——否则第 30 章会去找 jeremiah-1。
COMPARE_ACCENT = {
    'calvin': '#800000', 'mhenry': '#C9922A', 'owen': '#1f5a4b',
    'bridges': '#96613F', 'hodge': '#1f3a5f',
}
COMPARE_LABEL = {
    'calvin': '加尔文注释', 'mhenry': '马太亨利注释', 'owen': '约翰欧文注释',
    'bridges': '毕列志注释', 'hodge': '贺智注释',
}


def _chapter_range(d: Path):
    """目录里 <N>.md / <N>/ 的章号区间。取不到返回 None。"""
    ns = []
    for p in d.iterdir():
        m = re.fullmatch(r'(\d{1,3})(?:\.md)?', p.name)
        if m:
            ns.append(int(m.group(1)))
    return (min(ns), max(ns)) if ns else None


def build_compare_sources() -> str:
    """→ _data/compare_sources.yml 的内容。"""
    from collections import defaultdict
    out = defaultdict(list)
    for aid, meta in AUTHORS.items():
        base = ROOT / meta['dir']
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name.endswith('-index') or not has_content(d):
                continue
            name = d.name
            is_en = name.endswith('-en')
            core = name[:-3] if is_en else name
            if core.startswith('harmony'):
                continue
            m = re.match(r'^(.+)-(\d+)$', core)
            book = m.group(1) if m else core
            rng = _chapter_range(d)
            # 章级 zh（欧文）→ /owen/hebrews/{ch}/zh/
            # 占位符用 __CH__ 而非 {ch}：Liquid 的 replace: 参数里出现 `}`
            # 会与 `}}` 终止符冲突，整站构建报 Liquid syntax error（实测）
            tpl = (f'/{meta["dir"]}/{name}/__CH__/zh/'
                   if (d / '1' / 'zh').is_dir() else f'/{meta["dir"]}/{name}/__CH__/')
            key = aid + ('-en' if is_en else '')
            label = COMPARE_LABEL.get(aid, aid) + ('（英文）' if is_en else '')
            e = {'key': key, 'author': aid, 'label': label, 'url_tpl': tpl,
                 'accent': COMPARE_ACCENT.get(aid, '#555')}
            if rng:
                e['ch_from'], e['ch_to'] = rng
            out[book].append(e)
    lines = ['# 由 scripts/build_commentaries_index.py 生成，勿手改。',
             '# 对比注释的可选源：书卷 → 各注释家的章节 URL 模板（__CH__ 为章号占位）。',
             '# 新增注释家：改脚本里的 AUTHORS / COMPARE_LABEL / COMPARE_ACCENT 后重跑，',
             '# 所有 layout 的对比功能会自动带上它——不必改任何 layout。',
             '', 'sources:']
    for book in sorted(out):
        srcs = out[book]
        if len(srcs) < 2:          # 只有自己一家，没有可对照的
            continue
        lines.append(f'  {book}:')
        for e in srcs:
            rng = (f", ch_from: {e['ch_from']}, ch_to: {e['ch_to']}"
                   if 'ch_from' in e else '')
            lines.append(f'    - {{key: {e["key"]}, author: {e["author"]}, '
                         f'label: {yaml_escape(e["label"])}, '
                         f'url_tpl: {yaml_escape(e["url_tpl"])}, '
                         f'accent: {yaml_escape(e["accent"])}{rng}}}')
    return '\n'.join(lines) + '\n'

def theme_color(aid: str) -> tuple:
    return AUTHOR_COLORS.get(aid) or ('#2d4a3a', '#3f6a54')
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

# 合参覆盖的书卷 → (入口路径, 中文书名, 英文书名)
# 中文名取站内既有写法，勿另造：
#   calvin/harmony-index/index.html      title: 共观福音注释
#   calvin/harmony-law-index/index.html  title: 摩西五经合参
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

# 各卷章数：读 mhenry/<book>/index.html 的 front matter。
# 曾用 _data/calvin_books.yml，但那份表只覆盖加尔文注过的卷，且分卷写成
# isaiah-1/2、合参写成 harmony-law-N，66 卷里有 28 卷取不到（箴言就是其一）。
# 马太亨利 66 卷齐全、id 与本表一一对应，是站内唯一现成的全表。
def _load_chapters():
    out = {}
    base = ROOT / 'mhenry'
    if not base.is_dir():
        return out
    for idx in base.glob('*/index.html'):
        m = re.search(r'^chapters:\s*(\d+)', idx.read_text(encoding='utf-8'), re.M)
        if m:
            out[idx.parent.name] = int(m.group(1))
    return out

CHAPTERS = _load_chapters()


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


def entry_path(author_id: str, dirname: str) -> str:
    """书卷入口路径。**有书卷级中文版就指中文**——历代解经是中文读者的入口，
    落在英文页上等于让人先自己找一次「中文版」按钮（用户 2026-09-02 指定）。
    中文页顶部本来就有「English →」，回英文一步可达。

    只认书卷级 `<book>/zh/index.html`。欧文是章级 `<ch>/zh/`（整卷没有中文
    索引页），这里不会误指过去。"""
    d = AUTHORS[author_id]['dir']
    if (ROOT / d / dirname / 'zh' / 'index.html').exists():
        return f'/{d}/{dirname}/zh/'
    return f'/{d}/{dirname}/'


def chapter_url_tpl(author_id: str, dirname: str, path: str) -> str:
    """章节 URL 模板，`__CH__` 为章号占位。供 _includes/compare-commentary.html 用。

    三家的形态不一样，不能简单拼 path + 章号：
      calvin / hodge / mhenry  书卷级 zh → `/calvin/romans/{ch}/`
      owen                     **章级** zh → `/owen/hebrews/{ch}/zh/`
                               （整卷没有中文索引页，zh 在章号之后）
    判据：存在 `<book>/1/zh/` 就是章级 zh。
    """
    d = AUTHORS[author_id]['dir']
    book = ROOT / d / dirname
    if (book / '1' / 'zh').is_dir():
        return f'/{d}/{dirname}/__CH__/zh/'
    return path.rstrip('/') + '/__CH__/'


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
            found[book] = (vol, entry_path(author_id, d.name), n)
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
    for bid, cn, testament, en in BOOKS:
        entries = [(aid, by_author[aid][bid][0], by_author[aid][bid][1])
                   for aid in AUTHORS
                   if bid in by_author[aid] and aid not in EXCLUDED_AUTHORS]
        # 合参覆盖的书卷：加尔文没有分卷注释，补一条指向对应的合参索引页。
        # 放在最前，与其他卷「加尔文在先」的次序一致。
        if bid in HARMONY_MAP and 'calvin' not in EXCLUDED_AUTHORS:
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
        # 不再 `if not entries: continue`——66 卷全部输出，没有条目的在版面上
        # 画成虚线框。少输出的话页面就得自己再拼一份书卷全表，两处容易不同步。
        total_links += len(entries)
        lines += [f'  - id: {bid}',
                  f'    name: {yaml_escape(cn)}',
                  f'    en: {yaml_escape(en)}',
                  f'    testament: {testament}',
                  f'    chapters: {CHAPTERS.get(bid, 0)}',
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
            elif (aid, bid) in BOOK_TITLES:
                t_cn, t_en = BOOK_TITLES[(aid, bid)]
            else:
                t_cn, t_en = AUTHORS[aid]['work_cn'], AUTHORS[aid]['work_en']
            note_f = f', note: {yaml_escape(note)}' if note else ''
            c0, c1 = theme_color(aid)
            _dir = path.strip('/').split('/')[1] if path.count('/') > 2 else bid
            tpl = chapter_url_tpl(aid, _dir, path)
            lines.append(f'      - {{author: {aid}, path: {yaml_escape(path)}, '
                         f'url_tpl: {yaml_escape(tpl)}, '
                         f'title_cn: {yaml_escape(t_cn)}, title_en: {yaml_escape(t_en)}'
                         f', c0: {yaml_escape(c0)}, c1: {yaml_escape(c1)}'
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

    # 对比注释数据源（见 build_compare_sources 上方说明）
    cs = ROOT / '_data' / 'compare_sources.yml'
    cs_text = build_compare_sources()
    cs.write_text(cs_text, encoding='utf-8')
    print(f'✓ {cs.relative_to(ROOT)}  '
          f'（{cs_text.count(chr(10) + "  ") - cs_text.count(chr(10) + "    ")} 卷可对照，'
          f'{cs_text.count(chr(10) + "    - ")} 个源）')
    covered = sum(1 for bid, _, _, _ in BOOKS if any(bid in by_author[a] for a in AUTHORS))
    print(f'✓ {out.relative_to(ROOT)}')
    for aid in AUTHORS:
        print(f'    {AUTHORS[aid]["name"]:<12} {len(by_author[aid]):>2} 卷')
    print(f'    覆盖 {covered}/66 卷，共 {total_links} 个入口')


if __name__ == '__main__':
    main()
