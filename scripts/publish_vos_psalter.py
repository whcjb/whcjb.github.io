#!/usr/bin/env python3
"""Vos, "Eschatology of the Psalter" 英文页发布：extract.json + corrections.tsv → vos/psalter/index.md

链条：scripts/vos_psalter_extract.py → 本脚本。重跑两次产物须逐字节不变。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'vos_raw' / 'psalter'
OUT = ROOT / 'vos' / 'psalter' / 'index.md'
DATE = '2026-11-10 10:02'      # 英文本校定完成时刻；重跑不改


def load_corrections():
    rows = []
    for ln in (RAW / 'corrections.tsv').read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        page, find, repl, why = ln.split('\t')
        rows.append((page, find, repl, why))
    return rows


def main():
    d = json.loads((RAW / 'extract.json').read_text(encoding='utf-8'))
    paras = [p['text'] for p in d['paras']]
    notes = {int(k): v for k, v in d['notes'].items()}

    # 改正：每条在正文+脚注里必须恰好一处
    bad = []
    corr = load_corrections()
    for page, find, repl, why in corr:
        hits = [('p', i) for i, t in enumerate(paras) if find in t] + \
               [('n', k) for k, t in notes.items() if find in t]
        cnt = sum(paras[i].count(find) for k_, i in hits if k_ == 'p') + \
            sum(notes[k].count(find) for k_, k in hits if k_ == 'n')
        if cnt != 1:
            bad.append(f'p{page} 命中 {cnt} 处: {find}')
            continue
        kind, idx = hits[0]
        if kind == 'p':
            paras[idx] = paras[idx].replace(find, repl)
        else:
            notes[idx] = notes[idx].replace(find, repl)
    if bad:
        sys.exit('改正表定位失败：\n  ' + '\n  '.join(bad))

    def tidy(t):
        t = re.sub(r'\*\s+\*', ' ', t)                 # 跨行的两段斜体并成一段
        return t

    paras = [tidy(t) for t in paras]
    # 录入本把篇末署名「Princeton. / GEERHARDUS VOS.」录成两段正文；署名由下面的 .vs-sign 照原刊版式排，这里去掉
    while paras and re.fullmatch(r'(⟦p\d+⟧)?\s*(Princeton\.|GEERHARDUS VOS\.)\s*', paras[-1]):
        paras.pop()
    notes = {k: tidy(v) for k, v in notes.items()}

    left = [t for t in paras + list(notes.values()) if '⟪heb:' in t]
    if left:
        sys.exit(f'还有 {len(left)} 处希伯来字体乱码未解码')

    # 注号与注文一一对应
    refs = [int(x) for x in re.findall(r'\[\^(\d+)\]', ' '.join(paras))]
    if refs != sorted(notes) or refs != list(range(1, len(notes) + 1)):
        sys.exit(f'注号不连续或与注文不符：{refs}')

    def pb(t):
        t = re.sub(r'(⟦p\d+⟧)([,.;:!?’”"\']+)', r'\2\1', t)    # 标记挪到紧跟的标点之后，免得「词 p.2 ,」
        return re.sub(r'⟦p(\d+)⟧', r'<span class="vs-pb" id="p\1" data-p="\1"></span>', t)

    def he(t):                                         # 希伯来文包一层，给字体和方向
        return re.sub(r'([֐-׿][֐-׿ְ-ׇ]*)', r'<span class="vs-he" lang="he" dir="rtl">\1</span>', t)

    out = ['---',
           'layout: vos-essay',
           'title: "Eschatology of the Psalter"',
           'subtitle: "Geerhardus Vos · The Princeton Theological Review 18 (1920): 1–43"',
           'author_en: "Geerhardus Vos"',
           'description: "Geerhardus Vos, Eschatology of the Psalter (Princeton Theological Review, January 1920). Full text with footnotes, collated against the original printing."',
           f'date: {DATE}',
           *(['zh_url: /vos/psalter/zh/'] if (ROOT / 'vos' / 'psalter' / 'zh' / 'index.md').exists() else []),
           '---',
           '']
    out.append('<div class="vs-source" markdown="0">'
               'Text: Ted Hildebrandt’s transcription (biblicalelearning.org), collated word by word against the '
               'original printing in <i>The Princeton Theological Review</i> 18 (Jan. 1920) 1–43 '
               f'(Internet Archive <code>princetontheolog1811arms</code>); {len(corr)} transcription slips corrected from the page images. '
               'Misprints of the original are kept as printed. Grey <span class="vs-pbk">p.N</span> marks give the 1920 pagination.'
               '</div>')
    out.append('')
    for t in paras:
        out.append(he(pb(t)))
        out.append('')
    out.append('<p class="vs-sign"><i>Princeton.</i><span>Geerhardus Vos.</span></p>')   # 原刊：斜体地名 + 小型大写署名
    out.append('')
    for k in sorted(notes):
        out.append(f'[^{k}]: {he(notes[k])}')
    out.append('')
    text = '\n'.join(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = OUT.read_text(encoding='utf-8') if OUT.exists() else None
    OUT.write_text(text, encoding='utf-8')
    print(f'{"未变" if old == text else "已写"} {OUT.relative_to(ROOT)}  段 {len(paras)}  注 {len(notes)}')


if __name__ == '__main__':
    main()
