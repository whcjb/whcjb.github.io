#!/usr/bin/env python3
"""jenkyn_raw/jude/zh_chapters/*.md → jenkyn/jude/zh/*.md（中文版）。

    python3 scripts/publish_jenkyn_zh.py

骨架照搬 publish_adams_zh.py。与英文版共用 jenkyn-chapter / jenkyn-book 两个 layout，
靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 犹大书只一章：有已译的正文页才出中文章目录 zh/1.md。
- 书的首页 /jenkyn/jude/ 换成中文目录，英文目录在 /en/。
- 跑完回调 publish_jenkyn_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import sect_names  # noqa: E402  教派名补原名
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'jenkyn_raw' / 'jude'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
EN = ROOT / 'jenkyn' / 'jude'
OUT = EN / 'zh'
BOOK_NAME_ZH = '詹金《犹大书讲解》'
AUTHOR_ZH = '威廉·詹金'
AUTHOR_EN = 'William Jenkyn'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)

FRONT_LABEL = {
    'title1': ('书名页（第一部分）', '伦敦，1652'),
    'to-the-reader': ('致读者', '致伦敦基督堂（Christ-Church）堂区众信徒'),
    'errata1': ('勘误表（第一部分）', AUTHOR_EN),
    'advertisement': ('书商告读者', AUTHOR_EN),
    'title2': ('书名页（第二部分）', '伦敦，1654'),
    'dedication': ('献辞（第二部分）', '致伦敦黑衣修士区（Black-Friars）的神的教会'),
    'errata2': ('勘误表（第二部分）', AUTHOR_EN),
}
RE_PART = re.compile(r'\(part (\d+) of (\d+)\)')


def label(p):
    if 'ch' in p:
        a, b = p['v1'], p['v2']
        s = f'犹大书 {a}' + (f'-{b}' if b != a else '') + ' 节'
        if p.get('src') == '8-ii':
            s += '（第二部分）'
        m = RE_PART.search(p['title'])
        return s + (f'（第 {m.group(1)}/{m.group(2)} 段）' if m else '')
    return FRONT_LABEL[p['slug']][0]


def subtitle(p):
    return AUTHOR_EN if 'ch' in p else FRONT_LABEL[p['slug']][1]


# 原书分条「2. …」各自成段——段首「数字 + 点 + 空格」会被 kramdown 当成有序列表、
# 从 1 重新编号（第 2 条显示成 1.）。转义那个点，原样显示。
RE_OL = re.compile(r'^(\d+)\. ', re.M)
# 音译专名后的原名括注「（Augustine）」→ 小一号灰字方括号（样式在 layout 的 .jk-orig）。
# 只认括号里全是西文字母的；夹了中文的、拉丁词释义都不动。zh_chapters 里仍存圆括号。
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    """经文弹层认的中文书卷名，直接从 _includes/scripture-popup.html 的 BOOKS 表读（同一份来源，免得两边不一致）。"""
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


# 原书书卷名排斜体（*Matth.* 10.4），译文照搬成「*马太福音* 10:4」——渲染后书名与章节号落在两个文本节点，
# 经文弹层逐个文本节点找引用，就认不出来。书名挪到斜体外：「*亚勒腓，见马太福音* 10:3」→「*亚勒腓，见*马太福音 10:3」。
REF_BOOK_ITALIC = _ref_books_re()


def _unitalic_ref(m):
    pre = m.group(1)
    if not pre.strip():
        return m.group(2)
    core = pre.rstrip()
    return f'*{core}*{pre[len(core):]}{m.group(2)}'


def clean(body: str) -> str:
    # 相邻两段斜体在译文里常被并成 `**`：本书没有粗体，只合并孤立的 `**`
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    # 模型常给页边旁注外加一对括号：「比喻（<旁注>）」。旁注在宽屏挪到页边显示，正文里只剩一对空括号。
    # 括号里只裹着一条旁注、别无他字时，去掉括号（原书本无此括号）
    body = re.sub(r'[（(]\s*(<span class="jk-margin[^>]*>.*?</span>)\s*[）)]', r'\1', body)
    body = REF_BOOK_ITALIC.sub(_unitalic_ref, body)
    body = RE_OL.sub(r'\1\\. ', body)
    # 章题照原书斜体搬来——中文书名里斜体不成样子，标题行去掉星号
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    body = ORIG_NAME.sub(r'<span class="jk-orig">[\1]</span>', body)
    # 首字下沉：模型把英文首字母连同外壳里的字一起丢了，留下空壳——把中文第一个字挪进去
    body = re.sub(r'<span class="jk-dropcap"></span>([^\s<*])', r'<span class="jk-dropcap">\1</span>', body)
    # 扉页英文几行（AN / EXPOSITION / Of the Epistle of）在中文里并成一行，剩下的空行去掉
    body = re.sub(r'<div class="jk-tp-l[^"]*"></div>\n', '', body)
    # 扉页是 HTML 块，kramdown 不解析里面的 *斜体*：换回 <i>
    body = re.sub(r'(<div class="jk-tp-l[^"]*">)(.*?)(</div>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    body = re.sub(r'(<p>)(.*?)(</p>)',
                  lambda m: m.group(1) + re.sub(r'\*([^*]+)\*', r'<i>\1</i>', m.group(2)) + m.group(3), body)
    return body.strip()


RE_HEADS = re.compile(r'^(###|####) (.+?)\n\{: \.jk-(part|clause) #(c\d+)\}', re.M)


def add_toc(body, p, names, bodies):
    """页顶「本节内容」目录：按译好的两层小标题生成（同英文页 clause_toc），跨续页链到中文续页。
    放在经文框与 commentary-anchor 之后；续页没有经文框，放页首。"""
    if 'ch' not in p:
        return body
    groups, n = [], 0
    for q in names:
        if q.get('src') != p.get('src') or 'ch' not in q:
            continue
        for m in RE_HEADS.finditer(bodies[q['slug']]):
            href = f'#{m.group(4)}' if q is p else f'{{{{ site.baseurl }}}}/jenkyn/jude/zh/{q["slug"]}/#{m.group(4)}'
            a = f'<a href="{href}">{m.group(2).strip("*")}</a>'
            if m.group(3) == 'part':
                groups.append([a, []])
            else:
                if not groups:
                    groups.append([None, []])
                groups[-1][1].append(a)
                n += 1
    if n < 2:
        return body
    toc = ['<nav class="jk-ctoc"><span class="jk-ctoc-h">本节内容</span>']
    for head, items in groups:
        if head:
            toc.append(f'<div class="jk-ctoc-part">{head}</div>')
        if items:
            toc.append('<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>')
    toc.append('</nav>')
    last = None
    for last in re.finditer(r'<div class="commentary-anchor"[^>]*></div>', body):
        pass
    k = last.end() if last else 0
    return body[:k] + ('\n\n' if k else '') + ''.join(toc) + '\n\n' + body[k:].lstrip('\n')


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    pages = json.loads(PAGES.read_text(encoding='utf-8'))
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    names = [p for p in pages if p['slug'] in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True,
                         check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)

    bodies = {p['slug']: clean((ZH_RAW / f'{p["slug"]}.md').read_text(encoding='utf-8')) for p in names}
    for k, p in enumerate(names):
        slug = p['slug']
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: jenkyn-chapter', 'book_id: jude',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{label(p)}"',
              f'subtitle: "{subtitle(p)}"', f'date: {date}']
        if 'ch' in p:
            fm += [f'chapter: {p["ch"]}', f'verse_from: {p["v1"]}', f'verse_to: {p["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/jenkyn/jude/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/jenkyn/jude/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/jenkyn/jude/{slug}/"', 'zh: true', '---']
        body = add_toc(bodies[slug], p, names, bodies)
        body = sect_names.annotate(body, (EN / f'{slug}.md').read_text(encoding='utf-8'), 'jk-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 章目录页 + 章内导航数据（只列已译的正文页）
    nav = {}
    secs = [p for p in names if 'ch' in p]
    if secs:
        for p in secs:
            if p.get('cont') or p.get('src') == '8-ii':
                continue
            for v in range(p['v1'], p['v2'] + 1):
                nav.setdefault('1', []).append({'v': v, 'slug': p['slug']})
        lst = '\n'.join(f'<li><a href="{{{{ site.baseurl }}}}/jenkyn/jude/zh/{p["slug"]}/">'
                        f'{label(p)}</a></li>' for p in secs)
        fm = ['---', 'layout: jenkyn-chapter', 'book_id: jude', f'book_name: "{BOOK_NAME_ZH}"',
              'title: "犹大书"', f'subtitle: "{AUTHOR_EN}"',
              f'date: {meta.get(secs[-1]["slug"], now)}', 'chapter: 1',
              'en_url: "/jenkyn/jude/1/"', 'zh: true', '---']
        (OUT / '1.md').write_text('\n'.join(fm) + f'\n\n<ul class="jk-chtoc">\n{lst}\n</ul>\n',
                                  encoding='utf-8')
    (ROOT / '_data' / 'jenkyn_jude_zh.json').write_text(
        json.dumps(nav, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(names, pages), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_jenkyn_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(names)}/{len(pages)} 篇 → {OUT}')


def build_index(names, pages):
    out = ['---', 'layout: jenkyn-book', 'book_id: jude', f'book_name: "{BOOK_NAME_ZH}"',
           f'author: "{AUTHOR_ZH}（William Jenkyn，1613–1685）"',
           'edition: "An Exposition of the Epistle of Jude · 伦敦，第一部分 1652，第二部分 1654"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/jenkyn/jude/en/"', 'zh: true', '---', '']

    def group(name, pred):
        lst = [p for p in names if pred(p)]
        if lst:
            out.append(f'<h2 class="jk-group">{name}</h2>')
            out.append('<ul class="jk-toc">')
            out.extend(f'  <li><a href="{{{{ site.baseurl }}}}/jenkyn/jude/zh/{p["slug"]}/">{label(p)}</a></li>'
                       for p in lst)
            out.append('</ul>')

    group('第一部分（1652）卷首', lambda p: p['group'] == 'front1')
    group('第一部分：第 1–8 节', lambda p: p.get('part') == 1 and not p.get('cont'))
    group('第二部分（1654）卷首', lambda p: p['group'] == 'front2')
    group('第二部分：第 8–25 节', lambda p: p.get('part') == 2 and not p.get('cont'))
    group('勘误', lambda p: p['group'] == 'tail')
    out.append(f'<p class="jk-note-zh">中译已上线 {len(names)} / {len(pages)} 篇，逐篇推进；未译的篇见'
               '<a href="{{ site.baseurl }}/jenkyn/jude/en/">英文版</a>。</p>')
    out.append(TEXT_NOTE)
    return '\n'.join(out) + '\n'


# 底本文字上的改动（英文版首页「About this text」有全文，这里只列读者会撞见的一条）
TEXT_NOTE = ('<p class="jk-note-zh"><b>底本改字说明。</b>原书缺大号 W 字模，以两个 V 拼成「VV」顶替'
             '（全书 19 处，多在段首大字与斜体词），本站一律作 W，如 <i>VVE have finished</i> 作 '
             '<i>WE have finished</i>、<i>VVhat</i> 作 <i>What</i>。这是印刷字形，不是拼法，与长 ſ 作 s 同理；'
             '其余拼法、斜体照原书。详见<a href="{{ site.baseurl }}/jenkyn/jude/en/">英文版首页</a>文本说明。</p>')


if __name__ == '__main__':
    main()
