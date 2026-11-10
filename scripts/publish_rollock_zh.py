#!/usr/bin/env python3
"""rollock_raw/thessalonians/zh_chapters/<book>/*.md → rollock/<book>/zh/*.md（中文版）。

    python3 scripts/publish_rollock_zh.py                 # 两卷都跑（没有译稿的卷跳过）
    python3 scripts/publish_rollock_zh.py --book 1thessalonians

骨架照搬 publish_dickson_zh.py。英文版一讲一页，中文版同样：zh/<讲首节>.md、卷首 zh/<篇名>.md。
与英文版共用 rollock-chapter / rollock-book 两个 layout，靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**（键 "<book>/<slug>"）；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 书首页 /rollock/<book>/ 换成中文目录：已译的讲链中文，未译的链英文并标「英文」；
  英文目录在 /en/（publish_rollock_en 见到 zh/ 就不再覆盖首页）。
- 跑完回调 publish_rollock_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sect_names  # noqa: E402  教派名补原名
import publish_rollock_en as P  # noqa: E402

RAW = ROOT / 'rollock_raw' / 'thessalonians'
META = RAW / 'zh_meta.json'
AUTHOR_ZH = '罗伯特·罗洛克'
AUTHOR_EN = 'Robert Rollock'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
CN = '零一二三四五六七八九'

BOOK_ZH = {
    '1thessalonians': dict(name='罗洛克《帖撒罗尼迦前书讲章》', ref='帖撒罗尼迦前书',
                           edition='Lectures vpon the First and Second Epistles of Paul to the Thessalonians · 爱丁堡，1606',
                           front={'title': ('书名页', '爱丁堡，1606'),
                                  'dedication': ('献辞', '致埃利的威廉·司各特（William Scot of Ely）'),
                                  'to-the-reader': ('致基督徒读者', ''),
                                  'argument': ('前书提要', '')}),
    '2thessalonians': dict(name='罗洛克《帖撒罗尼迦后书讲章》', ref='帖撒罗尼迦后书',
                           edition='Lectures vpon the Second Epistle of the Apostle Paul to the Thessalonians · 爱丁堡，1606',
                           front={'title': ('书名页', '爱丁堡，1606'),
                                  'argument': ('后书提要', '')}),
}


def cn(n):
    if n < 10:
        return CN[n]
    t, u = divmod(n, 10)
    return ('' if t == 1 else CN[t]) + '十' + (CN[u] if u else '')


def rng_zh(book, pg):
    """'1 Thessalonians 1:9–2:2' → '帖撒罗尼迦前书 1:9–2:2'。"""
    return pg['rng'].replace(P.BOOKS[book]['ref'], BOOK_ZH[book]['ref'])


def lec_no(pg):
    return int(re.search(r'\d+', pg['short']).group(0))


def label(book, pg):
    if pg['group'] == 'front':
        return BOOK_ZH[book]['front'][pg['slug']][0]
    return f'第{cn(lec_no(pg))}讲'


def title(book, pg):
    return label(book, pg) if pg['group'] == 'front' else f'{label(book, pg)} · {rng_zh(book, pg)}'


def subtitle(book, pg):
    return BOOK_ZH[book]['front'][pg['slug']][1] if pg['group'] == 'front' else AUTHOR_EN


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表。转义那个点。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .rl-orig）
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    """经文弹层认的中文书卷名，直接从 _includes/scripture-popup.html 的 BOOKS 表读。"""
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


# 书卷名排斜体「*罗马书* 10:4」——书名与章节号落在两个文本节点，经文弹层认不出：书名挪到斜体外
REF_BOOK_ITALIC = _ref_books_re()


def _unitalic_ref(m):
    pre = m.group(1)
    if not pre.strip():
        return m.group(2)
    core = pre.rstrip()
    return f'*{core}*{pre[len(core):]}{m.group(2)}'


def clean(body: str) -> str:
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = REF_BOOK_ITALIC.sub(_unitalic_ref, body)
    body = RE_OL.sub(r'\1\\. ', body)
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    # 模型常给页边旁注外加一对括号：「比喻（<旁注>）」。旁注在宽屏挪到页边显示，正文里只剩一对空括号。
    # 括号里只裹着一条旁注、别无他字时，去掉括号（原书本无此括号）
    body = re.sub(r'[（(]\s*(<span class="rl-margin[^>]*>.*?</span>)\s*[）)]', r'\1', body)
    # 讲前经文框照抄和合本：英文 KJV/日内瓦本的斜体是「译者补字」，搬进和合本只会把「*在*」「*归与*」排成斜体
    body = re.sub(r'(<p class="rl-v"[^>]*>)(.*?)(</p>)', lambda m: m.group(1) + m.group(2).replace('*', '') + m.group(3),
                  body)
    body = ORIG_NAME.sub(r'<span class="rl-orig">[\1]</span>', body)
    body = re.sub(r'<span class="rl-dropcap"></span>([^\s<*])', r'<span class="rl-dropcap">\1</span>', body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def publish(book, meta, now):
    zh_raw = RAW / 'zh_chapters' / book
    en = ROOT / 'rollock' / book
    out = en / 'zh'
    pages = P.build_pages(book)
    done = {p.stem for p in zh_raw.glob('*.md')} if zh_raw.exists() else set()
    names = [pg for pg in pages if pg['slug'] in done]
    if not names:
        return 0
    out.mkdir(parents=True, exist_ok=True)
    for k, pg in enumerate(names):
        slug = pg['slug']
        path = out / f'{slug}.md'
        date = meta.get(f'{book}/{slug}') or existing_date(path) or now
        fm = ['---', 'layout: rollock-chapter', f'book_id: {book}',
              f'book_name: "{BOOK_ZH[book]["name"]}"', f'title: "{title(book, pg)}"']
        if subtitle(book, pg):
            fm.append(f'subtitle: "{subtitle(book, pg)}"')
        fm.append(f'date: {date}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/rollock/{book}/zh/{q["slug"]}/"', f'prev_label: "{label(book, q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/rollock/{book}/zh/{q["slug"]}/"', f'next_label: "{label(book, q)}"']
        fm += [f'en_url: "/rollock/{book}/{slug}/"', 'zh: true', '---']
        body = clean((zh_raw / f'{slug}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (en / f'{slug}.md').read_text(encoding='utf-8'), 'rl-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
    chapters_zh(book, en, out, pages, done, meta, now)
    (en / 'index.html').write_text(build_index(book, pages, done), encoding='utf-8')
    print(f'{book}: 发布中文 {len(names)}/{len(pages)} 篇 → {out}')
    return len(names)


def chapters_zh(book, en, out, pages, done, meta, now):
    """章目录页 zh/<章>.md：照英文章目录页（en/<章>.md 的 rl-chtoc）列的讲章次序，只列已译的讲。
    章目录是导航页、不是正文，不送模型（2026-11-10 用户令补齐辅助页）。"""
    by = {pg['slug']: pg for pg in pages}
    chs = sorted(int(f.stem) for f in en.glob('*.md') if f.stem.isdigit())
    made = []
    for c in chs:
        t = (en / f'{c}.md').read_text(encoding='utf-8')
        slugs = [x for x in re.findall(rf'/rollock/{book}/([\w-]+)/', t) if x in done and x in by]
        if slugs:
            made.append((c, slugs, t))
    for i, (c, slugs, t) in enumerate(made):
        fm_en = dict(re.findall(r'^(verse_from|verse_to): *(\d+)', t, re.M))
        items = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/rollock/{book}/zh/{x}/">{label(book, by[x])}'
                          f'<small>{rng_zh(book, by[x])}</small></a></li>' for x in slugs)
        date = max((meta.get(f'{book}/{x}') or now) for x in slugs)
        fm = ['---', 'layout: rollock-chapter', f'book_id: {book}', f'book_name: "{BOOK_ZH[book]["name"]}"',
              f'title: "{BOOK_ZH[book]["ref"]} 第{cn(c)}章"', f'subtitle: "{AUTHOR_EN}"', f'date: {date}',
              f'chapter: {c}']
        fm += [f'{k}: {v}' for k, v in fm_en.items()]
        if i > 0:
            fm += [f'prev_url: "/rollock/{book}/zh/{made[i - 1][0]}/"',
                   f'prev_label: "{BOOK_ZH[book]["ref"]} 第{cn(made[i - 1][0])}章"']
        if i + 1 < len(made):
            fm += [f'next_url: "/rollock/{book}/zh/{made[i + 1][0]}/"',
                   f'next_label: "{BOOK_ZH[book]["ref"]} 第{cn(made[i + 1][0])}章"']
        fm += [f'en_url: "/rollock/{book}/{c}/"', 'zh: true', '---']
        (out / f'{c}.md').write_text('\n'.join(fm) + f'\n\n<ul class="rl-chtoc">\n{items}\n</ul>\n', encoding='utf-8')


def build_index(book, pages, done):
    cfg = BOOK_ZH[book]
    out = ['---', 'layout: rollock-book', f'book_id: {book}', f'book_name: "{cfg["name"]}"',
           f'title: "{cfg["name"]}"', f'author: "{AUTHOR_ZH}（Robert Rollock，1555?–1599）"',
           f'edition: "{cfg["edition"]}"', f'en_url: "/rollock/{book}/en/"', 'zh: true', '---', '']

    def li(pg, extra=''):
        if pg['slug'] in done:
            return (f'  <li><a href="{{{{ site.baseurl }}}}/rollock/{book}/zh/{pg["slug"]}/">{label(book, pg)}'
                    f'{extra}</a></li>')
        return (f'  <li><a class="rl-other" href="{{{{ site.baseurl }}}}/rollock/{book}/{pg["slug"]}/">'
                f'{label(book, pg)}{extra}<small>英文</small></a></li>')
    out.append('<h2 class="rl-group">卷首</h2>')
    out.append('<ul class="rl-toc">')
    out.extend(li(pg) for pg in pages if pg['group'] == 'front')
    out.append('</ul>')
    out.append('<h2 class="rl-group">各讲</h2>')
    out.append('<ul class="rl-toc">')
    out.extend(li(pg, f'<small>{rng_zh(book, pg)}</small>') for pg in pages if pg['group'] == 'lecture')
    out.append('</ul>')
    n = sum(1 for pg in pages if pg['group'] == 'lecture' and pg['slug'] in done)
    nl = sum(1 for pg in pages if pg['group'] == 'lecture')
    out.append(f'<p class="rl-note-zh">中译已上线 {n} / {nl} 讲；标「英文」的篇暂只有英文。'
               '原书录入本里读不出的字，中文里同样标红留在明面；编者推补以方括号另色标出。底本与缺字说明见'
               f'<a href="{{{{ site.baseurl }}}}/rollock/{book}/en/">英文版首页</a>。</p>')
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', choices=list(BOOK_ZH))
    a = ap.parse_args()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True,
                         check=True).stdout.strip()
    total = sum(publish(b, meta, now) for b in ([a.book] if a.book else BOOK_ZH))
    if not total:
        sys.exit('zh_chapters 里没有任何已译的篇')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_rollock_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)


if __name__ == '__main__':
    main()
