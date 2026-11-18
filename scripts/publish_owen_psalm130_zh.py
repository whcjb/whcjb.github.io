#!/usr/bin/env python3
"""owen_raw/psalm130/zh_chapters/<页>.md → owen/psalm130/zh/<页>.md（中文版）+ zh/index.html（中文书首页）。

与英文版共用 owen-psalm130-chapter / owen-psalm130-book 两个 layout，靠 `zh: true` 切换（中文页挂经文引用弹层，layout 里已接）。
页名、组名取 owen_raw/psalm130/titles_zh.tsv；上下页导航只在已译的页之间串；date 取 zh_meta.json 里该页实际译完的时刻。
跑完回调 publish_owen_psalm130_en.py（英文页挂 zh_url）与 build_commentaries_index.py（历代解经入口有中文就指中文）。
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sect_names   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'owen_raw' / 'psalm130'
ZH_RAW = RAW / 'zh_chapters'
EN = ROOT / 'owen' / 'psalm130'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'
BASE = '/owen/psalm130'
ORDER = ['prefatory-note', 'to-the-reader'] + [str(n) for n in range(1, 40)]
BOOK = '欧文《诗篇 130 篇实践讲解》'
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def load_titles():
    pages, groups = {}, {}
    for line in (RAW / 'titles_zh.tsv').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        r = line.split('\t')
        if r[0] == 'GROUP':
            groups[r[1]] = r[2]
        else:
            pages[r[0]] = r[1]
    return pages, groups


def fm_value(text, key):
    m = re.search(rf'^{key}: "?(.*?)"?$', text, re.M)
    return m.group(1).strip() if m else None


def main():
    done = [s for s in ORDER if (ZH_RAW / f'{s}.md').exists()]
    if not done:
        sys.exit('zh_chapters 里没有任何已译的页')
    titles, groups = load_titles()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(done):
        en = (EN / f'{s}.md').read_text(encoding='utf-8')
        sub = fm_value(en, 'subtitle')
        fm = ['---', 'layout: owen-psalm130-chapter', 'book_id: psalm130', f'book_name: "{BOOK}"',
              f'title: "{titles[s]}"'] + ([f'subtitle: "{groups[sub]}"'] if sub else []) + [f'date: {meta.get(s, now)}']
        if k > 0:
            fm += [f'prev_url: "{BASE}/zh/{done[k - 1]}/"', f'prev_label: "{titles[done[k - 1]]}"']
        if k + 1 < len(done):
            fm += [f'next_url: "{BASE}/zh/{done[k + 1]}/"', f'next_label: "{titles[done[k + 1]]}"']
        fm += [f'en_url: "{BASE}/{s}/"', 'zh: true', '---']
        body = (ZH_RAW / f'{s}.md').read_text(encoding='utf-8').strip()
        body = ORIG_NAME.sub(r'<span class="op-orig">（\1）</span>', body)
        body = sect_names.annotate(body, en, 'op-orig')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    # 中文书首页：目录照英文首页的分组（已译的指中文，未译的标「英文」指英文页）
    en_idx = (EN / 'index.html').read_text(encoding='utf-8')
    toc = []
    for line in en_idx.splitlines():
        m = re.match(r'<h2 class="op-group">(.*)</h2>$', line)
        if m:
            toc.append(f'<h2 class="op-group">{groups[html.unescape(m.group(1))]}</h2>')
            continue
        m = re.match(r'\s*<li><a href="\{\{ site\.baseurl \}\}' + re.escape(BASE) + r'/([^/]+)/">(.*)</a></li>$', line)
        if m:
            s = m.group(1)
            if s in done:
                toc.append(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/zh/{s}/">{titles[s]}</a></li>')
            else:
                toc.append(f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{s}/">{m.group(2)} <small>英文</small></a></li>')
            continue
        if line.strip() in ('<ul class="op-toc">', '</ul>'):
            toc.append(line)
    idx = ['---', 'layout: owen-psalm130-book', 'book_id: psalm130', f'book_name: "诗篇 130 篇实践讲解"',
           'author: "约翰·欧文（John Owen，1616–1683）"',
           'edition: "A Practical Exposition upon Psalm CXXX · 1668 年初版；据 Goold 编《欧文全集》第 6 卷"',
           f'title: "{BOOK}"', f'en_url: "{BASE}/"', 'zh: true', '---', ''] + toc + [
        '', '<div class="op-note">',
        f'<p class="op-note-zh"><b>文本说明。</b>中译已上线 {len(done)} / {len(ORDER)} 页{"" if len(done) == len(ORDER) else "；未译的页暂只有英文"}。'
        '英文底本是 CCEL（基督教经典电子图书馆）录入本，所据为 Goold 编《欧文全集》第 6 卷；斜体、脚注照该本。'
        '经文照和合本；欧文自己的直译按他的字面译出。书名页、出版许可与 CCEL 所附索引未收。</p>',
        '</div>', '']
    (OUT / 'index.html').write_text('\n'.join(idx), encoding='utf-8')

    for cmd in ('publish_owen_psalm130_en.py', 'build_commentaries_index.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f'{cmd} 失败：{r.stderr[-400:]}')
    print(f'中文 {len(done)} 页已写出')


if __name__ == '__main__':
    main()
