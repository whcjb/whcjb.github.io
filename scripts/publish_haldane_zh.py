#!/usr/bin/env python3
"""haldane_raw/romans/zh_chapters/<章>.md → haldane/romans/zh/<章>.md（中文版）+ zh/index.html（中文书首页）。

与英文版共用 haldane-chapter / haldane-book 两个 layout，靠 `zh: true` 切换（中文页挂经文引用弹层，layout 里已接）。
上下章导航只在已译的章之间串；date 取 zh_meta.json 里该章实际译完的时刻。
跑完回调 publish_haldane_en.py（英文页挂 zh_url）与 build_commentaries_index.py（历代解经入口有中文就指中文）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sect_names   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'haldane_raw' / 'romans'
ZH_RAW = RAW / 'zh_chapters'
EN = ROOT / 'haldane' / 'romans'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'
CN = '〇一二三四五六七八九'
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


def cn(n):
    if n < 10:
        return CN[n]
    t, u = divmod(n, 10)
    return ('' if t == 1 else CN[t]) + '十' + (CN[u] if u else '')


def open_lead_em(p):
    """段首引句只有孤立 </em>（录入本 <i> 跨段，见 publish_haldane_en.md_para）→ 补开标签。
    模型偶尔把 </em> 挪到「——」后面去（12 章「这里的“</em>世界”」），那就收在「——」处。"""
    i, j = p.find('</em>'), p.find('<em>')
    if i < 0 or (0 <= j < i):
        return p
    k = p.find('——')
    if 0 <= k and k + 2 < i:
        return '<em>' + p[:k + 2] + '</em>' + p[k + 2:i] + p[i + 5:]
    return '<em>' + p


def clean(body):
    body = '\n\n'.join(open_lead_em(p) for p in body.split('\n\n'))
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = ORIG_NAME.sub(r'<span class="hd-orig">（\1）</span>', body)
    return body.strip()


def main():
    done = sorted(int(p.stem) for p in ZH_RAW.glob('*.md') if p.stem.isdigit())
    if not done:
        sys.exit('zh_chapters 里没有任何已译的章')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, ch in enumerate(done):
        fm = ['---', 'layout: haldane-chapter', 'book_id: romans', 'book_name: "霍尔丹《罗马书释义》"',
              f'title: "罗马书 第{cn(ch)}章"', 'subtitle: "Robert Haldane"', f'date: {meta.get(str(ch), now)}',
              f'chapter: {ch}']
        if k > 0:
            fm += [f'prev_url: "/haldane/romans/zh/{done[k - 1]}/"', f'prev_label: "第{cn(done[k - 1])}章"']
        if k + 1 < len(done):
            fm += [f'next_url: "/haldane/romans/zh/{done[k + 1]}/"', f'next_label: "第{cn(done[k + 1])}章"']
        fm += [f'en_url: "/haldane/romans/{ch}/"', 'zh: true', '---']
        body = clean((ZH_RAW / f'{ch}.md').read_text(encoding='utf-8'))
        body = sect_names.annotate(body, (EN / f'{ch}.md').read_text(encoding='utf-8'), 'hd-orig')
        (OUT / f'{ch}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
    idx = ['---', 'layout: haldane-book', 'book_id: romans', 'book_name: "霍尔丹《罗马书释义》"',
           'title: "霍尔丹《罗马书释义》"', 'author: "罗伯特·霍尔丹（Robert Haldane，1764–1842）"',
           'edition: "Exposition of the Epistle to the Romans · 1835–1839"', 'en_url: "/haldane/romans/"', 'zh: true', '---', '',
           '<h2 class="hd-group">逐章释义</h2>', '<ul class="hd-chgrid">']
    idx += [f'  <li><a href="{{{{ site.baseurl }}}}/haldane/romans/zh/{c}/">罗马书 第{cn(c)}章</a></li>' if c in done
            else f'  <li><a class="hd-other" href="{{{{ site.baseurl }}}}/haldane/romans/{c}/">Romans {c}<small>英文</small></a></li>'
            for c in range(1, 17)]
    idx += ['</ul>', '', f'<p class="hd-note-zh">中译已上线 {len(done)} / 16 章；未译的章暂只有英文。底本说明（含录入本缺的序言、导论、'
            '书末专论与附录、七条脚注正文）见<a href="{{ site.baseurl }}/haldane/romans/">英文版书首页</a>。</p>', '']
    (OUT / 'index.html').write_text('\n'.join(idx), encoding='utf-8')
    for cmd in ('publish_haldane_en.py', 'build_commentaries_index.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print(f'⚠️ {cmd} 失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(done)}/16 章 → {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
