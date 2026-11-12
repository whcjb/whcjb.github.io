#!/usr/bin/env python3
"""福特《路加福音讲义》讲题下的经文出处行（`**LUKE XXn. 47-^3.**`）读花的 28 讲（2026-11-12）。

两个来源互证才改：publish_foote_en.VERSES（各讲经文范围，按连续性定、四讲以经文段末节号核过）与
整页转录（看图读的）里同书同章的出处行逐字相合。写法照转录（印本 `LUKE XXIII. 44, 45.` 用逗号的照录）。

    python3 scripts/foote_heads.py --rules    # → heads_fixes.tsv
    python3 scripts/foote_heads.py --hand-rules   # → hand_bullet_fixes.tsv（同在链条末段出表）
    python3 scripts/foote_heads.py --apply    # 链条末段（foote_junk_check --apply --late 之后）

另附：注号读成 `•` 的页脚注卷进正文 4 处（notes_leak 只认 ♦ 起头，漏了这几处）——删出正文、该页注区没有的按转录补；
第 41 讲正文夹着书帖记号 `• VOL. II.`（印本页脚的折帖号），删去并接回 `number`。2026-11-12 转录逐条核过。
"""
import argparse
import glob
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_junk_check as J  # noqa: E402
import foote_vlm_adjudicate as V  # noqa: E402
from publish_foote_en import VERSES  # noqa: E402

RULES = A.RAW / 'heads_fixes.tsv'
HAND = A.RAW / 'hand_bullet_fixes.tsv'
# (讲, 卷, 叶, 正文卷入串, 改作)：叶为转录所在叶（注条取它的 [FN:] 行）
BULLETS = [
    ('017', 1, 249, 'where he had • Doddridge, *in, locum.* been', 'where he had been'),
    ('035', 1, 500, 'I told you, • John iv. 25. f John viii. 12; 24. and', 'I told you, and'),
    ('051', 2, 165, 'kingdom of • Acts Yi. 1^. God,', 'kingdom of God,'),
    ('121', 3, 442, 'content with • Henry. their wages."', 'content with their wages."'),
]
SIGNATURE = ('041', 'without num • VOL. n. ber:"', 'without number:"')
ROM = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI',
       'XVII', 'XVIII', 'XIX', 'XX', 'XXI', 'XXII', 'XXIII', 'XXIV']
HEAD = re.compile(r'^\*\*LUKE [^\n]*\*\*$', re.M)


def rules():
    seen = set()
    for f in glob.glob(str(V.VLM / 'v*' / '*.txt')):
        seen |= {m.group() for m in re.finditer(r'LUKE [IVXL]+\. \d+(?:[-–]|, )\d+\.', Path(f).read_text(encoding='utf-8'))}
    out = []
    for lec in range(1, 138):
        t = (A.SRC / f'{lec:03d}.md').read_text(encoding='utf-8')
        m = HEAD.search(t)
        if not m or not (J.BAD.search(m.group()) or re.search(r'[a-z]', m.group()[6:])):
            continue
        c, r = VERSES[lec].split(':')
        a, b = r.split('-')
        hits = sorted({h.replace('–', '-') for h in seen
                       if re.fullmatch(rf'LUKE {ROM[int(c)]}\. {a}(?:-|, ){b}\.', h.replace('–', '-'))})
        if len(hits) != 1:
            print(f'{lec}: 转录无相合出处行 {hits}', file=sys.stderr)
            continue
        out.append((f'{lec:03d}', m.group(), f'**{hits[0]}**'))
    RULES.write_text('# lecture\t原串\t改作 —— foote_heads.py 生成（讲题下经文出处行：VERSES 与看图转录相合）\n'
                     + ''.join('\t'.join(r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {RULES}', file=sys.stderr)


def hand_rules():
    import foote_notes_leak as L
    L.hand_rules(BULLETS, path=HAND)
    with open(HAND, 'a', encoding='utf-8') as fh:
        fh.write('\t'.join(SIGNATURE) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--hand-rules', action='store_true')
    a = ap.parse_args()
    if a.rules:
        rules()
    elif a.hand_rules:
        hand_rules()
    elif a.apply:
        for t in (RULES, HAND):
            if t.exists():
                I.apply_multiline(t)


if __name__ == '__main__':
    main()
