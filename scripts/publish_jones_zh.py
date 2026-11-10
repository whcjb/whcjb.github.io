#!/usr/bin/env python3
"""jones_raw/<book>/zh_chapters/*.md → jones/<book>/zh/*.md（中文版）。

    python3 scripts/publish_jones_zh.py                 # 两卷都跑（没有译稿的卷跳过）
    python3 scripts/publish_jones_zh.py --book 2john

骨架照搬 publish_rollock_zh.py。英文版一节一页，中文版同样：zh/1-<节>.md、卷首 zh/<篇名>.md、章目录 zh/1.md。
与英文版共用 jones-chapter / jones-book 两个 layout，靠 `zh: true` 切换（中文页才挂经文引用弹层）。
卷末勘误表（errata）原先不译；2026-11-10 用户令也译出。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**（键 "<book>/<slug>"）；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 书首页 /jones/<book>/ 换成中文目录：已译的链中文，未译的链英文并标「英文」；
  英文目录在 /en/（publish_jones_en 见到 zh/ 就不再覆盖首页）。
- zh/1.md 章目录让 build_commentaries_index 认出中文版（对照面板多一个中文源）。
- 跑完回调 publish_jones_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
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
import publish_jones_en as P  # noqa: E402

RAW = ROOT / 'jones_raw'
META = RAW / 'zh_meta.json'
AUTHOR_ZH = '威廉·琼斯'
AUTHOR_EN = 'William Jones'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
SKIP = set()   # 2026-11-10 用户令勘误表也译

FRONT_ZH = {'title': ('书名页', '伦敦，1635'),
            'dedication': ('献辞', '致托马斯·杰明爵士（Sir Thomas Jermyn）'),
            'to-the-reader': ('致基督徒读者', ''),
            'errata': ('勘误表', '印本页行号对照')}
BOOK_ZH = {
    '2john': dict(name='琼斯《约翰二书简释》', ref='约翰二书'),
    '3john': dict(name='琼斯《约翰三书简释》', ref='约翰三书'),
}
EDITION = ('A Compendious Explication of the Second and Third Epistles of Saint Iohn · '
           '附《腓利门书、希伯来书注释》卷末，伦敦，1635')


def rng_zh(book, pg):
    """'2 John 1:1' → '约翰二书 1:1'。"""
    return pg['rng'].replace(P.REF[book], BOOK_ZH[book]['ref'])


def label(book, pg):
    return FRONT_ZH[pg['slug']][0] if pg['group'] == 'front' or pg['slug'] in FRONT_ZH else pg['short']


def title(book, pg):
    return label(book, pg) if pg['group'] == 'front' or pg['slug'] in FRONT_ZH else rng_zh(book, pg)


def subtitle(book, pg):
    return FRONT_ZH[pg['slug']][1] if pg['group'] == 'front' or pg['slug'] in FRONT_ZH else AUTHOR_EN


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表。转义那个点。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .jw-orig）
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
    body = re.sub(r'[（(]\s*(<span class="jw-margin[^>]*>.*?</span>)\s*[）)]', r'\1', body)
    body = ORIG_NAME.sub(r'<span class="jw-orig">[\1]</span>', body)
    body = re.sub(r'<span class="jw-dropcap"></span>([^\s<*])', r'<span class="jw-dropcap">\1</span>', body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def publish(book, meta, now):
    zh_raw = RAW / book / 'zh_chapters'
    en = ROOT / 'jones' / book
    out = en / 'zh'
    pages = [pg for pg in P.build_pages(book) if pg['slug'] not in SKIP]
    done = {p.stem for p in zh_raw.glob('*.md')} if zh_raw.exists() else set()
    names = [pg for pg in pages if pg['slug'] in done]
    if not names:
        return 0
    out.mkdir(parents=True, exist_ok=True)
    for k, pg in enumerate(names):
        slug = pg['slug']
        path = out / f'{slug}.md'
        date = meta.get(f'{book}/{slug}') or existing_date(path) or now
        fm = ['---', 'layout: jones-chapter', f'book_id: {book}',
              f'book_name: "{BOOK_ZH[book]["name"]}"', f'title: "{title(book, pg)}"']
        if subtitle(book, pg):
            fm.append(f'subtitle: "{subtitle(book, pg)}"')
        fm.append(f'date: {date}')
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/jones/{book}/zh/{q["slug"]}/"', f'prev_label: "{label(book, q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/jones/{book}/zh/{q["slug"]}/"', f'next_label: "{label(book, q)}"']
        fm += [f'en_url: "/jones/{book}/{slug}/"', 'zh: true', '---']
        body = clean((zh_raw / f'{slug}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (en / f'{slug}.md').read_text(encoding='utf-8'), 'jw-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
    secs = [pg for pg in names if pg.get('ch') == 1]
    if secs:
        date = meta.get(f'{book}/{secs[-1]["slug"]}') or now
        fm = ['---', 'layout: jones-chapter', f'book_id: {book}', f'book_name: "{BOOK_ZH[book]["name"]}"',
              f'title: "{BOOK_ZH[book]["ref"]}"', f'subtitle: "{AUTHOR_EN}"', f'date: {date}', 'chapter: 1',
              'verse_from: 1', f'verse_to: {secs[-1]["v2"]}', f'en_url: "/jones/{book}/1/"', 'zh: true', '---']
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/jones/{book}/zh/{p["slug"]}/">{p["short"]}'
                        f'<small>{rng_zh(book, p)}</small></a></li>' for p in secs)
        (out / '1.md').write_text('\n'.join(fm) + f'\n\n<ul class="jw-chtoc">\n{lst}\n</ul>\n', encoding='utf-8')
    (en / 'index.html').write_text(build_index(book, pages, done), encoding='utf-8')
    print(f'{book}: 发布中文 {len(names)}/{len(pages)} 篇 → {out}')
    return len(names)


def build_index(book, pages, done):
    cfg = BOOK_ZH[book]
    other = '3john' if book == '2john' else '2john'
    out = ['---', 'layout: jones-book', f'book_id: {book}', f'book_name: "{cfg["name"]}"',
           f'title: "{cfg["name"]}"', f'author: "{AUTHOR_ZH}（William Jones，1561–1636）"',
           f'edition: "{EDITION}"', f'en_url: "/jones/{book}/en/"', 'zh: true', '---', '']

    def li(pg, extra=''):
        if pg['slug'] in done:
            return (f'  <li><a href="{{{{ site.baseurl }}}}/jones/{book}/zh/{pg["slug"]}/">{label(book, pg)}'
                    f'{extra}</a></li>')
        return (f'  <li><a class="jw-other" href="{{{{ site.baseurl }}}}/jones/{book}/{pg["slug"]}/">'
                f'{label(book, pg)}{extra}<small>英文</small></a></li>')
    out.append('<h2 class="jw-group">卷首</h2>')
    out.append('<ul class="jw-toc">')
    out.extend(li(pg) for pg in pages if pg['group'] == 'front')
    out.append('</ul>')
    out.append('<h2 class="jw-group">逐节简释</h2>')
    out.append('<ul class="jw-toc">')
    out.extend(li(pg, f'<small>{rng_zh(book, pg)}</small>') for pg in pages if pg['group'] == 'section')
    out.append('</ul>')
    back = [pg for pg in pages if pg['group'] == 'back']
    if back:
        out.append('<h2 class="jw-group">卷末</h2>')
        out.append('<ul class="jw-toc">')
        out.extend(li(pg) for pg in back)
        out.append('</ul>')
    n = sum(1 for pg in pages if pg['group'] == 'section' and pg['slug'] in done)
    nl = sum(1 for pg in pages if pg['group'] == 'section')
    out.append(f'<p class="jw-note-zh">中译已上线 {n} / {nl} 篇；标「英文」的篇暂只有英文。'
               '约翰二书、三书的讲解附在琼斯《腓利门书、希伯来书注释》卷末（伦敦 1635），本站只收这两篇'
               f'（另一卷见<a href="{{{{ site.baseurl }}}}/jones/{other}/">{BOOK_ZH[other]["name"]}</a>）。'
               '原书录入本里读不出的字，中文里同样标红留在明面；编者推补以方括号另色标出。底本与缺字说明见'
               f'<a href="{{{{ site.baseurl }}}}/jones/{book}/en/">英文版首页</a>。</p>')
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
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_jones_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)


if __name__ == '__main__':
    main()
