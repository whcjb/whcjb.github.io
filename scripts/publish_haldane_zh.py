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
ORDER = ['preface', 'introduction'] + [str(c) for c in range(1, 17)] + ['conclusion']
NAME = {'preface': '序言', 'introduction': '导论', 'conclusion': '结语'}
GK = re.compile(r'(?<![\w">])([\u0370-\u03ff\u1f00-\u1fff](?:[\u0370-\u03ff\u1f00-\u1fff’᾽ ,.…]*[\u0370-\u03ff\u1f00-\u1fff])?)')


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


def short(slug):
    return NAME.get(slug) or f'第{cn(int(slug))}章'


def title(slug, body=''):
    # 英文页题照 AGES：第 1 章页题是 EXPOSITION（CHAPTER 1 在其下）；中文译文是按新版式译的（正文里有「第一章」
    # 那行 hd-h-ch）才同样用「释义」，旧版译文仍题「第一章」
    if slug == '1' and 'hd-h-ch' in body:
        return '释义'
    return NAME.get(slug) or f'第{cn(int(slug))}章'


def clean(body):
    body = '\n\n'.join(open_lead_em(p) for p in body.split('\n\n'))
    body = GK.sub(r'<span class="hd-gk">\1</span>', body)      # 希腊文蓝色（同英文页 AGES 版式）
    body = re.sub(r'(?<!\*)\*\*(?!\*)', '', body)
    body = ORIG_NAME.sub(r'<span class="hd-orig">（\1）</span>', body)
    return body.strip()


def main():
    done = [s for s in ORDER if (ZH_RAW / f'{s}.md').exists()]
    if not done:
        sys.exit('zh_chapters 里没有任何已译的页')
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    OUT.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(done):
        raw = (ZH_RAW / f'{s}.md').read_text(encoding='utf-8')
        fm = ['---', 'layout: haldane-chapter', 'book_id: romans', 'book_name: "霍尔丹《罗马书释义》"',
              f'title: "{title(s, raw)}"', f'date: {meta.get(s, now)}']
        if s.isdigit():
            fm.append(f'chapter: {s}')
        if k > 0:
            fm += [f'prev_url: "/haldane/romans/zh/{done[k - 1]}/"', f'prev_label: "{short(done[k - 1])}"']
        if k + 1 < len(done):
            fm += [f'next_url: "/haldane/romans/zh/{done[k + 1]}/"', f'next_label: "{short(done[k + 1])}"']
        fm += [f'en_url: "/haldane/romans/{s}/"', 'zh: true', '---']
        body = clean(raw)
        body = sect_names.annotate(body, (EN / f'{s}.md').read_text(encoding='utf-8'), 'hd-orig')
        (OUT / f'{s}.md').write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')

    small = {'preface': 'Preface', 'introduction': 'Introduction', 'conclusion': 'Conclusion'}

    def tile(s, wide=False):
        cls = 'hd-tile' + (' hd-tile-wide' if wide else '')
        big = NAME.get(s) or s
        lab = small.get(s, 'Chapter')
        if s in done:
            return f'  <a class="{cls}" href="{{{{ site.baseurl }}}}/haldane/romans/zh/{s}/"><span>{lab}</span>{big}</a>'
        return (f'  <a class="{cls} hd-tile-pending" title="尚未翻译，点开为英文" '
                f'href="{{{{ site.baseurl }}}}/haldane/romans/{s}/"><span>{lab} · 英文</span>{big}</a>')
    idx = ['---', 'layout: haldane-book', 'book_id: romans', 'book_name: "霍尔丹《罗马书释义》"',
           'title: "霍尔丹《罗马书释义》"', 'sub: "罗伯特·霍尔丹（Robert Haldane）· 1764–1842 · 爱丁堡"',
           'en_url: "/haldane/romans/"', 'zh: true', '---', '',
           '<div class="hd-wide2">', tile('preface', True), tile('introduction', True), '</div>', '<div class="hd-tgrid">']
    idx += [tile(str(c)) for c in range(1, 17)]
    idx += ['</div>', '<div class="hd-wide2">', tile('conclusion', True), '</div>', '',
            '<details class="hd-about"><summary>底本说明</summary>',
            f'<p>中译已上线 {len(done)} / {len(ORDER)} 页；虚线格尚未翻译，点开为英文。</p>',
            '<p>英文底本与版式据 AGES 数字图书馆版（字色、小型大写、对齐照原样），跨页分段以 1874 年第九版核对；'
            '详见<a href="{{ site.baseurl }}/haldane/romans/">英文版书首页</a>的 About this edition。</p>',
            '</details>', '']
    (OUT / 'index.html').write_text('\n'.join(idx), encoding='utf-8')
    for cmd in ('publish_haldane_en.py', 'build_commentaries_index.py'):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / cmd)], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            print(f'⚠️ {cmd} 失败：' + r.stderr[-300:], file=sys.stderr)
    print(f'发布中文 {len(done)}/{len(ORDER)} 页 → {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
