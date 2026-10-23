#!/usr/bin/env python3
"""莱尔《马太福音释义》英文版发布：ryle_raw/matthew/sections.json + kjv_1857.json → ryle/matthew/

    python3 scripts/publish_ryle_en.py            # 试跑
    python3 scripts/publish_ryle_en.py --apply

一章一页 ryle/matthew/<章>.md（历代解经扫描器与对照抽屉都按章号页找书），章内按原书分段：
段首 MATTHEW I. 1—17. → 双栏经文框（1857 原书版式）→ 每节一个 commentary-anchor → 释义 → 本段脚注。
另出序言页 preface.md 与书首页 index.html（目录、文本说明、出处勘误表）。
date 沿用 en_meta.json 里的原值，新页才写当前真实时间。
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ryle_apply import REF_ERRATA, roman  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
OUT = ROOT / 'ryle' / 'matthew'
META = RAW / 'en_meta.json'
BOOK_NAME = 'Expository Thoughts on Matthew'
AUTHOR = 'J. C. Ryle'
EDITION = 'Expository Thoughts on the Gospels, for Family and Private Use · St. Matthew · New York: Robert Carter, 1857'


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def sc(text):
    """⟪THESE⟫ → 首字母大写 + 其余小型大写（原书段首词、钦定本的 LORD）。"""
    return re.sub(r'⟪([A-Z]+)⟫', lambda m: f'<span class="ry-sc">{m.group(1)[0]}{m.group(1)[1:].lower()}</span>', text)


def esc_md(p):
    """段首「1. 」不让 kramdown 当成列表（原书是正文段落）。"""
    return re.sub(r'^(\d+)\. ', r'\1\\. ', p)


def section_html(s, kjv, fn_base):
    ch, v1, v2 = s['ch'], s['v1'], s['v2']
    out = [f'<h2 class="ry-sechead" id="{ch}-{v1}">MATTHEW {roman(ch).upper()}. {v1}—{v2}.</h2>', '',
           '<div class="ry-text" markdown="1">', '']
    for v in range(v1, v2 + 1):
        out.append(f'<p class="ry-v" markdown="1"><span class="ry-vn">{v}</span> {sc(kjv[f"{ch}:{v}"])}</p>')
    out += ['', '</div>', '']
    out += [f'<div class="commentary-anchor" id="matthew-{ch}-{v}"></div>' for v in range(v1, v2 + 1)]
    out.append('')
    notes = iter(range(len(s['notes'])))
    for p in s['paras']:
        p = re.sub('⟦fn⟧', lambda m: f'[^{fn_base + next(notes) + 1}]', p)
        out += [esc_md(sc(p)), '']
    for i, n in enumerate(s['notes']):
        body = '\n\n'.join('    ' + esc_md(sc(x)) if j else esc_md(sc(x)) for j, x in enumerate(n.split('\n\n')))
        out += [f'[^{fn_base + i + 1}]: {body}', '']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = json.loads((RAW / 'sections.json').read_text(encoding='utf-8'))
    kjv = json.loads((RAW / 'kjv_1857.json').read_text(encoding='utf-8'))
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    secs = d['sections']
    chs = sorted({s['ch'] for s in secs})
    pages = {}
    for ch in chs:
        body, fn = [], 0
        for s in [x for x in secs if x['ch'] == ch]:
            body += section_html(s, kjv, fn)
            fn += len(s['notes'])
        slug = str(ch)
        meta.setdefault(slug, stamp)
        nv = max(int(k.split(':')[1]) for k in kjv if k.startswith(f'{ch}:'))
        fm = ['---', 'layout: ryle-chapter', 'book_id: matthew', f'book_name: "{BOOK_NAME}"',
              f'title: "Matthew {ch}"', f'subtitle: "Expository Thoughts · {AUTHOR}"', f'date: {meta[slug]}',
              f'chapter: {ch}', 'verse_from: 1', f'verse_to: {nv}',
              f'prev_url: "/ryle/matthew/{ch - 1 if ch > 1 else "preface"}/"',
              f'prev_label: "{"Matthew " + str(ch - 1) if ch > 1 else "Preface"}"']
        if ch < chs[-1]:
            fm += [f'next_url: "/ryle/matthew/{ch + 1}/"', f'next_label: "Matthew {ch + 1}"']
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "/ryle/matthew/zh/{slug}/"')
        fm.append('---')
        pages[f'{slug}.md'] = '\n'.join(fm) + '\n\n' + '\n'.join(body).rstrip() + '\n'

    meta.setdefault('preface', stamp)
    pre = [sc(p) for p in d['preface']]
    sig = pre[-3:]                       # J. C. RYLE. / Helmingham Rectory, / December, 1856.
    pages['preface.md'] = '\n'.join([
        '---', 'layout: ryle-chapter', 'book_id: matthew', f'book_name: "{BOOK_NAME}"', 'title: "Preface"',
        f'subtitle: "{AUTHOR} · Helmingham, December 1856"', f'date: {meta["preface"]}',
        'next_url: "/ryle/matthew/1/"', 'next_label: "Matthew 1"', '---', '']) + '\n' + \
        '\n\n'.join(esc_md(p) for p in pre[:-3]) + '\n\n<p class="ry-closer" markdown="1">' + \
        '<br>'.join(sig) + '</p>\n'

    pages['index.html'] = index_page(secs)
    if a.apply:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, text in pages.items():
            (OUT / name).write_text(text, encoding='utf-8')
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{"写入" if a.apply else "试跑"} {len(pages)} 页（{len(chs)} 章 + 序言 + 书首页），'
          f'{len(secs)} 段，脚注 {sum(len(s["notes"]) for s in secs)}')


def index_page(secs):
    out = ['---', 'layout: ryle-book', 'book_id: matthew', f'book_name: "{BOOK_NAME}"', f'title: "{BOOK_NAME}"',
           f'author: "{AUTHOR} (1816–1900)"', f'edition: "{EDITION}"', '---', '',
           '<h2 class="ry-group">Preface</h2>',
           '<ul class="ry-toc"><li><a href="{{ site.baseurl }}/ryle/matthew/preface/">Preface'
           '<small>Helmingham Rectory, December 1856</small></a></li></ul>',
           '<h2 class="ry-group">Chapters</h2>', '<ul class="ry-chgrid">']
    for ch in sorted({s['ch'] for s in secs}):
        out.append(f'<li><a href="{{{{ site.baseurl }}}}/ryle/matthew/{ch}/">Matthew {ch}</a></li>')
    out += ['</ul>', '<h2 class="ry-group">Expositions</h2>', '<ul class="ry-toc">']
    for s in secs:
        out.append(f'<li><a href="{{{{ site.baseurl }}}}/ryle/matthew/{s["ch"]}/#{s["ch"]}-{s["v1"]}">'
                   f'Matthew {s["ch"]}:{s["v1"]}–{s["v2"]}</a></li>')
    out.append('</ul>')
    rows = ''.join(f'<tr><td><a href="{{{{ site.baseurl }}}}/ryle/matthew/{sec.split(":")[0]}/#{sec.replace(":", "-")}">'
                   f'{sec}</a></td><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(w)}</td></tr>'
                   for sec, a, b, w in REF_ERRATA)
    out += [
        '<div class="ry-note">',
        '<p><b>About this text.</b> The text follows the first American edition (New York: Robert Carter, 1857; '
        'the preface is dated Helmingham Rectory, December 1856), with the text of St. Matthew printed before each '
        'exposition as in the original. It was prepared from the e-Sword module of 2009 (a keyed text with the '
        'original wording and italics) collated word by word against the Internet Archive scan of the 1857 volume. '
        'Where the module departs from the 1857 page, the 1857 reading is restored after inspection of the page image: '
        'modernised quotations of Scripture, altered words and word order, Americanised spellings '
        '(Saviour, fulfil, fulness, offence, marvellous and the like), the omitted “St.”, and references in the '
        'original form (roman chapter numbers). The Scripture text of the boxes is the King James Version as printed '
        'in the 1857 volume, which in a few places differs from the Oxford text (laborers, honor, cloak, often …).</p>',
        '<p class="ry-note-zh"><b>文本说明。</b>本书依 1857 年纽约 Robert Carter 首个美国版（序言落款 1856 年 12 月，'
        'Helmingham 教区），每段前照原书排出马太福音经文。底本为 2009 年 e-Sword 模块（人工录入，措辞与斜体保留原书），'
        '与 Internet Archive 所藏 1857 年版扫描件逐词对齐：凡模块与原书不同之处，逐处看原书影像后照原书回改——'
        '包括被改成现代译本的引经、改过的词与词序、被美式化的拼写（Saviour、fulfil、fulness、offence、marvellous 等）、'
        '被删去的「St.」，以及出处的原书写法（章号用罗马数字）。经文框是 1857 年版所印的钦定本，'
        '个别拼写与牛津本不同（laborers、honor、cloak、often 等），照原书。原书显系误植之处（如 Due Veil、'
        '「is this world」）沿用录入本的改正；出处误植见下表。</p>',
        f'<h3 class="ry-errhead">出处勘误（{len(REF_ERRATA)} 处）</h3>',
        '<p class="ry-note-zh">以下出处 1857 年原书印错（引文按钦定本核过），正文沿用录入本已改正的章节。</p>',
        '<table class="ry-errtab"><tr><th>位置</th><th>1857 原印</th><th>现作</th><th>依据</th></tr>' + rows + '</table>',
        '</div>', '']
    return '\n'.join(out)


if __name__ == '__main__':
    main()
