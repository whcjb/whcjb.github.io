#!/usr/bin/env python3
"""福特《路加福音讲义》注区里含希腊/希伯来文的脚注（2026-11-12 用户令「放进书里」）。

前面三层把含希腊文的注都挡在外面待同意：
  · notes_greek_pending.tsv：注区整页看图答 B（转录与印面一致）、含希腊文的 26 页——整页 NOTE 块换成转录各条；
  · notes_missing_greek.tsv：整页丢失、含希腊文的 7 页——按页序插进注区（该页已有注的不插）；
  · hand_greek_leak_fixes.tsv：卷进正文、含希腊文的 4 处（12/60/118/123 讲），人工看图核定，删出正文、插回注区。

希腊字形：转录本给活字补了重音，印面大多只有送气符（偶有长音符）。每段希腊文先找同页看图第二读
（foote_greek_read.py，不给提示、照印面读）里字母相同的一段，用它的写法；找不到的去掉锐音、钝音符。

    python3 scripts/foote_greek_notes.py --rules     # 在链条里它的位置上（notes_leak 之后）出表 → greek_notes_fixes.tsv
    python3 scripts/foote_greek_notes.py --apply
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_greek_read as G  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_check as N  # noqa: E402
import foote_notes_missing as M  # noqa: E402

RAW = A.RAW
RULES = RAW / 'greek_notes_fixes.tsv'
HAND = RAW / 'hand_greek_leak_fixes.tsv'
LOG = A.ROOT / 'logs' / 'foote_greek_notes.tsv'
GR = re.compile(r"[Ͱ-Ͽἀ-῿᾿῾ʼʽ’'][Ͱ-Ͽἀ-῿᾿῾\s,.;:·’'ʼʽ\-]*[Ͱ-Ͽἀ-῿]|[Ͱ-Ͽἀ-῿]")


def second_reads():
    out = {}
    for f in G.ANS.glob('v*/*.json'):
        d = json.loads(f.read_text(encoding='utf-8'))
        p = d['page']
        out[(p['vol'], p['leaf'])] = [m.group(1).strip() for m in re.finditer(r'⟦(.*?)⟧', d['raw'])]
    return out


def drop_acute(t):
    t = unicodedata.normalize('NFD', t)
    return unicodedata.normalize('NFC', ''.join(c for c in t if c not in '̀́̀́'))


def greekify(text, reads, stat):
    def sub(m):
        g = m.group()
        for x in reads:
            if '[?]' not in x and G.bare(x) == G.bare(g):
                stat['用第二读'] += 1
                return re.sub(r'(?<=\w)-(?=\w)', '', x.strip(' .,;:'))
        stat['去锐钝音'] += 1
        return drop_acute(g)
    return GR.sub(sub, text)


def entries(vol, leaf, page, reads, stat):
    vn = N.vlm_notes(vol, leaf)
    return '\n\n'.join(f"<!-- NOTE p.{page} --> {N.SYM.get(s, s)} {greekify(t, reads, stat)}".rstrip() for s, t in vn)


def rules():
    sr = second_reads()
    rows, out, stat = [], [], Counter()
    texts = {}
    for r in list(csv.reader(open(RAW / 'notes_greek_pending.tsv', encoding='utf-8'), delimiter='\t'))[1:]:
        lec, page, vol, leaf, ours = r[0], r[1], int(r[2]), int(r[3]), r[4]
        text = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        _, bl = N.note_blocks(int(lec), text)
        if page not in bl:          # 只认页：该页转录已看图答 B；块内字可能已被希腊文层改过
            rows.append(('无此页块', lec, page))
            continue
        s, e, _ = bl[page]
        old = text[s:e]
        new = entries(vol, leaf, page, sr.get((vol, leaf), []), stat) + A.FN_MARK * old.count(A.FN_MARK)
        if text.count(old) != 1:
            rows.append(('not-unique', lec, page))
            continue
        texts[lec] = text.replace(old, new)
        out.append((lec, old, new))
        rows.append(('换', lec, page))
    for r in list(csv.reader(open(RAW / 'notes_missing_greek.tsv', encoding='utf-8'), delimiter='\t'))[1:]:
        lec, page, vol, leaf, v = r[0], r[1], int(r[2]), int(r[3]), r[4]
        if '[?]' in v:
            rows.append(('转录读不出', lec, page))
            continue
        text = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if page in M.NOTE.findall(text):
            rows.append(('该页已有注', lec, page))
            continue
        o, n = M.insert_row(text, page, entries(vol, leaf, page, sr.get((vol, leaf), []), stat))
        if text.count(o) != 1:
            rows.append(('not-unique', lec, page))
            continue
        texts[lec] = text.replace(o, n)
        out.append((lec, o, n))
        rows.append(('插', lec, page))
    with open(LOG, 'w', encoding='utf-8', newline='') as fh:
        csv.writer(fh, delimiter='\t').writerows(rows)
    RULES.write_text('# lecture\t原串\t改作 —— foote_greek_notes.py 生成（含希腊文的脚注：转录各条，希腊字形取看图第二读；2026-11-12 用户同意）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(dict(Counter(r[0] for r in rows)), dict(stat), f'规则 {len(out)} → {RULES}', file=sys.stderr)


# 卷进正文、含希腊文的 4 处：(讲, 卷, 叶, 卷入串左界, 右界, 正文改作) —— 左界起、右界止的那截换成改作。
# 注文按页图读定（转录在希腊词上带 [?]，用看图第二读；12 讲印面就是 συκοφοντησητε；60 讲注下还有一行
# Horace 引文，转录漏了，原注区那条读花了，一并按图改）。2026-11-12
GREEK_LEAKS = [
    ('012', 1, 180, 'sent, more ♦', 'ftilly to instruct', 'sent, more fully to instruct'),
    ('060', 2, 298, 'is brought to ♦', 'elegance. your very door', 'is brought to your very door'),
    ('118', 3, 395, 'title of some\n\n<!-- PAGE 391 -->', 'an al- of the kings', 'title of some of the kings'),
    ('123', 3, 463, 'and almost\n\n<!-- PAGE 459 -->', '^kmcU invariably obtain', 'and almost invariably obtain'),
]
GREEK_NOTES = {
    '012': '<!-- NOTE p.176 --> ♦ μηδε συκοφοντησητε.\n\n<!-- NOTE p.176 --> † Matt. viii. 5; Acts x.',
    '118': '<!-- NOTE p.391 --> ♦ It is possible that our Lord may have used this one Greek word, ᾿Ευεργετης, though he was '
           'not speaking in Greek; or, he may have used one corresponding to it, and in allusion to it; or, there may be an al-',
    '123': '<!-- NOTE p.459 --> ♦ Ps. xxxv. 15.\n\n<!-- NOTE p.459 --> † The word ῥαπισμα seems to have come to signify a blow '
           'of any kind.',
}
HORACE = ('060', '<!-- NOTE p.294 --> Nil oritunim alias, nil ortum tale *fsiicntxi,—Horace,*,',
          '<!-- NOTE p.294 --> ♦ A greater, πλειον, something greater than Solomon, and a greater than Jonas. Classic authors '
          'frequently use the neuter gender in this way, when speaking of persons; and this is reckoned an elegance.\n\n'
          '<!-- NOTE p.294 --> Nil oriturum alias, nil ortum tale fatentes.—*Horace.*')


def hand_rules():
    import foote_notes_leak as L
    cases = []
    for lec, vol, leaf, a, b, new in GREEK_LEAKS:
        t = (A.SRC / f'{lec}.md').read_text(encoding='utf-8')
        i = t.find(a)
        j = t.find(b, i)
        if i < 0 or j < 0 or t.count(a) != 1:
            raise SystemExit(f'{lec}: 界定位失败')
        cases.append((lec, vol, leaf, t[i:j + len(b)], new))
    L.hand_rules(cases, path=HAND, note_text=GREEK_NOTES)
    lec, o, n = HORACE
    with open(HAND, 'a', encoding='utf-8') as fh:
        fh.write('\t'.join(x.replace('\n', '\\n') for x in (lec, o, n)) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--hand-rules', action='store_true')
    a = ap.parse_args()
    if a.hand_rules:
        hand_rules()
    elif a.rules:
        rules()
    elif a.apply:
        for t in (RULES, HAND):
            if t.exists():
                I.apply_multiline(t)


if __name__ == '__main__':
    main()
