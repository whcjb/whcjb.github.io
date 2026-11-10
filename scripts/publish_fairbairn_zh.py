#!/usr/bin/env python3
"""fairbairn_raw/pastoral/zh_chapters/<卷>/*.md → fairbairn/<卷>/zh/*.md（中文版），外加中文书首页 zh/index.html。

    python3 scripts/publish_fairbairn_zh.py

骨架照搬 publish_candlish_zh.py。与英文版共用 fairbairn-chapter / fairbairn-book 两个 layout，靠 `zh: true` 切换
（中文页才挂经文引用弹层，layout 里已接）。目前只有提前目录（含全书共用的序言、导论、附录）。
- 上下篇导航只在已译的篇之间串；date 取 zh_meta.json 里该篇实际译完的时刻。
- 跑完回调 publish_fairbairn_en.py --apply（英文页、英文书首页挂 zh_url），再重建「历代解经」数据
  （书首页 zh/index.html 存在 → 历代解经入口自动指中文）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sect_names   # noqa: E402  教派/主义名程序兜底括注原名

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'fairbairn_raw' / 'pastoral'
WORK_ZH = '费尔贝恩《教牧书信》'
BOOKS = {'1timothy': ('提摩太前书', 6), 'titus': ('提多书', 3), '2timothy': ('提摩太后书', 4)}
AUTHOR_EN = 'Patrick Fairbairn'
CN = '〇一二三四五六七八九'

TITLE0 = {'preface': ('序言', ''),
         'introduction-1': ('导论　第一节', '书信的作者'),
         'introduction-2': ('导论　第二节', '写作的时间与地点'),
         'introduction-3': ('导论　第三节', '提摩太生平'),
         'introduction-4': ('导论　第四节', '提多生平'),
         'text': ('提摩太前书：原文与译文', ''),
         'appendix-a': ('附录 A', '福音时代的特别见证（提摩太前书 2:6）'),
         'appendix-b': ('附录 B', '论「作一个妇人的丈夫」一语的意义（提摩太前书 3:2、12；提多书 1:6）'),
         'appendix-c': ('附录 C', '新约圣经对奴隶制的处理（提摩太前书 6:2；提多书 2:10）')}


def slugs_of(book):
    n = BOOKS[book][1]
    return ((['preface'] + [f'introduction-{k}' for k in range(1, 5)] if book == '1timothy' else []) + ['text']
            + [str(c) for c in range(1, n + 1)] + ([f'appendix-{L}' for L in 'abc'] if book == '1timothy' else []))


def titles(book):
    name = BOOKS[book][0]
    t = {k: v for k, v in TITLE0.items() if not k.startswith(('preface', 'introduction', 'appendix')) or book == '1timothy'}
    t['text'] = (f'{name}：原文与译文', '')
    for c in range(1, BOOKS[book][1] + 1):
        t[str(c)] = (f'{name} 第{CN[c]}章', '')
    return t

ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def clean(body: str) -> str:
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)                       # 空斜体
    body = re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', body)              # 页面是 HTML 段落，星号转回 <em>
    body = ORIG_NAME.sub(r'<span class="fb-orig">（\1）</span>', body)
    return body.strip()


def existing_date(path: Path):
    if not path.exists():
        return None
    m = re.search(r'^date:\s*(.+)$', path.read_text(encoding='utf-8')[:800], re.M)
    return m.group(1).strip() if m else None


def publish_book(book, now):
    name = BOOKS[book][0]
    ZH_RAW = RAW / 'zh_chapters' / book
    EN = ROOT / 'fairbairn' / book
    OUT = EN / 'zh'
    SL, TITLE = slugs_of(book), titles(book)
    label = lambda x: TITLE[x][0]
    done = [x for x in SL if (ZH_RAW / f'{x}.md').exists()]
    if not done:
        return 0
    meta = {}
    for mf in (RAW / 'zh_meta.json', RAW / f'zh_meta_{book}.json'):    # 两卷并行时各记一个文件
        if mf.exists():
            meta.update(json.loads(mf.read_text(encoding='utf-8')))
    OUT.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(done):
        path = OUT / f'{s}.md'
        date = meta.get(f'{book}/{s}') or existing_date(path) or now
        t, sub = TITLE[s]
        fm = ['---', 'layout: fairbairn-chapter', f'book_id: {book}', f'book_name: "{WORK_ZH} · {name}"',
              f'title: "{t}"', f'subtitle: "{(sub + " · ") if sub else ""}{AUTHOR_EN}"', f'date: {date}']
        if s.isdigit():
            fm.append(f'chapter: {s}')
        if k > 0:
            fm += [f'prev_url: "/fairbairn/{book}/zh/{done[k - 1]}/"', f'prev_label: "{label(done[k - 1])}"']
        if k + 1 < len(done):
            fm += [f'next_url: "/fairbairn/{book}/zh/{done[k + 1]}/"', f'next_label: "{label(done[k + 1])}"']
        fm += [f'en_url: "/fairbairn/{book}/{s}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{s}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (EN / f'{s}.md').read_text(encoding='utf-8'), 'fb-orig')
        path.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
    (OUT / 'index.html').write_text(build_index(book, done, SL, TITLE), encoding='utf-8')
    print(f'发布中文 {name} {len(done)}/{len(SL)} 篇 → {OUT}')
    return len(done)


def main():
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True, check=True).stdout.strip()
    if not sum(publish_book(b, now) for b in BOOKS):
        sys.exit('zh_chapters 里没有任何已译的篇')
    for cmd in (['publish_fairbairn_en.py', '--apply'], ['build_commentaries_index.py']):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd[0]), *cmd[1:]], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            print(f'⚠️ {cmd[0]} 失败：' + r.stderr[-300:], file=sys.stderr)


def build_index(book, done, SL, TITLE):
    name = BOOKS[book][0]
    label = lambda x: TITLE[x][0]
    li = lambda s: (f'  <li><a href="{{{{ site.baseurl }}}}/fairbairn/{book}/zh/{s}/">{label(s)}'
                    + (f'<span class="fb-ref">{TITLE[s][1]}</span>' if TITLE[s][1] else '') + '</a></li>')
    out = ['---', 'layout: fairbairn-book', f'book_id: {book}', f'book_name: "{WORK_ZH}"',
           f'title: "{WORK_ZH} · {name}"', 'author: "帕特里克·费尔贝恩（Patrick Fairbairn，1805–1874）"',
           'edition: "The Pastoral Epistles: The Greek Text and Translation, with Introduction, Expository Notes, '
           'and Dissertations · 爱丁堡，1874"', f'en_url: "/fairbairn/{book}/"', 'zh: true', '---', '']
    n = BOOKS[book][1]
    groups = [('序言与导论', ['preface'] + [f'introduction-{k}' for k in range(1, 5)], 'fb-toc'),
              (f'{name}原文与译文', ['text'], 'fb-toc'),
              (f'{name}逐章注释', [str(c) for c in range(1, n + 1)], 'fb-chgrid'),
              ('附录', [f'appendix-{L}' for L in 'abc'], 'fb-toc')]
    for h, ss, cls in groups:
        ss = [s for s in ss if s in done]
        if ss:
            out += [f'<h2 class="fb-group">{h}</h2>', f'<ul class="{cls}">'] + [li(s) for s in ss] + ['</ul>']
    if book != '1timothy':
        out.append('<p class="fb-note-zh">全书序言、导论四节与附录 A–C 见'
                   '<a href="{{ site.baseurl }}/fairbairn/1timothy/zh/">提摩太前书中文目录</a>。</p>')
    if len(done) < len(SL):
        out.append(f'<p class="fb-note-zh">中译已上线 {len(done)} / {len(SL)} 篇，逐篇推进；未译的篇见'
                   f'<a href="{{{{ site.baseurl }}}}/fairbairn/{book}/">英文版</a>。</p>')
    out.append(f'<p class="fb-note-zh">底本说明见<a href="{{{{ site.baseurl }}}}/fairbairn/{book}/">英文版书首页</a>。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main()
