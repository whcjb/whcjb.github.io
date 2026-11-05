#!/usr/bin/env python3
"""petter_raw/mark/zh_chapters/*.md → petter/mark/zh/*.md（中文版）。

    python3 scripts/publish_petter_zh.py

骨架照搬 publish_rollock_zh.py。英文版一讲一页，中文版同样：zh/<讲首节>.md、卷首 zh/<篇名>.md；
另出各章目录页 zh/<章>.md（已译的讲链中文，未译的链英文并标「英文」）。
与英文版共用 petter-chapter / petter-book 两个 layout，靠 `zh: true` 切换（中文页才挂经文引用弹层）。

- 上下篇导航**只在已译的篇之间串**（指向未译的篇等于送读者去 404）。
- date 取 zh_meta.json 里该篇**实际译完的时刻**；取不到才沿用已发布文件原值，再取不到才用当前时间。
- 书首页 /petter/mark/ 换成中文目录；英文目录（含缺字判读与编者推补逐条说明）在 /en/
  （tcp_publish 见到 zh/ 就不再覆盖首页）。
- 跑完回调 publish_petter_en.py --apply，让英文页补上「中文版 →」；再重建「历代解经」数据。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import sect_names  # noqa: E402  教派名补原名
import publish_petter_en as P  # noqa: E402

RAW = ROOT / 'petter_raw' / 'mark'
ZH_RAW = RAW / 'zh_chapters'
META = RAW / 'zh_meta.json'
EN = ROOT / 'petter' / 'mark'
OUT = EN / 'zh'
BOOK_NAME_ZH = '佩特《马可福音注释》'
AUTHOR_ZH = '乔治·佩特'
AUTHOR_EN = 'George Petter'   # 页面副标题一律写英文原名（用户 2026-10-16 定）
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
CN = '零一二三四五六七八九'
MONTH = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9,
         'oct': 10, 'nov': 11, 'dec': 12}
FRONT = {'title': ('书名页', '伦敦，1661'), 'preface': ('致敬虔读者的序', '作者之弟约翰·佩特（John Petter），1661'),
         'alphabetical-table': ('主题索引', '本注释的主要内容')}


def cn(n):
    if n < 10:
        return CN[n]
    t, u = divmod(n, 10)
    return ('' if t == 1 else CN[t]) + '十' + (CN[u] if u else '')


def preached(pg):
    """rng 里的讲道日期 'preached June 7. 1618.' → '1618 年 6 月 7 日讲'；日期残缺的不写。"""
    m = re.search(r'preached\s+([A-Za-z]+)\W+(\d{1,2})\W+(\d{4})', pg.get('rng', ''))
    if not m or m.group(1)[:3].lower() not in MONTH:
        return ''
    return f'{m.group(3)} 年 {MONTH[m.group(1)[:3].lower()]} 月 {m.group(2)} 日讲'


def short_zh(pg):
    s = pg['short'].replace(' (2nd)', '（第二讲）').replace(' (3rd)', '（第三讲）').replace(' (4th)', '（第四讲）')
    return re.sub(r' \((\d+)th\)', r'（第\1讲）', s)


def label(pg):
    if pg['group'] == 'front':
        return FRONT[pg['slug']][0]
    return f'马可福音 {short_zh(pg)}'


def subtitle(pg):
    return FRONT[pg['slug']][1] if pg['group'] == 'front' else AUTHOR_EN


RE_OL = re.compile(r'^(\d+)\. ', re.M)
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def _ref_books_re():
    src = (ROOT / '_includes' / 'scripture-popup.html').read_text(encoding='utf-8')
    a = src.index('var BOOKS = ['); b = src.index('];', a)
    names = sorted(re.findall(r"\['([^']+)',\d+\]", src[a:b]), key=len, reverse=True)
    return re.compile(r'\*([^*\n]*?)(' + '|'.join(map(re.escape, names)) + r')\*(?=\s*\d{1,3}\s*[:：]\s*\d)')


REF_BOOK_ITALIC = _ref_books_re()


def _unitalic_ref(m):
    pre = m.group(1)
    if not pre.strip():
        return m.group(2)
    core = pre.rstrip()
    return f'*{core}*{pre[len(core):]}{m.group(2)}'


# 页边纲目标签：translate_petter.MARK_ZH 没收到的少数写法（改译前的匹配会动缓存键，这里在发布时补译）
MARK_FIX = {'Instr.': '教导', 'Instruct.': '教导', '[Answ.': '答', 'Ʋs.': '应用', 'Obj': '异议', 'Resp.': '答',
            'Vers.': '第'}


def mark_fix(m):
    s = m.group(1)
    for k, v in MARK_FIX.items():
        if s.startswith(k):
            num = s[len(k):].strip()
            if k == 'Vers.':
                return f'<span class="pt-mark">第 {num} 节</span>'
            return f'<span class="pt-mark">{v}{(" " + num) if num else ""}</span>'
    return m.group(0)


def clean(body: str) -> str:
    body = re.sub(r'<span class="pt-mark">([^<]*[A-Za-zƲ][^<]*)</span>', mark_fix, body)
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = re.sub(r'<<<[^>]*>>>', '', body)
    body = REF_BOOK_ITALIC.sub(_unitalic_ref, body)
    body = RE_OL.sub(r'\1\\. ', body)
    body = re.sub(r'^(#+ .*)$', lambda m: m.group(1).replace('*', ''), body, flags=re.M)
    # 模型给页边旁注外加的括号（原书本无）
    body = re.sub(r'[（(]\s*(<span class="pt-margin[^>]*>.*?</span>)\s*[）)]', r'\1', body)
    # 段首经文框照抄和合本：英文 KJV 的斜体是「译者补字」，搬进和合本只会乱排斜体
    body = re.sub(r'(<div class="pt-text" markdown="1">)(.*?)(</div>)',
                  lambda m: m.group(1) + re.sub(r'(?<![\\<])\*', '', m.group(2)) + m.group(3), body, flags=re.S)
    body = ORIG_NAME.sub(r'<span class="pt-orig">[\1]</span>', body)
    body = re.sub(r'<span class="pt-dropcap"></span>([^\s<*])', r'<span class="pt-dropcap">\1</span>', body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:800])
    return m.group(1).strip() if m else None


def main():
    pages = P.BOOK.build_pages()
    done = {p.stem for p in ZH_RAW.glob('*.md')} if ZH_RAW.exists() else set()
    names = [pg for pg in pages if pg['slug'] in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已译的篇')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True, check=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, pg in enumerate(names):
        slug = pg['slug']
        path = OUT / f'{slug}.md'
        date = meta.get(slug) or existing_date(path) or now
        fm = ['---', 'layout: petter-chapter', 'book_id: mark', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "{label(pg)}"', f'subtitle: "{subtitle(pg)}"', f'date: {date}']
        if 'ch' in pg:
            fm += [f'chapter: {pg["ch"]}', f'verse_from: {pg["v1"]}', f'verse_to: {pg["v2"]}']
        if k > 0:
            q = names[k - 1]
            fm += [f'prev_url: "/petter/mark/zh/{q["slug"]}/"', f'prev_label: "{label(q)}"']
        if k + 1 < len(names):
            q = names[k + 1]
            fm += [f'next_url: "/petter/mark/zh/{q["slug"]}/"', f'next_label: "{label(q)}"']
        fm += [f'en_url: "/petter/mark/{slug}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{slug}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (EN / f'{slug}.md').read_text(encoding='utf-8'), 'pt-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 各章目录页：至少有一讲已译的章才出
    chs = sorted({pg['ch'] for pg in names if 'ch' in pg})
    for ch in chs:
        secs = [pg for pg in pages if pg.get('ch') == ch]
        path = OUT / f'{ch}.md'
        date = existing_date(path) or max((meta.get(pg['slug'], '') for pg in secs), default='') or now
        fm = ['---', 'layout: petter-chapter', 'book_id: mark', f'book_name: "{BOOK_NAME_ZH}"',
              f'title: "马可福音 第{cn(ch)}章"', f'subtitle: "{AUTHOR_EN}"', f'date: {date}', f'chapter: {ch}',
              'verse_from: 1', f'verse_to: {P.BOOK.NV[ch]}', f'en_url: "/petter/mark/{ch}/"', 'zh: true', '---']
        lst = []
        for pg in secs:
            d = preached(pg)
            sub = f'<small>{d}</small>' if d else ''
            if pg['slug'] in done:
                lst.append(f'<li><a href="{{{{ site.baseurl }}}}/petter/mark/zh/{pg["slug"]}/">{short_zh(pg)}{sub}</a></li>')
            else:
                lst.append(f'<li><a class="pt-other" href="{{{{ site.baseurl }}}}/petter/mark/{pg["slug"]}/">'
                           f'{short_zh(pg)}<small>英文</small></a></li>')
        path.write_text('\n'.join(fm) + '\n\n<ul class="pt-chtoc">\n' + '\n'.join(lst) + '\n</ul>\n', encoding='utf-8')

    (EN / 'index.html').write_text(build_index(pages, done, chs), encoding='utf-8')
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_petter_en.py'), '--apply'],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 英文页回调失败：' + r.stderr[-300:], file=sys.stderr)
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_commentaries_index.py')],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print('⚠️ 历代解经数据重建失败：' + r.stderr[-300:], file=sys.stderr)
    n = sum(1 for pg in names if pg['group'] == 'section')
    nl = sum(1 for pg in pages if pg['group'] == 'section')
    print(f'发布中文 {n}/{nl} 讲（另卷首 {len(names) - n} 篇）→ {OUT}')


def build_index(pages, done, chs):
    out = ['---', 'layout: petter-book', 'book_id: mark', f'book_name: "{BOOK_NAME_ZH}"',
           f'title: "{BOOK_NAME_ZH}"', f'author: "{AUTHOR_ZH}（George Petter，?–1654）"',
           'edition: "A Learned, Pious, and Practical Commentary upon the Gospel according to St. Mark · 伦敦，1661"',
           'en_url: "/petter/mark/en/"', 'zh: true', '---', '']
    front = [pg for pg in pages if pg['group'] == 'front']
    out.append('<h2 class="pt-group">卷首</h2>')
    out.append('<ul class="pt-toc">')
    for pg in front:
        if pg['slug'] in done:
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/petter/mark/zh/{pg["slug"]}/">{label(pg)}'
                       f'<small>{subtitle(pg)}</small></a></li>')
        else:
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/petter/mark/{pg["slug"]}/">{label(pg)}'
                       f'<small>英文</small></a></li>')
    out.append('</ul>')
    out.append('<h2 class="pt-group">各章</h2>')
    cells = []
    for c in range(1, 17):
        if c in chs:
            cells.append(f'<li><a href="{{{{ site.baseurl }}}}/petter/mark/zh/{c}/">第{cn(c)}章</a></li>')
        elif c in P.BOOK.NV:
            cells.append(f'<li><a class="pt-other" href="{{{{ site.baseurl }}}}/petter/mark/{c}/">'
                         f'第{cn(c)}章<small>英文</small></a></li>')
        else:
            cells.append(f'<li><span class="pt-none">第{cn(c)}章<small>原书藏本缺</small></span></li>')
    out.append('<ul class="pt-chgrid">' + ''.join(cells) + '</ul>')
    n = sum(1 for pg in pages if pg['group'] == 'section' and pg['slug'] in done)
    nl = sum(1 for pg in pages if pg['group'] == 'section')
    out.append('<div class="pt-note">')
    out.append(f'<p class="pt-note-zh">中译已上线 {n} / {nl} 讲；虚线框的章暂只有英文。原书第 12–16 章录入本所据藏本缺失，本站暂无。'
               '原书录入本里读不出的字，中文里同样标红留在明面；英文版中由编者看原书影像推补的字，'
               '中文里以无衬线字体加方括号标出，如 <span class="pt-conj">[如此]</span>。'
               '底本、缺字判读与推补逐条说明见<a href="{{ site.baseurl }}/petter/mark/en/">英文版首页</a>。</p>')
    out.append('</div>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
