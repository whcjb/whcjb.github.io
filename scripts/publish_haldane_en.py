#!/usr/bin/env python3
"""霍尔丹《罗马书释义》英文版发布：haldane_raw/romans/units.json → haldane/romans/*.md + index.html

链条：extract_haldane_ages.py（AGES PDF → units.json）→ 本脚本 → build_commentaries_index.py。
发布时刻记在 en_meta.json，首次写入后不改。

**版式照 AGES**（用户 2026-11-18：「格式全部按照 ages，包括字体颜色，对齐等」）：
- 卷首 PREFACE / INTRODUCTION、卷末 CONCLUSION 各一页；正文一章一页。
- 页题用普通「Romans N / Preface …」；AGES 的章题照印在正文（同贺智）：EXPOSITION（第 1 章）、CHAPTER N（PART 2 前
  AGES 重印的也照印）蓝色大字居中；PART N. 绿色居中；ROMANS a:b-c 黑粗居中
  （AGES 在哪条前印，就在哪条前出）；章首概述不加标签。
- 每条：「**Ver. N.** —」+ 经文（AGES 原样的红 / 黑字色）。写法照 pdf-pipeline / hodge 产物：红斜体
  `<span style="color:#800000">*X*</span>`、黑斜体 `*X*`、粗体 `**X**`、藏青 / 希腊文 / 小型大写用行内 style；
  标题 `<p class="title-block-h1|h2" style="text-align:center…" markdown="1">`；居中 / 缩进段 `<p style=… markdown="1">`；
  段落起始页变了插 `<!-- PAGE N -->`（Gate 5g / 13）。左对齐。
- 每条注释前放 commentary-anchor（id romans-章-节）；没单独讲的经节挂到讲它的那一条（向前找最近的一条）。
- 正文写成 markdown 段落（内含行内 HTML），脚注 [^fN] 由 kramdown 渲染，定义放该页末尾。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'haldane_raw' / 'romans'
OUT = ROOT / 'haldane' / 'romans'
META = RAW / 'en_meta.json'
BASE = '/haldane/romans'
NV = [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27]   # 罗马书各章节数
ORDER = ['preface', 'introduction'] + [str(c) for c in range(1, 17)] + ['conclusion']
LABEL = {'preface': 'Preface', 'introduction': 'Introduction', 'conclusion': 'Conclusion'}


def now():
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()


def label(slug):
    return LABEL.get(slug, f'Romans {slug}')


def md_para(t: str, align: str = '') -> list:
    """段落 → markdown 行。对齐照 AGES：居中 / 缩进 / 卷末 THE END 用行内样式 <p … markdown="1">（Gate 5b）。"""
    t = re.sub(r'^(\d+)\. ', r'\1\\. ', t)          # 段首「1. 」别被 kramdown 当有序列表
    t = re.sub(r'^([#>+\-]) ', r'\\\1 ', t)
    if align == 'center':
        return [f'<p style="text-align:center" markdown="1">{t}</p>', '']
    if align == 'indent':
        return [f'<p style="margin-left:1.5em" markdown="1">{t}</p>', '']
    if align == 'center-end':
        return [f'<p style="text-align:center; color:#006411; font-size:20px; margin-top:26px;" markdown="1">{t}</p>', '']
    return [t, '']


def head_html(h):
    """AGES 居中标题：PREFACE / INTRODUCTION / EXPOSITION / CHAPTER N / CONCLUSION 蓝 24pt、PART N. 绿 16pt、
    ROMANS a:b-c 黑粗 12pt。"""
    if h.startswith('CHAPTER') or h in ('PREFACE', 'INTRODUCTION', 'EXPOSITION', 'CONCLUSION'):
        return (f'<p class="title-block-h1" style="text-align:center; color:#0000d4; font-size:30px; '
                f'margin:22px 0 6px;" markdown="1">{h}</p>')
    if h.upper().startswith('PART'):
        return (f'<p class="title-block-h2" style="text-align:center; color:#006411; font-size:22px; '
                f'margin:20px 0 10px;" markdown="1">{h}</p>')
    return (f'<p class="title-block-h2" style="text-align:center; font-size:16px; font-weight:bold; '
            f'margin:6px 0 18px;" markdown="1">{h}</p>')


class Pager:
    """页码标记 <!-- PAGE N -->：段落起始页变了就在段前插一行（Gate 5g / 13）。"""
    def __init__(self):
        self.last = None

    def mark(self, page):
        if page and page != self.last:
            self.last = page
            return [f'<!-- PAGE {page} -->', '']
        return []


def span(e):
    m = re.fullmatch(r'verses?-(\d+)(?:-(\d+))?', e['key'])
    return (int(m.group(1)), int(m.group(2) or m.group(1))) if m else None


def chapter_md(c):
    ch = c['ch']
    out, covered, notes_here, pg = [], set(), [], Pager()
    ves = [e for e in c['entries'] if span(e)]
    owner = {}
    for v in range(1, NV[ch - 1] + 1):
        cand = [e for e in ves if span(e)[0] <= v <= span(e)[1]] or [e for e in ves if span(e)[0] <= v][-1:] or ves[:1]
        owner.setdefault(id(cand[0]), []).append(v)
    if ch == 1:                                            # AGES：EXPOSITION 在 CHAPTER 1 之上
        out += [head_html('EXPOSITION'), '']
    for e in c['entries']:
        refs = re.findall(r'\[\^f(\d+)\]', ' '.join(e['paras'] + [e['lemma']]))
        notes_here += [r for r in refs if r not in notes_here]
        for h in e.get('heads', []):
            out += [head_html(h), '']                      # 章题照 AGES 印在正文（同贺智：页题另用普通「Romans N」）
        for v in owner.get(id(e), []):
            out.append(f'<div class="commentary-anchor" id="romans-{ch}-{v}"></div>')
            covered.add(v)
        if span(e):
            out += [''] + pg.mark(e.get('lemma_page')) + [f'**{e["ver"]}** — {e["lemma"]}', '{: .hd-lemma}', '']
        mids = {i: hs for i, hs in e.get('mid_heads', [])}
        for i, (p, al) in enumerate(zip(e['paras'], e['align'])):
            for h in mids.get(i, []):
                out += [head_html(h), '']
            out += pg.mark(e['pages'][i]) + md_para(p, al)
    return out, notes_here, covered


def page_md(lines, notes_here, defs):
    for r in notes_here:
        lines.append(f'[^f{r}]: {defs[r]}')
    return '\n'.join(lines).rstrip() + '\n'


def main():
    u = json.loads((RAW / 'units.json').read_text(encoding='utf-8'))
    defs = u['notes']
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    stamp = now()
    OUT.mkdir(parents=True, exist_ok=True)
    pages, bad = {}, []
    for f in u['front'] + u['back']:
        lines, pg = [head_html(f['key'].upper()), ''], Pager()
        for p, al, pn in zip(f['paras'], f['align'], f['pages']):
            lines += pg.mark(pn) + md_para(p, al)
        refs = []
        for p in f['paras']:
            refs += [r for r in re.findall(r'\[\^f(\d+)\]', p) if r not in refs]
        pages[f['key']] = page_md(lines, refs, defs)
    for c in u['chapters']:
        lines, refs, covered = chapter_md(c)
        miss = set(range(1, NV[c['ch'] - 1] + 1)) - covered
        if miss:
            bad.append((c['ch'], sorted(miss)))
        pages[str(c['ch'])] = page_md(lines, refs, defs)
    if bad:
        sys.exit(f'有经节没有锚点：{bad}')
    for i, slug in enumerate(ORDER):
        meta.setdefault(slug, stamp)
        title = label(slug)                               # 页题用普通「Romans N」；AGES 的章题印在正文（同贺智）
        fm = ['---', 'layout: haldane-chapter', 'book_id: romans', 'book_name: "Haldane on Romans"',
              f'title: "{title}"', f'date: {meta[slug]}']
        if slug.isdigit():
            fm.append(f'chapter: {slug}')
        if i:
            fm += [f'prev_url: "{BASE}/{ORDER[i - 1]}/"', f'prev_label: "{label(ORDER[i - 1])}"']
        if i + 1 < len(ORDER):
            fm += [f'next_url: "{BASE}/{ORDER[i + 1]}/"', f'next_label: "{label(ORDER[i + 1])}"']
        if (OUT / 'zh' / f'{slug}.md').exists():
            fm.append(f'zh_url: "{BASE}/zh/{slug}/"')
        fm.append('---')
        (OUT / f'{slug}.md').write_text('\n'.join(fm) + '\n\n' + pages[slug], encoding='utf-8')
    (OUT / 'index.html').write_text(index_html(u), encoding='utf-8')
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    n_e = sum(len(c['entries']) for c in u['chapters'])
    print(f'写入 {len(ORDER)} 页 + 书首页 → {OUT.relative_to(ROOT)}；条目 {n_e}；经节锚点 433/433；脚注 {len(defs)} 条')


def index_html(u):
    fixes = u.get('ver_fixes', [])
    out = ['---', 'layout: haldane-book', 'book_id: romans', 'book_name: "Haldane on Romans"',
           'title: "Robert Haldane · Exposition of the Epistle to the Romans"', 'author: "Robert Haldane (1764–1842)"',
           'edition: "Exposition of the Epistle to the Romans, with Remarks on the Commentaries of Dr. Macknight, '
           'Professor Moses Stuart, and Professor Tholuck · first published 1835–1839"',
           *(['zh_url: "/haldane/romans/zh/"'] if (OUT / 'zh' / 'index.html').exists() else []), '---', '',
           '<ul class="hd-chgrid hd-wide">',
           f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/preface/">Preface</a></li>',
           f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/introduction/">Introduction</a></li>',
           '</ul>', '<h2 class="hd-group">Exposition</h2>', '<ul class="hd-chgrid">']
    out += [f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/{c}/">Romans {c}</a></li>' for c in range(1, 17)]
    out += ['</ul>', '<ul class="hd-chgrid hd-wide">',
            f'  <li><a href="{{{{ site.baseurl }}}}{BASE}/conclusion/">Conclusion</a></li>', '</ul>', '',
            '<div class="hd-note">',
            '<p><b>About this edition.</b> The text and its typography (colours, small capitals, alignment) follow the '
            'AGES Digital Library edition (AGES Software, 1998; <code>HAL_ROMA.PDF</code>). Paragraph breaks that the AGES '
            'typesetting lost in the later chapters are restored from the BibleSupport.com transcription, which descends '
            'from the same electronic text. The modern foreword printed in the AGES edition is not reproduced.</p>',
            '<p>Not in the AGES edition and not yet given here: the two dissertations added to the later editions, '
            '“The State of the Heathen World Destitute of the Gospel” (with “The Case of Cornelius”) and “The Sanctification '
            'of the Sabbath”, and the Appendix (letter to the Rev. Edward Bickersteth; remarks on Mr. Stuart, Dr. Macknight '
            'and Mr. Tholuck), pp. 653–702 and 713–730 of the ninth edition (Edinburgh, 1874).</p>',
            '<p>Editorial corrections: Greek words, which the AGES edition gives in its own transliteration code, are '
            'given in Greek type; '
            + ('; '.join(f'Romans {x}' for x in fixes) + '; ' if fixes else '')
            + ''.join(f'Romans {x}; ' for x in u.get('ed_fixes', []))
            + 'Romans 5:18 δικαιώματος (AGES omits the μ).</p>',
            '</div>', '']
    return '\n'.join(out)


if __name__ == '__main__':
    main()
