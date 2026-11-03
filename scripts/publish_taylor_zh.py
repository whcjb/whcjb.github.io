#!/usr/bin/env python3
"""taylor_raw/titus/zh_chapters/*.md → taylor/titus/zh/*.md（中文版）。

    python3 scripts/publish_taylor_zh.py

骨架照搬 publish_jenkyn_zh.py。与英文版共用 taylor-chapter / taylor-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层，layout 里已接）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 有已译正文页的章才出中文章目录 zh/<章>.md。
- 书的首页 /taylor/titus/ 换成中文目录，英文目录在 /en/（publish_taylor_en 见到 zh/ 就不再覆盖首页）。
- 跑完回调 publish_taylor_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import publish_taylor_en as P  # noqa: E402

RAW = ROOT / 'taylor_raw' / 'titus'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
EN = ROOT / 'taylor' / 'titus'
OUT = EN / 'zh'
BOOK_NAME_ZH = '泰勒《提多书注释》'
AUTHOR_ZH = '托马斯·泰勒'
AUTHOR_EN = 'Thomas Taylor'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

LABEL = {
    'title': ('书名页', '剑桥，1612'),
    'dedication': ('献辞', '致里奇男爵罗伯特（Robert Lord Rich）'),
    'to-the-reader': ('致基督徒读者', AUTHOR_EN),
    'argument': ('本书缘起与分段', AUTHOR_EN),
    'doctrines': ('教义简表', '第一表'),
    'observations': ('其他有益的札记', '第二表'),
    'questions': ('问题简表', '第三表'),
    'errata': ('勘误表', AUTHOR_EN),
}


def short(p):
    return f'{p["ch"]}:{p["v1"]}' + ('' if p['v1'] == p['v2'] else f'–{p["v2"]}')


def label(p):
    return f'提多书 {short(p)}' if 'ch' in p else LABEL[p['slug']][0]


def subtitle(p):
    return AUTHOR_EN if 'ch' in p else LABEL[p['slug']][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表。转义那个点。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .ty-orig）
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    """经文弹层认的中文书卷名，直接从 _includes/scripture-popup.html 的 BOOKS 表读。"""
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


# 书卷名排斜体「*马太福音* 10:4」——书名与章节号落在两个文本节点，经文弹层认不出：书名挪到斜体外
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
    body = ORIG_NAME.sub(r'<span class="ty-orig">[\1]</span>', body)
    body = re.sub(r'<span class="ty-dropcap"></span>([^\s<*])', r'<span class="ty-dropcap">\1</span>', body)
    # HTML 块里 kramdown 不解析 *斜体*：换回 <i>
    body = re.sub(r'(<p>)(.*?)(</p>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    pages = P.build_pages()
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    names = [p for p in pages if p['slug'] in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True,
                         check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    for k, p in enumerate(names):
        slug = p['slug']
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: taylor-chapter', 'book_id: titus',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/taylor/titus/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/taylor/titus/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/taylor/titus/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 章目录页（只列已译的正文页）
    for ch in sorted({p['ch'] for p in names if 'ch' in p}):
        secs = [p for p in names if p.get('ch') == ch]
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/taylor/titus/zh/{p["slug"]}/">{short(p)}'
                        f'<small>{label(p)}</small></a></li>' for p in secs)
        fm = ['---', 'layout: taylor-chapter', 'book_id: titus', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "提多书 第 {ch} 章"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', f'chapter: {ch}',
              f'en_url: "/taylor/titus/{ch}/"', 'zh: true', '---']
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + f'\n\n<ul class="ty-chtoc">\n{lst}\n</ul>\n',
                                      encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, pages), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_taylor_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, pages):
    out = ['---', 'layout: taylor-book', 'book_id: titus', f'book_name: "{BOOK_NAME_ZH}"',
           f'title: "{BOOK_NAME_ZH}"', f'author: "{AUTHOR_ZH}（Thomas Taylor，1576–1633）"',
           'edition: "A Commentarie vpon the Epistle of S. Paul written to Titus · 剑桥，1612"',
           'en_url: "/taylor/titus/en/"', 'zh: true', '---', '']

    def group(name, lst, show_sub=True):
        if lst:
            out.append(f'<h2 class="ty-group">{name}</h2>')
            out.append('<ul class="ty-toc">')
            out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/taylor/titus/zh/{p["slug"]}/">{label(p)}'
                       + (f'<small>{subtitle(p)}</small>' if show_sub and 'ch' not in p else '')
                       + '</a></li>' for p in lst)
            out.append('</ul>')

    group('卷首', [p for p in names if p['group'] == 'front'])
    group('注释', [p for p in names if p['group'] == 'section'])
    group('卷末三表与勘误', [p for p in names if p['group'] == 'back'])
    out.append(f'<p class="ty-note-zh">中译已上线 {len(names)} / {len(pages)} 篇，逐篇推进；未译的篇见'
               '<a href="{{ site.baseurl }}/taylor/titus/en/">英文版</a>。原书录入本里读不出、经编者推补的字，'
               '中文里同样以方括号标出，逐条说明见英文版首页。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
