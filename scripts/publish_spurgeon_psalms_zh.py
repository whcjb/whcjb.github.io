#!/usr/bin/env python3
"""司布真《大卫的宝库》中文版发布：spurgeon_raw/psalms/zh_chapters/<页>.md → spurgeon/psalms/zh/<页>.md

zh_chapters 由 scripts/translate_spurgeon_psalms.py 生成（斜体是 *…*，节标题已按表译）。本脚本：
  - *…* 转回 <em>（页面是 HTML 段落，kramdown 不处理块内 markdown）；
  - 前言：date 取 zh_meta.json（每篇真正译完的时刻）；上一篇 / 下一篇只链已有中文页的；
  - 中文目录 spurgeon/psalms/zh/index.html：照英文目录的结构，已译的指中文页，未译的虚线格指英文页；
  - 给已译篇的英文页、英文目录补 zh_url（版式据此显示「中文版 →」）。
跑完再跑 build_commentaries_index.py，「历代解经」入口即改指中文目录。

用法：python3 scripts/publish_spurgeon_psalms_zh.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate_spurgeon_psalms import all_slugs   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'spurgeon_raw' / 'psalms'
SRC = RAW / 'zh_chapters'
EN = ROOT / 'spurgeon' / 'psalms'
OUT = EN / 'zh'
META = RAW / 'zh_meta.json'


def em(t: str) -> str:
    """标签外的 *…* → <em>…</em>。"""
    parts = re.split(r'(<[^<>]+>)', t)
    return ''.join(p if p.startswith('<') else re.sub(r'\*([^*\n]+?)\*', r'<em>\1</em>', p) for p in parts)


def fix_stray(slug: str, body: str) -> str:
    """模型偶尔把斜体星号对错，em() 之后剩单个 `*` 露在页面上。逐段对英文：英文那段本来没有字面星号的，
    才删中文里落单的星号（英文页全书有 26 处字面星号，如注号，不能一律删）。"""
    en = (EN / f'{slug}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1]
    en_blocks = [b.strip() for b in en.split('\n\n') if b.strip()]
    zh_blocks = body.split('\n\n')
    if len(en_blocks) != len(zh_blocks):
        print(f'  ⚠ {slug}: 中英块数不等（{len(en_blocks)}/{len(zh_blocks)}），不修星号', file=sys.stderr)
        return body
    n = 0
    for i, (e, z) in enumerate(zip(en_blocks, zh_blocks)):
        if '*' in re.sub(r'<[^<>]+>', '', e):
            continue
        parts = re.split(r'(<[^<>]+>)', z)
        k = sum(p.count('*') for p in parts if not p.startswith('<'))
        if k:
            zh_blocks[i] = ''.join(p if p.startswith('<') else p.replace('*', '') for p in parts)
            n += k
    if n:
        print(f'  {slug}: 去掉落单星号 {n} 个', file=sys.stderr)
    return '\n\n'.join(zh_blocks)


def label(slug: str) -> str:
    if slug == 'preface':
        return '序'
    if slug.startswith('119/'):
        a, b = slug.split('/')[1].split('-')
        return f'诗篇 119 篇 {a}–{b} 节'
    return f'诗篇 {slug} 篇'


def set_fm(path: Path, key: str, val: str) -> None:
    """在 front matter 里加 / 改一行 key: "val"（幂等）。"""
    t = path.read_text(encoding='utf-8')
    head, sep, rest = t.partition('\n---\n')
    line = f'{key}: "{val}"'
    if re.search(rf'^{key}:', head, re.M):
        head = re.sub(rf'^{key}:.*$', line, head, flags=re.M)
    else:
        head += '\n' + line
    new = head + sep + rest
    if new != t:
        path.write_text(new, encoding='utf-8')


def toc_zh(have: set) -> str:
    """英文目录的 <ul>/<h2> 部分照搬，改链接与标签。"""
    t = (EN / 'index.html').read_text(encoding='utf-8').split('\n---\n', 1)[1]
    t = t.split('<div class="td-note">')[0].strip()

    def link(m):
        slug, text = m.group(1).strip('/'), m.group(2)
        text = {'Preface': '序', 'Whole Psalm': '全篇'}.get(text, text)
        if slug in have:
            return f'<a href="{{{{ site.baseurl }}}}/spurgeon/psalms/zh/{slug}/">{text}</a>'
        return (f'<a class="td-en-only" href="{{{{ site.baseurl }}}}/spurgeon/psalms/{slug}/" '
                f'title="暂只有英文">{text}</a>')
    t = re.sub(r'<a href="\{\{ site\.baseurl \}\}/spurgeon/psalms/([^"]*)">([^<]*)</a>', link, t)
    t = t.replace('<h2 class="td-group">Psalms</h2>', '<h2 class="td-group">诗篇</h2>')
    t = re.sub(r'<h2 class="td-group">Psalm 119 <small>[^<]*</small></h2>',
               '<h2 class="td-group">诗篇 119 篇 <small>（每八节一段）</small></h2>', t)
    return t


def main():
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    order = all_slugs()
    have = [s for s in order if (SRC / f'{s}.md').exists()]
    for s in have:
        body = fix_stray(s, em((SRC / f'{s}.md').read_text(encoding='utf-8')).strip())
        i = order.index(s)
        prev = next((x for x in reversed(order[:i]) if x in have), None)
        nxt = next((x for x in order[i + 1:] if x in have), None)
        fm = ['---', 'layout: spurgeon-psalms-chapter', 'book_id: psalms', 'book_name: "大卫的宝库"',
              f'title: "{label(s)}"', f'date: {meta[s]}', 'zh: true', f'en_url: "/spurgeon/psalms/{s}/"']
        if prev:
            fm += [f'prev_url: "/spurgeon/psalms/zh/{prev}/"', f'prev_label: "{label(prev)}"']
        if nxt:
            fm += [f'next_url: "/spurgeon/psalms/zh/{nxt}/"', f'next_label: "{label(nxt)}"']
        fm.append('---')
        dst = OUT / f'{s}.md'
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text('\n'.join(fm) + '\n\n' + body + '\n', encoding='utf-8')
        set_fm(EN / f'{s}.md', 'zh_url', f'/spurgeon/psalms/zh/{s}/')
    hs = set(have)
    n_num = sum(1 for s in have if s.isdigit())
    idx = ['---', 'layout: spurgeon-psalms-book', 'book_id: psalms', 'book_name: "大卫的宝库"',
           'author: "司布真（Charles Haddon Spurgeon，1834–1892）"', 'edition: "七卷，伦敦，1869–1885"',
           'title: "司布真《大卫的宝库》"', 'zh: true', 'en_url: "/spurgeon/psalms/"', '---', '',
           toc_zh(hs), '',
           '<div class="td-note">',
           f'<p>中译逐篇推进中，已译 {n_num} 篇；深色格子已有中译，虚线格暂只有英文。'
           '每篇含司布真本人的「释经」、他汇集的历代注释与古人语录（「解经札记与警句」），以及「给乡村传道人的提示」。'
           '经文照和合本；所引作者首次出现括注英文原名。底本说明见<a href="{{ site.baseurl }}/spurgeon/psalms/">英文版首页</a>。</p>',
           '</div>', '']
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'index.html').write_text('\n'.join(idx), encoding='utf-8')
    set_fm(EN / 'index.html', 'zh_url', '/spurgeon/psalms/zh/')
    print(f'✓ 中文 {len(have)} 页：{", ".join(have)}', file=sys.stderr)


if __name__ == '__main__':
    main()
