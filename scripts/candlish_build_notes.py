#!/usr/bin/env python3
"""坎德利什约翰一书：e-Sword 本的脚注原样（work/notes_cc.json）→ 机械清理 → candlish_raw/1john/notes.json

    python3 scripts/candlish_build_notes.py

只做「从录入本导出损坏里还原」的机械清理，不改字：
  - e-Sword 把恰好与经卷名缩写同形的词展开成经卷名，并在后面加「 ,」：
    `Isaiah ,`→is  `Song of Solomon ,`→Son  `Hebrews ,`→he  `Prayer of Manasseh ,`→man
  - 数字与前词粘连、数字后多一个空格：`October1860 ,`→`October 1860,`；`ver24`→`ver. 24`（Monergism 正文作 `ver.`）
  - 经文引用被换成链接后残下的「 ,」：`( , 2:2)`→`(2:2)`、`of , Revelation`→`of Revelation`
  - 引用整个被吃掉、只剩 `()` 的：记号 ⟦lost⟧，发布时标出「录入本此处缺文」，不擅补
  - `Lcke`→`Lücke`（ü 在 e-Sword 本丢了；Monergism 正文作 Lücke）
e-Sword 本这几条脚注的 OCR 错字（cither / tome / lam …）**不在这里改**，见 notes_pending.tsv，经同意才落。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'candlish_raw' / '1john'

# 脚注号 → 所在讲次（units.json 里的 num / 前言标题）与 `*` 前的锚定文字（发布时按它定位）
PLACE = {
    1: ('PREFACE TO FIRST EDITION', "argument in his great Epistle."),
    2: ('PREFACE TO FIRST EDITION', "who has helped me\nmost."),
    3: ('PREFACE TO FIRST EDITION', "full sense of this epistle. "),
    4: ('VI', 'that taketh away the sin of the world."'),
    5: ('VII', 'hereby know we that we are in him."'),
    6: ('XV', 'He is not "separate from sinners."'),
    7: ('XV', 'ministry as the Christ.'),
    8: ('XVI', '1 JOHN 2:24, 25.'),
    9: ('XVI', 'Father and the Son."'),
    10: ('XVIII', 'that we are "born of God."'),
    11: ('XIX', '1 JOHN 2:29–3:2.'),
    12: ('XIX', 'in respect of our being born of God.'),
    13: ('XIX', 'whose Son he was."'),
    14: ('XXI', '"in him is no sin."'),
    15: ('XXI', 'neither known him at all.'),
    16: ('XXII', '1 JOHN 3:6 and 9.'),
    17: ('XXII', 'incapable of doing evil.'),
    18: ('XXIII', 'its very perfection.'),
    19: ('XXVII', 'God\'s glory is the conclusion."'),
    20: ('XXXIII', '"the love which God hath in us."'),
    21: ('XXXIV', '"Herein is love with us made perfect,'),
    22: ('XXXIV', '"we love, because he first loved us."'),
    23: ('XXXVI', 'paradise, before they fell.'),
    24: ('XXXVIII', 'and these three agree in one."'),
    25: ('XXXIX', '1 JOHN 5:9, 10.'),
    26: ('XLI', '1 JOHN 5:13–15.'),
    27: ('XLII', '1 JOHN 5:16, 17.'),
    28: ('XLIV', '"the wicked one toucheth you not."'),
    29: ('XLV', '[even] in his Son Jesus Christ."'),
}

ESWORD = [('Song of Solomon ,', 'Son,'), ('Isaiah ,', 'is,'), ('Hebrews ,', 'he,'),
          ('Prayer of Manasseh ,', 'man,')]


def clean(t):
    t = t.replace('" Hebrews ," "him,"', '"he," "him,"')
    for a, b in ESWORD:
        t = t.replace(' ' + a, ' ' + b)
    t = t.replace('Lcke', 'Lücke')
    t = re.sub(r'\bver(\d)', r'ver. \1', t)
    t = re.sub(r'([A-Za-z])(\d)', r'\1 \2', t)
    t = re.sub(r'(\d) ([,;.)])', r'\1\2', t)
    t = re.sub(r'\(\s*,\s*', '(', t)
    t = re.sub(r'(\d) , (\d)', r'\1, \2', t)
    t = re.sub(r'\bof , ', 'of ', t)
    t = re.sub(r'\band , ', 'and ', t)
    t = t.replace('Ephesians , where', 'Ephesians, where')
    t = t.replace('()', '(⟦lost⟧)')
    return t


def main():
    cc = json.loads((RAW / 'work' / 'notes_cc.json').read_text())
    out = []
    for n, (unit, anchor) in PLACE.items():
        r = cc.get(str(n))
        rec = dict(n=n, unit=unit, anchor=anchor)
        if r is None:
            rec['text'] = None
        else:
            t = clean(r['cc'])
            if n == 7:
                head, _, body = t.partition('\n')
                rec['head'] = 'Note referred to at page 186'
                t = body.strip()
            if n == 29 and t.endswith('.")'):
                t = t[:-1]          # 段尾多出的右括号（e-Sword 本把括注拆成独立段时残下）
            rec['text'] = t
        out.append(rec)
    (RAW / 'notes.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    for r in out:
        print(f"#{r['n']} {r['unit']}: {(r['text'] or '—缺—')[:2000]}\n")


if __name__ == '__main__':
    main()
